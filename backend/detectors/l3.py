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


# ── 入口 ──

def detect(packets: list[dict], l1_result: dict | None = None) -> dict:
    """运行全部 L3 检测 → 汇总报告."""
    return {
        "l3_5": detect_l3_5(packets, l1_result),
        "l3_1": detect_l3_1(packets),
    }
