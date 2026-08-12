"""L3 场景检测器 — 运营期核心 (L3-5 源路由/MTORR 失效)

输入: cubx_reader/tshark 解析的包 dict 列表 (需 nwk_cmd_id/nwk_status_code/nwk_status_target).
输出: 检测报告 dict, 按 ADR-0002 置信度分级 (高/中/低/不可判定).

判定规则来源: docs/scenarios/L3-5.md v1.0 (官方依据 + 838D 素材实证)
"""
from __future__ import annotations

from collections import defaultdict

# ── 结论/证据输出 (诊断页人工复核, 2026-08-05 需求) ──
EVIDENCE_MAX = 15


def _ev(ts, pid, type_, detail) -> dict:
    return {"ts": round(ts, 3), "packet_id": pid, "type": type_, "detail": detail}


def _cut(items: list) -> tuple[list, int]:
    return items[:EVIDENCE_MAX], len(items)


def _addr4(v) -> str:
    return f"0x{v:04X}" if v is not None else "?"

# ── NWK 命令 / 错误码 (官方 stack-info.h) ──
NWK_CMD_NETWORK_STATUS = 3
NWK_CMD_ROUTE_REQUEST = 1
NWK_CMD_ROUTE_RECORD = 5
NWK_CMD_LEAVE = 4
NS_CODE_SOURCE_ROUTE_FAILURE = 0x0B   # Source Route Failure (下行, concentrator 专属)
NS_CODE_MANY_TO_ONE_ROUTE_FAILURE = 0x0C  # Many-to-One Route Failure (上行)
NS_CODE_INDIRECT_EXPIRY = 0x06        # 间接事务过期 (L6-S3)

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
    # MTORR 真实计数: Route Request many-to-one 标志 (2026-08-05 提取, 位定义行为实证)
    mtorr_count = sum(1 for p in packets
                      if p.get("nwk_cmd_id") == NWK_CMD_ROUTE_REQUEST
                      and p.get("nwk_route_request_mto") == 1)
    route_record_count = sum(1 for p in packets if p.get("nwk_cmd_id") == NWK_CMD_ROUTE_RECORD)

    # 2b. Network Status 全码统计 (0x00-0x13, 2026-08-05 需求: 全错误码记录)
    # 含 0x0B/0x0C 之外的码 (0x06 等) — 诊断页显示分布, 异常码后续按需补规则
    ns_codes: dict[int, int] = defaultdict(int)
    ns_by_code_src: dict[int, set] = defaultdict(set)
    for p in packets:
        if p.get("nwk_cmd_id") == NWK_CMD_NETWORK_STATUS:
            c = p.get("nwk_status_code")
            if c is not None:
                ns_codes[c] += 1
                ns_by_code_src[c].add(p.get("nwk_src"))

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
        # ⚠️ 2026-08-05: 0x0C 的 dest 字段决定失败方向 (Network Status = [src][dst][code][dest]):
        #   dest=0x0000 → 发往协调器的上行失败; dest=其他 → 发往该设备的下行失败
        # (用户指出 v1 结论"0x0C=上行"过于简化, G32 素材实证: dest=0xBE5A/0xEE48 下行为主)
        direction = None
        if code == NS_CODE_MANY_TO_ONE_ROUTE_FAILURE:
            direction = "up" if target == 0x0000 else "down"
        elif code == NS_CODE_SOURCE_ROUTE_FAILURE:
            direction = "down"
        if rounds >= MIN_ROUNDS:
            t["hits"].append({
                "code": code,
                "count": n, "rounds": rounds, "span_s": round(span, 1),
                "src": sorted(srcs), "rule": rule,
                "direction": direction,
                "l1_3_cross": l1_cross,
                "confidence": "高" if code == NS_CODE_SOURCE_ROUTE_FAILURE else "中",
            })
        else:
            t["hits"].append({
                "code": code, "count": n, "rounds": rounds, "span_s": round(span, 1),
                "src": sorted(srcs), "rule": None,
                "direction": direction,
                "l1_3_cross": l1_cross,
                "confidence": None,  # 单轮 = 官方预期行为, 不判定
            })

    # 5. 汇总
    evidence = []  # 人工复核证据帧 (命中组的 Network Status)
    results = []
    for target, t in sorted(targets.items()):
        hits = [h for h in t["hits"] if h["rule"]]
        sub_rules = "/".join(h["rule"] for h in hits)
        cross_hint = (f"; ⚠️ 与 L1-3 交叉: 该设备同时命中密钥分发异常 — "
                      "密钥循环可能是本场景根因的表象 (838D 案例)" if any(h["l1_3_cross"] for h in hits) else "")
        if hits:
            conf = "高" if any(h["confidence"] == "高" for h in hits) else "中"
            def _dir_text(h):
                d = h.get("direction")
                if d == "up":
                    return "上行失败"
                if d == "down":
                    return "下行失败"
                return ""
            detail = "; ".join(
                f"code=0x{h['code']:02X} ×{h['count']} ({h['rounds']}轮/{h['span_s']}s, "
                f"{_dir_text(h)}, src={[hex(s or 0) for s in h['src']]})"
                for h in hits)
            results.append({
                "device": target, "verdict": "L3-5_HIT", "sub_rule": sub_rules,
                "confidence": conf,
                "summary": f"源路由/MTORR 失效: {detail}{cross_hint}",
                "route_error_count": sum(h["count"] for h in t["hits"]),
                "rounds": sum(h["rounds"] for h in hits),
                "src": sorted({s for h in t["hits"] for s in (h["src"] or [])}),
                "_hits": t["hits"],  # 结论方向判定用 (生成后 pop)
            })
            # 证据: 命中组的 Network Status 帧 (供人工复核)
            for (code, tg), frames in groups.items():
                if tg == target and code in (NS_CODE_SOURCE_ROUTE_FAILURE,
                                             NS_CODE_MANY_TO_ONE_ROUTE_FAILURE):
                    for p in frames[:3]:
                        evidence.append(_ev(
                            p["ts"], p.get("packet_id"), "Network Status",
                            f"code=0x{code:02X} {_addr4(p.get('nwk_src'))} → target={_addr4(tg)}"))
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
        # 无任何 0x0B/0x0C: 一律不可判定 (2026-08-10 自审裁定, 用户拍板) —
        # 原"有活动→HEALTHY 负例"导致 verdict=健康但 conclusion=无法判定的自相矛盾
        # (绿卡误信"路由没问题", 838D 案例正是 0x0B 缺失期); route error 不保证送达 (message.h),
        # 0x0B 缺失 ≠ 绝对无失败 → 琥珀"无法判定"才与语义一致
        has_activity = any(p.get("nwk_src") is not None or p.get("nwk_dst") is not None for p in packets)
        verdict = "INCONCLUSIVE"
        confidence = "低"
        if has_activity:
            summary = ("无法判定: 无 Network Status 0x0B/0x0C 证据 (网络有活动; "
                       "⚠️ 盲区: route error 不保证送达, 0x0B 缺失 ≠ 绝对无失败)")
        else:
            summary = "无法判定: 无网络活动 (需断链链路覆盖)"
    else:
        verdict = "INCONCLUSIVE"
        confidence = "低"
        summary = "无 Network Status 0x0B/0x0C (需断链链路覆盖)"

    # 自愈迹象 (全素材级, 2026-08-05: MTORR 真实计数, many-to-one 标志已提取)
    # MTORR 频率: 健康默认 60s 周期 (Concentrator 插件); 实测 G32 两包 3.4-7.2s —
    # 高频 = 配置过短或隐含路由问题持续触发重建 [观察信号, 需配置信息佐证]
    mtorr_interval_s = None
    if mtorr_count >= 2:
        mto_ts = sorted(p["ts"] for p in packets
                        if p.get("nwk_cmd_id") == NWK_CMD_ROUTE_REQUEST
                        and p.get("nwk_route_request_mto") == 1)
        if len(mto_ts) >= 2:
            mtorr_interval_s = round((mto_ts[-1] - mto_ts[0]) / (len(mto_ts) - 1), 1)
    if mtorr_interval_s is not None:
        mto_txt = (f"MTORR ×{mtorr_count} (Route Request 共 {route_request_count}, "
                   f"平均 {mtorr_interval_s}s/次)")
    else:
        mto_txt = f"MTORR ×{mtorr_count} (Route Request 共 {route_request_count})"
    if route_request_count or route_record_count:
        note = f"{mto_txt} + Route Record ×{route_record_count} 存在"
    else:
        note = "无 Route Request/Route Record (自愈机制未活动或未抓取)"
    self_heal = {
        "route_request_count": route_request_count,
        "mtorr_count": mtorr_count,
        "mtorr_interval_s": mtorr_interval_s,
        "route_record_count": route_record_count,
        "note": note,
    }

    # 结论 (简短易懂, 诚实)
    if hits:
        parts = []
        for r in hits:
            srcs = ", ".join(_addr4(s) for s in (r.get("src") or []))
            rule = r.get("sub_rule") or ""
            if "R1" in rule:
                parts.append(f"0x{r['device']:04X} 下行链路持续失败 (断链前一跳 {srcs or '?'}, "
                             f"{r.get('rounds')} 轮)")
            elif "R2" in rule:
                # ⚠️ 0x0C 方向由 dest 决定 (up=发往协调器失败 / down=发往该设备失败)
                dirs = [h.get("direction") for h in r.get("_hits", [])]
                up = "up" in dirs
                dn = "down" in dirs
                if up and dn:
                    parts.append(f"0x{r['device']:04X} 路由双向持续失败 (MTORR, 断链前一跳 {srcs or '?'}, "
                                 f"{r.get('rounds')} 轮)")
                elif dn:
                    parts.append(f"0x{r['device']:04X} 下行链路持续失败 (MTORR, 断链前一跳 {srcs or '?'}, "
                                 f"{r.get('rounds')} 轮)")
                else:
                    parts.append(f"0x{r['device']:04X} 上行链路持续失败 (MTORR, 断链前一跳 {srcs or '?'}, "
                                 f"{r.get('rounds')} 轮)")
            else:
                parts.append(f"0x{r['device']:04X} 路由持续失败 (断链前一跳 {srcs or '?'}, "
                             f"{r.get('rounds')} 轮)")
        conclusion = "; ".join(parts) + " — 方向: R1 下行 / R2 由 dest 决定 (0x0000=上行, 其他=下行)"
        if any(r["confidence"] == "高" for r in hits):
            conclusion += " (高置信)"
        else:
            conclusion += " (中置信)"
        for r in hits:
            r.pop("_hits", None)  # 内部字段不进 API 响应
    elif healthies:
        conclusion = "未发现持续的路由失败 (下行链路正常)"
    else:
        conclusion = "无法判定路由状态: 无 Network Status 0x0B/0x0C (数据不足或未覆盖断链链路)"

    evidence, evidence_total = _cut(evidence)
    return {
        "scenario": "L3-5",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "network_status_total": sum(len(v) for v in groups.values()),
        "source_route_failure_count": sum(1 for (c, _), v in groups.items()
                                          if c == NS_CODE_SOURCE_ROUTE_FAILURE for _ in v),
        "mto_route_failure_count": sum(1 for (c, _), v in groups.items()
                                       if c == NS_CODE_MANY_TO_ONE_ROUTE_FAILURE for _ in v),
        "self_heal": self_heal,
        "network_status_codes": {f"0x{c:02X}": n for c, n in sorted(ns_codes.items())},
        "network_status_src": {f"0x{c:02X}": sorted({_addr4(s) for s in srcs})
                               for c, srcs in sorted(ns_by_code_src.items())},
        "devices": results,
    }


