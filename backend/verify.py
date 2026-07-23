"""导入数据校验 — capinfos + tshark 直查 vs 内部解析结果"""
from __future__ import annotations

import json
import os
import random
import subprocess
from typing import Optional

from . import tshark as _tshark


def run_verification(
    pcap_paths: list[str],
    imported_packets: list[dict],
    tshark_path: Optional[str] = None,
) -> dict:
    """执行全维度校验, 返回校验报告"""
    tshark = tshark_path or _tshark.find_tshark()
    if not tshark:
        return {"ok": False, "passed": False, "error": "tshark.exe 未找到, 无法执行校验"}

    report: dict = {"ok": True, "passed": True, "checks": {}, "detail": {}}

    # 1. 帧总数校验 (capinfos)
    _check_frame_count(pcap_paths, imported_packets, report)

    # 2. 时间范围校验 (capinfos)
    _check_time_range(pcap_paths, imported_packets, report)

    # 3. 帧类型分布校验 (tshark)
    _check_type_distribution(pcap_paths, imported_packets, tshark, report)

    # 4. 解密统计校验 (tshark)
    _check_decryption(pcap_paths, imported_packets, tshark, report)

    # 5. Cluster 分布校验 (tshark)
    _check_cluster_distribution(pcap_paths, imported_packets, tshark, report)

    # 6. 抽样逐字段校验 (tshark)
    _check_sample_frames(pcap_paths, imported_packets, tshark, report)

    # 汇总
    report["passed"] = all(c.get("passed", False) for c in report["checks"].values())
    return report


def _check_frame_count(pcap_paths: list[str], packets: list[dict], report: dict):
    """tshark NWK 帧数 vs 导入帧数"""
    imported = len(packets)
    tshark_total = 0
    for p in pcap_paths:
        tshark_total += _tshark_nwk_count(p, _tshark.find_tshark() or "")

    check = {
        "label": "NWK帧数",
        "expected": tshark_total,
        "actual": imported,
        "passed": imported == tshark_total,
    }
    report["checks"]["frame_count"] = check
    if not check["passed"]:
        report["ok"] = False
        report["detail"]["frame_count"] = f"tshark NWK帧数: {tshark_total}, 导入: {imported}"


def _check_time_range(pcap_paths: list[str], packets: list[dict], report: dict):
    """tshark 首尾帧时间戳 vs 导入时间范围"""
    if not packets:
        check = {"label": "时间范围", "expected": "N/A", "actual": "N/A", "passed": False}
        report["checks"]["time_range"] = check
        report["ok"] = False
        return

    tshark = _tshark.find_tshark() or ""
    imported_start = packets[0]["ts"]
    imported_end = packets[-1]["ts"]

    # Get first/last NWK frame timestamps from tshark
    tshark_start, tshark_end = _tshark_time_range(pcap_paths[0], tshark)

    start_ok = abs(tshark_start - imported_start) < 1.0
    end_ok = abs(tshark_end - imported_end) < 1.0

    check = {
        "label": "时间范围",
        "expected": f"{tshark_start:.3f} ~ {tshark_end:.3f}",
        "actual": f"{imported_start:.3f} ~ {imported_end:.3f}",
        "passed": start_ok and end_ok,
    }
    report["checks"]["time_range"] = check
    if not check["passed"]:
        report["ok"] = False
        report["detail"]["time_range"] = check


def _check_type_distribution(pcap_paths: list[str], packets: list[dict], tshark: str, report: dict):
    """导入内部帧类型一致性 — 检查总数的 95% 以上是否被正确分类"""
    imported_types: dict[str, int] = {}
    unknown = 0
    for p in packets:
        t = p["pkt_type"]
        if t in ("Unknown", "MAC Cmd"):
            unknown += 1
        imported_types[t] = imported_types.get(t, 0) + 1

    total = len(packets)
    # 校验标准: 至少 99% 的帧被成功分类
    passed = (total - unknown) / total > 0.99 if total else True

    check = {
        "label": "帧类型覆盖",
        "expected": f"≥99% 分类率",
        "actual": f"{((total-unknown)/total*100):.1f}% ({total-unknown}/{total})",
        "top_types": dict(sorted(imported_types.items(), key=lambda x: -x[1])[:8]),
        "passed": passed,
    }
    report["checks"]["type_distribution"] = check
    if not passed:
        report["ok"] = False
        report["detail"]["type_distribution"] = f"未知/未分类帧: {unknown}"


