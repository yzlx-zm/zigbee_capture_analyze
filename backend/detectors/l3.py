"""L3 场景检测器 — 运营期核心 (L3-5 源路由/MTORR 失效)

输入: cubx_reader/tshark 解析的包 dict 列表 (需 nwk_cmd_id/nwk_status_code/nwk_status_target).
输出: 检测报告 dict, 按 ADR-0002 置信度分级 (高/中/低/不可判定).

判定规则来源: docs/scenarios/L3-5.md v1.0 (官方依据 + 838D 素材实证)
"""
from __future__ import annotations

from collections import defaultdict

# ── NWK 命令 / 错误码 (官方 stack-info.h) ──
NWK_CMD_NETWORK_STATUS = 3
NWK_CMD_ROUTE_REQUEST = 1
NWK_CMD_ROUTE_RECORD = 5
NS_CODE_SOURCE_ROUTE_FAILURE = 0x0B   # Source Route Failure (下行, concentrator 专属)
NS_CODE_MANY_TO_ONE_ROUTE_FAILURE = 0x0C  # Many-to-One Route Failure (上行)

# ── L3-5 判定参数 (grilling 定稿 + 素材校准 2026-08-04) ──
ROUND_GAP_S = 0.5       # 同轮判定: 间隔 <0.5s 归同轮 (APS 重试 3 连发 = 1 轮, 素材间隔 3-10ms)
MIN_ROUNDS = 2          # ≥2 轮才判定 (≤1 轮 = 单次失败重试的官方预期行为, message.h)
SELF_HEAL_WINDOW_S = 10.0  # 自愈观察: 失败持续超过该窗口且无恢复迹象 → 持续故障佐证


def _rounds(frames: list[dict]) -> int:
    """同 target 的 Network Status 按时间间隔分组 → 轮数."""
    if not frames:
        return 0
    frames = sorted(frames, key=lambda p: p["ts"])
    rounds = 1
    for i in range(1, len(frames)):
        if frames[i]["ts"] - frames[i - 1]["ts"] >= ROUND_GAP_S:
            rounds += 1
    return rounds


