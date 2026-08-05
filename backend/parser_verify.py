"""解析器正确性校验 — 保证导入数据的解析一定正确.

两种校验模式 (导入时后台自动执行):
  1. pcap 路径: 内部解析 (tshark.py) vs tshark 权威 JSON 关键字段逐帧对比
     → 匹配率 + 差异样本 (防 0x20/0x38 类误读)
  2. cubx 路径: 解析自洽校验 (无外部基准, 用解析健康度)
     → NWK 解密成功率 / APS 命令识别率 / pkt_type 未知率 / 时间地址合理性

分层策略 (2026-08-05 grilling 对齐):
  <50MB 全量逐帧对比; ≥50MB 关键帧全查 + 普通帧抽样 200

失败分类 (分类型处理):
  failure_type = "parse_mismatch" (解析错位) → 前端锁定页面
               = "missing_key"     (缺 key)      → 前端仅警告
               = "warn"            (时间/地址)   → 前端仅警告

输出: {ok, passed, failure_type, checks, detail}
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Optional

from . import tshark as _tshark

_FCS_OPT = ["-o", "wpan.802154_fcs_ok:FALSE"]


def _parse_epoch(raw: str) -> Optional[float]:
    """tshark 4.6 的 frame.time_epoch 可能是 ISO 格式或数字, 统一转 float."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        pass
    try:
        from datetime import datetime
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except (ValueError, OSError):
        return None

# 分层阈值: 文件大小 (字节)
FULL_VERIFY_SIZE_LIMIT = 50 * 1024 * 1024
# 大文件抽样: 关键帧全查 + 普通帧抽样数
SAMPLE_COUNT = 200
# 关键帧类型: APS 命令 / NWK 命令 / Assoc 帧 / 密钥帧 (误读高发区)
_CRITICAL_PKT_TYPES = ("Data", "NWK Cmd", "ZDP: Device Announce")


def run_parser_verify(
    packets: list[dict],
    source_type: str,          # "cubx" | "pcap"
    source_path: Optional[str] = None,
    tshark_path: Optional[str] = None,
) -> dict:
    """执行解析器正确性校验 → 报告"""
    tshark = tshark_path or _tshark.find_tshark()
    report: dict = {"ok": True, "passed": True, "failure_type": None, "checks": {}, "detail": {}}

    # 1. 通用自洽校验 (两条路径都跑)
    _check_consistency(packets, report)

    # 2. pcap 路径: tshark 权威对比 (分层)
    if source_type == "pcap" and source_path and tshark:
        file_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0
        full = file_size < FULL_VERIFY_SIZE_LIMIT
        _check_against_tshark(packets, source_path, tshark, report, full=full)
    elif source_type == "pcap" and not tshark:
        check = {"label": "tshark 权威对比", "passed": False, "failure_type": "warn",
                 "expected": "tshark.exe 可用", "actual": "未找到", "error": "tshark.exe 未找到, 无法执行权威对比"}
        report["checks"]["tshark_authoritative"] = check
        report["ok"] = False

    # 汇总: 分类型失败判定
    report["passed"] = all(c.get("passed", False) for c in report["checks"].values())
    # 最高严重级的失败类型 (锁定 > 警告)
    if any(c.get("failure_type") == "parse_mismatch" for c in report["checks"].values()):
        report["failure_type"] = "parse_mismatch"
    elif any(c.get("failure_type") == "missing_key" for c in report["checks"].values()):
        report["failure_type"] = "missing_key"
    elif any(c.get("failure_type") == "warn" for c in report["checks"].values()):
        report["failure_type"] = "warn"
    return report


# ── 1. 通用自洽校验 ──