# ── L3-1 判定参数 (MCP 核对 2026-08-06, 见 L3-1.md) ──
# APS 重传: 50ms×hops 间隔, 3 次尝试, 单次 1600ms (非 SED 完整失败链 4.8s);
# 配对窗口复用 aps_pairing.ACK_MATCH_WINDOW_S (5s, 覆盖完整重试链)
L31_MIN_NO_ACK_PER_DEV = 2   # 设备级收敛: 同设备同方向无 ack ≥2 才输出 (排除单帧瞬态)
L31_RETRY_THRESHOLD = 2      # R2 高置信: 同 counter 重发 ≥2 (栈内重传证据)
L31_CROSS_WINDOW_S = 10.0    # 交叉归因窗口: 0x0B/0x06/Leave 在无 ack 帧前后 ±10s
# 2026-08-07 自审修正 (用户指出): "无独立 ack 帧" ≠ "命令未送达" —
# 素材实证部分设备固件 (含中继) 以应用层响应 (ZCL 响应/状态报告) 作为端到端确认,
# 不回独立 APS Ack 帧 (Silicon Labs 官方: sl_zigbee_send_reply 的 reply 附着于 ACK,
# "nonstandard extension" — 应用回复替代独立 ack 是生态内认可模式)。
# 判定改为 "无 ack 且无应用层响应" 才算命令无确认; 响应证据按强度分级:
#   ① 同 ZCL tsn (事务级铁证: Write Attrs→Write Attrs Rsp / On→On 报告同 tsn, 素材实证)
#   ② 同 cluster 反向数据帧 (应用层响应/状态报告)
#   ③ 命令帧 cluster 不可解析 → 任一反向数据帧 (降级; 素材 591 例 cluster=None)
L31_APP_RESP_WINDOW_S = 2.0  # 应用层响应窗口 (素材实测 <0.4s; G32 SED 边界 ~1.9s)
                             # ⚠️ SED 响应可能延迟到 poll 周期 >2s — 边界情况保留计数 (诚实标注)


