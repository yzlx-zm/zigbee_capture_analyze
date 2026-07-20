"""Ubiqua CSV 导出解析器"""
from __future__ import annotations

import csv
import os


def parse_hex(s: str) -> int | None:
    """'0xC85E' -> 0xC85E, '' -> None"""
    s = s.strip()
    if not s:
        return None
    return int(s, 16)


def read_csv(filepath: str) -> list[dict]:
    """读取 Ubiqua 导出的 CSV, 返回扁平化包列表"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    packets = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = float(row.get("Timestamp", "0") or "0")
                packets.append({
                    "ts": ts,
                    "ch": int(row.get("Ch", "0") or "0"),
                    "pkt_type": (row.get("Packet Type") or "").strip(),
                    "pan_src": parse_hex(row.get("PAN Src", "")),
                    "pan_dst": parse_hex(row.get("PAN Dst", "")),
                    "mac_src": parse_hex(row.get("MAC Src", "")),
                    "mac_dst": parse_hex(row.get("MAC Dst", "")),
                    "mac_seq": parse_hex(row.get("MAC Seq", "")),
                    "nwk_src": parse_hex(row.get("NWK Src", "")),
                    "nwk_dst": parse_hex(row.get("NWK Dst", "")),
                    "nwk_seq": parse_hex(row.get("NWK Seq", "")),
                    "security": (row.get("Security") or "").strip(),
                    "status": (row.get("Status") or "").strip(),
                })
            except (ValueError, KeyError):
                continue
    return packets


# 广播地址
BROADCAST = {0xFFFF, 0xFFFC, 0xFFFD, 0xFFFE}


def is_unicast(addr: int | None) -> bool:
    return isinstance(addr, int) and 0x0000 <= addr < 0xFFF0


def extract_nodes(packets: list[dict]) -> dict[int, dict]:
    """提取节点: {aid: {aid, seen, pan, is_coord, types_seen}}"""
    nodes: dict[int, dict] = {}
    for p in packets:
        for addr in (p["mac_src"], p["mac_dst"], p["nwk_src"], p["nwk_dst"]):
            if not is_unicast(addr):
                continue
            if addr not in nodes:
                nodes[addr] = {"aid": addr, "seen": 0, "pan": None, "is_coord": False, "types": set()}
            nodes[addr]["seen"] += 1
            nodes[addr]["types"].add(p["pkt_type"])
            # PAN association
            pan = p["pan_src"] or p["pan_dst"]
            if pan and not nodes[addr]["pan"]:
                nodes[addr]["pan"] = pan
            # Coordinator detection (Beacon sender in its own PAN)
            if "Beacon" in p["pkt_type"] and addr == p["mac_src"]:
                nodes[addr]["is_coord"] = True
    # Clean up types
    for n in nodes.values():
        n["type_list"] = sorted(n["types"])
        del n["types"]
    return nodes
