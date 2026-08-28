"""L6 场景检测器 — SED 专项 (L6-S3 间接事务过期)

输入: cubx_reader/tshark 解析的包 dict 列表 (含 MAC 帧: mac_cmd_id/mac_src).
输出: 检测报告 dict, 按 ADR-0002 置信度分级.

判定规则来源: docs/scenarios/L6-S3.md v1.0 (官方依据 + G32 素材实证)
"""
from __future__ import annotations

from collections import defaultdict

# ── 常量 (官方依据) ──
MAC_DATA_REQUEST = 4            # MAC 命令 cmd_id=0x04 (SED 轮询)
NWK_CMD_NETWORK_STATUS = 3
NS_CODE_INDIRECT_EXPIRY = 0x06      # INDIRECT_TRANSACTION_EXPIRY
NS_CODE_NO_INDIRECT_CAPACITY = 0x05 # NO_INDIRECT_CAPACITY (区分用)
INDIRECT_TIMEOUT_S = 7.68           # EMBER_INDIRECT_TRANSMISSION_TIMEOUT 默认

# ── 结论/证据输出 (诊断页人工复核) ──
EVIDENCE_MAX = 15


def _ev(ts, pid, type_, detail, idx=None) -> dict:
    return {"ts": round(ts, 3), "packet_id": pid, "id": idx, "type": type_, "detail": detail}


def _cut(items: list) -> tuple[list, int]:
    return items[:EVIDENCE_MAX], len(items)


def _addr4(v) -> str:
    return f"0x{v:04X}" if v is not None else "?"