def _cross_signals(packets: list[dict], ts: float) -> dict:
    """无 ack 帧时间点的交叉信号 (R3 归因): 0x0B 路由错误 / 0x06 间接过期 / Leave."""
    lo, hi = ts - L31_CROSS_WINDOW_S, ts + L31_CROSS_WINDOW_S
    out = {"route_error": 0, "indirect_expiry": 0, "leave": 0}
    for p in packets:
        t = p.get("ts", 0.0)
        if not (lo <= t <= hi):
            continue
        if p.get("nwk_cmd_id") == NWK_CMD_NETWORK_STATUS:
            c = p.get("nwk_status_code")
            if c in (NS_CODE_SOURCE_ROUTE_FAILURE, NS_CODE_MANY_TO_ONE_ROUTE_FAILURE):
                # 0x0B (下行源路由) / 0x0C (上行 MTORR) 均属 L3-5 路由失效
                out["route_error"] += 1
            elif c == NS_CODE_INDIRECT_EXPIRY:  # 0x06 (L6-S3)
                out["indirect_expiry"] += 1
        elif p.get("nwk_cmd_id") == NWK_CMD_LEAVE:
            out["leave"] += 1
    return out


def _has_app_response(packets: list[dict], p: dict) -> bool:
    """命令帧 p 的接收方是否有应用层响应 (2s 窗口内反向数据帧).

    返回 True = 命令送达且接收方有应用层交互 (设备以响应确认, 非"命令无确认")。
    三级证据 (素材实证, 2026-08-07): 同 ZCL tsn 铁证 / 同 cluster / cluster 缺失降级。
    """
    src, dst = p.get("nwk_src"), p.get("nwk_dst")
    ts0 = p.get("ts", 0.0)
    if src is None or dst is None or ts0 == 0.0:
        return False
    hi = ts0 + L31_APP_RESP_WINDOW_S
    tsn = p.get("zcl_seq")
    cluster = p.get("aps_cluster")
    for q in packets:
        if q.get("pkt_type") == "APS Ack":
            continue
        t = q.get("ts", 0.0)
        if not (ts0 < t <= hi):
            continue
        if q.get("nwk_src") != dst or q.get("nwk_dst") != src:
            continue  # 只认接收方 → 发送方的数据帧 (反向)
        if tsn is not None and q.get("zcl_seq") == tsn:
            return True  # ① 同 ZCL 事务序列号 (响应命令, 铁证)
        if cluster is not None and q.get("aps_cluster") == cluster:
            return True  # ② 同 cluster (应用层响应/状态报告)
        if cluster is None:
            return True  # ③ 命令帧 cluster 不可解析 → 任一反向数据帧 (降级)
    return False


