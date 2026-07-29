"""tshark 调用封装 — 查找/验证/解析 pcap → 内部 dict 格式 (兼容 CSV _packets)"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Optional

from . import zcl_defs

# ── tshark 路径查找 ──

_KNOWN_TSHARK_PATHS: list[str] = [
    r"D:\work_tool\Wireshark\tshark.exe",
    r"C:\Program Files\Wireshark\tshark.exe",
    r"C:\Program Files (x86)\Wireshark\tshark.exe",
]

if getattr(sys, "frozen", False):
    _MEIPASS = sys._MEIPASS  # type: ignore[attr-defined]
    _KNOWN_TSHARK_PATHS.insert(0, os.path.join(_MEIPASS, "tshark.exe"))
    _KNOWN_TSHARK_PATHS.insert(0, os.path.join(os.path.dirname(sys.executable), "tshark.exe"))

_cached_tshark_path: Optional[str] = None


def find_tshark() -> Optional[str]:
    """查找 tshark.exe, 返回路径或 None"""
    global _cached_tshark_path
    if _cached_tshark_path and os.path.exists(_cached_tshark_path):
        return _cached_tshark_path
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path_dir, "tshark.exe")
        if os.path.exists(candidate):
            _cached_tshark_path = candidate
            return candidate
    for candidate in _KNOWN_TSHARK_PATHS:
        if os.path.exists(candidate):
            _cached_tshark_path = candidate
            return candidate
    return None


def set_tshark_path(path: str) -> bool:
    """手动设置 tshark 路径"""
    global _cached_tshark_path
    if os.path.exists(path):
        _cached_tshark_path = path
        return True
    return False


def check_tshark(path: Optional[str] = None) -> dict:
    """验证 tshark 是否可用 → {ok, path, version}"""
    tshark = path or find_tshark()
    if not tshark:
        return {"ok": False, "path": None, "error": "tshark.exe 未找到"}
    try:
        result = subprocess.run([tshark, "--version"], capture_output=True, text=True, timeout=10)
        version_line = result.stdout.strip().split("\n")[0] if result.stdout else ""
        return {"ok": True, "path": tshark, "version": version_line}
    except Exception as e:
        return {"ok": False, "path": tshark, "error": str(e)}


# ── pcap 解析 ──

def parse_packets(
    pcap_paths: list[str],
    tshark_path: Optional[str] = None,
    progress_callback=None,
) -> list[dict]:
    """解析多个 pcap 文件, 返回合并+按时间戳排序的包列表 (内部 dict 格式)"""
    tshark = tshark_path or find_tshark()
    if not tshark:
        raise RuntimeError("tshark.exe 未找到, 请在设置中配置路径")

    all_packets: list[dict] = []
    for i, pcap_path in enumerate(pcap_paths):
        frames = _parse_single(tshark, pcap_path)
        all_packets.extend(frames)
        if progress_callback:
            progress_callback(i + 1, len(pcap_paths), len(frames))

    all_packets.sort(key=lambda p: p["ts"])
    return all_packets


def _parse_single(tshark_path: str, pcap_path: str) -> list[dict]:
    """调用 tshark -T json 解析单个 pcap, 并补充 -T fields 获取完整 relay list"""
    # ── 主解析: JSON ──
    # -o wpan.802154_fcs_ok:FALSE: 某些抓包工具导出的 pcap FCS=0xffff, tshark 默认
    #   只在 FCS 有效时解析 NWK 层 (wpan.802154_fcs_ok=TRUE), 导致全部帧被跳过。
    cmd = [tshark_path, "-r", pcap_path, "-Y", "zbee_nwk", "-T", "json",
           "-o", "wpan.802154_fcs_ok:FALSE"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(f"tshark 解析失败: {result.stderr.strip()}")

    if not result.stdout.strip():
        return []

    raw_frames = json.loads(result.stdout)

    # ── 补充: -T fields 提取完整 relay_device 列表 (JSON 多实例只保留最后一个) ──
    relay_map: dict[int, list[int]] = {}  # frame_number → [addr, ...]
    try:
        relay_cmd = [tshark_path, "-r", pcap_path, "-Y", "zbee_nwk.cmd.id == 0x05",
                     "-T", "fields", "-e", "frame.number", "-e", "zbee_nwk.cmd.relay_device",
                     "-o", "wpan.802154_fcs_ok:FALSE"]
        relay_result = subprocess.run(relay_cmd, capture_output=True, text=True, timeout=60)
        if relay_result.returncode == 0 and relay_result.stdout.strip():
            for line in relay_result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 2 and parts[1]:
                    fn = int(parts[0])
                    # tshark -T fields 多实例字段用逗号连接: "0x5b5d,0x934f"
                    addrs = []
                    for a in parts[1].split(","):
                        a = a.strip()
                        if a:
                            addr = _h(a)
                            if addr is not None:
                                addrs.append(addr)
                    if addrs:
                        relay_map[fn] = addrs
    except Exception:
        pass  # fields 提取失败不影响主流程, relay 数据可能不完整

    return [_frame_to_dict(f, relay_map) for f in raw_frames]


# ── tshark JSON → 内部 dict ──

def _frame_to_dict(tf: dict, relay_map: dict[int, list[int]] | None = None) -> dict:
    """tshark 单帧 JSON → 内部 dict (兼容 CSV _packets 格式)"""
    layers = tf.get("_source", {}).get("layers", {})

    # 时间戳 — tshark 4.6 返回 ISO 格式, 需要解析
    frame = layers.get("frame", {})
    ts_raw = frame.get("frame.time_epoch", "0")
    try:
        ts = float(ts_raw)
    except ValueError:
        # ISO 格式: "2026-06-18T20:16:53.796795+00:00"
        from datetime import datetime
        dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        ts = dt.timestamp()

    # MAC 层 (wpan)
    wpan = layers.get("wpan", {})
    mac_fcf = int(wpan.get("wpan.fcf", "0"), 16)
    mac_frame_type = mac_fcf & 0x07
    mac_src = _h(wpan.get("wpan.src16", ""))
    mac_dst = _h(wpan.get("wpan.dst16", ""))
    mac_dst_pan = _h(wpan.get("wpan.dst_pan", ""))
    mac_src_pan = _h(wpan.get("wpan.src_pan", "")) or mac_dst_pan
    mac_seq = int(wpan.get("wpan.seq_no", "0"), 16) if wpan.get("wpan.seq_no") else None
    fcs_ok = wpan.get("wpan.fcs_ok", "0") == "1"

    # NWK 层
    nwk = layers.get("zbee_nwk", {})
    nwk_fcf = int(nwk.get("zbee_nwk.fcf", "0"), 16) if nwk.get("zbee_nwk.fcf") else 0
    nwk_secure = (nwk_fcf >> 7) & 0x01
    nwk_src = _h(nwk.get("zbee_nwk.src", ""))
    nwk_dst = _h(nwk.get("zbee_nwk.dst", ""))
    nwk_radius = int(nwk.get("zbee_nwk.radius", "0"), 16) if nwk.get("zbee_nwk.radius") else None
    nwk_seq = int(nwk.get("zbee_nwk.seqno", ""), 16) if nwk.get("zbee_nwk.seqno") else None
    nwk_src64 = _hex_colon(nwk.get("zbee_nwk.src64", ""))

    # ── NWK 命令数据提取 (Link Status 邻居表 / Route Record 中继路径) ──
    link_status_neighbors = None
    route_record_relays = None
    cmd_name = None
    cmd_data = None
    for key in nwk:
        if key.startswith("Command Frame:"):
            cmd_name = key.split(":", 1)[1].strip()
            cmd_data = nwk[key]
            break

    if cmd_name == "Link Status" and isinstance(cmd_data, dict):
        neighbors = []
        for lk, lv in cmd_data.items():
            if lk.startswith("Link ") and not any(x in lk.lower() for x in ("count", "first", "last")):
                if isinstance(lv, dict):
                    nb_addr = _h(lv.get("zbee_nwk.cmd.link.address", ""))
                    if nb_addr is not None:
                        neighbors.append({
                            "addr": nb_addr,
                            "in_cost": int(lv.get("zbee_nwk.cmd.link.incoming_cost", "0")),
                            "out_cost": int(lv.get("zbee_nwk.cmd.link.outgoing_cost", "0")),
                        })
        link_status_neighbors = neighbors if neighbors else None

    if cmd_name == "Route Record" and isinstance(cmd_data, dict):
        relay_count = int(cmd_data.get("zbee_nwk.cmd.relay_count", "0"))
        # 优先使用 -T fields 提取的完整 relay 列表 (JSON 多实例字段只保留最后一个)
        frame_num_raw = frame.get("frame.number", "")
        frame_num = int(frame_num_raw) if frame_num_raw else None
        if frame_num is not None and relay_map and frame_num in relay_map:
            relays = relay_map[frame_num]
        else:
            relays = []
            if relay_count > 0:
                for rk, rv in cmd_data.items():
                    if "relay_device" in rk and "_tree" not in rk:
                        if isinstance(rv, dict):
                            relay_addr = _h(rv.get("zbee_nwk.cmd.relay_device", ""))
                        else:
                            relay_addr = _h(str(rv))
                        if relay_addr is not None:
                            relays.append(relay_addr)
        route_record_relays = {"count": len(relays), "relays": relays}

    # 安全头
    sec = nwk.get("ZigBee Security Header", {})
    sec_level_raw = sec.get("zbee.sec.sec_level", "")
    sec_level = int(sec_level_raw, 16) if sec_level_raw else None
    sec_frame_counter = int(sec.get("zbee.sec.counter", "0")) if sec.get("zbee.sec.counter") else None
    sec_key = _hex_colon(sec.get("zbee.sec.key", ""))
    sec_key_label = sec.get("zbee.sec.decryption_key", "")
    sec_mic = _hex_colon(sec.get("zbee.sec.mic", ""))

    # APS 层
    aps = layers.get("zbee_aps", {})
    aps_cluster_zcl = _h(aps.get("zbee_aps.cluster", ""))
    aps_cluster_zdp = _h(aps.get("zbee_aps.zdp_cluster", ""))
    aps_cluster = aps_cluster_zcl if aps_cluster_zcl is not None else aps_cluster_zdp
    aps_profile = _h(aps.get("zbee_aps.profile", ""))
    aps_counter = int(aps.get("zbee_aps.counter", "0")) if aps.get("zbee_aps.counter") else None
    aps_src_ep = int(aps.get("zbee_aps.src", ""), 16) if aps.get("zbee_aps.src") else None
    aps_dst_ep = int(aps.get("zbee_aps.dst", ""), 16) if aps.get("zbee_aps.dst") else None

    # ZCL 层
    zcl = layers.get("zbee_zcl", {})
    zcl_cmd_id = _h(zcl.get("zbee_zcl.cmd.id", ""))
    zcl_seq = int(zcl.get("zbee_zcl.cmd.tsn", ""), 16) if zcl.get("zbee_zcl.cmd.tsn") else None
    zcl_dir = _zcl_direction(zcl)

    # 解密判断 — APS 层存在(有Counter等字段)即表示 NWK payload 已解密
    decrypted = bool(aps_counter is not None or aps.get("zbee_aps.cluster") or aps.get("zbee_aps.zdp_cluster"))

    # 包类型 — 检查 ZDP/NWK/MAC 逐层确定
    pkt_type = _pkt_type(mac_frame_type, nwk, aps, decrypted)

    return {
        "ts": ts, "ch": 0,
        "pkt_type": _pkt_type(mac_frame_type, nwk, aps, decrypted),
        "pan_src": mac_src_pan, "pan_dst": mac_dst_pan,
        "mac_src": mac_src, "mac_dst": mac_dst, "mac_seq": mac_seq,
        "nwk_src": nwk_src, "nwk_dst": nwk_dst, "nwk_seq": nwk_seq,
        "security": "Decrypted" if decrypted else "Encrypted",
        "status": "Decrypted" if decrypted else ("Encrypted" if nwk_secure else ""),
        "aps_cluster": aps_cluster,
        "aps_cluster_name": zcl_defs.get_cluster_name(aps_cluster),
        "aps_profile": aps_profile,
        "aps_counter": aps_counter,
        "aps_src_ep": aps_src_ep, "aps_dst_ep": aps_dst_ep,
        "zcl_cmd_id": zcl_cmd_id,
        "zcl_cmd_name": zcl_defs.get_command_name(aps_cluster, zcl_cmd_id) if zcl_cmd_id is not None else None,
        "zcl_direction": zcl_dir,
        "zcl_seq": zcl_seq,
        "sec_level": sec_level,
        "sec_key": sec_key,
        "sec_key_label": sec_key_label,
        "sec_frame_counter": sec_frame_counter,
        "sec_mic": sec_mic,
        "decrypted": decrypted,
        "nwk_radius": nwk_radius,
        "nwk_src64": nwk_src64,
        "nwk_security": bool(nwk_secure),
        "mac_fcs_ok": fcs_ok,
        "mac_frame_type": mac_frame_type,
        "link_status_neighbors": link_status_neighbors,
        "route_record_relays": route_record_relays,
        "raw_layers": layers,
    }


# ── helpers ──

def _h(val: str) -> int | None:
    """'0x0019' → 25, '' → None"""
    val = val.strip()
    return int(val, 16) if val else None


def _hex_colon(val: str) -> str | None:
    """'b4:e3:f9:ff:...' → 'b4e3f9ff...'"""
    val = val.strip().replace(":", "")
    return val if val else None


def _zcl_direction(zcl: dict) -> str | None:
    fcf = zcl.get("Frame Control Field", {})
    if isinstance(fcf, dict):
        d = fcf.get("zbee_zcl.dir", "")
    else:
        d = zcl.get("zbee_zcl.dir", "")
    if d == "1":
        return "Server→Client"
    elif d == "0":
        return "Client→Server"
    return None


def _pkt_type(mac_ft: int, nwk: dict, aps: dict | None = None, decrypted: bool = False) -> str:
    """识别包类型 — MAC 层分类 + NWK 命令 + ZDP 命令细分"""
    mac_names = {0: "Beacon", 1: "Data", 2: "Acknowledgement", 3: "MAC Cmd"}
    base = mac_names.get(mac_ft, "Unknown")
    if mac_ft == 1:
        # Check for ZDP first (profile 0x0000 + Data FCF, not ACK)
        aps_fcf = list(aps.keys())[0] if aps else ""
        is_aps_ack = "Ack" in aps_fcf
        if is_aps_ack:
            return "APS Ack"
        if aps and aps.get("zbee_aps.profile") == "0x0000":
            zdp_cluster = aps.get("zbee_aps.zdp_cluster", "")
            zdp_names = {
                "0x0000": "ZDP: NWK Addr Req", "0x0001": "ZDP: IEEE Addr Req",
                "0x0002": "ZDP: Node Desc Req", "0x0003": "ZDP: Power Desc Req",
                "0x0004": "ZDP: Simple Desc Req", "0x0005": "ZDP: Active EP Req",
                "0x0006": "ZDP: Match Desc Req", "0x0010": "ZDP: End Dev Announce",
                "0x0013": "ZDP: Device Announce", "0x0031": "ZDP: Mgmt LQI Req",
                "0x0032": "ZDP: Mgmt Routing Req",
                "0x8002": "ZDP: Node Desc Resp", "0x8005": "ZDP: Active EP Resp",
            }
            return zdp_names.get(zdp_cluster, "ZDP Cmd") if zdp_cluster else "ZDP"
        if nwk:
            # Check for named NWK command frame in tshark JSON
            for key in nwk:
                if key.startswith("Command Frame:"):
                    return key.split(":", 1)[1].strip()
            fcf_tree = nwk.get("zbee_nwk.fcf_tree", {})
            if fcf_tree.get("zbee_nwk.frame_type") == "0x0001":
                return "NWK Cmd"
        if decrypted and aps:
            # Decrypted Data frame — allow Data if no specific type matches
            return "Data"
    return base