def detect_l6_3(packets: list[dict], l3_result: dict | None = None) -> dict:
    """SED 间接事务过期检测 (文档 L6-S3.md v1.0).

    规则 (grilling 定稿 2026-08-05):
      - R1: Network Status 0x06 出现 → 命中 (父节点间接消息过期, 官方语义)
      - R2: 形态细分 — 目标 SED poll 活跃 (间隔 <7.68s) 仍过期 → 下行投递失败型
            (与 L3-5 交叉, G32 实证); poll 缺失/间隔 ≥7.68s → 睡眠型 [待素材]
      - R3: 0x05 (队列满) 单独记录, 不混入 L6-S3 判定
    """
    # 1. 收集 0x06 / 0x05 帧
    expiry = [p for p in packets
              if p.get("nwk_cmd_id") == NWK_CMD_NETWORK_STATUS
              and p.get("nwk_status_code") == NS_CODE_INDIRECT_EXPIRY]
    no_cap = [p for p in packets
              if p.get("nwk_cmd_id") == NWK_CMD_NETWORK_STATUS
              and p.get("nwk_status_code") == NS_CODE_NO_INDIRECT_CAPACITY]

    # 2. poll 统计 (MAC DataRequest, 按 mac_src)
    poll_by_dev: dict[int, list[float]] = defaultdict(list)
    for p in packets:
        if p.get("mac_cmd_id") == MAC_DATA_REQUEST and p.get("mac_src") is not None:
            poll_by_dev[p["mac_src"]].append(p["ts"])

    # 3. 每 0x06 目标的形态判定
    evidence = []
    results = []
    by_target: dict[int, dict] = defaultdict(lambda: {"count": 0, "parents": set(),
                                                      "poll_active": False,
                                                      "min_poll_gap_after": None})
    for p in expiry:
        tgt = p.get("nwk_status_target")
        parent = p.get("nwk_src")
        if tgt is None:
            continue
        d = by_target[tgt]
        d["count"] += 1
        if parent is not None:
            d["parents"].add(parent)
        # 0x06 距最近 poll (投递失败判据)
        polls = sorted(poll_by_dev.get(tgt, []))
        import bisect
        i = bisect.bisect_right(polls, p["ts"]) - 1
        if i >= 0 and (d["min_poll_gap_after"] is None
                       or p["ts"] - polls[i] < d["min_poll_gap_after"]):
            d["min_poll_gap_after"] = p["ts"] - polls[i]
        # poll 活跃判定: 目标有 poll 且间隔 < 间接超时
        if polls:
            gaps = [polls[j + 1] - polls[j] for j in range(len(polls) - 1)]
            if gaps and max(gaps) < INDIRECT_TIMEOUT_S:
                d["poll_active"] = True
            elif len(polls) >= 2:
                d["poll_active"] = all(g < INDIRECT_TIMEOUT_S for g in gaps[:3])

    # L3-5 交叉: 同目标是否有 0x0C 下行失败
    l3_cross: dict[int, bool] = {}
    if l3_result:
        l35 = l3_result.get("l3_5") or {}
        for dev in l35.get("devices") or []:
            if dev.get("sub_rule") and "R2" in dev.get("sub_rule", ""):
                l3_cross[dev.get("device")] = True

    for tgt, d in sorted(by_target.items()):
        parents = ", ".join(_addr4(p) for p in sorted(d["parents"]))
        cross = l3_cross.get(tgt, False)
        # 形态: poll 活跃 → 投递失败型; 否则 → 睡眠型 (低置信)
        if d["poll_active"]:
            form = "下行投递失败型"
            conf = "高"
            form_hint = (f"目标 poll 活跃 (间隔 <{INDIRECT_TIMEOUT_S}s) 仍过期"
                         + (f", 0x06 距 poll 最短 {d['min_poll_gap_after']:.1f}s" if d["min_poll_gap_after"] else ""))
        else:
            form = "睡眠型 (poll 缺失/间隔大)"
            conf = "中"
            form_hint = "目标 poll 缺失或间隔 ≥7.68s"
        cross_hint = " — ⚠️ 与 L3-5 交叉 (下行失败 SED 侧表现)" if cross else ""
        results.append({
            "device": tgt, "verdict": "L6-S3_HIT", "sub_rule": "R1/R2",
            "confidence": conf,
            "summary": f"间接事务过期 ×{d['count']} (父 {parents}): {form_hint}{cross_hint}",
            "expiry_count": d["count"],
            "parents": sorted(d["parents"]),
            "form": form,
            "l3_5_cross": cross,
        })
        # 证据
        for p in expiry[:2]:
            if p.get("nwk_status_target") == tgt:
                evidence.append(_ev(p["ts"], p.get("packet_id"), "Network Status 0x06",
                                    f"{_addr4(p.get('nwk_src'))} → {_addr4(tgt)} (间接消息过期)",
                                    p.get("_idx")))
                break

    # 汇总
    if results:
        verdict = "L6-S3_HIT"
        confidence = "高" if any(r["confidence"] == "高" for r in results) else "中"
        summary = "SED 间接事务过期: " + ", ".join(
            f"{_addr4(r['device'])} ×{r['expiry_count']}" for r in results)
        conclusion = ("SED 消息过期: " + "; ".join(
            f"{_addr4(r['device'])} ({r['form']})" for r in results) +
            (" (高置信)" if confidence == "高" else " (中置信)"))
    else:
        verdict = "HEALTHY"
        confidence = "高"
        summary = "无间接事务过期 (0x06 = 0)"
        conclusion = "未发现 SED 间接消息过期"
    if no_cap:
        summary += f" | 注意: 0x05 (队列满) ×{len(no_cap)} 单独记录"

    evidence, evidence_total = _cut(evidence)
    return {
        "scenario": "L6-S3",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "expiry_count": len(expiry),
        "no_indirect_capacity_count": len(no_cap),
        "devices": results,
    }


# ── 入口 ──

def detect(packets: list[dict], l3_result: dict | None = None) -> dict:
    """运行全部 L6 检测 → 汇总报告."""
    for _i, _p in enumerate(packets):
        _p["_idx"] = _i  # S2: 证据帧列表索引 (前端跳报文页 tlJumpFrame 用)
    return {
        "l6_3": detect_l6_3(packets, l3_result),
    }