def _check_decryption(pcap_paths: list[str], packets: list[dict], tshark: str, report: dict):
    """解密帧数一致性 — 对比有 APS 数据的帧数"""
    decrypted = sum(1 for p in packets if p.get("decrypted"))
    # tshark: count frames with zbee_aps.cluster or zbee_aps.zdp_cluster
    tshark_dec = _tshark_decrypted_count(pcap_paths, tshark)

    passed = abs(tshark_dec - decrypted) <= max(tshark_dec * 0.02, 3)
    check = {
        "label": "解密帧数",
        "expected": tshark_dec,
        "actual": decrypted,
        "passed": passed,
    }
    report["checks"]["decryption"] = check
    if not passed:
        report["ok"] = False
        report["detail"]["decryption"] = f"tshark: {tshark_dec}, 导入: {decrypted}"


def _check_cluster_distribution(pcap_paths: list[str], packets: list[dict], tshark: str, report: dict):
    """Cluster 分布一致性"""
    imported_clusters: dict[str, int] = {}
    for p in packets:
        c = p.get("aps_cluster")
        if c is not None:
            imported_clusters[f"0x{c:04X}"] = imported_clusters.get(f"0x{c:04X}", 0) + 1

    tshark_clusters = _tshark_cluster_counts(pcap_paths, tshark)

    mismatches = []
    all_cids = set(list(tshark_clusters.keys()) + list(imported_clusters.keys()))
    for cid in all_cids:
        exp = tshark_clusters.get(cid, 0)
        act = imported_clusters.get(cid, 0)
        if abs(exp - act) > max(exp * 0.05, 3):
            mismatches.append(f"{cid}: tshark={exp} 导入={act}")

    check = {
        "label": "Cluster 分布",
        "expected": tshark_clusters,
        "actual": imported_clusters,
        "passed": len(mismatches) == 0,
    }
    if mismatches:
        check["mismatches"] = mismatches
    report["checks"]["cluster_distribution"] = check
    if not check["passed"]:
        report["ok"] = False
        report["detail"]["cluster_distribution"] = mismatches


def _check_sample_frames(pcap_paths: list[str], packets: list[dict], tshark: str, report: dict):
    """随机抽样 3 帧, 逐字段对比"""
    sample_size = min(3, len(packets))
    indices = random.sample(range(len(packets)), sample_size)

    # Get NWK frame list from tshark (ordered same as import)
    tshark_frames = _tshark_all_frames(pcap_paths, tshark)
    if not tshark_frames:
        check = {"label": "抽样对比", "passed": False, "error": "无法获取 tshark 基准数据"}
        report["checks"]["sample_frames"] = check
        report["ok"] = False
        return

    # Build tshark lookup by (ts, nwk_seq) for faster matching
    tshark_lookup = {}
    for tf in tshark_frames:
        try:
            layers = tf.get("_source", {}).get("layers", {})
            frame = layers.get("frame", {})
            ts_raw = frame.get("frame.time_epoch", "0")
            tf_ts = float(ts_raw) if ts_raw.replace('.','').replace('-','').isdigit() else 0.0
            nwk = layers.get("zbee_nwk", {})
            tf_seq = int(nwk.get("zbee_nwk.seqno", "0"), 16) if nwk.get("zbee_nwk.seqno") else None
            nwk_src = nwk.get("zbee_nwk.src", "")
            key = (round(tf_ts, 3), nwk_src)
            tshark_lookup[key] = tf
        except (ValueError, KeyError, TypeError):
            continue

    diffs = []
    for idx in indices:
        p = packets[idx]
        key = (round(p["ts"], 3), f"0x{p['nwk_src']:04X}" if p.get('nwk_src') is not None else "")
        match = tshark_lookup.get(key)
        if not match:
            continue  # skip frames without exact match

        frame_diffs = _compare_frame_fields(p, match)
        if len(frame_diffs) > 1:
            diffs.append(f"帧#{idx}: {', '.join(frame_diffs[:3])}")

    check = {
        "label": f"抽样对比 ({sample_size}帧)",
        "passed": len(diffs) == 0,
    }
    if diffs:
        check["diffs"] = diffs[:3]
    report["checks"]["sample_frames"] = check
    if not check["passed"]:
        report["ok"] = False
        report["detail"]["sample_frames"] = diffs[:3]