def detect_l3_1(packets: list[dict]) -> dict:
    """发送命令无 APS Ack 检测 (文档 L3-1.md v1.0).

    规则 (MCP 核对 2026-08-06):
      - R1 : 数据帧 aps_ack_req=True 且 5s 配对窗口无 ack → 无确认 (中置信, 字段级)
      - R2 : R1 + 同 counter 重发 ≥2 (栈内重传证据) → 栈确认失败 (高置信, 非 SED 近铁证)
            ⚠️ 重发次数不做硬阈值上限 (应用层可叠加, 社区案例 23 条)
      - R3 : 交叉归因 — 伴随 0x0B → L3-5; 0x06 → L6-S3; Leave → 离线
      - R4 : 方向细分 — 下行 (协调器→设备=控制失败) / 上行 (上报丢失)
      设备级收敛: 同设备同方向无 ack ≥2 次才输出结论 (排除单帧瞬态/抓包盲区)
    """
    from ..aps_pairing import build_ack_match
    ack_to_orig, _ = build_ack_match(packets)

    # 事务级无 ack 判定: 有 ack 的事务 = ack_to_orig 里任一被确认帧的 (nwk_src, aps_counter);
    # 重传帧 (同 counter) 只需最近一帧被 ack 配对, 整个事务即算"有 ack" (修正 2026-08-06)
    acked_txn = {(packets[oi].get("nwk_src"), packets[oi].get("aps_counter"))
                 for oi in ack_to_orig.values()}
    # 无 ack 帧 = ack_req=True 且其事务无任何 ack 配对
    no_ack: list[tuple[int, dict]] = []
    for i, p in enumerate(packets):
        if p.get("aps_ack_req") and p.get("pkt_type") != "APS Ack" \
                and (p.get("nwk_src"), p.get("aps_counter")) not in acked_txn:
            no_ack.append((i, p))

    # 2026-08-07 自审修正: 排除"无独立 ack 但接收方回了应用层响应"的帧 —
    # 设备固件以 ZCL 响应/状态报告确认送达, 不回独立 ack 帧 (设备行为差异, 非故障)
    app_ack = [(i, p) for i, p in no_ack if _has_app_response(packets, p)]
    no_ack = [(i, p) for i, p in no_ack if not _has_app_response(packets, p)]

    # 重传统计: 同 (nwk_src, aps_counter) 去重复捕获 (同 counter+mac_seq = 物理帧被抓两次)
    # 后的帧数 (栈内重传; 新 counter = 应用新事务不计)
    retry_cnt: dict[tuple, int] = defaultdict(int)
    seen_mac: set = set()
    for p in packets:
        s, c = p.get("nwk_src"), p.get("aps_counter")
        if s is None or c is None or p.get("pkt_type") == "APS Ack":
            continue
        mkey = (s, c, p.get("mac_seq"))
        if mkey in seen_mac:
            continue
        seen_mac.add(mkey)
        retry_cnt[(s, c)] += 1

    # 按设备+方向聚合
    dev_map: dict[tuple, dict] = {}
    for i, p in no_ack:
        src, dst = p.get("nwk_src"), p.get("nwk_dst")
        downlink = dst != 0x0000  # 目标非协调器 = 下行 (网关→设备)
        key = (src, dst if downlink else src)  # 设备视角: 下行按 dst, 上行按 src
        agg = dev_map.setdefault(key, {
            "device": dst if downlink else src,
            "direction": "downlink" if downlink else "uplink",
            "count": 0, "retries": [], "cross": {"route_error": 0, "indirect_expiry": 0, "leave": 0},
            "clusters": defaultdict(int), "first_ts": p.get("ts", 0.0), "last_ts": p.get("ts", 0.0),
            "first_pid": None, "last_pid": None,
        })
        agg["count"] += 1
        agg["first_ts"] = min(agg["first_ts"], p.get("ts", 0.0))
        agg["last_ts"] = max(agg["last_ts"], p.get("ts", 0.0))
        if agg["first_pid"] is None:
            agg["first_pid"] = p.get("packet_id")
        agg["last_pid"] = p.get("packet_id")
        agg["clusters"][p.get("aps_cluster_name") or "?"] += 1
        agg["retries"].append(retry_cnt.get((p.get("nwk_src"), p.get("aps_counter")), 1))
        cs = _cross_signals(packets, p.get("ts", 0.0))
        for k in agg["cross"]:
            agg["cross"][k] += cs[k]

    results = []
    evidence = []
    for agg in dev_map.values():
        if agg["count"] < L31_MIN_NO_ACK_PER_DEV:
            continue  # 单帧瞬态/盲区, 不输出
        max_retry = max(agg["retries"])
        cross = agg["cross"]
        cross_hints = []
        if cross["route_error"]:
            cross_hints.append("L3-5 源路由失效")
        if cross["indirect_expiry"]:
            cross_hints.append("L6-S3 间接过期")
        if cross["leave"]:
            cross_hints.append("设备离线/被踢")
        # 置信度: R2 (重发) + 交叉 → 高; 仅 R1 + 交叉 → 中; 仅 R1 → 中 (收敛后)
        conf, rule = "中", "R1"
        if max_retry >= L31_RETRY_THRESHOLD:
            conf, rule = "高", "R2"
        if cross_hints:
            hint_s = " 交叉: " + "/".join(cross_hints)
        else:
            hint_s = " 无交叉信号 (抓包盲区或设备侧)"
        summary = (f"命令无 APS Ack ×{agg['count']} ({'下行' if agg['direction']=='downlink' else '上行'}, "
                   f"重发最多 ×{max_retry}){hint_s}")
        results.append({
            "device": agg["device"], "verdict": "L3-1_HIT",
            "sub_rule": rule, "confidence": conf,
            "direction": agg["direction"],
            "no_ack_count": agg["count"],
            "retry_max": max_retry,
            "cross": agg["cross"],
            "summary": summary,
        })
        # 证据帧: 设备级首末帧的真实帧号 (人工复核定位用)
        for ts, pid in ((agg["first_ts"], agg["first_pid"]), (agg["last_ts"], agg["last_pid"])):
            evidence.append(_ev(ts, pid, "L3-1", summary))

    ev, ev_total = _cut(evidence)
    if results:
        verdict, conf = "L3-1_HIT", max(r["confidence"] for r in results)
        total = sum(r["no_ack_count"] for r in results)
        excl = f"; 另有 {len(app_ack)} 帧无独立 ack 但接收方有应用层响应 (设备以响应确认, 未计入)" \
            if app_ack else ""
        concl = (f"发送命令无 APS Ack ×{total} (方向: 下行 {sum(1 for r in results if r['direction']=='downlink')} 设备"
                 f" / 上行 {sum(1 for r in results if r['direction']=='uplink')} 设备){excl}")
    else:
        verdict, conf = ("HEALTHY", "高") if no_ack else ("INCONCLUSIVE", "低")
        excl = (f"全部无 ack 帧均有应用层响应 ({len(app_ack)} 帧, 设备以响应确认, 非 L3-1)"
                if app_ack else "")
        concl = "未发现命令无确认" if verdict == "HEALTHY" else "无 ack 候选帧 (需含 ack_req 字段素材)"
        if excl:
            concl = f"未发现命令无确认 ({excl})"
    return {
        "scenario": "L3-1", "verdict": verdict, "confidence": conf,
        "summary": concl, "conclusion": concl,
        "no_ack_total": len(no_ack), "devices": results,
        "app_ack_absent_total": len(app_ack),  # 无独立 ack 但有应用层响应 (非故障, 2026-08-07)
        "evidence": ev, "evidence_total": ev_total,
    }


