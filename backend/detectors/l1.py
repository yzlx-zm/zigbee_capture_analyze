"""L1 场景检测器 — 网络形成与入网 (L1-1 发现失败 / L1-2 Association 失败)

输入: cubx_reader.parse_cubx(include_mac_frames=True) 的包 dict 列表.
输出: 检测报告 dict, 按 ADR-0002 置信度分级 (高/中/低/不可判定).

判定规则来源: docs/scenarios/L1-1.md v1.2, L1-2.md v1.2
"""
from __future__ import annotations

from collections import defaultdict

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


# ── 入口 ──

def detect(packets: list[dict]) -> dict:
    """运行全部 L1 检测 → 汇总报告."""
    return {
        "l1_1": detect_l1_1(packets),
        "l1_2": detect_l1_2(packets),
    }
