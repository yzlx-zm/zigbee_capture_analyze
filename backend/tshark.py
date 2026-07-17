"""tshark 封装 — 调用 Wireshark tshark.exe, 返回解析后的包列表"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field

TSHARK = r"D:\work_tool\Wireshark\tshark.exe"

# NWK 帧类型
NWK_DATA = 0
NWK_CMD = 1

# NWK 命令
NWK_CMD_LINK_STATUS = 0x01
NWK_CMD_ROUTE_REQ = 0x02
NWK_CMD_ROUTE_REPLY = 0x03
NWK_CMD_NETWORK_STATUS = 0x04
NWK_CMD_LEAVE = 0x05
NWK_CMD_ROUTE_RECORD = 0x06


@dataclass
class Packet:
    """从 tshark JSON 提取的扁平化包数据"""
    num: int           # frame.number
    ts: float          # epoch 时间戳
    proto: str          # frame.protocols (如 "wpan:zbee_nwk:data")
    # MAC 层
    mac_src: str = ""   # wpan.src16
    mac_dst: str = ""   # wpan.dst16
    mac_pan: str = ""   # wpan.dst_pan
    # NWK 层
    nwk_src: str = ""
    nwk_dst: str = ""
    nwk_radius: int = 0
    nwk_seq: int = 0
    nwk_frame_type: int = -1  # -1=无NWK, 0=Data, 1=Cmd
    nwk_cmd_id: int = -1      # NWK命令类型 (仅 NWK Cmd)
    nwk_secure: bool = False
    # 扩展地址
    nwk_src64: str = ""
    nwk_dst64: str = ""
    # Beacon
    is_beacon: bool = False
    beacon_pan: str = ""
    beacon_ext_pan: str = ""
    beacon_permit: bool = False
    beacon_depth: int = -1
    # 元信息
    fcs_ok: bool = True
    summary: str = ""  # tshark info 字段


def _parse_hex(v: str) -> int:
    """'0xfeed' -> 0xFEED, '0xfffc' -> 0xFFFC"""
    if not v:
        return 0
    return int(v, 16)


def read_pcap(filepath: str, key_hex: str = "") -> list[dict]:
    """用 tshark 解析 pcap/pcapng, 返回扁平化包列表"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    cmd = [TSHARK, "-r", filepath, "-T", "json"]
    if key_hex:
        cmd.extend(["-o", f"uat:zigbee_key_table:\"NWK\",\"{key_hex}\"\""])

    # 一次性输出到临时文件 (避免管道阻塞)
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8")
    tmp_path = tmp.name
    tmp.close()

    try:
        with open(tmp_path, "w", encoding="utf-8") as out:
            subprocess.run(cmd, stdout=out, stderr=subprocess.DEVNULL, timeout=120, check=False)
        with open(tmp_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as e:
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    packets = []
    for item in raw:
        try:
            layers = item["_source"]["layers"]
            frame = layers.get("frame", {})
            wpan = layers.get("wpan", {})
            nwk = layers.get("zbee_nwk", {})
            beacon = layers.get("zbee_beacon", {})

            proto = frame.get("frame.protocols", "")
            ts_str = frame.get("frame.time_epoch", "0")
            try:
                from datetime import datetime
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            except (ValueError, OSError):
                ts = 0.0

            # NWK 字段
            nwk_src = nwk.get("zbee_nwk.src", "")
            nwk_dst = nwk.get("zbee_nwk.dst", "")
            nwk_ft = _parse_hex(nwk.get("zbee_nwk.frame_type", "")) if nwk else -1

            # NWK 命令类型
            nwk_cmd_id = -1
            if nwk_ft == NWK_CMD:
                cmd_raw = nwk.get("zbee_nwk.cmd", "")
                if cmd_raw:
                    nwk_cmd_id = _parse_hex(cmd_raw)

            pkt = {
                "num": int(frame.get("frame.number", 0)),
                "ts": ts,
                "proto": proto,
                "mac_src": wpan.get("wpan.src16", ""),
                "mac_dst": wpan.get("wpan.dst16", ""),
                "mac_pan": wpan.get("wpan.dst_pan", ""),
                "nwk_src": nwk_src,
                "nwk_dst": nwk_dst,
                "nwk_radius": int(nwk.get("zbee_nwk.radius", 0) or 0),
                "nwk_seq": int(nwk.get("zbee_nwk.seqno", 0) or 0),
                "nwk_frame_type": nwk_ft,
                "nwk_cmd_id": nwk_cmd_id,
                "nwk_secure": nwk.get("zbee_nwk.security", "0") == "1",
                "nwk_src64": nwk.get("zbee_nwk.src64", ""),
                "nwk_dst64": nwk.get("zbee_nwk.dst64", ""),
                "is_beacon": "zbee_beacon" in proto,
                "beacon_pan": wpan.get("wpan.src_pan", ""),
                "beacon_ext_pan": beacon.get("zbee_beacon.extended_pan_id", ""),
                "beacon_permit": beacon.get("zbee_beacon.router", "0") == "1",
                "beacon_depth": int(beacon.get("zbee_beacon.depth", -1) or -1),
                "fcs_ok": wpan.get("wpan.fcs_ok", "1") == "1",
                "summary": frame.get("frame.protocols", "")[:200],
            }
            packets.append(pkt)
        except (KeyError, ValueError, TypeError):
            continue

    return packets


def extract_nodes(packets: list[dict]) -> dict[str, dict]:
    """提取所有节点: {addr: {eui64, seen, is_coord, pan, ...}}"""
    nodes = {}
    for p in packets:
        for addr in (p["nwk_src"], p["nwk_dst"], p["mac_src"], p["mac_dst"]):
            if not addr or addr in ("0xffff", "0xfffc", "0xfffd", "0xfffe"):
                continue
            aid = _parse_hex(addr)
            if aid < 0x0001 or aid > 0xFFF7:
                continue
            addr_str = f"0x{aid:04X}"
            if addr_str not in nodes:
                nodes[addr_str] = {"addr": addr_str, "aid": aid, "eui64": "",
                                   "seen": 0, "is_coord": False, "pan": "",
                                   "depth": -1, "dev_type": "?"}
            nodes[addr_str]["seen"] += 1

        # EUI64 from extended source
        if p["nwk_src64"] and p["nwk_src"]:
            k = p["nwk_src"]
            if k in nodes:
                nodes[k]["eui64"] = p["nwk_src64"]

        # Beacon data
        if p["is_beacon"]:
            src = p["mac_src"]
            if src in nodes:
                nodes[src]["pan"] = p["beacon_pan"]
                nodes[src]["depth"] = p["beacon_depth"]
                if "zbee_beacon" in p["proto"]:
                    nodes[src]["is_coord"] = True  # beacon sender is coordinator-capable

    return nodes
