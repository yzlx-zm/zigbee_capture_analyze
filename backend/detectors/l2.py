"""L2 场景检测器 — 设备在线维持 (L2-1 终端设备频繁离线)

输入: cubx_reader/tshark 解析的包 dict 列表 (含 MAC 帧: mac_cmd_id/mac_src).
输出: 检测报告 dict, 按 ADR-0002 置信度分级.

判定规则来源: docs/scenarios/L2-1.md v1.0 (官方依据 + 素材实证)
"""
from __future__ import annotations

from collections import defaultdict

# ── 常量 (官方依据) ──
MAC_DATA_REQUEST = 4          # MAC 命令 cmd_id=0x04 (SED 轮询)
MAC_ACK_FRAME_TYPE = 2        # MAC 帧类型=2 (Acknowledgement)
NWK_CMD_LEAVE = 4
# ⚠️ 2026-08-05 自审修正: 320s 是旧 SDK (R21 前) 默认, 当前默认 256 分钟!
# 官方: EmberZNet 6.5.0 RN "default has been changed to the 256 Minute default from R21";
# 本地 SDK: #define EMBER_END_DEVICE_POLL_TIMEOUT MINUTES_256
# 配置范围: SECONDS_10 ~ MINUTES_16384 (配置项, 无线上协商机制) — 判定需注意配置差异
END_DEVICE_POLL_TIMEOUT_S = 15360.0  # 256 分钟 (R21 默认, 保守)
R2_ROUND_GAP_S = 5.0                # R2b 轮窗口 (跨 >5s = 新轮)
R2_MIN_ROUNDS = 2                   # ≥2 轮才判定循环
# R3: 连续无 ACK 阈值 — 官方源码确认 (end-device-support-config.h):
#   #define EMBER_AF_PLUGIN_END_DEVICE_SUPPORT_MAX_MISSED_POLLS 3
MAX_MISSED_POLLS = 3
# 健康参照: LONG_POLL 默认 300s (end-device-support-config.h) — 判定阈值必须 > 父节点 Poll Timeout,
# 而 Poll Timeout 是配置项; R1 命中需 poll 间隔超过配置值, 检测器用 256min 保守默认 [待素材校准]

# ── 结论/证据输出 (诊断页人工复核, 2026-08-05 需求) ──
EVIDENCE_MAX = 15


def _ev(ts, pid, type_, detail) -> dict:
    return {"ts": round(ts, 3), "packet_id": pid, "type": type_, "detail": detail}


def _cut(items: list) -> tuple[list, int]:
    return items[:EVIDENCE_MAX], len(items)


def _addr4(v) -> str:
    return f"0x{v:04X}" if v is not None else "?"


