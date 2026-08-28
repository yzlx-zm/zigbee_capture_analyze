"""L1 场景检测器 — 网络形成与入网 (L1-1 发现失败 / L1-2 Association 失败 / L1-3 密钥分发失败)

输入: cubx_reader.parse_cubx(include_mac_frames=True) 的包 dict 列表.
输出: 检测报告 dict, 按 ADR-0002 置信度分级 (高/中/低/不可判定).

判定规则来源: docs/scenarios/L1-1.md v1.2, L1-2.md v1.2, L1-3.md v1.2
"""
from __future__ import annotations

from collections import defaultdict

# ── APS 命令 ID (官方 zigbee_packet_types.h) ──
APS_CMD_TRANSPORT_KEY = 0x05
APS_CMD_UPDATE_DEVICE = 0x06
APS_CMD_REMOVE_DEVICE = 0x07
APS_CMD_REQUEST_KEY = 0x08
APS_CMD_VERIFY_KEY = 0x0F
APS_CMD_VERIFY_KEY_CONFIRM = 0x10
APS_KEY_TYPE_NWK = 0x01          # TransportKey 里 NWK Key 的 key_type
APS_KEY_TYPE_TC_LINK = 0x04      # TransportKey 里 TC Link Key 的 key_type
ZDP_DEVICE_ANNOUNCE = 0x0013
ZDP_MGMT_LEAVE_REQ = 0x0034   # ZDO Mgmt Leave Req — TC 踢人管理指令 (L1-4-R2b, 素材实证)
NWK_CMD_LEAVE = 0x04

# ── L1-3 判定参数 ──
KEY_RESP_WINDOW_S = 5.0          # B1: ReqKey 后等 TCLK 响应窗口 [待素材校准]
VERIFY_LOOP_RETRY_THRESHOLD = 2  # B2-LOOP: verify/reqkey 重发轮次阈值 [待素材校准]

# ── MAC 命令 ID ──
MAC_ASSOC_REQ = 1
MAC_ASSOC_RESP = 2
MAC_DATA_REQ = 4
MAC_BEACON_REQ = 7

# ── 判定参数 (v1.2 验证值) ──
BEACON_RESP_WINDOW_S = 1.0    # BeaconReq 后响应窗口 (可靠异常阈值)
ASSOC_RESP_WINDOW_S = 5.0     # AssocReq 后 AssocResp 窗口
CONSECUTIVE_MISS_THRESHOLD = 2  # 连续 MISS 次数才判 L1-1
MIN_BEACON_REQ = 3            # 至少 3 次 request 才判定 (排除单次瞬态)
ASSOC_STATUS_OK = 0x00
ASSOC_STATUS_CAPACITY = 0x01
ASSOC_STATUS_DENIED = 0x02


def _fmt_addr(v) -> str | None:
    """EUI64 hex → xx:xx:xx:xx:xx:xx:xx:xx"""
    if not v:
        return None
    return ":".join(v[i:i+2] for i in range(0, len(v), 2))


# ── 结论/证据输出 (诊断页人工复核, 2026-08-05 需求) ──
EVIDENCE_MAX = 15   # 每检测器证据帧上限 (展示截断, 总数单独统计)


def _ev(ts, pid, type_, detail, idx=None) -> dict:
    """证据条目: 时间 + 帧号 + 类型 + 关键字段 + 列表索引 (S2: 前端跳报文页用)."""
    return {"ts": round(ts, 3), "packet_id": pid, "id": idx, "type": type_, "detail": detail}


def _cut(items: list) -> tuple[list, int]:
    """证据列表截断 → (展示列表, 总数)."""
    return items[:EVIDENCE_MAX], len(items)


def _addr4(v) -> str:
    """短地址 → 0xXXXX"""
    return f"0x{v:04X}" if v is not None else "?"


# ── L1-1 检测: 信道/网络发现失败 ──

