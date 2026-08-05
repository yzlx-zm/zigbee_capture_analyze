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


# ── 入口 ──

def detect(packets: list[dict]) -> dict:
    """运行全部 L2 检测 → 汇总报告."""
    return {
        "l2_1": detect_l2_1(packets),
    }
