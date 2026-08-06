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
