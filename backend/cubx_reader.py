""".cubx 原生解析器 — Ubiqua 抓包文件直读, 替代 pcap+tshark 管线.

参考: akubela-zigbee-analyser _capture_probe.py
依赖: scapy (Dot15d4FCS, ZigbeeNWK, ...), pycryptodome (AES-CCM)

输出格式兼容 tshark._frame_to_dict, 事件管道无感切换.
"""
from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Iterable

from Crypto.Cipher import AES
from scapy.all import Dot15d4FCS, conf
from scapy.layers.zigbee import (
    ZigbeeAppCommandPayload,
    ZigbeeAppDataPayload,
    ZigbeeNWK,
    ZigbeeNWKCommandPayload,
    ZigbeeSecurityHeader,
)

from . import key_store as _ks

conf.dot15d4_protocol = "zigbee"

# ── Crypto Primitives (from akubela _capture_probe.py) ──


@dataclass
class KeyRecord:
    label: str
    value: bytes


def _zigbee_hash(value: bytes) -> bytes:
    """Zigbee AES-MMO hash (Zigbee specification B.1.3/B.6)."""
    state = bytes(16)
    blocks: list[bytes] = []
    offset = 0
    while offset + 16 <= len(value):
        blocks.append(value[offset: offset + 16])
        offset += 16
    tail = bytearray(value[offset:])
    tail.append(0x80)
    while len(tail) % 16 != 14:
        tail.append(0)
    tail.extend((len(value) * 8).to_bytes(2, "big"))
    blocks.extend(bytes(tail[i: i + 16]) for i in range(0, len(tail), 16))
    for block in blocks:
        encrypted = AES.new(state, AES.MODE_ECB).encrypt(block)
        state = bytes(left ^ right for left, right in zip(encrypted, block))
    return state


def _zigbee_key_hash(key: bytes, selector: int) -> bytes:
    """Zigbee keyed hash used for key-transport/load keys."""
    inner = _zigbee_hash(bytes(byte ^ 0x36 for byte in key) + bytes([selector]))
    return _zigbee_hash(bytes(byte ^ 0x5C for byte in key) + inner)


def _security_candidates(
    key_type: int,
    network_keys: Sequence[KeyRecord],
    link_keys: Sequence[KeyRecord],
) -> Iterable[KeyRecord]:
    if key_type == 1:
        yield from network_keys
        return
    for record in link_keys:
        if key_type == 2:
            yield KeyRecord(f"{record.label}/transport", _zigbee_key_hash(record.value, 0x00))
        elif key_type == 3:
            yield KeyRecord(f"{record.label}/load", _zigbee_key_hash(record.value, 0x02))
        else:
            yield record


def _decrypt_security_blob(
    prefix: bytes,
    sec_bytes: bytes,
    extended_nonce: bool,
    key_type: int,
    candidates: Iterable[KeyRecord],
) -> tuple[bytes, str]:
    """Decrypt one Zigbee auxiliary-security payload using ENC-MIC-32."""
    if not extended_nonce:
        raise ValueError("security header has no extended nonce/source EUI")
    aux_length = 1 + 4 + 8 + (1 if key_type == 1 else 0)
    if len(sec_bytes) < aux_length + 4:
        raise ValueError("security payload is shorter than auxiliary header plus MIC")
    auxiliary = sec_bytes[:aux_length]
    ciphertext = sec_bytes[aux_length:-4]
    mic = sec_bytes[-4:]
    patched_control = (auxiliary[0] & 0xF8) | 5
    patched_auxiliary = bytes([patched_control]) + auxiliary[1:]
    nonce = auxiliary[5:13] + auxiliary[1:5] + bytes([patched_control])
    for record in candidates:
        cipher = AES.new(record.value, AES.MODE_CCM, nonce=nonce, mac_len=4)
        cipher.update(prefix + patched_auxiliary)
        try:
            return cipher.decrypt_and_verify(ciphertext, mic), record.label
        except ValueError:
            continue
    raise ValueError("MIC verification failed for all stored keys")