# ── L3-9 判定参数 (MCP 核对 2026-08-10, 见 L3-9.md v1.0) ──
# LS 机制: 路由器 15-16s 周期 1-hop 广播 (官方); in_cost 1-7 本地测量, out_cost 0=未知;
# out=0 初期正常 (2-3 次交换才有成本估计) — 持续性判定必须时间序列
L39_COST_DIFF = 3        # R1: 双向 in_cost 差 ≥3 (cost 1-7 显著差)
L39_MIN_REPORTS = 2      # R1: 双方各 ≥2 次报告 (排除单次交换噪声)
L39_TIME_ALIGN_S = 60.0  # R1: 双方最新报告时间差 >60s 跳过 (LS 周期 15-16s, 60s≈4 次交换;
                         # 自审 2026-08-10: 初版无时间对齐, 跨时段比较失真)
L39_ONEWAY_MIN = 3       # R2: one-way 判定需报告 ≥3 次
L39_ONEWAY_TAIL = 0.5    # R2: 最后 50% 报告 out_cost=0 才算持续 (排除初期未交换)
L39_ONEWAY_REPORTS_MIN = 3  # R2 尾部至少 2 条


def detect_l3_9(packets: list[dict], l3_5_result: dict | None = None) -> dict:
    """非对称链路检测 (文档 L3-9.md v1.0).

    规则 (MCP 核对 2026-08-10):
      - R1 : 同一对节点双向 LS 报告 in_cost 差 ≥3 且双方各 ≥2 次 → 不对称候选 (中置信)
            ⚠️ 双方最新报告时间差 >60s 跳过 (跨时段比较失真, 自审修正 2026-08-10)
      - R2 : (A,B) 报告 ≥3 次且最后 50% out_cost=0 → 持续 one-way 候选 (中置信)
            ⚠️ out=0 初期正常 (2-3 次交换) — 必须时间序列持续判定;
            ⚠️ 目标邻居必须自己发过 LS (路由器) — 终端不参与 LS, out=0 正常态
      - R3 : 方向性失败交叉 (0x0B 下行/0x0C 上行, 由 l3_5_result 传入) —
            命中链路端点 ∩ L3-5 方向性失败设备 → 交叉提示 (不单独判 HIT)
      素材实证 (2026-08-10): 三素材无 R1/R2 正例 (待素材); G32 BE5A↔协调器
      对称 in=1/out=1 ×187/40min 负例不误报
    """
    # 1. 收集 (sender, neighbor) -> [(in_cost, out_cost, ts, packet_id)]
    rep: dict[tuple, list] = defaultdict(list)
    for p in packets:
        if p.get("nwk_cmd_id") == 8 and p.get("link_status_neighbors"):
            src = p.get("nwk_src")
            if src is None:
                continue
            for nb in p["link_status_neighbors"]:
                key = (src, nb["addr"])
                rep[key].append((nb["in_cost"], nb["out_cost"],
                                 p.get("ts", 0.0), p.get("packet_id")))

    asym_links: list[dict] = []
    oneway_links: list[dict] = []

    # 2. R1: 双向 in_cost 差 ≥3 (用最新报告 — LS in_cost 是滚动平均, 当前状态)
    # 自审 2026-08-10: 加时间对齐 — 双方最新报告时间差 >60s 跳过 (跨时段比较失真)
    done: set = set()
    for (a, b), costs in rep.items():
        if (b, a) not in rep or tuple(sorted((a, b))) in done:
            continue
        done.add(tuple(sorted((a, b))))  # 排序对去重 (自审单测发现: 初版同序去重, 双向遍历会重复输出)
        ra, rb = rep[(a, b)], rep[(b, a)]
        if len(ra) < L39_MIN_REPORTS or len(rb) < L39_MIN_REPORTS:
            continue
        if abs(ra[-1][2] - rb[-1][2]) > L39_TIME_ALIGN_S:
            continue  # 最新报告时间差过大, 不比较 (时间对齐失败)
        a_in = ra[-1][0]   # a 报告 b 的 in_cost = a→b 接收质量
        b_in = rb[-1][0]   # b 报告 a 的 in_cost = b→a 接收质量
        if abs(a_in - b_in) >= L39_COST_DIFF:
            asym_links.append({
                "a": a, "b": b,
                "a_in": a_in, "b_in": b_in, "diff": abs(a_in - b_in),
                "reports": (len(ra), len(rb)),
                "evidence": (ra[-1][3], rb[-1][3]), "ts": ra[-1][2],
            })

    # 3. R2: 持续 one-way (全程 out=0)
    # ⚠️ 前提 1: 目标邻居 b 自己也是路由器 (发过 LS) — 终端不发 LS (官方), out=0 对非路由器是正常态
    # ⚠️ 前提 2 (自审修正 2026-08-10): 双向数据可见 — (b,a) 也存在于 rep
    #    (b 的 LS 被抓到且列出 a)。out=0 成因: b 未发 LS / b 的 LS 未捕获 (稀疏覆盖) /
    #    b 未列 a / a 收不到 b 的 LS。test2 pcap 素材 68% out=0 大规模误报 —
    #    大网络每个路由器仅 ~1.3 条 LS, 无 2-3 次交换 (官方: 交换前 out=0 是初始态),
    #    加上单抓包器覆盖不足 — out=0 是正常态; 仅当双向数据可见时 out=0 才有故障性判定意义
    # ⚠️ 前提 3 (自审修正 2026-08-10): 全程 out=0 — 前段有值后归 0 是 stale 重置
    #    (官方: age>6 时 outgoing cost 重置为 0) = 邻居停止发 LS (静默/离线, L2-6 场景),
    #    非 one-way; test2 剩余 5 条全为 stale 模式 (0xA92C 曾 out=1, 7F5D 停发后归 0)
    ls_senders = {k[0] for k in rep}
    for (a, b), costs in rep.items():
        if len(costs) < L39_ONEWAY_MIN or b not in ls_senders or (b, a) not in rep:
            continue
        if not all(c[1] == 0 for c in costs):
            continue  # 前段 out>0 = stale 重置, 非 one-way
        oneway_links.append({
            "a": a, "b": b,
            "in_cost": costs[-1][0], "out_cost": 0,
            "reports": len(costs),
            "evidence": costs[-1][3], "ts": costs[-1][2],
        })

    # 4. R3: 方向性失败交叉 (自审 2026-08-10 补实现 — 文档 v1.0 第 4 层规则, 初版代码缺失)
    # 命中链路端点 ∩ L3-5 方向性失败设备 → 交叉提示 (不单独判 HIT; 需现场确认)
    r3_hits: list[int] = []
    if l3_5_result:
        l35_devs = {d.get("device") for d in (l3_5_result.get("devices") or [])
                    if (d.get("verdict") or "").startswith("L3-5_HIT")}
        link_devs = set()
        for ln in asym_links + oneway_links:
            link_devs.update((ln["a"], ln["b"]))
        r3_hits = sorted(l35_devs & link_devs)

    # 5. 结论
    evidence = []
    for ln in asym_links:
        for pid in ln["evidence"]:
            evidence.append(_ev(
                ln["ts"], pid, "Link Status",
                f"不对称: {_addr4(ln['a'])}→{_addr4(ln['b'])} in={ln['a_in']} vs {_addr4(ln['b'])}→{_addr4(ln['a'])} in={ln['b_in']} (差{ln['diff']})"))
    for ln in oneway_links:
        evidence.append(_ev(
            ln["ts"], ln["evidence"], "Link Status",
            f"one-way: {_addr4(ln['a'])}→{_addr4(ln['b'])} in={ln['in_cost']} out=0 (×{ln['reports']} 报告全程 out=0)"))

    ev, ev_total = _cut(evidence)
    r3_txt = ""
    if r3_hits:
        r3_txt = ("; ⚠️ 方向性失败交叉 (L3-5): " + ", ".join(_addr4(d) for d in r3_hits)
                  + " 同时命中路由失效 — 非对称为候选根因之一 (需现场确认)")
    if asym_links or oneway_links:
        verdict, conf = "L3-9_HIT", "中"
        parts = []
        for ln in asym_links:
            parts.append(f"{_addr4(ln['a'])}↔{_addr4(ln['b'])} 双向成本不对称 (in {ln['a_in']} vs {ln['b_in']})")
        for ln in oneway_links:
            parts.append(f"{_addr4(ln['a'])}→{_addr4(ln['b'])} 持续 one-way (out=0)")
        summary = "非对称链路候选: " + "; ".join(parts)
        conclusion = summary + " — 需现场确认 (发射功率/灵敏度差异等设备侧因素)" + r3_txt
    elif rep:
        # 有 LS 双向数据 (检测可行) 且无命中 → 负例
        verdict, conf = "HEALTHY", "高"
        summary = f"未发现非对称链路 (LS 双向报告 {len(rep)} 对, in/out 成本对称)"
        conclusion = "未发现链路质量不对称" + r3_txt
    else:
        verdict, conf = "INCONCLUSIVE", "低"
        summary = "无 Link Status 双向报告 (需含 LS 帧素材或 ≥2 台路由器)"
        conclusion = "无法判定链路对称性: 素材无 Link Status 数据"

    return {
        "scenario": "L3-9", "verdict": verdict, "confidence": conf,
        "summary": summary, "conclusion": conclusion,
        "asymmetric_links": asym_links, "oneway_links": oneway_links,
        "cross": {"directional_failure": r3_hits},  # R3 交叉 (L3-5 方向性失败设备)
        "evidence": ev, "evidence_total": ev_total,
    }


