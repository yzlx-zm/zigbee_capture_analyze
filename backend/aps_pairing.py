"""APS Ack 配对 — 共享逻辑 (files.py 详情端点 + L3-1 检测器共用).

配对依据 (素材实证 + 官方机制, 2026-08-06):
- ack 帧携带完整 APS 头 (解密明文 8B: [FCF][dst_ep][cluster:2][profile:2][src_ep][counter])
- counter 沿用原帧 (FCF bit4 ack format=0; 第七次协调器 2B 短帧 format=1 但 counter 仍为原帧值)
- 匹配: 原帧 nwk_src == ack.nwk_dst 且 aps_counter 相同, 取 ack 前窗口内最近一帧
"""
from __future__ import annotations

from collections import defaultdict

# counter 为 8 位循环 (0-255), 长抓包同 (dst,counter) 跨周期重复;
# 实测 G32 97% 最近候选 <2s → 5s 窗内无候选视为不配对, 避免跨周期误配 (自审修正 60de1ff)
ACK_MATCH_WINDOW_S = 5.0


def build_ack_match(packets: list[dict]) -> tuple[dict, dict]:
    """APS Ack ↔ 原帧配对.

    返回 (ack_to_orig: {ack_idx: orig_idx}, orig_to_ack: {orig_idx: (ack_idx, ack_ts)}).
    索引为 packets 列表下标 (与 /api/packets/{idx} 一致).
    """
    idx: dict[tuple, list] = defaultdict(list)
    for i, p in enumerate(packets):
        s, c = p.get("nwk_src"), p.get("aps_counter")
        if c is not None and s is not None and p.get("pkt_type") != "APS Ack":
            idx[(s, c)].append((i, p))
    ack_to_orig: dict = {}
    orig_to_ack: dict = {}
    for ai, a in enumerate(packets):
        if a.get("pkt_type") != "APS Ack":
            continue
        ats = a.get("ts", 0.0)
        ctr, dst = a.get("aps_counter"), a.get("nwk_dst")
        if ctr is None or dst is None:
            continue
        cands = [(i, p) for i, p in idx.get((dst, ctr), [])
                 if ats - ACK_MATCH_WINDOW_S <= p.get("ts", 0.0) < ats]
        if not cands:
            continue
        best_i, _ = max(cands, key=lambda ip: ip[1].get("ts", 0.0))
        ack_to_orig[ai] = best_i
        # 一帧多 ack (重复捕获/重发) — 保留最近一条
        if best_i not in orig_to_ack or a.get("ts", 0.0) > orig_to_ack[best_i][1]:
            orig_to_ack[best_i] = (ai, a.get("ts", 0.0))
    return ack_to_orig, orig_to_ack


# 应用层响应窗口 (与 detectors/l3.py L31_APP_RESP_WINDOW_S 同源: 素材实测 <0.4s, SED 边界 ~1.9s)
APP_RESP_WINDOW_S = 2.0


def build_transaction_peers(packets: list[dict]) -> dict:
    """事务链 (U16-7a): ZCL 命令帧 → (ack, 同事务响应帧列表).

    ⚠️ 2026-08-25 收紧修正 (用户反馈 33 帧误配): 首版复用了 L3-1 检测器的宽松判定
    (同 tsn / 同 cluster / cluster 缺失降级任一反向帧), 密钥命令帧 (VerifyKeyConfirm,
    无 ZCL 层 cluster=None) 把 2s 窗口内全部反向帧误列 — 检测器是布尔语义 ("设备
    有没有回应"), UI 事务链需要精确语义. 修正:
      - 只对 ZCL 命令帧建链 (有 zcl_seq); APS 命令帧不建 — 其确认由 APS Ack 表达
      - 响应判定只认「同 ZCL tsn」 (事务级铁证, 素材实证: Write Attrs→Write Attrs Rsp
        / On→On 报告同 tsn), 删除 cluster 匹配与 fallback 降级
      - ack: APS Ack 配对 (build_ack_match, counter 级 + 5s 窗, 保留)

    返回 {orig_idx: {"ack": ack_idx|None, "responses": [{"id", "packet_id",
            "pkt_type", "zcl_cmd_name", "zcl_direction", "evidence"}]}}
    索引为 packets 列表下标 (与 /api/packets/{idx} 一致).
    """
    _, orig_to_ack = build_ack_match(packets)
    # S1 (2026-08-26): 索引化修复 — 原实现每 ZCL 命令帧遍历全部 packets (O(n²)),
    # 群控包 10.8 万帧点详情时事务构建卡死数分钟 (P1 性能缺陷)。
    # 响应候选按 (src, dst, tsn) 分组, 查询 O(1) 组内再过滤时间窗 —
    # 候选集合与原逻辑逐位一致 (同 tsn 反向帧), 语义不变, 线性复杂度.
    resp_cand: dict = defaultdict(list)
    for qi, q in enumerate(packets):
        if q.get("pkt_type") == "APS Ack":
            continue
        tsn = q.get("zcl_seq")
        if tsn is None:
            continue
        s, d = q.get("nwk_src"), q.get("nwk_dst")
        if s is None or d is None:
            continue
        resp_cand[(s, d, tsn)].append((qi, q))
    peers: dict = {}
    for i, p in enumerate(packets):
        # 只对 ZCL 命令帧建链 (需有事务序列号; 纯数据/报告帧/APS 命令不建)
        tsn = p.get("zcl_seq")
        if not p.get("zcl_cmd_name") or tsn is None:
            continue
        src, dst = p.get("nwk_src"), p.get("nwk_dst")
        ts0 = p.get("ts", 0.0)
        if src is None or dst is None or ts0 == 0.0:
            continue
        hi = ts0 + APP_RESP_WINDOW_S
        responses = []
        for qi, q in resp_cand.get((dst, src, tsn), []):
            # 响应候选已限定 (src,dst,tsn) 反向同 tsn; 时间窗过滤保留
            t = q.get("ts", 0.0)
            if not (ts0 < t <= hi):
                continue
            responses.append({
                "id": qi, "packet_id": q.get("packet_id"),
                "pkt_type": q.get("pkt_type"), "zcl_cmd_name": q.get("zcl_cmd_name"),
                "zcl_direction": q.get("zcl_direction"), "evidence": "tsn",
            })
        if responses or i in orig_to_ack:
            peers[i] = {"ack": (orig_to_ack[i][0] if i in orig_to_ack else None),
                        "responses": responses}
    return peers