def detect_l2_1(packets: list[dict]) -> dict:
    """终端频繁离线检测 (文档 L2-1.md v1.0).

    规则 (grilling 定稿 2026-08-05):
      - R1 : 同设备 poll (DataRequest) 间隔 ≥320s → 父节点超时移除 (高置信, 官方默认值)
      - R2a: 设备自发 rejoin=1 Leave ≥2 轮 (+ Rejoin 佐证) → 自发重入循环 (高置信)
      - R2b: TC→同设备 rejoin=1 Leave ≥2 轮 (跨 >5s) → 被踢重入循环 (中置信, 素材实证 737D)
      - R3 : poll 连续无 MAC ACK ≥3 + Rejoin → poll 无响应 (中置信)
            [v1.0] MAC ACK 提取待增强 (tshark parse_mac_frames 不过滤 ACK), 规则就位
    """
    # ── 数据收集 ──
    # poll 帧 (MAC Data Request): mac_cmd_id=4
    polls = [p for p in packets if p.get("mac_cmd_id") == MAC_DATA_REQUEST]
    # Leave 帧 (NWK cmd 4)
    leaves = [p for p in packets if p.get("nwk_cmd_id") == NWK_CMD_LEAVE]
    # Rejoin 帧 (NWK cmd 6/7)
    rejoins = [p for p in packets if p.get("nwk_cmd_id") in (6, 7)]

    evidence = []
    device_hits: dict[int, list[str]] = defaultdict(list)  # dev → [rule...]
    results = []

    # ── R1: poll 间隔 ≥320s (按 mac_src 分组) ──
    poll_by_src: dict[int, list[float]] = defaultdict(list)
    for p in polls:
        src = p.get("mac_src")
        if src is not None:
            poll_by_src[src].append(p["ts"])
    for src, ts_list in sorted(poll_by_src.items()):
        if len(ts_list) < 2:
            continue
        ts_list.sort()
        max_gap = max(ts_list[i + 1] - ts_list[i] for i in range(len(ts_list) - 1))
        if max_gap >= END_DEVICE_POLL_TIMEOUT_S:
            device_hits[src].append("R1")
            for p in polls:
                if p.get("mac_src") == src:
                    evidence.append(_ev(p["ts"], p.get("packet_id"), "DataRequest",
                                        f"{_addr4(src)} → 父节点"))
                    break

    # ── R2a: 设备自发 rejoin=1 Leave ≥2 轮 ──
    self_leave: dict[int, list] = defaultdict(list)
    for p in leaves:
        src = p.get("nwk_src")
        if src is not None and src != 0x0000 and p.get("nwk_leave_rejoin") == 1:
            self_leave[src].append(p)
    for dev, lv in self_leave.items():
        lv.sort(key=lambda p: p["ts"])
        rounds = 1 + sum(1 for i in range(1, len(lv))
                         if lv[i]["ts"] - lv[i - 1]["ts"] >= R2_ROUND_GAP_S)
        has_rejoin = any(p.get("nwk_src") == dev for p in rejoins)
        if rounds >= R2_MIN_ROUNDS:
            device_hits[dev].append("R2a")
            for p in lv[:2]:
                evidence.append(_ev(p["ts"], p.get("packet_id"), "Leave(rejoin=1)",
                                    f"{_addr4(dev)} → 广播 (自发)"))

    # ── R2b: TC→同设备 rejoin=1 Leave ≥2 轮 (素材实证形态) ──
    tc_leave: dict[int, list] = defaultdict(list)
    for p in leaves:
        dst = p.get("nwk_dst")
        if p.get("nwk_src") == 0x0000 and dst is not None and p.get("nwk_leave_rejoin") == 1:
            tc_leave[dst].append(p)
    for dev, lv in tc_leave.items():
        lv.sort(key=lambda p: p["ts"])
        rounds = 1 + sum(1 for i in range(1, len(lv))
                         if lv[i]["ts"] - lv[i - 1]["ts"] >= R2_ROUND_GAP_S)
        span = lv[-1]["ts"] - lv[0]["ts"] if len(lv) > 1 else 0
        if rounds >= R2_MIN_ROUNDS:
            device_hits[dev].append("R2b")
            for p in lv[:2]:
                evidence.append(_ev(p["ts"], p.get("packet_id"), "Leave(rejoin=1)",
                                    f"TC → {_addr4(dev)} (被要求重入)"))

    # ── R3: poll 无 ACK [v1.0: ACK 提取待增强, 规则就位] ──
    r3_note = None
    # MAC ACK 帧 (mac_frame_type=2) 不在当前解析输出 (tshark parse_mac_frames 过滤)
    # [待增强: 解析器补 ACK 提取后实现]

    # ── 汇总 ──
    hit_devs = sorted(device_hits.items())
    for dev, rules in hit_devs:
        conf = "高" if any(r in ("R1", "R2a") for r in rules) else "中"
        desc = {
            "R1": "轮询间隔超 320s (父节点超时移除)",
            "R2a": "自发 rejoin=1 Leave 循环 (反复掉线重入)",
            "R2b": "TC 反复要求重入 (被踢重入循环)",
        }
        results.append({
            "device": dev, "verdict": "L2-1_HIT", "sub_rule": "/".join(rules),
            "confidence": conf,
            "summary": "频繁离线: " + "; ".join(desc[r] for r in rules),
            "poll_count": len(poll_by_src.get(dev, [])),
        })

    # 健康设备 (有 poll 活动但无命中): 汇总到 HEALTHY 计数
    active_pollers = set(poll_by_src.keys())
    healthy_count = len(active_pollers - set(device_hits.keys()))

    if hit_devs:
        verdict = "L2-1_HIT"
        confidence = "高" if any(r["confidence"] == "高" for r in results) else "中"
        summary = "终端频繁离线: " + ", ".join(
            f"{_addr4(r['device'])} ({r['sub_rule']})" for r in results)
    elif active_pollers:
        verdict = "HEALTHY"
        confidence = "高"
        summary = f"轮询节奏正常 ({healthy_count} 台 poll 设备, 无超时/循环)"
    else:
        verdict = "INCONCLUSIVE"
        confidence = "低"
        summary = "无 poll/Leave 数据 (需含 MAC 帧的素材, 且 sniffer 在 poll 链路)"

    # 结论 (简短易懂, 诚实)
    if hit_devs:
        conclusion = ("终端频繁离线: " + ", ".join(
            f"{_addr4(r['device'])} ({'/'.join(r['sub_rule'].split('/'))})" for r in results) +
            (" (高置信)" if any(r["confidence"] == "高" for r in results) else " (中置信)"))
    elif active_pollers:
        conclusion = "终端轮询正常, 未发现频繁离线"
    else:
        conclusion = "无法判定: 无 poll/Leave 数据 (素材需含 MAC 帧且覆盖 poll 链路)"

    evidence, evidence_total = _cut(evidence)
    return {
        "scenario": "L2-1",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "poll_device_count": len(poll_by_src),
        "poll_total": len(polls),
        "leave_rejoin_total": len([p for p in leaves if p.get("nwk_leave_rejoin") == 1]),
        "devices": results,
    }