def _decrypt_nwk(nwk: ZigbeeNWK, network_keys: Sequence[KeyRecord],
                 link_keys: Sequence[KeyRecord]) -> tuple[bytes, str]:
    sec = nwk[ZigbeeSecurityHeader]
    sec_bytes = bytes(sec)
    nwk_bytes = bytes(nwk)
    prefix = nwk_bytes[: -len(sec_bytes)]
    # NWK 层绝大多数用 Network Key (key_type=1), 但部分帧可能用 Data Key (key_type=0).
    # 合并两种 key 候选以覆盖所有情况.
    all_candidates = list(network_keys) + list(link_keys)
    return _decrypt_security_blob(prefix, sec_bytes, bool(sec.extended_nonce),
                                  int(sec.key_type), all_candidates)


def _decrypt_aps(
    aps: ZigbeeAppDataPayload,
    network_keys: Sequence[KeyRecord],
    link_keys: Sequence[KeyRecord],
) -> tuple[bytes, str]:
    sec = aps[ZigbeeSecurityHeader]
    sec_bytes = bytes(sec)
    aps_bytes = bytes(aps)
    prefix = aps_bytes[: -len(sec_bytes)]
    return _decrypt_security_blob(prefix, sec_bytes, bool(sec.extended_nonce),
                                  int(sec.key_type),
                                  _security_candidates(int(sec.key_type), network_keys, link_keys))


# ── Key Loading ──


def _load_cubx_keys_internal(db: sqlite3.Connection) -> tuple[list[KeyRecord], list[KeyRecord]]:
    """读取 .cubx Keys 表 → (network_keys, link_keys)."""
    network_keys: list[KeyRecord] = []
    link_keys: list[KeyRecord] = []
    for key_id, kind, value in db.execute("SELECT Id, Type, Key FROM Keys ORDER BY Id"):
        record = KeyRecord(f"cubx-key-{key_id}", bytes(value))
        normalized = str(kind).lower()
        if "network" in normalized:
            network_keys.append(record)
        elif "link" in normalized:
            link_keys.append(record)
    return network_keys, link_keys


def _load_all_keys(db: sqlite3.Connection) -> tuple[list[KeyRecord], list[KeyRecord]]:
    """合并 .cubx 内嵌 key + zigbee_pc_keys 外部 key (去重)."""
    network_keys, link_keys = _load_cubx_keys_internal(db)

    # 补充 zigbee_pc_keys 中的 key (外部积累的历史密钥)
    ext_keys = _ks.read_all_keys()
    ext_hex_set = {k.value.hex().upper() for k in network_keys}
    for ek in ext_keys:
        hex_up = ek["hex"].upper()
        if hex_up not in ext_hex_set:
            try:
                network_keys.append(KeyRecord(ek["label"], bytes.fromhex(hex_up)))
                ext_hex_set.add(hex_up)
            except ValueError:
                pass

    return network_keys, link_keys


# ── Frame Parser ──


NWK_COMMAND_NAMES = {
    1: "Route Request", 2: "Route Reply", 3: "Network Status",
    4: "Leave", 5: "Route Record", 6: "Rejoin Request", 7: "Rejoin Response",
    8: "Link Status", 9: "Network Report", 10: "Network Update",
    11: "End Device Timeout Request", 12: "End Device Timeout Response",
}

ZDP_CLUSTER_NAMES = {
    0x0000: "ZDP: NWK Addr Req", 0x0001: "ZDP: IEEE Addr Req",
    0x0002: "ZDP: Node Desc Req", 0x0004: "ZDP: Simple Desc Req",
    0x0005: "ZDP: Active EP Req", 0x0010: "ZDP: End Dev Announce",
    0x0013: "ZDP: Device Announce", 0x0031: "ZDP: Mgmt LQI Req",
    0x8000: "ZDP: NWK Addr Resp", 0x8001: "ZDP: IEEE Addr Resp",
    0x8002: "ZDP: Node Desc Resp", 0x8005: "ZDP: Active EP Resp",
}


