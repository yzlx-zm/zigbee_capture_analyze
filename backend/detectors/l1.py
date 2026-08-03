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

    return {
        "scenario": "L1-1",
        "verdict": verdict,
        "confidence": confidence,
        "beacon_request_count": total,
        "hit_count": hit_count,
        "hit_rate": hit_rate,
        "max_consecutive_miss": max_consecutive_miss,
        "beacon_count": len(beacons),
        "delay_summary_ms": delay_summary,
        "requests": results,
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
        detail = {"packet_id": r.get("packet_id"), "ts": r["ts"],
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

    return {
        "scenario": "L1-2",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "assoc_req_count": len(flows),
        "success_count": len(successes),
        "no_response_count": len(no_resp),
        "rejected_count": len(rejected),
        "flows": flows,
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
        }

    # 2. 每台设备收集证据
    results = []
    for dev in sorted(joined_devs):
        ev = {
            "transport_nwk": [], "request_key": [], "transport_tclk": [],
            "verify": [], "confirm": [], "announce": [], "leave": [],
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

        dev_result = _judge_l1_3_device(dev, ev)
        results.append(dev_result)

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

    return {
        "scenario": "L1-3",
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "joined_device_count": len(results),
        "devices": results,
    }


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
            if left:
                return hit("B2-LOOP", "中",
                           f"验证循环: Confirm 后仍重发 VerifyKey/ReqKey ×{len(retries_after)}, 设备离开")
            return inconclusive(
                f"验证循环: Confirm 后仍重发 ×{len(retries_after)} (设备未离开, 需设备日志确认)", "低")
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


# ── 入口 ──

def detect(packets: list[dict]) -> dict:
    """运行全部 L1 检测 → 汇总报告."""
    return {
        "l1_1": detect_l1_1(packets),
        "l1_2": detect_l1_2(packets),
        "l1_3": detect_l1_3(packets),
    }