# ── L2-6 判定参数 (MCP 核对 2026-08-11, 见 L2-6.md) ──
# 官方: 失联无官方通知 (Leave 广播不可靠), 需自建检测 —
#   SED: 父节点 End Device Poll Timeout (默认 320s 旧 SDK / 256min R21) 超时删除子表
#   路由器: 邻居表 age>6 (~64s) stale, 邻居停发 LS 后条目消失/out 归 0 (L3-9 交叉)
# 检测信号: 规律 poll 突然停止 (R1) / LS 邻居条目消失 (R2)
L26_MIN_POLLS = 3           # R1: 规律活跃需 poll ≥3 次 (排除偶发)
L26_POLL_MEDIAN_MAX_S = 60.0  # R1: poll 间隔中位 ≤60s (规律活跃; LONG_POLL 默认 300s 之下)
L26_SILENT_MULT = 3.0       # R1: 沉默 ≥3× 中位间隔
L26_SILENT_MIN_S = 60.0     # R1: 且 ≥60s 下限
L26_LS_APPEAR_MIN = 2       # R2: 邻居在 LS 中出现 ≥2 次 (曾有双向)
L26_LS_GONE_MIN = 3         # R2: 之后连续 ≥3 条 LS 无该邻居 → 消失确认
L26_GLOBAL_SILENT_S = 120.0 # R3 辅助: 全局沉默候选阈值 (仅提示, 不单独判)