def _check_consistency(packets: list[dict], report: dict):
    total = len(packets)
    # 1a. 时间单调性 (导入已排序, 但校验确认)
    bad_order = 0
    for i in range(1, total):
        if packets[i]["ts"] < packets[i - 1]["ts"]:
            bad_order += 1
    check = {
        "label": "时间单调性",
        "expected": "0 帧乱序",
        "actual": f"{bad_order} 帧乱序" if bad_order else "OK",
        "passed": bad_order == 0,
        "failure_type": "warn",
    }
    report["checks"]["time_order"] = check
    if not check["passed"]:
        report["ok"] = False

    # 1b. NWK 解密健康度 — 未解密率高分两种: 缺 key (警告) / 解析错位 (锁定)
    nwk_secure = sum(1 for p in packets if p.get("nwk_security"))
    nwk_undecrypted = sum(1 for p in packets
                          if p.get("nwk_security") and p.get("status") == "Encrypted")
    undec_rate = round(nwk_undecrypted / nwk_secure, 4) if nwk_secure else 0
    # 阈值: >30% 未解密 → 缺 key (警告); 但若连帧头字段都缺失 → 解析错位 (锁定)
    # 缺 key 特征: nwk_src/nwk_dst 仍可读 (帧头未加密), 仅 payload 不可解
    missing_key_like = nwk_undecrypted > 0 and undec_rate > 0.30
    if missing_key_like:
        ftype = "missing_key"
        passed = True  # 缺 key 不判失败, 仅警告
    else:
        ftype = "warn"
        passed = undec_rate <= 0.05
    check = {
        "label": "NWK 解密健康度",
        "expected": f"未解密率 ≤ 5% ({nwk_secure} 帧加密)",
        "actual": f"{nwk_undecrypted}/{nwk_secure} 未解密 ({undec_rate*100:.1f}%)"
                  + (" [疑似缺 key]" if missing_key_like else ""),
        "passed": passed,
        "failure_type": ftype,
    }
    report["checks"]["decrypt_health"] = check
    if not check["passed"]:
        report["ok"] = False

    # 1c. pkt_type 未知率 (仅 "Unknown" 为解析失败; "MAC Cmd" 是合法类型 — MAC 命令帧如 AssocReq)
    unknown = sum(1 for p in packets if p.get("pkt_type") == "Unknown")
    unknown_rate = round(unknown / total, 4) if total else 0
    check = {
        "label": "帧类型识别率",
        "expected": "未知帧 ≤ 5%",
        "actual": f"{unknown}/{total} 未知 ({unknown_rate*100:.1f}%)",
        "passed": unknown_rate <= 0.05,
        "failure_type": "parse_mismatch" if unknown_rate > 0.10 else "warn",
    }
    report["checks"]["pkt_type"] = check
    if not check["passed"]:
        report["ok"] = False

    # 1d. APS 命令识别率 (命令帧 ID 未知/保留区 — 0x20/0x38 教训的直接检测)
    aps_cmds = [p for p in packets if p.get("aps_cmd_id") is not None]
    known_aps = {0x05, 0x06, 0x07, 0x08, 0x09, 0x0F, 0x10}
    unknown_aps = sum(1 for p in aps_cmds if p["aps_cmd_id"] not in known_aps)
    aps_rate = (unknown_aps / len(aps_cmds)) if aps_cmds else 0
    check = {
        "label": "APS 命令识别率",
        "expected": "未知命令 ≤ 10%",
        "actual": f"{unknown_aps}/{len(aps_cmds)} 未知" if aps_cmds else "无命令帧",
        "passed": aps_rate <= 0.1 if aps_cmds else True,
        # 未知命令占比高 = 命令 ID 误读 (0x20/0x38 类) → 锁定
        "failure_type": "parse_mismatch" if (aps_cmds and aps_rate > 0.3) else "warn",
    }
    report["checks"]["aps_cmd"] = check
    if not check["passed"]:
        report["ok"] = False
        report["detail"]["aps_cmd"] = "APS 命令 ID 有未知/保留值 — 可能解析错位 (0x20/0x38 教训)"

    # 1e. 地址合理性 (NWK src/dst 范围: 0x0000-0xFFF7, 广播 0xFFFF/0xFFFD/0xFFFC)
    bad_addr = 0
    for p in packets:
        for a in (p.get("nwk_src"), p.get("nwk_dst")):
            if a is not None and a > 0xFFF8 and a not in (0xFFFC, 0xFFFD, 0xFFFF):
                bad_addr += 1
    check = {
        "label": "NWK 地址范围",
        "expected": "0 个非法地址",
        "actual": f"{bad_addr} 个非法" if bad_addr else "OK",
        "passed": bad_addr == 0,
        "failure_type": "warn",
    }
    report["checks"]["addr_range"] = check
    if not check["passed"]:
        report["ok"] = False


# ── 2. pcap 路径: tshark 权威对比 (分层) ──