# ── L3-2 判定参数 (MCP 核对 2026-08-12, 见 L3-2.md) ──
# ZCL status 码 (EmberAfStatus 枚举, MCP 官方): 0x00=SUCCESS, 0x01=FAILURE,
# 0x86=UNSUPPORTED_ATTRIBUTE, 0x87=INVALID_VALUE, 0x88=READ_ONLY, 0x8B=NOT_FOUND,
# 0xC0=HARDWARE_FAILURE, 0xC1=SOFTWARE_FAILURE, 0xC3=UNSUPPORTED_CLUSTER
L32_MIN_ERR_PER_DEV = 2   # 同设备错误响应 ≥2 才输出 (排除单帧瞬态)

ZCL_STATUS_NAMES = {
    0x00: "成功", 0x01: "失败", 0x86: "属性不支持", 0x87: "值无效",
    0x88: "只读", 0x89: "空间不足", 0x8B: "未找到", 0x8C: "属性不可上报",
    0x8D: "数据类型无效", 0x80: "命令格式错误", 0x81: "不支持簇命令",
    0x82: "不支持通用命令", 0x85: "字段无效", 0xC0: "硬件故障",
    0xC1: "软件故障", 0xC2: "校准错误", 0xC3: "不支持簇",
}


def detect_l3_2(packets: list[dict]) -> dict:
    """命令送达未执行检测 (文档 L3-2.md v1.0).

    规则 (MCP 核对 2026-08-12):
      - R1 : ZCL 响应 status ≠ 0 → 命令送达但设备未执行 (候选)
            status 分类: 0x86 属性不支持 (应用层固件问题) / 0x01 通用失败 /
            0x80-0x8D 格式/字段问题 / 0xC0/C1 硬件软件故障
      - R2 : 方向细分 — 下行命令 (协调器→设备) 错误响应 = 控制失败 (用户可感知);
            上行 = 设备上报失败
      收敛: 同设备错误响应 ≥2 才输出 (排除单帧瞬态)
      交叉: 有错误响应 = 命令送达 (与 L3-1 无 ack 互补 — 设备回复了, 只是拒绝执行)
      素材实证 (2026-08-12): 第七次 Write Attr Rsp status=0x86 ×16 (含 0xFFDE 厂商属性被拒)
    """
    # 1. 收集错误响应帧
    err_frames: list[tuple[int, dict]] = []
    for i, p in enumerate(packets):
        st = p.get("zcl_status")
        if st is not None and st != 0:
            err_frames.append((i, p))

    # 2. 按设备聚合 (响应者 = nwk_src)
    dev_map: dict[int, dict] = {}
    for i, p in err_frames:
        dev = p.get("nwk_src")
        if dev is None:
            continue
        # 方向语义 (自审修正 2026-08-12): 响应者=协调器 → 协调器拒绝设备命令;
        # 响应者=设备 → 设备拒绝协调器下行命令
        if dev == 0x0000:
            direction = "coordinator_reject"
        else:
            direction = "downlink" if p.get("nwk_dst") == 0x0000 else "uplink"
        agg = dev_map.setdefault(dev, {
            "device": dev, "direction": direction,
            "count": 0, "status": {}, "clusters": {}, "first_ts": p.get("ts", 0.0),
            "last_ts": p.get("ts", 0.0), "first_pid": None,
        })
        agg["count"] += 1
        s = p.get("zcl_status")
        agg["status"][s] = agg["status"].get(s, 0) + 1
        cl = p.get("aps_cluster_name") or "?"
        agg["clusters"][cl] = agg["clusters"].get(cl, 0) + 1
        agg["last_ts"] = max(agg["last_ts"], p.get("ts", 0.0))
        if agg["first_pid"] is None:
            agg["first_pid"] = p.get("packet_id")

    # 3. 判定
    results = []
    evidence = []
    for dev, agg in sorted(dev_map.items()):
        if agg["count"] < L32_MIN_ERR_PER_DEV:
            continue
        # status 白话汇总
        st_parts = []
        for s, n in sorted(agg["status"].items()):
            name = ZCL_STATUS_NAMES.get(s, f"0x{s:02X}")
            st_parts.append(f"{name}×{n}")
        if agg["direction"] == "coordinator_reject":
            dir_txt = "协调器拒绝设备命令"
        elif agg["direction"] == "downlink":
            dir_txt = "设备拒绝下行命令"
        else:
            dir_txt = "上行响应"
        cluster_txt = ", ".join(f"{k}×{v}" for k, v in
                                sorted(agg["clusters"].items(), key=lambda x: -x[1])[:3])
        summary = (f"命令送达但未执行: ZCL 错误响应 ×{agg['count']} "
                   f"({', '.join(st_parts)}, {dir_txt}, {cluster_txt})")
        # 置信度 (自审修正 2026-08-12): 仅 0x01 通用失败 = 弱信号 → 低;
        # 含明确码 (0x86/0xC3/0xC0/C1 等) → 中
        conf = "低" if set(agg["status"]) == {0x01} else "中"
        results.append({
            "device": dev, "verdict": "L3-2_HIT", "sub_rule": "R1",
            "confidence": conf, "direction": agg["direction"],
            "error_count": agg["count"], "status": agg["status"],
            "clusters": agg["clusters"], "summary": summary,
        })
        evidence.append(_ev(agg["first_ts"], agg["first_pid"], "L3-2", summary))

    ev, ev_total = _cut(evidence)
    if results:
        verdict, conf = "L3-2_HIT", "中"
        total = sum(r["error_count"] for r in results)
        names = ", ".join(f"0x{r['device']:04X}" for r in results)
        conclusion = f"命令送达但设备未执行 ×{total} ({names}) — 应用层拒绝 (固件/配置), 需设备侧确认"
    elif err_frames:
        # 有错误响应但设备级 <2 → 瞬态
        verdict, conf = "HEALTHY", "高"
        conclusion = f"仅 {len(err_frames)} 帧 ZCL 错误响应 (单帧瞬态, 未收敛)"
    elif any(p.get("zcl_status") is not None for p in packets):
        verdict, conf = "HEALTHY", "高"
        conclusion = "未发现命令送达未执行 (ZCL 响应全部成功)"
    else:
        verdict, conf = "INCONCLUSIVE", "低"
        conclusion = "无法判定: 素材无 ZCL 响应 status 数据 (cubx 支持; pcap 待 P5)"

    return {
        "scenario": "L3-2", "verdict": verdict, "confidence": conf,
        "summary": conclusion, "conclusion": conclusion,
        "devices": results, "evidence": ev, "evidence_total": ev_total,
    }


