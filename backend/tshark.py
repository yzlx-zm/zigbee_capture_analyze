"""tshark 调用封装 — 查找/验证/解析 pcap → 内部 dict 格式 (兼容 CSV _packets)"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Optional

from . import zcl_defs

# ZDP 集群名称表 (与 cubx_reader.ZDP_CLUSTER_NAMES 对齐 — 双路径契约一致)
ZDP_CLUSTER_NAMES = {
    0x0000: "ZDP: NWK Addr Req", 0x0001: "ZDP: IEEE Addr Req",
    0x0002: "ZDP: Node Desc Req", 0x0003: "ZDP: Power Desc Req",
    0x0004: "ZDP: Simple Desc Req", 0x0005: "ZDP: Active EP Req",
    0x0006: "ZDP: Match Desc Req", 0x0010: "ZDP: End Dev Announce",
    0x0013: "ZDP: Device Announce", 0x0031: "ZDP: Mgmt LQI Req",
    0x0032: "ZDP: Mgmt Routing Req",
    0x8000: "ZDP: NWK Addr Resp", 0x8001: "ZDP: IEEE Addr Resp",
    0x8002: "ZDP: Node Desc Resp", 0x8005: "ZDP: Active EP Resp",
}

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


def parse_mac_frames(tshark_path: str, pcap_path: str) -> list[dict]:
    """提取 pcap 的 MAC 命令帧 + Beacon (L1-1/L1-2 入网检测需要).

    字段对齐 cubx_reader 的 mac_* 命名:
      mac_cmd_id / mac_src64 / mac_dst64 / mac_cmd_payload
      mac_beacon_pan / mac_beacon_permit / mac_frame_type / packet_id
    """
    cmd = [tshark_path, "-r", pcap_path, "-o", "wpan.802154_fcs_ok:FALSE",
           "-Y", "wpan.cmd or wpan.assoc_permit", "-T", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 and not result.stdout.strip():
        return []
    if not result.stdout.strip():
        return []
    try:
        raw_frames = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    frames = []
    for tf in raw_frames:
        layers = tf.get("_source", {}).get("layers", {})
        frame = layers.get("frame", {})
        wpan = layers.get("wpan", {})
        # 时间戳
        ts_raw = frame.get("frame.time_epoch", "0")
        try:
            ts = float(ts_raw)
        except ValueError:
            from datetime import datetime
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).timestamp()
            except (ValueError, OSError):
                continue
        frame_num = int(frame.get("frame.number", "0"))
        fcf_tree = wpan.get("wpan.fcf_tree", {})
        frame_type_raw = fcf_tree.get("wpan.frame_type", "")
        try:
            ft = int(frame_type_raw, 16) if frame_type_raw else -1
        except ValueError:
            ft = -1

        # AssocResp payload: wpan.asoc.addr (short addr) + wpan.assoc.status
        # 构造与 cubx mac_cmd_payload 等价的 bytes (short_addr 2LE + status 1)
        mac_payload = None
        ar = wpan.get("Association Response", {})
        if ar:
            try:
                saddr = int(ar.get("wpan.asoc.addr", "0"), 16)
                status = int(ar.get("wpan.assoc.status", "0"), 16)
                mac_payload = bytes([saddr & 0xFF, (saddr >> 8) & 0xFF, status])
            except (ValueError, TypeError):
                mac_payload = None

        d = {
            "ts": ts, "ch": 0,
            "packet_id": frame_num,
            "mac_frame_type": ft,
            "mac_cmd_id": _h(wpan.get("wpan.cmd", "")),
            "mac_src64": _hex_colon(wpan.get("wpan.src64", "")),
            "mac_dst64": _hex_colon(wpan.get("wpan.dst64", "")),
            "mac_cmd_payload": mac_payload,
            "mac_beacon_pan": _h(wpan.get("wpan.src_pan", "")),
            "mac_beacon_permit": None,
            "mac_src": _h(wpan.get("wpan.src16", "")),
            "mac_dst": _h(wpan.get("wpan.dst16", "")),
            "mac_seq": _num(wpan.get("wpan.seq_no", "")),
            "pan_src": _h(wpan.get("wpan.src_pan", "")),
            "pan_dst": _h(wpan.get("wpan.dst_pan", "")),
            "pkt_type": "MAC Cmd" if ft == 3 else "Beacon",
        }
        # Beacon PermitJoin (tshark 放在 "Superframe Specification" 子 dict)
        permit_raw = None
        for k, v in wpan.items():
            if isinstance(v, dict) and "wpan.assoc_permit" in v:
                permit_raw = v["wpan.assoc_permit"]
                break
        if permit_raw is None:
            permit_raw = wpan.get("wpan.assoc_permit")
        if permit_raw is not None:
            d["mac_beacon_permit"] = 1 if str(permit_raw) in ("1", "True", "true") else 0
        frames.append(d)
    return frames


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
    # ⚠️ 2026-08-05 修复: packet_id 此前未提取 → 诊断页证据表帧号显示 '—' (pcap 路径)
    packet_id = int(frame.get("frame.number", "0")) if frame.get("frame.number") else None

    # MAC 层 (wpan)
    wpan = layers.get("wpan", {})
    mac_fcf = int(wpan.get("wpan.fcf", "0"), 16)
    mac_frame_type = mac_fcf & 0x07
    mac_src = _h(wpan.get("wpan.src16", ""))
    mac_dst = _h(wpan.get("wpan.dst16", ""))
    mac_dst_pan = _h(wpan.get("wpan.dst_pan", ""))
    mac_src_pan = _h(wpan.get("wpan.src_pan", "")) or mac_dst_pan
    mac_seq = _num(wpan.get("wpan.seq_no", ""))
    fcs_ok = wpan.get("wpan.fcs_ok", "0") == "1"

    # NWK 层
    nwk = layers.get("zbee_nwk", {})
    # 安全位用 tshark 官方 fcf_tree 解析结果 (zbee_nwk.security) — 不自行按位运算:
    # 曾误用 (fcf>>7)&1 提取 multicast 位 → nwk_security 全 False;
    # 位序随 tshark 版本/字节序解释有差异, fcf_tree 是 dissector 已解析的权威值
    nwk_fcf = int(nwk.get("zbee_nwk.fcf", "0"), 16) if nwk.get("zbee_nwk.fcf") else 0
    nwk_secure = 1 if nwk.get("zbee_nwk.fcf_tree", {}).get("zbee_nwk.security", "0") == "1" else 0
    nwk_src = _h(nwk.get("zbee_nwk.src", ""))
    nwk_dst = _h(nwk.get("zbee_nwk.dst", ""))
    nwk_radius = _num(nwk.get("zbee_nwk.radius", ""))
    nwk_seq = _num(nwk.get("zbee_nwk.seqno", ""))
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

    # ── NWK 命令 ID + Leave 标志 (L1-4 踢人检测 / L1-3 Leave 判定需要) ──
    # 命令名 → ID 映射 (zigbee_packet_types.h): 1=Route Request, 2=Route Reply,
    # 3=Network Status, 4=Leave, 5=Route Record, 6=Rejoin Request, 7=Rejoin Response, 8=Link Status
    NWK_CMD_IDS = {
        "Route Request": 1, "Route Reply": 2, "Network Status": 3,
        "Leave": 4, "Route Record": 5, "Rejoin Request": 6,
        "Rejoin Response": 7, "Link Status": 8,
        "Network Report": 9, "Network Update": 10,
        "End Device Timeout Request": 11, "End Device Timeout Response": 12,
    }
    nwk_cmd_id = NWK_CMD_IDS.get(cmd_name) if cmd_name else None
    # MTORR: Route Request 的 many-to-one 标志 (2026-08-05, 自愈分析需要)
    # 与 cubx_reader nwk_route_request_mto 对齐 (options bit3 行为实证)
    nwk_route_request_mto = None
    if cmd_name == "Route Request" and isinstance(cmd_data, dict):
        mto_raw = str(cmd_data.get("zbee_nwk.cmd.route.opts.many2one", ""))
        if mto_raw in ("1", "True", "true"):
            nwk_route_request_mto = 1
        elif mto_raw in ("0", "False", "false"):
            nwk_route_request_mto = 0
    # Network Status (0x03): 状态码 + 目标短地址 (L3 检测 0x0B Source Route Failure 需要).
    # 目标字段名随 tshark 版本变化: zbee_nwk.cmd.route.dest (实测 4.6) / zbee_nwk.cmd.status.target
    nwk_status_code = nwk_status_target = None
    if cmd_name == "Network Status" and isinstance(cmd_data, dict):
        nwk_status_code = _h(cmd_data.get("zbee_nwk.cmd.status", ""))
        tgt_raw = cmd_data.get("zbee_nwk.cmd.route.dest") or cmd_data.get("zbee_nwk.cmd.status.target")
        nwk_status_target = _h(tgt_raw)
    nwk_leave_rejoin = nwk_leave_request = nwk_leave_children = None
    if cmd_name == "Leave" and isinstance(cmd_data, dict):
        # 官方字段: zbee_nwk.cmd.leave.rejoin (0x20) / request (0x40) / children (0x80)
        nwk_leave_rejoin = 1 if str(cmd_data.get("zbee_nwk.cmd.leave.rejoin", "")) in ("1", "True", "true") else 0
        nwk_leave_request = 1 if str(cmd_data.get("zbee_nwk.cmd.leave.request", "")) in ("1", "True", "true") else 0
        nwk_leave_children = 1 if str(cmd_data.get("zbee_nwk.cmd.leave.children", "")) in ("1", "True", "true") else 0

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
    # sec_level 在 field_tree 子 dict (实测 JSON: zbee.sec.field_tree.zbee.sec.sec_level)
    sec_level_raw = sec.get("zbee.sec.field_tree", {}).get("zbee.sec.sec_level", "")
    sec_level = int(sec_level_raw, 16) if sec_level_raw else None
    sec_frame_counter = int(sec.get("zbee.sec.counter", "0")) if sec.get("zbee.sec.counter") else None
    sec_key = _hex_colon(sec.get("zbee.sec.key", ""))
    sec_key_label = sec.get("zbee.sec.decryption_key", "")
    sec_mic = _hex_colon(sec.get("zbee.sec.mic", ""))
    # nwk_src64 缺失时从安全头补 (对齐 cubx: 安全头含源 EUI64, zbee.sec.src64)
    if nwk_src64 is None:
        nwk_src64 = _hex_colon(sec.get("zbee.sec.src64", ""))

    # APS 层
    aps = layers.get("zbee_aps", {})
    aps_cluster_zcl = _h(aps.get("zbee_aps.cluster", ""))
    aps_cluster_zdp = _h(aps.get("zbee_aps.zdp_cluster", ""))
    aps_cluster = aps_cluster_zcl if aps_cluster_zcl is not None else aps_cluster_zdp
    aps_profile = _h(aps.get("zbee_aps.profile", ""))
    aps_counter = int(aps.get("zbee_aps.counter", "0")) if aps.get("zbee_aps.counter") else None
    aps_src_ep = _num(aps.get("zbee_aps.src", ""))
    aps_dst_ep = _num(aps.get("zbee_aps.dst", ""))
    # APS 命令帧 (L1-3 密钥分发检测): 命令 ID + key_type 在 "Command Frame: X" 子 dict —
    # 曾从顶层 zbee_aps.cmd.id 读 → 恒 None, 密钥流程 5 帧 (0x05/0x08/0x0F/0x10)
    # 在 pcap 路径全部漏检 (素材实测: JSON 结构为 'Command Frame: Transport Key': {...})
    aps_cmd_id = None
    aps_cmd_key_type = None
    aps_cmd_remove_target = None
    aps_cmd_update_status = None
    for akey in aps:
        if akey.startswith("Command Frame:"):
            aps_cmd = aps[akey]
            if isinstance(aps_cmd, dict):
                aps_cmd_id = _h(aps_cmd.get("zbee_aps.cmd.id", ""))
                aps_cmd_key_type = _h(aps_cmd.get("zbee_aps.cmd.key_type", ""))
                # L1-4: Remove Device (0x07) target EUI64 / Update Device (0x06) status
                # 字段官方名: zbee_aps.cmd.device / zbee_aps.cmd.update_status
                if aps_cmd_id == 0x07:
                    aps_cmd_remove_target = _hex_colon(aps_cmd.get("zbee_aps.cmd.device", ""))
                elif aps_cmd_id == 0x06:
                    aps_cmd_update_status = _h(aps_cmd.get("zbee_aps.cmd.update_status", ""))
            break

    # ZCL 层
    zcl = layers.get("zbee_zcl", {})
    zcl_cmd_id = _h(zcl.get("zbee_zcl.cmd.id", ""))
    zcl_seq = _num(zcl.get("zbee_zcl.cmd.tsn", ""))
    zcl_dir = _zcl_direction(zcl)

    # 解密判断 — 加密帧 (nwk_secure) 且 APS 层可见 (有 Counter/cluster 字段) 才算解密成功.
    # 曾无 nwk_secure 条件: 非加密明文 APS 帧被误判 decrypted=True (cubx 语义: 解密成功才 True)
    decrypted = bool(nwk_secure and (aps_counter is not None
                                     or aps.get("zbee_aps.cluster") or aps.get("zbee_aps.zdp_cluster")))

    # 包类型 — 检查 ZDP/NWK/MAC 逐层确定
    pkt_type = _pkt_type(mac_frame_type, nwk, aps, decrypted)

    return {
        "ts": ts, "ch": 0,
        "lqi": None, "rssi": None,   # pcap 无 LQI/RSSI 数据源 (cubx 有) — 占位保持字段全集一致
        "packet_id": packet_id,
        "pkt_type": _pkt_type(mac_frame_type, nwk, aps, decrypted),
        "pan_src": mac_src_pan, "pan_dst": mac_dst_pan,
        "mac_src": mac_src, "mac_dst": mac_dst, "mac_seq": mac_seq,
        "nwk_src": nwk_src, "nwk_dst": nwk_dst, "nwk_seq": nwk_seq,
        # security 语义与 cubx 对齐: 非加密帧 = "" (曾恒 "Encrypted" 导致拓扑误判加密)
        "security": "Decrypted" if decrypted else ("Encrypted" if nwk_secure else ""),
        "status": "Decrypted" if decrypted else ("Encrypted" if nwk_secure else ""),
        # MAC 命令/Beacon 字段占位 (主路径 -Y zbee_nwk 不含 MAC 帧, 见 parse_mac_frames)
        "mac_cmd_id": None, "mac_src64": None, "mac_dst64": None,
        "mac_cmd_payload": None, "mac_beacon_pan": None, "mac_beacon_permit": None,
        "aps_cluster": aps_cluster,
        "aps_cluster_name": _aps_cluster_name(aps_profile, aps_cluster),
        "aps_profile": aps_profile,
        "aps_counter": aps_counter,
        "aps_src_ep": aps_src_ep, "aps_dst_ep": aps_dst_ep,
        "aps_cmd_id": aps_cmd_id,
        "aps_cmd_key_type": aps_cmd_key_type,
        "aps_cmd_remove_target": aps_cmd_remove_target,
        "aps_cmd_update_status": aps_cmd_update_status,
        "aps_payload_hex": None,   # cubx 路径提供 APS 解密明文 hex (ZDP 详情) — pcap 路径占位
        "nwk_cmd_id": nwk_cmd_id,
        "nwk_route_request_mto": nwk_route_request_mto,
        "nwk_status_code": nwk_status_code,       # Network Status 错误码 (0x0B=Source Route Failure)
        "nwk_status_target": nwk_status_target,   # Network Status 目标短地址
        "nwk_leave_rejoin": nwk_leave_rejoin,
        "nwk_leave_request": nwk_leave_request,
        "nwk_leave_children": nwk_leave_children,
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


def _num(val: str) -> int | None:
    """tshark JSON 数值字段: '0x2d' → 45 (hex 带前缀), '45' → 45 (十进制).

    tshark 4.6 对 seq/radius/EP 等数值字段输出十进制字符串 ('238'),
    地址/标识字段输出 0x 前缀 ('0x0019') — 数值字段用本函数, 兼容两种格式.
    """
    val = val.strip()
    if not val:
        return None
    return int(val, 16) if val.startswith("0x") else int(val, 10)


def _aps_cluster_name(profile: int | None, cluster: int | None) -> str | None:
    """集群名称: ZDP (profile 0x0000) 用 ZDP 表, 其余用 zcl_defs — 与 cubx_reader 对齐."""
    if cluster is None:
        return None
    if profile == 0x0000:
        return ZDP_CLUSTER_NAMES.get(cluster, "ZDP Cmd")
    return zcl_defs.get_cluster_name(cluster)


def _hex_colon(val: str) -> str | None:
    """'b4:e3:f9:ff:...' → 'b4e3f9ff...'"""
    val = val.strip().replace(":", "")
    return val if val else None


def _zcl_direction(zcl: dict) -> str | None:
    # key 带后缀如 "Frame Control Field: Profile-wide (0x10)" — 前缀匹配
    fcf = None
    for k in zcl:
        if k.startswith("Frame Control Field"):
            fcf = zcl[k]
            break
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
            zdp_cluster = _h(aps.get("zbee_aps.zdp_cluster", ""))
            if zdp_cluster is not None:
                return ZDP_CLUSTER_NAMES.get(zdp_cluster, "ZDP Cmd")
            return "ZDP"
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