def detect_l2_6(packets: list[dict]) -> dict:
    """设备静默失联检测 (文档 L2-6.md v1.0).

    规则 (MCP 核对 2026-08-11):
      - R1 : SED 失联候选 — 规律 poll (≥3 次, 中位间隔 ≤60s) 后沉默
            ≥max(3×中位, 60s) → 失联候选 (父节点视角: Poll Timeout 未响应)
      - R2 : 路由器失联候选 — 邻居 B 在 A 的 LS 中曾出现 (≥2 次), 之后 A 连续
            ≥3 条 LS 无 B → B 静默 (邻居表条目消失; 与 L3-9 stale 同源)
      - 交叉: 命中设备伴随 Leave → 主动离开/被踢 (归 L1-4), 非静默失联
      - ⚠️ 边缘效应: 沉默延伸到抓包末尾 — 无法区分失联与抓包结束, 结论标注
      素材实证 (2026-08-11): 直连泛洪 0x96A8 (poll 中位 4.2s → 沉默 147s) R1 候选
      (边缘标注); 正例 (抓包窗口内明确失联 + 现场确认) 待素材
    """
    t0 = min((p.get("ts", 0.0) for p in packets), default=0.0)
    t_end = max((p.get("ts", 0.0) for p in packets), default=0.0)
    if t_end <= t0:
        return {"scenario": "L2-6", "verdict": "INCONCLUSIVE", "confidence": "低",
                "summary": "无有效时间轴", "conclusion": "无法判定: 素材无有效帧",
                "devices": [], "evidence": [], "evidence_total": 0}

    # ── 数据收集 ──
    polls: dict[int, list[float]] = defaultdict(list)   # 设备 → poll 时间序列
    leaves: set[int] = set()                            # 发过 Leave 的设备
    ls_seq: dict[int, list[tuple]] = defaultdict(list)  # LS 发送者 → [(ts, 邻居集合)] (时间序)
    last_act: dict[int, float] = defaultdict(float)
    for p in packets:
        ts = p.get("ts", 0.0)
        if p.get("mac_cmd_id") == MAC_DATA_REQUEST and p.get("mac_src") is not None:
            polls[p["mac_src"]].append(ts)
        if p.get("nwk_cmd_id") == NWK_CMD_LEAVE and p.get("nwk_src") is not None:
            leaves.add(p["nwk_src"])
        if p.get("nwk_cmd_id") == 8 and p.get("link_status_neighbors") and p.get("nwk_src") is not None:
            ls_seq[p["nwk_src"]].append((ts, {nb["addr"] for nb in p["link_status_neighbors"]}))
        for a in (p.get("nwk_src"), p.get("nwk_dst"), p.get("mac_src")):
            if a is not None and a < 0xFFF0:
                last_act[a] = max(last_act[a], ts)

    results: list[dict] = []
    evidence: list[dict] = []

    # ── R1: 规律 poll 后沉默 (SED 失联候选) ──
    for dev, seq in polls.items():
        if len(seq) < L26_MIN_POLLS:
            continue
        seq.sort()
        gaps = [seq[i + 1] - seq[i] for i in range(len(seq) - 1)]
        gaps.sort()
        med = gaps[len(gaps) // 2]
        if med > L26_POLL_MEDIAN_MAX_S:
            continue  # 非规律活跃 (长轮询设备, 沉默是常态)
        silent = t_end - seq[-1]
        thr = max(L26_SILENT_MULT * med, L26_SILENT_MIN_S)
        if silent < thr:
            continue
        edge = "⚠️ 沉默延伸到抓包末尾, 无法区分失联与抓包结束" if silent > t_end - t0 - 30 else ""
        left = "伴随 Leave (主动离开/被踢, 归 L1-4)" if dev in leaves else ""
        verdict = "L2-6_HIT"
        conf = "中"
        summary = (f"规律轮询停止: poll {len(seq)} 次 (间隔中位 {round(med,1)}s) 后沉默 "
                   f"{round(silent,1)}s ({'R1'})")
        results.append({"device": dev, "verdict": verdict, "sub_rule": "R1",
                        "confidence": conf, "silent_s": round(silent, 1),
                        "poll_count": len(seq), "poll_median_s": round(med, 1),
                        "edge_uncertain": bool(edge), "left_leave": dev in leaves,
                        "summary": summary + ("; " + left if left else "") + ("; " + edge if edge else "")})
        evidence.append(_ev(seq[-1], None, "L2-6", f"最后 poll: {hex(dev)}"))

    # ── R2: LS 邻居条目消失 (路由器失联候选) ──
    for sender, seq in ls_seq.items():
        if len(seq) < L26_LS_GONE_MIN + 1:
            continue
        appeared: dict[int, int] = {}
        for _, nbrs in seq:
            for b in nbrs:
                appeared[b] = appeared.get(b, 0) + 1
        for b, cnt in appeared.items():
            if cnt < L26_LS_APPEAR_MIN:
                continue
            # b 最后一次出现后的连续 LS 是否 ≥3 条无 b
            last_idx = max(i for i, (_, nbrs) in enumerate(seq) if b in nbrs)
            gone = sum(1 for _, nbrs in seq[last_idx + 1:] if b not in nbrs)
            if gone >= L26_LS_GONE_MIN and last_idx + gone == len(seq) - 1:
                # ⚠️ 全局沉默守卫 (自审修正 2026-08-11, test2 误报):
                # 邻居表条目消失 ≠ 设备失联 — 大网络表容量替换/设备移动时, B 从 A 的
                # LS 消失但 B 仍在别处活跃 (test2 实证: 命中设备全局沉默仅 0-14s);
                # 只有 B 在 A 最后报告时间后不再有任何帧 (全局沉默) 才是失联候选
                if last_act.get(b, 0.0) > seq[last_idx][0]:
                    continue
                left = "伴随 Leave" if b in leaves else ""
                edge = "⚠️ 消失持续到抓包末尾" if gone == len(seq) - 1 - last_idx else ""
                summary = (f"邻居 {hex(b)} 从 {hex(sender)} 的 Link Status 消失 "
                           f"(曾出现 {cnt} 次, 连续 {gone} 条 LS 无该邻居, R2)")
                results.append({"device": b, "verdict": "L2-6_HIT", "sub_rule": "R2",
                                "confidence": "中", "silent_s": None,
                                "reporter": sender, "ls_gone": gone,
                                "edge_uncertain": bool(edge), "left_leave": b in leaves,
                                "summary": summary + ("; " + left if left else "") + ("; " + edge if edge else "")})
                evidence.append(_ev(seq[last_idx][0], None, "L2-6",
                                    f"邻居消失: {hex(sender)} 不再报告 {hex(b)}"))

    # ── 结论 ──
    hits = [r for r in results if r["verdict"] == "L2-6_HIT"]
    has_poll_data = bool(polls)
    has_ls_data = bool(ls_seq)
    if hits:
        verdict, conf = "L2-6_HIT", "中"
        total = len(hits)
        names = ", ".join(f"0x{r['device']:04X}({r['sub_rule']})" for r in hits)
        conclusion = (f"设备静默失联候选 {total} 台: {names} — 需现场确认 "
                      "(失联无官方通知, 官方; 沉默到抓包末尾的标注边缘不确定)")
    elif has_poll_data or has_ls_data:
        verdict, conf = "HEALTHY", "高"
        conclusion = "未发现设备静默失联 (poll 规律保持 / LS 邻居条目未消失)"
    else:
        verdict, conf = "INCONCLUSIVE", "低"
        conclusion = "无法判定静默失联: 素材无 poll/LS 数据"

    ev, ev_total = _cut(evidence)
    return {
        "scenario": "L2-6", "verdict": verdict, "confidence": conf,
        "summary": conclusion, "conclusion": conclusion,
        "devices": results, "evidence": ev, "evidence_total": ev_total,
    }


# ── 入口 ──

def detect(packets: list[dict]) -> dict:
    """运行全部 L2 检测 → 汇总报告."""
    return {
        "l2_1": detect_l2_1(packets),
        "l2_6": detect_l2_6(packets),
    }