def _h(val) -> int | None:
    """scapy field → int, or None."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _addr(val) -> int | None:
    """scapy address → int (0xFFFF=65535 → None for broadcast)."""
    v = _h(val)
    if v is None or v >= 0xFFF0:
        return None
    return v


def _format_eui(val) -> str | None:
    """scapy EUI64 → hex string without colons."""
    if val is None:
        return None
    try:
        return f"{int(val):016x}"
    except (ValueError, TypeError):
        return None


def _pkt_type(mac_frame_type: int, nwk, aps, decrypted: bool,
              nwk_cmd_id: int | None) -> str:
    """判别包类型, 与 tshark._pkt_type 对齐."""
    mac_names = {0: "Beacon", 1: "Data", 2: "Acknowledgement", 3: "MAC Cmd"}
    base = mac_names.get(mac_frame_type, "Unknown")
    if mac_frame_type == 1:
        if nwk_cmd_id is not None and nwk_cmd_id in NWK_COMMAND_NAMES:
            return NWK_COMMAND_NAMES[nwk_cmd_id]
        if aps is not None:
            profile = _h(getattr(aps, "profile", None))
            if profile == 0x0000:
                cluster = _h(getattr(aps, "cluster", None))
                if cluster is not None:
                    return ZDP_CLUSTER_NAMES.get(cluster, f"ZDP Cmd")
            if decrypted:
                return "Data"
        if nwk is not None and int(getattr(nwk, "frametype", -1)) == 1:
            return "NWK Cmd"
    return base


def _parse_link_status(plaintext: bytes) -> list[dict] | None:
    """从 NWK command payload 解析 Link Status 邻居表.

    scapy 字段名 (ZigbeeNWKCommandPayload 对 cmd 0x08):
      entry_count, link_status_list[i].neighbor_network_address / incoming_cost / outgoing_cost
    """
    try:
        cmd = ZigbeeNWKCommandPayload(plaintext)
        if int(cmd.cmd_identifier) != 8:
            return None
        count = int(cmd.entry_count)
        ls_list = cmd.link_status_list
        neighbors = []
        for i in range(min(count, len(ls_list))):
            entry = ls_list[i]
            nb_addr = int(entry.neighbor_network_address)
            if nb_addr < 0xFFF0:
                neighbors.append({
                    "addr": nb_addr,
                    "in_cost": int(entry.incoming_cost),
                    "out_cost": int(entry.outgoing_cost),
                })
        return neighbors if neighbors else None
    except Exception:
        return None


def _parse_route_record(plaintext: bytes) -> dict | None:
    """从 NWK 解密后 payload 手动解析 Route Record 中继列表.

    scipy 的 ZigbeeNWKCommandPayload 对 relay_list 解析不可靠,
    改为手动: cmd_id(1) + options(1) + relay_count(1) + relay_device[](each 2 LE).
    """
    if len(plaintext) < 3:
        return None
    cmd_id = plaintext[0]
    if cmd_id != 0x05:  # Route Record
        return None
    # Route Record format: cmd_id(1) + relay_count(1) + relay_device[](each 2 LE)
    relay_count = plaintext[1]
    if relay_count == 0:
        return None
    relays = []
    for i in range(min(relay_count, 32)):  # 安全上限
        offset = 2 + i * 2
        if offset + 1 >= len(plaintext):
            break
        addr = int.from_bytes(plaintext[offset:offset + 2], "little")
        if addr < 0xFFF0:
            relays.append(addr)
    return {"count": len(relays), "relays": relays} if relays else None


def _parse_nwk_command_id(plaintext: bytes) -> int | None:
    """从 NWK payload 第一个字节提取命令 ID (用于 pkt_type 判别, 不解析完整结构)."""
    return plaintext[0] if len(plaintext) > 0 else None


def _raw_to_dict(raw: bytes, packet_id: int, timestamp: float,
                 channel: int, lqi: int, rssi: int,
                 network_keys: list[KeyRecord],
                 link_keys: list[KeyRecord]) -> dict:
    """单帧完整解析 → dict (兼容 tshark._frame_to_dict)."""
    result: dict = {
        "ts": timestamp, "ch": channel, "lqi": lqi, "rssi": rssi,
        "pkt_type": "Unknown",
        "pan_src": None, "pan_dst": None,
        "mac_src": None, "mac_dst": None, "mac_seq": None,
        "nwk_src": None, "nwk_dst": None, "nwk_seq": None,
        "security": "", "status": "", "decrypted": False,
        "aps_cluster": None, "aps_cluster_name": None, "aps_profile": None,
        "aps_counter": None, "aps_src_ep": None, "aps_dst_ep": None,
        "zcl_cmd_id": None, "zcl_cmd_name": None,
        "sec_level": None, "sec_key": None, "sec_key_label": None,
        "sec_frame_counter": None, "sec_mic": None,
        "nwk_radius": None, "nwk_src64": None, "nwk_security": False,
        "mac_fcs_ok": True, "mac_frame_type": 1,
        "link_status_neighbors": None,
        "route_record_relays": None,
        "raw_layers": {},
    }

    # MAC layer
    try:
        pkt = Dot15d4FCS(raw)
    except Exception:
        return result

    mac = pkt.payload
    mac_frame_type = int(pkt.fcf_frametype)

    def _pan_field(field_name) -> int | None:
        v = getattr(mac, field_name, None)
        return _h(v) if v is not None else None

    result["mac_frame_type"] = mac_frame_type
    result["mac_seq"] = _h(getattr(mac, "seqnum", None))
    result["mac_dst"] = _addr(getattr(mac, "dest_addr", None))
    result["mac_src"] = _addr(getattr(mac, "src_addr", None))
    result["pan_dst"] = _pan_field("dest_panid")
    result["pan_src"] = _pan_field("src_panid") or result["pan_dst"]

    # NWK layer
    if not pkt.haslayer(ZigbeeNWK):
        return result

    nwk = pkt[ZigbeeNWK]
    nwk_secure = bool(int(nwk.flags) & 0x02)
    result["nwk_src"] = _addr(nwk.source)
    result["nwk_dst"] = _addr(nwk.destination)
    result["nwk_radius"] = _h(getattr(nwk, "radius", None))
    result["nwk_seq"] = _h(getattr(nwk, "seqnum", None))
    result["nwk_src64"] = _format_eui(getattr(nwk, "ext_src", None))
    result["nwk_security"] = nwk_secure

    nwk_cmd_id: int | None = None
    plaintext = bytes(nwk.payload)

    # NWK decryption
    if nwk_secure:
        try:
            plaintext, key_label = _decrypt_nwk(nwk, network_keys, link_keys)
            result["decrypted"] = True
            result["security"] = "Decrypted"
            result["status"] = "Decrypted"
            sec = nwk[ZigbeeSecurityHeader]
            result["sec_level"] = _h(getattr(sec, "sec_level", None))
            result["sec_key_label"] = key_label
            result["sec_frame_counter"] = _h(getattr(sec, "fc", None))
            # extract source EUI64 from security header for mapping
            if bool(sec.extended_nonce) and result["nwk_src64"] is None:
                result["nwk_src64"] = _format_eui(getattr(sec, "source", None))
        except Exception:
            result["security"] = "Encrypted"
            result["status"] = "Encrypted"
    else:
        # 非加密 NWK 帧可能仍含可识别 payload
        pass

    # NWK command parsing (on decrypted plaintext)
    if int(nwk.frametype) == 1:
        nwk_cmd_id = _parse_nwk_command_id(plaintext)
        if nwk_cmd_id == 8:  # Link Status
            result["link_status_neighbors"] = _parse_link_status(plaintext)
        elif nwk_cmd_id == 5:  # Route Record
            result["route_record_relays"] = _parse_route_record(plaintext)

    # APS / ZDP parsing (only for NWK Data frames, not NWK commands)
    aps = None
    if int(nwk.frametype) == 0:
        try:
            aps = ZigbeeAppDataPayload(plaintext)
        except Exception:
            pass

    if aps is not None:
        if int(aps.frame_control) & 0x02:  # APS security
            try:
                aps_plaintext, key_label = _decrypt_aps(aps, network_keys, link_keys)
                result["decrypted"] = True
                result["security"] = "Decrypted"
                result["status"] = "Decrypted"
                result["sec_key_label"] = key_label
                aps_plain = aps_plaintext
            except Exception:
                aps_plain = None
        else:
            aps_plain = bytes(aps.payload)

        result["aps_cluster"] = _h(getattr(aps, "cluster", None))
        result["aps_profile"] = _h(getattr(aps, "profile", None))
        result["aps_counter"] = _h(getattr(aps, "counter", None))
        result["aps_src_ep"] = _h(getattr(aps, "src_endpoint", None))
        result["aps_dst_ep"] = _h(getattr(aps, "dst_endpoint", None))

        # APS Ack detection: frametype==2 AND no payload/counter (genuine short Ack)
        aps_fcf = int(aps.frame_control)
        aps_has_payload = (aps_plain is not None and len(aps_plain) > 0)
        if (aps_fcf & 0x03) == 2 and not aps_has_payload and result["aps_counter"] is None:
            result["pkt_type"] = "APS Ack"

    # Final pkt_type
    if result["pkt_type"] == "Unknown":
        result["pkt_type"] = _pkt_type(mac_frame_type, nwk, aps,
                                       result["decrypted"], nwk_cmd_id)

    return result


# ── Public API ──


def parse_cubx(path: str) -> tuple[list[dict], int, int]:
    """解析 .cubx 文件 → (包列表, key新增数, key去重总数).

    Key 自动同步到 zigbee_pc_keys (去重, 幂等).
    包列表按 timestamp 排序, 格式兼容 tshark.parse_packets 输出.
    """
    cubx_path = Path(path).expanduser().resolve()
    if not cubx_path.is_file():
        raise FileNotFoundError(f"cubx 文件不存在: {cubx_path}")

    db = sqlite3.connect(f"{cubx_path.as_uri()}?mode=ro", uri=True)
    try:
        # Keys (cubx 内嵌 + zigbee_pc_keys 补充)
        nwk_keys, link_keys = _load_all_keys(db)

        # Sync NetworkKey to zigbee_pc_keys
        nwk_hex_list = [k.value.hex().upper() for k in nwk_keys]
        sync_result = _ks.merge_from_ubiqua(nwk_hex_list)

        # Packets
        rows = db.execute(
            "SELECT Id, Raw, Timestamp, Channel, LQI, RSSI FROM Packets ORDER BY Id"
        ).fetchall()
        packets: list[dict] = []
        for row in rows:
            pkt_id, raw, ts, ch, lqi, rssi = row
            pkt = _raw_to_dict(
                bytes(raw), int(pkt_id), float(ts),
                int(ch), int(lqi), int(rssi),
                nwk_keys, link_keys,
            )
            # 只保留 NWK 帧 (与 tshark -Y zbee_nwk 对齐)
            if pkt.get("nwk_src") is not None or pkt.get("nwk_dst") is not None:
                packets.append(pkt)

        packets.sort(key=lambda p: p["ts"])
        return packets, sync_result["added"], sync_result["total"]
    finally:
        db.close()