def detect_l3_5(packets: list[dict], l1_result: dict | None = None) -> dict:
    """源路由/MTORR 失效检测 (文档 L3-5.md v1.0).

    规则 (grilling 定稿 + 838D 素材实证):
      - R1 : Network Status code=0x0B (Source Route Failure), 同 target ≥2 轮 → 高置信
            (0x0B 仅 concentrator 模式发生; 断链前一跳生成并回传 — message.h 官方)
      - R2 : code=0x0C (Many-to-One Route Failure), 同 target ≥2 轮 → 中置信 [待素材]
      - 单轮 (≤3 条) 不判定 — 官方: 单次失败 APS 重试的预期行为
      - 自愈观察: MTORR/Route Record 出现 + 失败轮数持续 → 自愈失败佐证
      - 交叉提示: 同 target 设备同时命中 L1-3 → 表象/根因交叉 (838D 案例)
    """
    # 1. Network Status 按 (code, target) 分组
    groups: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for p in packets:
        code = p.get("nwk_status_code")
        if p.get("nwk_cmd_id") == NWK_CMD_NETWORK_STATUS and code in (
                NS_CODE_SOURCE_ROUTE_FAILURE, NS_CODE_MANY_TO_ONE_ROUTE_FAILURE):
            target = p.get("nwk_status_target")
            if target is not None:
                groups[(code, target)].append(p)

    # 2. MTORR/Route Record 自愈观察 (全素材统计)
    route_request_count = sum(1 for p in packets if p.get("nwk_cmd_id") == NWK_CMD_ROUTE_REQUEST)
    route_record_count = sum(1 for p in packets if p.get("nwk_cmd_id") == NWK_CMD_ROUTE_RECORD)

    # 3. L1-3 交叉索引: target 设备是否 L1-3_HIT
    l1_hits = set()
    if l1_result:
        l3 = l1_result.get("l1_3") or {}
        for d in l3.get("devices") or []:
            if d.get("verdict", "").startswith("L1-3"):
                l1_hits.add(d.get("device"))

    # 4. 逐组判定
    targets: dict[int, dict] = {}
    for (code, target), frames in sorted(groups.items(), key=lambda kv: kv[0][1]):
        frames.sort(key=lambda p: p["ts"])
        n = len(frames)
        rounds = _rounds(frames)
        srcs = sorted({p.get("nwk_src") for p in frames})
        span = frames[-1]["ts"] - frames[0]["ts"]
        l1_cross = target in l1_hits
        t = targets.setdefault(target, {
            "device": target, "hits": [],
        })

        rule = "R1" if code == NS_CODE_SOURCE_ROUTE_FAILURE else "R2"
        if rounds >= MIN_ROUNDS:
            t["hits"].append({
                "code": code,
                "count": n, "rounds": rounds, "span_s": round(span, 1),
                "src": sorted(srcs), "rule": rule,
                "l1_3_cross": l1_cross,
                "confidence": "高" if code == NS_CODE_SOURCE_ROUTE_FAILURE else "中",
            })
        else:
            t["hits"].append({
                "code": code, "count": n, "rounds": rounds, "span_s": round(span, 1),
                "src": sorted(srcs), "rule": None,
                "l1_3_cross": l1_cross,
                "confidence": None,  # 单轮 = 官方预期行为, 不判定
            })

    # 5. 汇总
    results = []
    for target, t in sorted(targets.items()):
        hits = [h for h in t["hits"] if h["rule"]]
        sub_rules = "/".join(h["rule"] for h in hits)
        cross_hint = (f"; ⚠️ 与 L1-3 交叉: 该设备同时命中密钥分发异常 — "
                      "密钥循环可能是本场景根因的表象 (838D 案例)" if any(h["l1_3_cross"] for h in hits) else "")
        if hits:
            conf = "高" if any(h["confidence"] == "高" for h in hits) else "中"
            detail = "; ".join(
                f"code=0x{h['code']:02X} ×{h['count']} ({h['rounds']}轮/{h['span_s']}s, src={[hex(s or 0) for s in h['src']]})"
                for h in hits)
            results.append({
                "device": target, "verdict": "L3-5_HIT", "sub_rule": sub_rules,
                "confidence": conf,
                "summary": f"源路由/MTORR 失效: {detail}{cross_hint}",
                "route_error_count": sum(h["count"] for h in t["hits"]),
                "rounds": sum(h["rounds"] for h in hits),
            })
        elif t["hits"]:
            # 全部单轮 → 瞬态 (健康)
            n = sum(h["count"] for h in t["hits"])
            results.append({
                "device": target, "verdict": "HEALTHY", "sub_rule": None,
                "confidence": "高",
                "summary": f"Network Status 0x0B/0x0C ×{n} 但仅 1 轮 (单次失败重试, 官方预期行为)",
                "route_error_count": n, "rounds": 1,
            })
        else:
            results.append({
                "device": target, "verdict": "INCONCLUSIVE", "sub_rule": None,
                "confidence": "低", "summary": "无 Network Status 0x0B/0x0C",
                "route_error_count": 0, "rounds": 0,
            })

    hits = [r for r in results if r["verdict"] == "L3-5_HIT"]
    healthies = [r for r in results if r["verdict"] == "HEALTHY"]
    if hits:
        verdict = "L3-5_HIT"
        confidence = "高" if any(r["confidence"] == "高" for r in hits) else "中"
        summary = "源路由/MTORR 失效: " + ", ".join(
            f"0x{r['device']:04X} ({r['sub_rule']})" for r in hits)
    elif healthies:
        verdict = "HEALTHY"
        confidence = "高"
        summary = f"无持续源路由失败 ({len(healthies)}/{len(results)} 组仅瞬态或无 0x0B/0x0C)"
    elif not groups:
        # 无任何 0x0B/0x0C: 有网络活动 → 健康 (负例); 无活动 → 不可判定
        has_activity = any(p.get("nwk_src") is not None or p.get("nwk_dst") is not None for p in packets)
        if has_activity:
            verdict = "HEALTHY"
            confidence = "高"
            summary = ("无源路由失败证据 (Network Status 0x0B/0x0C = 0 帧); "
                       "⚠️ 盲区: route error 不保证送达 (message.h), 0x0B 缺失 ≠ 绝对无失败")
        else:
            verdict = "INCONCLUSIVE"
            confidence = "低"
            summary = "无网络活动 (需断链链路覆盖)"
    else:
        verdict = "INCONCLUSIVE"
        confidence = "低"
        summary = "无 Network Status 0x0B/0x0C (需断链链路覆盖)"

    # 自愈迹象 (全素材级)
    # ⚠️ 诚实标注: Route Request 总数含普通路由发现; MTORR (many-to-one 标志) 数量
    # 未单独解析 (解析器未提取 route request options) — 不做 "含 MTORR" 断言
    self_heal = {
        "route_request_count": route_request_count,
        "route_record_count": route_record_count,
        "note": (f"Route Request ×{route_request_count} + Route Record ×{route_record_count} 存在"
                 f" (MTORR 数量未解析, many-to-one 标志待提取 [待增强])"
                 if route_request_count or route_record_count
                 else "无 Route Request/Route Record (自愈机制未活动或未抓取)"),
    }

    return {
        "scenario": "L3-5",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "network_status_total": sum(len(v) for v in groups.values()),
        "source_route_failure_count": sum(1 for (c, _), v in groups.items()
                                          if c == NS_CODE_SOURCE_ROUTE_FAILURE for _ in v),
        "mto_route_failure_count": sum(1 for (c, _), v in groups.items()
                                       if c == NS_CODE_MANY_TO_ONE_ROUTE_FAILURE for _ in v),
        "self_heal": self_heal,
        "devices": results,
    }


# ── 入口 ──

def detect(packets: list[dict], l1_result: dict | None = None) -> dict:
    """运行全部 L3 检测 → 汇总报告."""
    return {
        "l3_5": detect_l3_5(packets, l1_result),
    }