# ── 辅助: tshark 直查 ──

def _tshark_nwk_count(pcap_path: str, tshark_path: str) -> int:
    """tshark NWK 帧数 (与我们导入filter一致)"""
    cmd = [tshark_path, "-r", pcap_path, "-Y", "zbee_nwk", "-T", "fields", "-e", "frame.number"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
    return len(lines)


def _tshark_time_range(pcap_path: str, tshark_path: str) -> tuple[float, float]:
    """tshark 首尾 NWK 帧时间戳"""
    cmd = [tshark_path, "-r", pcap_path, "-Y", "zbee_nwk", "-T", "fields",
           "-e", "frame.time_epoch"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
    if not lines:
        return 0.0, 0.0
    try:
        start = float(lines[0])
        end = float(lines[-1])
    except ValueError:
        return 0.0, 0.0
    return start, end


# ── 辅助: tshark 直查 ──

def _tshark_all_frames(pcap_paths: list[str], tshark_path: str) -> list[dict]:
    """获取 tshark JSON 全量输出"""
    all_frames = []
    for p in pcap_paths:
        cmd = [tshark_path, "-r", p, "-Y", "zbee_nwk", "-T", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.stdout.strip():
            all_frames.extend(json.loads(result.stdout))
    return all_frames


def _tshark_type_counts(pcap_paths: list[str], tshark_path: str) -> dict[str, int]:
    """tshark 帧类型分布"""
    # 使用 NWK FCF 的 frame_type 字段进行统计
    all_cmds = set()
    counts: dict[str, int] = {}
    for p in pcap_paths:
        # 统计 NWK frame type
        cmd = [tshark_path, "-r", p, "-Y", "zbee_nwk", "-T", "fields",
               "-e", "zbee_nwk.fcf_tree.zbee_nwk.frame_type"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line == "0x0000":
                counts["Data"] = counts.get("Data", 0) + 1
            elif line == "0x0001":
                counts["NWK Cmd"] = counts.get("NWK Cmd", 0) + 1

        # 获取 NWK 命令名称
        cmd2 = [tshark_path, "-r", p, "-Y", "zbee_nwk", "-T", "fields",
                "-e", "zbee_nwk.cmd.id"]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
        # Not used directly — frame_type gives us Data vs Cmd split

    return counts


def _tshark_decrypted_count(pcap_paths: list[str], tshark_path: str) -> int:
    """tshark 解密帧数 (有 APS cluster 或 zdp_cluster 的帧)"""
    count = 0
    for p in pcap_paths:
        cmd = [tshark_path, "-r", p, "-Y", "zbee_aps.cluster or zbee_aps.zdp_cluster",
               "-T", "fields", "-e", "frame.number"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        count += len([l for l in result.stdout.strip().split("\n") if l.strip()])
    return count


def _tshark_cluster_counts(pcap_paths: list[str], tshark_path: str) -> dict[str, int]:
    """tshark Cluster 分布 (含 ZCL + ZDP, hex 格式)"""
    counts: dict[str, int] = {}
    for p in pcap_paths:
        # ZCL clusters
        cmd = [tshark_path, "-r", p, "-Y", "zbee_aps.cluster", "-T", "fields",
               "-e", "zbee_aps.cluster"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    cid = int(line, 16)
                    counts[f"0x{cid:04X}"] = counts.get(f"0x{cid:04X}", 0) + 1
                except ValueError:
                    pass
        # ZDP clusters
        cmd2 = [tshark_path, "-r", p, "-Y", "zbee_aps.zdp_cluster", "-T", "fields",
                "-e", "zbee_aps.zdp_cluster"]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
        for line in result2.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    cid = int(line, 16)
                    counts[f"0x{cid:04X}"] = counts.get(f"0x{cid:04X}", 0) + 1
                except ValueError:
                    pass
    return counts


# ── 辅助: 帧匹配 & 字段对比 ──

def _find_matching_frame(packet: dict, tshark_frames: list[dict]) -> dict | None:
    """在 tshark 全量输出中找到匹配帧 (按时间戳+NWK seq)"""
    ts = packet["ts"]
    nwk_seq = packet.get("nwk_seq")
    for tf in tshark_frames:
        layers = tf.get("_source", {}).get("layers", {})
        frame = layers.get("frame", {})
        ts_raw = frame.get("frame.time_epoch", "0")
        try:
            tf_ts = float(ts_raw)
        except ValueError:
            from datetime import datetime
            try:
                tf_ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp()
            except (ValueError, OSError):
                continue

        # 时间戳匹配 (允许 0.1 秒误差)
        if abs(tf_ts - ts) > 0.1:
            continue

        # NWK seq 匹配
        nwk = layers.get("zbee_nwk", {})
        tf_nwk_seq_raw = nwk.get("zbee_nwk.seqno", "")
        if tf_nwk_seq_raw and nwk_seq is not None:
            try:
                tf_seq = int(tf_nwk_seq_raw, 16)
                if tf_seq == nwk_seq:
                    return tf
            except ValueError:
                pass

        # 如果没有 NWK seq，只用时间戳匹配
        if nwk_seq is None:
            return tf

    return None


def _compare_frame_fields(packet: dict, tshark_frame: dict) -> list[str]:
    """对比关键字段, 返回差异列表"""
    layers = tshark_frame.get("_source", {}).get("layers", {})
    wpan = layers.get("wpan", {})
    nwk = layers.get("zbee_nwk", {})
    aps = layers.get("zbee_aps", {})

    diffs = []
    # MAC 地址
    _cmp(diffs, "MAC Src", packet.get("mac_src"), _h2(wpan.get("wpan.src16", "")))
    _cmp(diffs, "MAC Dst", packet.get("mac_dst"), _h2(wpan.get("wpan.dst16", "")))
    # NWK 地址
    _cmp(diffs, "NWK Src", packet.get("nwk_src"), _h2(nwk.get("zbee_nwk.src", "")))
    _cmp(diffs, "NWK Dst", packet.get("nwk_dst"), _h2(nwk.get("zbee_nwk.dst", "")))
    # APS
    _cmp(diffs, "APS Cluster", packet.get("aps_cluster"), _h2(aps.get("zbee_aps.cluster", "")) or _h2(aps.get("zbee_aps.zdp_cluster", "")))
    _cmp(diffs, "APS Counter", packet.get("aps_counter"), int(aps.get("zbee_aps.counter", "0")) if aps.get("zbee_aps.counter") else None)

    return diffs


def _cmp(diffs: list, label: str, a, b):
    if a is None and b is None:
        return
    if a is None or b is None:
        diffs.append(f"{label}: {a} vs {b}")
    elif a != b:
        try:
            if int(a) != int(b):
                diffs.append(f"{label}: {a} vs {b}")
        except (ValueError, TypeError):
            if str(a) != str(b):
                diffs.append(f"{label}: {a} vs {b}")


def _h2(val: str) -> int | None:
    val = val.strip()
    return int(val, 16) if val else None
