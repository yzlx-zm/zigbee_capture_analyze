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
    """提取节点: {aid: {aid, seen, pan, is_coord, types_seen}}
    PAN 取该节点出现次数最多的 PAN（处理多通道 sniffer 场景）"""
    nodes: dict[int, dict] = {}
    pan_counts: dict[int, dict[int, int]] = {}  # aid -> {pan: count}
    for p in packets:
        pan = p["pan_src"] or p["pan_dst"]
        for addr in (p["mac_src"], p["mac_dst"], p["nwk_src"], p["nwk_dst"]):
            if not is_unicast(addr):
                continue
            if addr not in nodes:
                nodes[addr] = {"aid": addr, "seen": 0, "pan": None, "is_coord": False, "types": set()}
                pan_counts[addr] = {}
            nodes[addr]["seen"] += 1
            nodes[addr]["types"].add(p["pkt_type"])
            if pan:
                pan_counts[addr][pan] = pan_counts[addr].get(pan, 0) + 1
            # Coordinator detection (Beacon sender in its own PAN)
            if "Beacon" in p["pkt_type"] and addr == p["mac_src"]:
                nodes[addr]["is_coord"] = True
    # Assign most common PAN to each node
    for aid, pc in pan_counts.items():
        if pc:
            nodes[aid]["pan"] = max(pc, key=pc.get)
    # Clean up types
    for n in nodes.values():
        n["type_list"] = sorted(n["types"])
        del n["types"]
    return nodes