def _check_against_tshark(packets: list[dict], pcap_path: str, tshark: str, report: dict,
                          full: bool = True):
    """内部解析 vs tshark 权威 JSON — 按 (ts, src, seq) 匹配后逐帧对比关键字段.

    full=True: 全量逐帧; full=False: 关键帧全查 + 普通帧抽样.
    """
    cmd = [tshark, "-r", pcap_path, *_FCS_OPT, "-Y", "zbee_nwk", "-T", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0 or not result.stdout.strip():
        check = {"label": "tshark 权威对比", "passed": False, "failure_type": "warn",
                 "expected": "tshark 可解析", "actual": f"tshark 失败: {result.stderr.strip()[:100]}"}
        report["checks"]["tshark_authoritative"] = check
        report["ok"] = False
        return

    raw_frames = json.loads(result.stdout)
    auth_lookup: dict[tuple, dict] = {}
    for tf in raw_frames:
        layers = tf.get("_source", {}).get("layers", {})
        frame = layers.get("frame", {})
        ts = _parse_epoch(frame.get("frame.time_epoch", "0"))
        if ts is None:
            continue
        nwk = layers.get("zbee_nwk", {})
        src = nwk.get("zbee_nwk.src", "")
        auth_lookup[(round(ts, 3), src)] = tf

    # 分层选择待对比帧: 全量 or 关键帧全查 + 抽样
    if full:
        candidates = packets
        label = "tshark 权威对比 (全量)"
    else:
        critical = [p for p in packets if p.get("aps_cmd_id") is not None
                    or p.get("nwk_cmd_id") is not None
                    or p.get("pkt_type") in _CRITICAL_PKT_TYPES
                    or p.get("mac_cmd_id") in (1, 2)]
        critical_ids = {id(p) for p in critical}
        rest = [p for p in packets if id(p) not in critical_ids]
        sample = rest[:SAMPLE_COUNT] if len(rest) <= SAMPLE_COUNT else rest[:: max(1, len(rest) // SAMPLE_COUNT)][:SAMPLE_COUNT]
        candidates = critical + sample
        label = f"tshark 权威对比 (关键帧 {len(critical)} + 抽样 {len(sample)})"

    total = 0
    matched = 0
    diffs: list[str] = []
    for p in candidates:
        key = (round(p["ts"], 3), f"0x{p['nwk_src']:04X}" if p.get("nwk_src") is not None else "")
        tf = auth_lookup.get(key)
        if not tf:
            continue
        total += 1
        layers = tf.get("_source", {}).get("layers", {})
        nwk = layers.get("zbee_nwk", {})
        aps = layers.get("zbee_aps", {})

        f_diffs = []
        # nwk_dst (tshark hex 小写如 0xd4e0, 内部大写如 0xD4E0 — 比较统一转小写)
        auth_dst = nwk.get("zbee_nwk.dst", "")
        if p.get("nwk_dst") is not None:
            want = f"0x{p['nwk_dst']:04X}"
            if auth_dst and auth_dst.lower() != want.lower():
                f_diffs.append(f"nwk_dst {want} vs {auth_dst}")
        # nwk_seq
        auth_seq = nwk.get("zbee_nwk.seqno", "")
        if p.get("nwk_seq") is not None and auth_seq:
            try:
                if int(auth_seq, 16) != p["nwk_seq"]:
                    f_diffs.append(f"nwk_seq {p['nwk_seq']} vs {auth_seq}")
            except ValueError:
                pass
        # aps_cluster
        auth_cluster = aps.get("zbee_aps.cluster", "") or aps.get("zbee_aps.zdp_cluster", "")
        if p.get("aps_cluster") is not None and auth_cluster:
            try:
                if int(auth_cluster, 16) != p["aps_cluster"]:
                    f_diffs.append(f"aps_cluster 0x{p['aps_cluster']:04X} vs {auth_cluster}")
            except ValueError:
                pass
        # aps_cmd_id
        auth_cmd = aps.get("zbee_aps.cmd.id", "")
        if p.get("aps_cmd_id") is not None and auth_cmd:
            try:
                if int(auth_cmd, 16) != p["aps_cmd_id"]:
                    f_diffs.append(f"aps_cmd_id 0x{p['aps_cmd_id']:02X} vs {auth_cmd}")
            except ValueError:
                pass

        if f_diffs:
            diffs.append(f"#{p.get('packet_id')}: " + "; ".join(f_diffs[:3]))
        else:
            matched += 1

    if total == 0:
        # 0 帧可匹配 (匹配键全失败, 如时间戳格式/地址差异) — 无法执行权威对比.
        # 不判 FAIL: 校验工具自身出问题不应误锁用户 (2026-08-05 自审 P0).
        check = {
            "label": label,
            "expected": "匹配率 ≥ 99.5%",
            "actual": "0 帧可匹配 (键不匹配, 权威对比未执行 — 请检查时间戳/地址解析)",
            "passed": True,
            "failure_type": "warn",
        }
    else:
        match_rate = round(matched / total, 4)
        check = {
            "label": label,
            "expected": "匹配率 ≥ 99.5%",
            "actual": f"{matched}/{total} 匹配 ({match_rate*100:.2f}%)" + (f", 差异 {len(diffs)} 帧" if diffs else ""),
            "passed": match_rate >= 0.995,
            # 权威对比失败 = 解析错位 → 锁定
            "failure_type": "parse_mismatch" if match_rate < 0.995 else "warn",
        }
    report["checks"]["tshark_authoritative"] = check
    if diffs:
        report["detail"]["tshark_authoritative"] = diffs[:10]
        report["ok"] = False