# ── L3-3 判定参数 (MCP 核对 2026-08-12, 见 L3-3.md) ──
# ZCL 上报机制 (官方): 属性变化 + minInterval 已过 / maxInterval 到 才触发 Report;
# playbook P1-3: Write → Report 正常 <1s; taxonomy: >10s 或无 Report = 滞后
L33_WRITE_REPORT_GAP_S = 10.0   # Write 成功 → 同 cluster Report 间隔阈值
L33_LOOKAHEAD_S = 300.0         # Write 后观察窗口 (5min)
L33_MIN_WRITES = 2              # 设备级: 滞后 Write ≥2 次才输出 (排除单次偶发)


def detect_l3_3(packets: list[dict]) -> dict:
    """状态上报滞后检测 (文档 L3-3.md v1.0).

    规则 (MCP 核对 2026-08-12):
      - R1 : Write Attributes (0x02, 协调器→设备) **成功**后, 设备首个 Report
            Attributes (0x0A, 任何 cluster) 间隔 >10s → 滞后候选 (taxonomy 阈值)
            ⚠️ 前提 1: Write 必须成功 — 被拒 (Write Attr Rsp status≠0) 后不上报是
            正常的 (状态没变, 第七次素材 Write 全被拒 → 不报, 负例实证)
            ⚠️ 前提 2 (自审修正 2026-08-12): **不要求同 cluster** — Basic 等属性
            上报稀疏 (0xCE93 案例: Write Basic 后 15.4s 才 Basic Report, 但设备
            4.9s 已在 On/Off/Color 上报 — 同 cluster 匹配误报); 设备级沉默才是
            滞后信号 (命令执行后设备完全无任何状态上报)
      - R2 : 无 Report (Write 成功后 300s 无任何上报) → 状态不一致候选 (R1 覆盖,
            标注弱信号: 设备可能未配置上报)
      素材实证 (2026-08-12): 中继 Write 成功 + 0.0-4.9s 上报 (不误报负例);
      正例 (Write 成功但设备 10s+ 完全无上报 + 现场确认) 待素材
    """
    # ⚠️ 自审修正 (2026-08-12): frame type 守卫 (cluster-specific 0x02/0x0A 与全局
    # Write/Report 同 ID, 素材实测 56 条 cluster-specific 0x02 被误当 Write) +
    # Write 重传去重 (同 nwk_dst+aps_counter, 素材 107→35 事务)
    writes = [p for p in packets
              if p.get("zcl_cmd_id") == 0x02 and p.get("zcl_frame_type") == 0
              and p.get("nwk_src") == 0
              and p.get("nwk_dst") is not None and 0 < p.get("nwk_dst", 0) < 0xFFF0]
    reports = [p for p in packets if p.get("zcl_cmd_id") == 0x0A and p.get("zcl_frame_type") == 0]
    seen_w: set[tuple] = set()
    writes = [w for w in writes
              if not ((w.get("nwk_dst"), w.get("aps_counter")) in seen_w)
              and not seen_w.add((w.get("nwk_dst"), w.get("aps_counter")))]
    # Write 被拒集合: Write Attr Rsp (0x04) status≠0 的 (设备, cluster)
    rejected: set[tuple] = set()
    for p in packets:
        if p.get("zcl_cmd_id") == 0x04 and p.get("zcl_status") not in (None, 0):
            rejected.add((p.get("nwk_src"), p.get("aps_cluster")))

    lag_dev: dict[int, dict] = {}
    for w in writes:
        dev, cl = w.get("nwk_dst"), w.get("aps_cluster")
        if (dev, cl) in rejected:
            continue  # Write 被拒 — 状态未变, 不上报正常
        t = w["ts"]
        # 设备级: Write 后首个 Report (任何 cluster)
        nxt = [r for r in reports
               if r.get("nwk_src") == dev
               and t < r["ts"] <= t + L33_LOOKAHEAD_S]
        if nxt:
            gap = nxt[0]["ts"] - t
            if gap > L33_WRITE_REPORT_GAP_S:
                agg = lag_dev.setdefault(dev, {
                    "device": dev, "lag_count": 0, "max_gap_s": 0.0,
                    "clusters": {}, "first_ts": t, "first_pid": w.get("packet_id"),
                })
                agg["lag_count"] += 1
                agg["max_gap_s"] = max(agg["max_gap_s"], gap)
                agg["clusters"][nxt[0].get("aps_cluster")] = \
                    agg["clusters"].get(nxt[0].get("aps_cluster"), 0) + 1
        # else: 300s 无任何上报 — R2 弱信号 (设备可能未配置上报), 不单独触发

    results = []
    evidence = []
    for dev, agg in sorted(lag_dev.items()):
        if agg["lag_count"] < L33_MIN_WRITES:
            continue
        cluster_txt = ", ".join(f"{hex(k or 0)}×{v}" for k, v in
                                sorted(agg["clusters"].items(), key=lambda x: -x[1]))
        summary = (f"状态上报滞后: Write 成功 {agg['lag_count']} 次后上报间隔 "
                   f"{round(agg['max_gap_s'],1)}s (阈值 >{L33_WRITE_REPORT_GAP_S}s, {cluster_txt})")
        results.append({"device": dev, "verdict": "L3-3_HIT", "sub_rule": "R1",
                        "confidence": "中", "lag_count": agg["lag_count"],
                        "max_gap_s": round(agg["max_gap_s"], 1),
                        "clusters": agg["clusters"], "summary": summary})
        evidence.append(_ev(agg["first_ts"], agg["first_pid"], "L3-3", summary))

    ev, ev_total = _cut(evidence)
    if results:
        verdict, conf = "L3-3_HIT", "中"
        names = ", ".join(f"0x{r['device']:04X}" for r in results)
        conclusion = (f"状态上报滞后 ×{len(results)} 台 ({names}) — 命令执行后状态上报延迟, "
                      "需现场确认 (上报配置/设备固件)")
    elif writes:
        verdict, conf = "HEALTHY", "高"
        conclusion = "未发现状态上报滞后 (Write 成功后的上报间隔正常)"
    else:
        verdict, conf = "INCONCLUSIVE", "低"
        conclusion = "无法判定: 素材无 Write Attributes 命令 (需含控制命令的抓包)"

    return {
        "scenario": "L3-3", "verdict": verdict, "confidence": conf,
        "summary": conclusion, "conclusion": conclusion,
        "devices": results, "evidence": ev, "evidence_total": ev_total,
    }


# ── 入口 ──

def detect(packets: list[dict], l1_result: dict | None = None) -> dict:
    """运行全部 L3 检测 → 汇总报告."""
    l3_5 = detect_l3_5(packets, l1_result)
    return {
        "l3_5": l3_5,
        "l3_1": detect_l3_1(packets),
        "l3_9": detect_l3_9(packets, l3_5),  # R3 交叉需要 L3-5 结果 (自审修正 2026-08-10)
        "l3_2": detect_l3_2(packets),
        "l3_3": detect_l3_3(packets),
    }