def detect_l1_1(packets: list[dict]) -> dict:
    """Beacon Request 命中率 + 响应延迟检测.

    规则 (v1.2):
      - 健康: 允许单次 MISS, 命中率可 < 100% (射频环境)
      - L1-1 判定: ≥3 次 request 且连续 ≥2 次 1s 窗口内 0 响应
      - request = 0 且网络 beacon 正常: 不可判定 (sniffer 盲区)
    """
    reqs = [p for p in packets if p.get("mac_cmd_id") == MAC_BEACON_REQ]
    beacons = [p for p in packets if p.get("mac_beacon_pan") is not None]

    # 每个 request 的 1s 窗口响应
    results = []
    for req in sorted(reqs, key=lambda p: p["ts"]):
        rt = req["ts"]
        resp = [b for b in beacons if rt <= b["ts"] <= rt + BEACON_RESP_WINDOW_S]
        pans = sorted(set(b["mac_beacon_pan"] for b in resp))
        delays = [round((b["ts"] - rt) * 1000, 1) for b in resp]
        results.append({
            "packet_id": req.get("packet_id"),
            "id": req.get("_idx"),
            "ts": rt,
            "response_count": len(resp),
            "delays_ms": delays,
            "pans": [f"0x{p:04X}" for p in pans],
            "hit": len(resp) > 0,
        })

    hit_count = sum(1 for r in results if r["hit"])
    total = len(results)
    hit_rate = round(hit_count / total, 3) if total else 0

    # 连续 MISS 检测
    max_consecutive_miss = 0
    cur = 0
    for r in results:
        if r["hit"]:
            cur = 0
        else:
            cur += 1
            max_consecutive_miss = max(max_consecutive_miss, cur)

    # 所有响应延迟
    all_delays = [d for r in results for d in r["delays_ms"]]
    delay_summary = None
    if all_delays:
        all_delays.sort()
        delay_summary = {
            "min": all_delays[0],
            "median": all_delays[len(all_delays) // 2],
            "max": all_delays[-1],
            "count": len(all_delays),
        }

    # 判定
    if total >= MIN_BEACON_REQ and max_consecutive_miss >= CONSECUTIVE_MISS_THRESHOLD:
        verdict = "L1-1_HIT"          # 连续多次无响应 → 发现失败
        confidence = "高"
    elif total >= MIN_BEACON_REQ:
        verdict = "HEALTHY"           # 有响应 (允许单次 MISS)
        confidence = "高"
    elif total == 0:
        if beacons:
            verdict = "INCONCLUSIVE"  # 无 request 但网络有 beacon → sniffer 盲区
            confidence = "不可判定"
        else:
            verdict = "INCONCLUSIVE"
            confidence = "不可判定"
    else:
        verdict = "INCONCLUSIVE"      # request 太少 (<3), 无法可靠判定
        confidence = "低"

    # 结论 (简短易懂, 诚实: 不可判定不强行结论)
    if verdict == "L1-1_HIT":
        conclusion = (f"设备找不到网络: Beacon 请求 {total} 次, 连续 {max_consecutive_miss} 次无响应 "
                      "(疑似信道/信号覆盖问题)")
    elif verdict == "HEALTHY":
        conclusion = f"网络发现正常: Beacon 请求 {total} 次, 命中 {hit_count} 次"
    elif total == 0 and beacons:
        conclusion = "无法判定: 抓包无 Beacon 请求但网络有 Beacon (sniffer 可能没听到设备)"
    elif total == 0:
        conclusion = "无法判定: 抓包中没有 Beacon 请求"
    else:
        conclusion = f"无法判定: Beacon 请求太少 ({total} 次), 数据不足"

    # 证据表 (人工复核)
    evidence = [_ev(r["ts"], r["packet_id"], "Beacon Request",
                    "命中" if r["hit"] else f"无响应 ({r['response_count']} 个 Beacon)",
                    r.get("id")) for r in results]
    evidence += [_ev(p["ts"], p.get("packet_id"), "Beacon",
                     f"PAN 0x{p['mac_beacon_pan']:04X}", p.get("_idx")) for p in beacons]
    evidence, evidence_total = _cut(evidence)

    return {
        "scenario": "L1-1",
        "verdict": verdict,
        "confidence": confidence,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "beacon_request_count": total,
        "hit_count": hit_count,
        "hit_rate": hit_rate,
        "max_consecutive_miss": max_consecutive_miss,
        "beacon_count": len(beacons),
        "delay_summary_ms": delay_summary,
        # S2: requests 明细字段前端未用, 已删 (API 膨胀, 大包 evidence 全部返回)
    }


# ── L1-2 检测: Association 失败 ──

def detect_l1_2(packets: list[dict]) -> dict:
    """Association 流程检测.

    规则 (v1.2):
      - req→resp 匹配: resp.dst64 == req.src64 (长地址)
      - status=0x00 成功 / 0x01 容量满 / 0x02 拒绝
      - 无响应型: AssocReq 后 5s 窗口无 AssocResp → 单次无响应不判定 (看重试)
      - 同 PAN 多 router 响应 status 不一致是正常
    """
    reqs = [p for p in packets if p.get("mac_cmd_id") == MAC_ASSOC_REQ]
    resps = [p for p in packets if p.get("mac_cmd_id") == MAC_ASSOC_RESP]

    # 解析 AssocResp payload
    resp_details = []
    for r in resps:
        pl = r.get("mac_cmd_payload") or b""
        detail = {"packet_id": r.get("packet_id"), "id": r.get("_idx"), "ts": r["ts"],
                  "src64": r.get("mac_src64"), "dst64": r.get("mac_dst64")}
        if len(pl) >= 3:
            detail["short_addr"] = int.from_bytes(pl[0:2], "little")
            detail["status"] = pl[2]
        resp_details.append(detail)

    # 每个 request 的响应匹配 (dst64 == req.src64, 5s 窗口)
    flows = []
    for req in sorted(reqs, key=lambda p: p["ts"]):
        rt = req["ts"]
        src64 = req.get("mac_src64")
        matched = [d for d in resp_details
                   if d["dst64"] == src64 and rt <= d["ts"] <= rt + ASSOC_RESP_WINDOW_S]
        statuses = [d.get("status") for d in matched if "status" in d]
        flow = {
            "packet_id": req.get("packet_id"),
            "id": req.get("_idx"),
            "ts": rt,
            "device": _fmt_addr(src64),
            "response_count": len(matched),
            "responses": matched,
            "statuses": [f"0x{s:02X}" for s in statuses],
            "delay_ms": [round((d["ts"] - rt) * 1000, 1) for d in matched],
        }
        # 判定: 有 status=0x00 的响应 → 成功; 无响应 → 无响应型; 只有拒绝 → 拒绝型
        if any(s == ASSOC_STATUS_OK for s in statuses):
            flow["result"] = "SUCCESS"
        elif len(matched) == 0:
            flow["result"] = "NO_RESPONSE"
        else:
            flow["result"] = "REJECTED"
        flows.append(flow)

    # 汇总判定
    successes = [f for f in flows if f["result"] == "SUCCESS"]
    no_resp = [f for f in flows if f["result"] == "NO_RESPONSE"]
    rejected = [f for f in flows if f["result"] == "REJECTED"]

    if not flows:
        verdict = "INCONCLUSIVE"
        confidence = "不可判定"
        summary = "无 Association 相关帧"
    elif rejected:
        verdict = "L1-2_HIT_REJECTED"
        confidence = "高"
        summary = "存在明确拒绝的 AssocResp"
    elif no_resp and not successes:
        verdict = "L1-2_POSSIBLE_NO_RESPONSE"
        confidence = "低"  # 单次无响应可能是瞬态, 需看重试结果
        summary = "AssocReq 无响应但无重试成功 (需设备日志佐证)"
    elif successes:
        verdict = "HEALTHY"
        confidence = "高"
        summary = f"Association 成功 ({len(successes)}/{len(flows)} 次成功, 含重试)"
    else:
        verdict = "INCONCLUSIVE"
        confidence = "低"
        summary = "未匹配到完整 req→resp"

    # 结论 (简短易懂, 诚实)
    if verdict == "L1-2_HIT_REJECTED":
        conclusion = f"设备被拒绝入网: AssocResp 明确拒绝 ({len(rejected)} 台设备)"
    elif verdict == "L1-2_POSSIBLE_NO_RESPONSE":
        conclusion = (f"设备入网申请无响应 ({len(no_resp)} 次) 且无成功 — "
                      "疑似信号覆盖问题 (低置信, 需设备日志佐证)")
    elif verdict == "HEALTHY":
        conclusion = f"设备入网申请成功 ({len(successes)}/{len(flows)} 次成功, 含重试)"
    else:
        conclusion = "无法判定: 未匹配到完整 Association 流程"

    # 证据表 (人工复核): AssocReq + AssocResp
    evidence = []
    for f in flows:
        evidence.append(_ev(f["ts"], f["packet_id"], "AssocReq",
                            f"{f['device']} → {f['result']}", f.get("id")))
        for r in f["responses"]:
            st = f"status=0x{r['status']:02X}" if "status" in r else "?"
            evidence.append(_ev(r["ts"], r["packet_id"], "AssocResp",
                                f"{st} → 0x{r.get('short_addr', 0):04X}", r.get("id")))
    evidence, evidence_total = _cut(evidence)

    return {
        "scenario": "L1-2",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "assoc_req_count": len(flows),
        "success_count": len(successes),
        "no_response_count": len(no_resp),
        "rejected_count": len(rejected),
        # S2: flows 明细字段前端未用, 已删 (API 膨胀)
    }


# ── L1-3 检测: 密钥分发失败 (Assoc 成功但拿不到/验证不了 NWK Key) ──

def detect_l1_3(packets: list[dict]) -> dict:
    """密钥分发流程检测 (文档 L1-3.md v1.2).

    规则 (官方依据 + 健康实测 + 真实故障素材确认):
      - A1: 0x05(NWK) 缺失 + Announce 缺失 + 设备重试/Leave → TC 未分发
      - A2: 0x05(NWK) 出现但设备无反应 (无 Announce/无后续) → 设备解不出
      - A' : 0x05(NWK) 缺失 + Announce 出现 → preconfigured NWK Key (排除)
      - B1 : 0x08 出现 + 5s 无 0x05(TCLK) 响应 + 设备 Leave → TC 不响应 key 请求
      - B2 : 0x05(TCLK) 出现 + 0x0F/0x10 缺失 + Leave → 验证失败
      - B2-LOOP: 0x05(TCLK)+0x10 出现但 verify/reqkey 反复重发 + Leave → 验证不收敛
      - C   : 0x10 出现 + 无反复重试 + 无 Leave → 健康
    按设备维度判定 (每台入网成功的设备独立评估), 任一命中 → L1-3_HIT.
    """
    # 1. 入网成功设备: AssocResp status=0x00 → 短地址
    joined_devs = set()
    for p in packets:
        if p.get("mac_cmd_id") != MAC_ASSOC_RESP:
            continue
        pl = p.get("mac_cmd_payload") or b""
        if len(pl) >= 3 and pl[2] == ASSOC_STATUS_OK:
            joined_devs.add(int.from_bytes(pl[0:2], "little"))

    if not joined_devs:
        return {
            "scenario": "L1-3", "verdict": "INCONCLUSIVE", "confidence": "不可判定",
            "summary": "无 Assoc 成功设备 (无入网活动)", "devices": [],
            "conclusion": "无法判定密钥分发: 抓包中没有 Association 成功的设备",
            "evidence": [], "evidence_total": 0,
        }

    # 2. 每台设备收集证据
    evidence = []  # 人工复核证据帧 (命中设备的关键帧)
    results = []
    for dev in sorted(joined_devs):
        ev = {
            "transport_nwk": [], "request_key": [], "transport_tclk": [],
            "verify": [], "confirm": [], "announce": [], "leave": [],
            "route_error": [],  # Network Status (Source Route Failure 等) 针对该设备
        }
        for p in packets:
            nsrc, ndst = p.get("nwk_src"), p.get("nwk_dst")
            cid = p.get("aps_cmd_id")
            if cid == APS_CMD_TRANSPORT_KEY:
                kt = p.get("aps_cmd_key_type")
                if kt == APS_KEY_TYPE_NWK and ndst == dev:
                    ev["transport_nwk"].append(p)
                elif kt == APS_KEY_TYPE_TC_LINK and ndst == dev:
                    ev["transport_tclk"].append(p)
            elif cid == APS_CMD_REQUEST_KEY and nsrc == dev:
                ev["request_key"].append(p)
            elif cid == APS_CMD_VERIFY_KEY and nsrc == dev:
                ev["verify"].append(p)
            elif cid == APS_CMD_VERIFY_KEY_CONFIRM and ndst == dev:
                ev["confirm"].append(p)
            elif p.get("aps_cluster") == ZDP_DEVICE_ANNOUNCE and nsrc == dev:
                ev["announce"].append(p)
            elif p.get("nwk_cmd_id") == NWK_CMD_LEAVE and (nsrc == dev or ndst == dev):
                ev["leave"].append(p)
            elif p.get("nwk_cmd_id") == 3 and p.get("nwk_status_target") == dev:
                # Network Status 路由错误, target == 本设备 (0x0B=Source Route Failure)
                ev["route_error"].append(p)

        dev_result = _judge_l1_3_device(dev, ev)
        results.append(dev_result)
        # 证据: 命中设备的密钥关键帧 (供人工复核)
        if dev_result["verdict"].startswith("L1-3"):
            _append_key_evidence(evidence, dev, ev)

    hits = [r for r in results if r["verdict"].startswith("L1-3")]
    healthies = [r for r in results if r["verdict"] == "HEALTHY"]
    if hits:
        verdict = "L1-3_HIT"
        confidence = "高" if any(r["confidence"] == "高" for r in hits) else "中"
        summary = "密钥分发/验证异常: " + ", ".join(
            f"0x{r['device']:04X} ({r['sub_rule']})" for r in hits)
    elif healthies:
        verdict = "HEALTHY"
        confidence = "高"
        summary = f"密钥流程完整 ({len(healthies)}/{len(results)} 设备验证成功)"
    else:
        verdict = "INCONCLUSIVE"
        confidence = "低"
        summary = "入网设备密钥流程未完整 (无异常判定证据)"

    # 结论 (简短易懂, 诚实)
    if hits:
        conclusion = ("密钥分发/验证异常: " + ", ".join(
            f"0x{r['device']:04X} ({r['sub_rule']})" for r in hits) +
            " — 设备拿不到密钥或验证失败" +
            (" (高置信)" if any(r["confidence"] == "高" for r in hits) else " (中置信, 需设备日志佐证)"))
    elif healthies:
        conclusion = "密钥分发流程正常 (设备成功拿到并验证密钥)"
    else:
        conclusion = "无法判定密钥分发: 入网设备密钥流程不完整 (数据不足)"

    evidence, evidence_total = _cut(evidence)
    return {
        "scenario": "L1-3",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "joined_device_count": len(results),
        "devices": results,
    }


_KEY_EV_TYPES = (
    ("transport_nwk", "TransportKey(NWK)"),
    ("transport_tclk", "TransportKey(TCLK)"),
    ("verify", "VerifyKey"),
    ("confirm", "VerifyKeyConfirm"),
    ("leave", "Leave"),
    ("announce", "Device Announce"),
)


def _append_key_evidence(evidence: list, dev: int, ev: dict) -> None:
    """L1-3 证据: 命中设备的密钥关键帧 (每类型最多 3 条)."""
    for key, label in _KEY_EV_TYPES:
        for p in ev[key][:3]:
            nsrc = _addr4(p.get("nwk_src"))
            ndst = _addr4(p.get("nwk_dst"))
            evidence.append(_ev(p["ts"], p.get("packet_id"), label,
                                f"0x{dev:04X}: {nsrc} → {ndst}", p.get("_idx")))


def _judge_l1_3_device(dev: int, ev: dict) -> dict:
    """单设备 L1-3 判定 → 规则 A1/A2/A'/B1/B2/B2-LOOP/C/INCONCLUSIVE."""
    tnwk = ev["transport_nwk"]; tclk = ev["transport_tclk"]
    rk = ev["request_key"]; vk = ev["verify"]; cf = ev["confirm"]
    ann = ev["announce"]; lv = ev["leave"]

    # Leave 方向: src=设备 → 设备主动; TC→设备 → 被踢
    leave_active = any(p.get("nwk_src") == dev for p in lv)
    leave_kicked = any(p.get("nwk_src") == 0x0000 and p.get("nwk_dst") == dev for p in lv)
    left = bool(lv)

    base = {
        "device": dev,
        "transport_nwk": len(tnwk), "request_key": len(rk),
        "transport_tclk": len(tclk), "verify": len(vk), "confirm": len(cf),
        "announce": len(ann), "leave": len(lv),
        "leave_active": leave_active, "leave_kicked": leave_kicked,
        "route_error": len(ev["route_error"]),
    }

    def hit(rule, conf, summary):
        return {**base, "verdict": "L1-3_HIT", "sub_rule": rule,
                "confidence": conf, "summary": summary}

    def healthy(summary):
        return {**base, "verdict": "HEALTHY", "sub_rule": "C",
                "confidence": "高", "summary": summary}

    def inconclusive(summary, conf="低"):
        return {**base, "verdict": "INCONCLUSIVE", "sub_rule": None,
                "confidence": conf, "summary": summary}

    # ── B2-LOOP: confirm 出现但验证不收敛 (真实素材 838D) ──
    if cf and (vk or rk):
        # 循环定义: 最后一次 confirm 之后仍有 verify/reqkey 重发 (验证未收敛).
        # 流程内的正常帧 (verify 在 confirm 前 / reqkey 在 TCLK 前) 不计入.
        last_cf = max(p["ts"] for p in cf)
        retries_after = [p for p in (vk + rk) if p["ts"] > last_cf]
        if retries_after:
            # 伴随路由错误 (Network Status) → 根因指向 L3 路由/链路层:
            # 真实素材 (中继入网抓包) 中 Confirm 经中继转发失败 (Source Route Failure),
            # 设备收不到确认而重发 — 不是密钥内容问题.
            route_errors = ev["route_error"]
            route_hint = (f", 伴随 Network Status 路由错误 ×{len(route_errors)} (疑似 Confirm 转发失败/非对称链路, L3 根因)"
                          if route_errors else "")
            if left:
                return hit("B2-LOOP", "中",
                           f"验证循环: Confirm 后仍重发 VerifyKey/ReqKey ×{len(retries_after)}, 设备离开{route_hint}")
            return inconclusive(
                f"验证循环: Confirm 后仍重发 ×{len(retries_after)} (设备未离开, 需设备日志确认){route_hint}", "低")
    # ── C: confirm 出现 + 无异常 → 健康 ──
    if cf:
        if left:
            return inconclusive(
                f"Confirm 出现但设备离开 (主动={leave_active}, 被踢={leave_kicked}) — 非密钥分发根因", "低")
        return healthy("Confirm 出现且设备未离开 (密钥验证完成)")

    # ── B2: TCLK 出现但 verify/confirm 缺失 ──
    if tclk:
        if left:
            return hit("B2", "高",
                       "TCLK 已分发但 VerifyKey/Confirm 缺失, 设备离开 (密钥验证失败)")
        return inconclusive("TCLK 已分发但 Verify/Confirm 缺失, 设备未离开", "中")

    # ── B1: ReqKey 出现 + 5s 无 TCLK 响应 ──
    if rk:
        first_rk = min(p["ts"] for p in rk)
        responded = [p for p in tclk if p["ts"] <= first_rk + KEY_RESP_WINDOW_S]
        if not responded:
            if left:
                return hit("B1", "高",
                           f"RequestKey ×{len(rk)} 无 TCLK 响应 (5s 窗口), 设备离开 (TC 不响应 key 请求)")
            return inconclusive("RequestKey 无响应但设备未离开", "中")

    # ── A2: NWK Key 出现但设备无反应 ──
    if tnwk and not ann and not vk:
        if left:
            return hit("A2", "高",
                       "TransportKey(NWK) 已发但设备无 Announce/后续 (设备解不出密钥)")
        return inconclusive("TransportKey(NWK) 已发但设备无反应, 未离开", "中")

    # ── A1: 无 NWK Key + 无 Announce ──
    if not tnwk:
        if ann:
            # A': preconfigured NWK Key (排除)
            return healthy("无 TransportKey(NWK) 但 Announce 出现 — preconfigured NWK Key 场景 (排除)")
        if left:
            return hit("A1", "高",
                       "无 TransportKey(NWK) 且无 Announce, 设备重试/离开 (TC 未分发密钥)")
        return inconclusive("无 TransportKey(NWK) 且无 Announce, 设备未离开", "中")

    # ── 兜底 ──
    if ann and not lv:
        return inconclusive("入网流程部分完成 (有 NWK Key/Announce 但密钥流程未走完)", "低")
    return inconclusive("入网设备无完整密钥流程证据", "低")


# ── L1-4 检测: TC 拒绝入网 / 运营期踢人 ──

BROADCAST_ADDR = 0xFFFD

def detect_l1_4(packets: list[dict]) -> dict:
    """TC 拒绝入网 / 运营期踢人检测 (文档 L1-4.md v1.2).

    规则 (官方依据 + 素材实证 2026-08-04):
      - R1 : Remove Device (0x07) 出现 + 目标未完成入网 (无 TransportKey(NWK)/Announce)
            → 入网阶段显式拒绝 (高置信, 官方: TC deny → Remove Device 给 parent)
      - R2a: Remove Device (0x07) 出现 + 目标已入网 → 运营期踢人 (高置信, APS 认证)
      - R2b: ZDO Mgmt Leave Req (cluster 0x0034, TC→设备) + 设备已入网
            → 运营期踢人 (高置信, ZDO 管理指令路径)
            素材实证: leave_question TC 踢 0xCBEB 走此路径 (Mgmt Leave Req ×12 可见)
      - R2c: 已入网设备广播 Leave (dst=0xFFFD, rejoin=0) + 无前置指令帧 + 无密钥验证失败上下文
            → 疑似运营期踢人 (中置信; 无法帧级排除设备自愿永久离网 — 两者广播 Leave 帧级相同,
            区别在有无前置指令帧; 指令帧可能未被 sniffer 捕获)
      - R3 : Assoc 成功 + 无 0x07 + 无 TransportKey(NWK) + 无 Announce + 设备消失/Leave
            → 静默拒绝 (中置信; 官方 ignore 路径 parent 2s 静默移除)
            ⚠️ 与 L1-3-A1 帧级重叠 → 双报提示, 需 TC/设备日志仲裁
      - EX  : 无 0x07 且 (TransportKey(NWK) 或 Announce 出现) → 排除 (TC 允许入网)
    按设备维度判定 (同 L1-3 模式), 任一命中 → L1-4_HIT.
    """
    # 1. 入网成功设备: AssocResp status=0x00 → 短地址 (同 detect_l1_3)
    joined_devs = set()
    for p in packets:
        if p.get("mac_cmd_id") != MAC_ASSOC_RESP:
            continue
        pl = p.get("mac_cmd_payload") or b""
        if len(pl) >= 3 and pl[2] == ASSOC_STATUS_OK:
            joined_devs.add(int.from_bytes(pl[0:2], "little"))

    # 2. Remove Device 事件全量 (供展示 + R1/R2a 设备匹配)
    remove_events = []
    for p in packets:
        if p.get("aps_cmd_id") == APS_CMD_REMOVE_DEVICE:
            remove_events.append({
                "packet_id": p.get("packet_id"),
                "id": p.get("_idx"),
                "ts": p["ts"],
                "nwk_src": p.get("nwk_src"),
                "nwk_dst": p.get("nwk_dst"),
                "target_eui64": p.get("aps_cmd_remove_target"),
            })

    # 3. Mgmt Leave Req (ZDP 0x0034) 事件全量 — ZDO 踢人指令 (素材实证路径)
    #    TC(0x0000) 向设备单播 Mgmt Leave Req → 设备执行 Leave
    mgmt_leave_events = []
    for p in packets:
        if p.get("aps_cluster") == ZDP_MGMT_LEAVE_REQ and p.get("nwk_src") == 0x0000:
            mgmt_leave_events.append({
                "packet_id": p.get("packet_id"),
                "id": p.get("_idx"),
                "ts": p["ts"],
                "nwk_dst": p.get("nwk_dst"),
            })

    # 4. 每台设备收集证据
    results = []
    for dev in sorted(joined_devs):
        ev = {
            "transport_nwk": [], "announce": [], "tclk": [], "verify": [], "confirm": [],
            "leave_broadcast": [], "leave_any": [],
        }
        for p in packets:
            nsrc, ndst = p.get("nwk_src"), p.get("nwk_dst")
            cid = p.get("aps_cmd_id")
            if cid == APS_CMD_TRANSPORT_KEY:
                kt = p.get("aps_cmd_key_type")
                if kt == APS_KEY_TYPE_NWK and ndst == dev:
                    ev["transport_nwk"].append(p)
                elif kt == APS_KEY_TYPE_TC_LINK and ndst == dev:
                    ev["tclk"].append(p)
            elif cid == APS_CMD_VERIFY_KEY and nsrc == dev:
                ev["verify"].append(p)
            elif cid == APS_CMD_VERIFY_KEY_CONFIRM and ndst == dev:
                ev["confirm"].append(p)
            elif p.get("aps_cluster") == ZDP_DEVICE_ANNOUNCE and nsrc == dev:
                ev["announce"].append(p)
            elif p.get("nwk_cmd_id") == NWK_CMD_LEAVE:
                if nsrc == dev:
                    ev["leave_any"].append(p)
                    # ⚠️ 2026-08-05: 部分设备自发 Leave 帧 cubx 解析 nwk_dst=None
                    # (解析缺口待查) — 设备自发 Leave 广播语义, 宽容计入
                    if ndst == BROADCAST_ADDR or ndst is None:
                        ev["leave_broadcast"].append(p)
        dev_result = _judge_l1_4_device(dev, ev, remove_events, mgmt_leave_events)
        results.append(dev_result)

    hits = [r for r in results if r["verdict"].startswith("L1-4")]
    healthies = [r for r in results if r["verdict"] == "HEALTHY"]
    if hits:
        verdict = "L1-4_HIT"
        confidence = "高" if any(r["confidence"] == "高" for r in hits) else "中"
        summary = "TC 拒绝/踢人: " + ", ".join(
            f"0x{r['device']:04X} ({r['sub_rule']})" for r in hits)
    elif healthies:
        verdict = "HEALTHY"
        confidence = "高"
        summary = f"无 TC 拒绝/踢人证据 ({len(healthies)}/{len(results)} 设备已入网且未被移除)"
    else:
        verdict = "INCONCLUSIVE"
        confidence = "低"
        summary = "无完整入网上下文 (L1-4 判定需 Assoc 成功设备)"

    # 结论 (简短易懂, 诚实)
    if hits:
        conclusion = ("TC 拒绝/踢人: " + ", ".join(
            f"0x{r['device']:04X} ({r['sub_rule']})" for r in hits) +
            (" (高置信)" if any(r["confidence"] == "高" for r in hits) else " (中置信, 疑似)"))
    elif healthies:
        conclusion = "未发现 TC 拒绝/踢人证据"
    else:
        conclusion = "无法判定 TC 拒绝: 无完整入网上下文"

    # 证据表 (人工复核): Remove Device + Mgmt Leave Req + 命中设备广播 Leave
    evidence = []
    for r in remove_events:
        evidence.append(_ev(r["ts"], r["packet_id"], "Remove Device(0x07)",
                            f"{_addr4(r['nwk_src'])} → {_addr4(r['nwk_dst'])}"
                            + (f" target={r['target_eui64']}" if r["target_eui64"] else ""),
                            r.get("id")))
    for m in mgmt_leave_events:
        evidence.append(_ev(m["ts"], m["packet_id"], "Mgmt Leave Req(0x0034)",
                            f"TC → {_addr4(m['nwk_dst'])}", m.get("id")))
    for d in hits:
        dev = d["device"]
        for p in d.get("_leave_frames") or []:
            evidence.append(_ev(p["ts"], p.get("packet_id"), "广播 Leave",
                                f"0x{dev:04X} → 广播 (rejoin={p.get('nwk_leave_rejoin')})",
                                p.get("_idx")))
        d.pop("_leave_frames", None)  # 帧对象含 bytes, 不进 API 响应
    evidence, evidence_total = _cut(evidence)

    return {
        "scenario": "L1-4",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "conclusion": conclusion,
        "evidence": evidence,
        "evidence_total": evidence_total,
        "joined_device_count": len(results),
        "remove_event_count": len(remove_events),
        "remove_events": remove_events,
        "mgmt_leave_req_count": len(mgmt_leave_events),
        "mgmt_leave_events": mgmt_leave_events,
        "devices": results,
    }


def _judge_l1_4_device(dev: int, ev: dict, remove_events: list[dict],
                       mgmt_leave_events: list[dict]) -> dict:
    """单设备 L1-4 判定 → R1/R2a/R2b/R2c/R3/HEALTHY/INCONCLUSIVE."""
    tnwk = ev["transport_nwk"]; ann = ev["announce"]
    tclk = ev["tclk"]; vk = ev["verify"]; cf = ev["confirm"]
    lb = ev["leave_broadcast"]; lany = ev["leave_any"]

    # 该设备的 Remove Device 帧: nwk_dst == 自身 (router 或直连 TC 的 ED)
    # (ED 经 parent 踢出时 dst=parent, target EUI64 匹配待增强 — 文档第 8 层已声明)
    rm_frames = [r for r in remove_events if r["nwk_dst"] == dev]
    # 该设备的 Mgmt Leave Req (TC→dev, ZDO 踢人指令)
    ml_req = [m for m in mgmt_leave_events if m["nwk_dst"] == dev]

    joined = bool(tnwk or ann)  # 已入网判据: 拿到 NWK Key 或发过 Announce

    base = {
        "device": dev,
        "remove_device": len(rm_frames),
        "mgmt_leave_req": len(ml_req),
        "transport_nwk": len(tnwk), "announce": len(ann),
        "leave_broadcast": len(lb), "leave": len(lany),
    }

    def hit(rule, conf, summary):
        return {**base, "verdict": "L1-4_HIT", "sub_rule": rule,
                "confidence": conf, "summary": summary}

    def healthy(summary):
        return {**base, "verdict": "HEALTHY", "sub_rule": None,
                "confidence": "高", "summary": summary}

    def inconclusive(summary, conf="低"):
        return {**base, "verdict": "INCONCLUSIVE", "sub_rule": None,
                "confidence": conf, "summary": summary}

    # ── R1/R2a: Remove Device 出现 (显式拒绝/踢人, 高置信) ──
    if rm_frames:
        if joined:
            return hit("R2a", "高",
                       f"Remove Device ×{len(rm_frames)} 踢已入网设备 (运营期踢人, APS 认证)")
        return hit("R1", "高",
                   f"Remove Device ×{len(rm_frames)} 拒绝入网 (设备未完成入网: 无 NWK Key/Announce)")

    # ── R2b: Mgmt Leave Req (ZDO 踢人指令, 高置信, 素材实证) ──
    if ml_req:
        if joined:
            return hit("R2b", "高",
                       f"Mgmt Leave Req (0x0034) ×{len(ml_req)} TC 指令设备离开 (ZDO 管理路径踢人)")
        return hit("R2b", "高",
                   f"Mgmt Leave Req (0x0034) ×{len(ml_req)} TC 指令未入网设备离开 (ZDO 管理路径)")

    # ── R2c: 已入网设备广播 Leave (rejoin=0) 无前置指令帧 ──
    kicked_bc = [p for p in lb
                 if p.get("nwk_leave_rejoin") == 0 and p.get("nwk_leave_request") == 0]
    if joined and kicked_bc:
        # 密钥验证失败上下文 (L1-3-B2 特征): TCLK 已分发但 Verify/Confirm 缺失
        key_fail_ctx = bool(tclk) and not (vk and cf)
        if not key_fail_ctx:
            r = hit("R2c", "中",
                    f"已入网设备广播 Leave ×{len(kicked_bc)} (rejoin=0/request=0) — "
                    "疑似运营期踢人 (无前置指令帧可见; 无法帧级排除设备自愿永久离网; "
                    "无密钥验证失败痕迹, 已排除 L1-3-B2)")
            r["_leave_frames"] = kicked_bc  # 证据帧 (供诊断页人工复核)
            return r
        return inconclusive(
            f"已入网设备广播 Leave ×{len(kicked_bc)} 但伴随 TCLK 验证失败上下文 — 归 L1-3-B2 判定", "中")

    # ── R3: 未入网 (Assoc 成功但无 key/Announce) + 设备消失/Leave → 静默拒绝 ──
    if not tnwk and not ann:
        if lany:
            return hit("R3", "中",
                       f"Assoc 成功但无 TransportKey(NWK)/Announce, 设备 Leave — 疑似 TC 静默拒绝"
                       "(官方 ignore 路径 2s 移除); ⚠️ 与 L1-3-A1 帧级重叠, 需 TC/设备日志仲裁")
        return inconclusive("Assoc 成功但无 TransportKey(NWK)/Announce, 设备未消失", "中")

    # ── 排除 ──
    if not lany:
        return healthy("已入网且无 Leave — TC 允许入网 (排除 L1-4)")
    rejoin_set = [p.get("nwk_leave_rejoin") for p in lb if p.get("nwk_leave_rejoin") is not None]
    if rejoin_set and all(r == 1 for r in rejoin_set):
        return inconclusive("已入网设备广播 Leave 但 rejoin=1 (设备暂离, 非永久离开)", "低")
    return inconclusive("已入网设备有 Leave 但未匹配踢人模式 (标志/方向不可读)", "低")


# ── 入口 ──

def detect(packets: list[dict]) -> dict:
    """运行全部 L1 检测 → 汇总报告."""
    for _i, _p in enumerate(packets):
        _p["_idx"] = _i  # S2: 证据帧列表索引 (前端跳报文页 tlJumpFrame 用)
    return {
        "l1_1": detect_l1_1(packets),
        "l1_2": detect_l1_2(packets),
        "l1_3": detect_l1_3(packets),
        "l1_4": detect_l1_4(packets),
    }
