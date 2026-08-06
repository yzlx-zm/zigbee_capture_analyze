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
from typing import Callable, Optional, Sequence, Iterable

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
from . import zcl_defs

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
) -> tuple[bytes, str, bytes]:
    """Decrypt one Zigbee auxiliary-security payload using ENC-MIC-32.

    返回 (明文, key label, key 值) — key 值用于填充 sec_key 字段 (对齐 tshark zbee.sec.key).
    """
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
            return cipher.decrypt_and_verify(ciphertext, mic), record.label, record.value
        except ValueError:
            continue
    raise ValueError("MIC verification failed for all stored keys")


def _decrypt_nwk(nwk: ZigbeeNWK, network_keys: Sequence[KeyRecord],
                 link_keys: Sequence[KeyRecord]) -> tuple[bytes, str, bytes]:
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
) -> tuple[bytes, str, bytes]:
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


# Zigbee 规范全局默认 Link Key "ZigBeeAlliance09" (公开 well-known key).
# 入网 TransportKey 帧用 TC Link Key 加密 (APS key-transport-key, key_id=0x02),
# 若抓包工具的 Keys 表未记录该 key, 解密失败会读到密文首字节 (Security Control),
# 曾导致 APS 命令 ID 被误读为 0x20/0x38 (实际是 security control 值).
# tshark 正是用此默认 key 解出命令 ID (验证素材实测确认).
_DEFAULT_TC_LINK_KEY_HEX = "5A6967426565416C6C69616E63653039"  # "ZigBeeAlliance09"


def _load_all_keys(db: sqlite3.Connection) -> tuple[list[KeyRecord], list[KeyRecord]]:
    """合并 .cubx 内嵌 key + zigbee_pc_keys 外部 key + 默认全局 Link Key (去重)."""
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

    # 补充默认全局 Link Key (ZigBeeAlliance09) — 入网密钥分发的兜底解密候选
    link_hex_set = {k.value.hex().upper() for k in link_keys}
    if _DEFAULT_TC_LINK_KEY_HEX not in link_hex_set:
        link_keys.append(KeyRecord("zigbee-default-link-key", bytes.fromhex(_DEFAULT_TC_LINK_KEY_HEX)))

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
    0x0002: "ZDP: Node Desc Req", 0x0003: "ZDP: Power Desc Req",
    0x0004: "ZDP: Simple Desc Req", 0x0005: "ZDP: Active EP Req",
    0x0006: "ZDP: Match Desc Req", 0x0010: "ZDP: End Dev Announce",
    0x0013: "ZDP: Device Announce", 0x0031: "ZDP: Mgmt LQI Req",
    0x0032: "ZDP: Mgmt Routing Req",
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


def _addr_nwk(val) -> int | None:
    """NWK 地址提取 — 保留广播地址 (0xFFFC/0xFFFD/0xFFFF), 对齐 tshark zbee_nwk.dst.

    P1 契约修复 (2026-08-05): tshark 对 Route Request 等广播命令帧输出 nwk_dst=0xfffc,
    cubx 此前经 _addr 过滤为 None — 双路径不一致, 且下游无法区分广播帧。
    MAC 层仍用 _addr (广播过滤); 分析层需要广播语义时读 nwk_dst (0xFFFF 需显式排除).
    """
    return _h(val)


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


def _parse_route_request(plaintext: bytes) -> dict | None:
    """手动解析 Route Request 载荷 (Zigbee NWK 命令 0x01).

    结构: [cmd_id(1)][options(1)][id(1)][dest(2 LE)][path_cost(1)]
    对齐 tshark zbee_nwk.cmd.route.* 字段 (详情面板 Route Request 展示).
    """
    if len(plaintext) < 6:
        return None
    if plaintext[0] != 0x01:
        return None
    return {
        "options": plaintext[1],
        "id": plaintext[2],
        "dest": int.from_bytes(plaintext[3:5], "little"),
        "cost": plaintext[5],
    }


def _parse_route_reply(plaintext: bytes) -> dict | None:
    """手动解析 Route Reply 载荷 (Zigbee NWK 命令 0x02).

    结构: [cmd_id(1)][options(1)][id(1)][originator(2 LE)][responder(2 LE)][path_cost(1)]
    """
    if len(plaintext) < 8:
        return None
    if plaintext[0] != 0x02:
        return None
    return {
        "options": plaintext[1],
        "id": plaintext[2],
        "originator": int.from_bytes(plaintext[3:5], "little"),
        "responder": int.from_bytes(plaintext[5:7], "little"),
        "cost": plaintext[7],
    }


def _raw_to_dict(raw: bytes, packet_id: int, timestamp: float,
                 channel: int, lqi: int, rssi: int,
                 network_keys: list[KeyRecord],
                 link_keys: list[KeyRecord]) -> dict:
    """单帧完整解析 → dict (兼容 tshark._frame_to_dict)."""
    result: dict = {
        "ts": timestamp, "ch": channel, "lqi": lqi, "rssi": rssi,
        "packet_id": packet_id,
        "pkt_type": "Unknown",
        "pan_src": None, "pan_dst": None,
        "mac_src": None, "mac_dst": None, "mac_seq": None,
        "nwk_src": None, "nwk_dst": None, "nwk_seq": None,
        "security": "", "status": "", "decrypted": False,
        "aps_cluster": None, "aps_cluster_name": None, "aps_profile": None,
        "aps_counter": None, "aps_src_ep": None, "aps_dst_ep": None,
        "aps_payload_hex": None,   # APS 解密明文 payload hex (ZDP 详情展示)
        "zcl_cmd_id": None, "zcl_cmd_name": None,
        "sec_level": None, "sec_key": None, "sec_key_label": None,
        "sec_frame_counter": None, "sec_mic": None,
        "nwk_radius": None, "nwk_src64": None, "nwk_security": False,
        "mac_fcs_ok": True, "mac_frame_type": 1,
        "mac_cmd_id": None,          # MAC 命令帧 ID (1=AssocReq, 2=AssocResp, 4=DataReq, 7=BeaconReq...)
        "mac_src64": None,           # MAC 长地址 (EUI64, 字符串)
        "mac_dst64": None,           # MAC 目标长地址
        "mac_cmd_payload": None,     # MAC 命令帧 payload bytes
        "mac_beacon_pan": None,      # Beacon PAN ID (帧类型 0)
        "mac_beacon_permit": None,   # Beacon PermitJoin 位 (帧类型 0)
        "link_status_neighbors": None,
        "route_record_relays": None,
        "route_req": None,          # Route Request 载荷 (详情面板)
        "route_reply": None,        # Route Reply 载荷 (详情面板)
        "nwk_cmd_id": None,          # NWK 命令 ID (4=Leave, 8=Link Status...)
        "nwk_status_code": None,     # Network Status 错误码 (0x0B=Source Route Failure)
        "nwk_status_target": None,   # Network Status 目标短地址
        "aps_cmd_id": None,          # APS 命令 ID (0x05=TransportKey, 0x08=RequestKey, 0x0F=VerifyKey, 0x10=Confirm)
        "aps_cmd_key_type": None,    # TransportKey 的 key_type (0x01=NWK Key, 0x04=TC Link Key)
        "aps_cmd_remove_target": None,   # Remove Device (0x07) 目标 EUI64 (L1-4 踢人检测)
        "aps_cmd_update_status": None,   # Update Device (0x06) 状态 (1=UNSECURED_JOIN, 2=DEVICE_LEFT)
        "nwk_leave_rejoin": None,        # Leave options bit5=rejoin
        "nwk_leave_request": None,       # Leave options bit6=request
        "nwk_leave_children": None,      # Leave options bit7=children
        "zcl_direction": None,           # ZCL 方向 (0=Client→Server, 1=Server→Client)
        "zcl_seq": None,                 # ZCL 事务序列号
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
    # mac 是 Dot15d4Data/Dot15d4Cmd 子类 (scapy 2.7), 无 seqnum 字段 — getattr 会链式
    # 穿透到 ZigbeeNWK 层读到 NWK seq (曾导致 mac_seq 系统性等于 nwk_seq).
    # 从 pkt (Dot15d4FCS) 读真实 MAC seq (素材实证: pkt.seqnum=238 vs tshark wpan.seq_no=238).
    result["mac_seq"] = _h(getattr(pkt, "seqnum", None))
    result["mac_dst"] = _addr(getattr(mac, "dest_addr", None))
    result["mac_src"] = _addr(getattr(mac, "src_addr", None))
    result["pan_dst"] = _pan_field("dest_panid")
    result["pan_src"] = _pan_field("src_panid") or result["pan_dst"]

    # MAC 命令帧详情 (L1-1/L1-2 检测需要: BeaconReq/AssocReq/AssocResp/DataReq + 长地址)
    if mac_frame_type == 3:
        result["mac_cmd_id"] = _h(getattr(mac, "cmd_id", None))
        # 长地址: AssocReq 源=长地址, AssocResp 目标=长地址
        result["mac_src64"] = _format_eui(getattr(mac, "src_addr", None)) if _addr(getattr(mac, "src_addr", None)) is None and getattr(mac, "src_addr", None) is not None else None
        result["mac_dst64"] = _format_eui(getattr(mac, "dest_addr", None)) if _addr(getattr(mac, "dest_addr", None)) is None and getattr(mac, "dest_addr", None) is not None else None
        try:
            result["mac_cmd_payload"] = bytes(mac.payload)
        except Exception:
            pass
    elif mac_frame_type == 0:
        # Beacon: PAN ID + PermitJoin (payload 前 3 字节: PAN(2 LE) + Superframe spec(1, bit7=permit))
        try:
            pl = bytes(mac.payload)
            if len(pl) >= 3:
                result["mac_beacon_pan"] = int.from_bytes(pl[0:2], "little")
                result["mac_beacon_permit"] = (pl[2] >> 7) & 1
        except Exception:
            pass

    # NWK layer
    if not pkt.haslayer(ZigbeeNWK):
        # MAC 帧 (Beacon/命令/ACK): 无 NWK 层, 直接按 MAC 层判定包类型
        # (修复: 此前提前 return, pkt_type 停留 "Unknown")
        result["pkt_type"] = _pkt_type(mac_frame_type, None, None, False, None)
        return result

    nwk = pkt[ZigbeeNWK]
    nwk_secure = bool(int(nwk.flags) & 0x02)
    result["nwk_src"] = _addr_nwk(nwk.source)
    result["nwk_dst"] = _addr_nwk(nwk.destination)
    result["nwk_radius"] = _h(getattr(nwk, "radius", None))
    result["nwk_seq"] = _h(getattr(nwk, "seqnum", None))
    result["nwk_src64"] = _format_eui(getattr(nwk, "ext_src", None))
    result["nwk_security"] = nwk_secure

    nwk_cmd_id: int | None = None
    plaintext = bytes(nwk.payload)
    # 明文有效性: 非加密帧明文可用; 加密帧仅解密成功后才有效
    # (曾解密失败时 plaintext 仍是密文, 密文首字节被当命令 ID — 0x20/0x38 误读同类复发)
    plain_valid = not nwk_secure

    # NWK decryption
    sec = None
    if nwk_secure:
        # 安全头信息 (sec_level/fc/mic) 解密成败都提取 — 对齐 tshark 从 JSON 安全头取值
        try:
            sec = nwk[ZigbeeSecurityHeader]
        except Exception:
            sec = None
        if sec is not None:
            # scapy 字段名 nwk_seclevel (非 sec_level — 曾导致恒 None)
            result["sec_level"] = _h(getattr(sec, "nwk_seclevel", None))
            result["sec_frame_counter"] = _h(getattr(sec, "fc", None))
            sec_bytes = bytes(sec)
            if len(sec_bytes) >= 4:
                result["sec_mic"] = sec_bytes[-4:].hex()
        try:
            plaintext, key_label, key_value = _decrypt_nwk(nwk, network_keys, link_keys)
            plain_valid = True
            result["decrypted"] = True
            result["security"] = "Decrypted"
            result["status"] = "Decrypted"
            result["sec_key_label"] = key_label
            result["sec_key"] = key_value.hex() if key_value else None
            # extract source EUI64 from security header for mapping
            if sec is not None and bool(sec.extended_nonce) and result["nwk_src64"] is None:
                result["nwk_src64"] = _format_eui(getattr(sec, "source", None))
        except Exception:
            result["security"] = "Encrypted"
            result["status"] = "Encrypted"
    else:
        # 非加密 NWK 帧可能仍含可识别 payload
        pass

    # NWK command parsing (on valid plaintext only)
    if int(nwk.frametype) == 1 and plain_valid:
        nwk_cmd_id = _parse_nwk_command_id(plaintext)
        result["nwk_cmd_id"] = nwk_cmd_id
        if nwk_cmd_id == 1 and len(plaintext) >= 2:  # Route Request
            # options bit3 (0x08) = many-to-one (MTORR) — 行为实证 (838D 素材 121/161)
            result["nwk_route_request_mto"] = (plaintext[1] >> 3) & 1
            # 完整载荷 (详情面板 Route Request 展示: Originator/Dest/Cost/ID/Options)
            result["route_req"] = _parse_route_request(plaintext)
        elif nwk_cmd_id == 2:  # Route Reply (详情面板展示: Originator/Responder/Cost)
            result["route_reply"] = _parse_route_reply(plaintext)
        elif nwk_cmd_id == 8:  # Link Status
            result["link_status_neighbors"] = _parse_link_status(plaintext)
        elif nwk_cmd_id == 5:  # Route Record
            result["route_record_relays"] = _parse_route_record(plaintext)
        elif nwk_cmd_id == 3 and len(plaintext) >= 4:  # Network Status
            # payload: [cmd_id(1)][code(1)][target(2 LE)]
            # 0x0B = Source Route Failure (L1-3 路由根因判定需要)
            result["nwk_status_code"] = plaintext[1]
            result["nwk_status_target"] = int.from_bytes(plaintext[2:4], "little")
        elif nwk_cmd_id == 4 and len(plaintext) >= 2:  # Leave
            # payload: [cmd_id(1)][options(1)]; options: bit5=rejoin, bit6=request, bit7=children
            # (与 tshark zbee_nwk.cmd.leave.* 对齐, L1-4 踢人判定需要)
            opts = plaintext[1]
            result["nwk_leave_rejoin"] = (opts >> 5) & 1
            result["nwk_leave_request"] = (opts >> 6) & 1
            result["nwk_leave_children"] = (opts >> 7) & 1

    # APS / ZDP parsing (only for NWK Data frames, not NWK commands)
    aps = None
    if int(nwk.frametype) == 0:
        try:
            aps = ZigbeeAppDataPayload(plaintext)
        except Exception:
            pass

    if aps is not None:
        # scapy 把 APS FCF 拆成独立字段: aps_frametype (0=data/1=cmd/2=ack), 不是 frame_control
        aps_ftype = _h(getattr(aps, "aps_frametype", None)) or 0
        # APS security: scapy 无 security_level 属性 (曾导致解密分支永不执行,
        # APS 命令 ID 读到密文首字节 Security Control → 0x20/0x38 误读),
        # 改用 ZigbeeSecurityHeader 子层判定 (FCF security 位已解析为子层).
        if aps.haslayer(ZigbeeSecurityHeader):
            try:
                aps_plaintext, key_label, key_value = _decrypt_aps(aps, network_keys, link_keys)
                result["decrypted"] = True
                result["security"] = "Decrypted"
                result["status"] = "Decrypted"
                result["sec_key_label"] = key_label
                result["sec_key"] = key_value.hex() if key_value else None
                aps_plain = aps_plaintext
            except Exception:
                aps_plain = None
        else:
            aps_plain = bytes(aps.payload)

        # APS 字段只在明文可得时提取 — 解密失败时 scapy 会从密文误解析出假 cluster/profile
        # (曾输出垃圾值, tshark 对这些帧正确置 None)
        if aps_plain is not None:
            result["aps_cluster"] = _h(getattr(aps, "cluster", None))
            result["aps_profile"] = _h(getattr(aps, "profile", None))
            # 集群名称: ZDP (profile 0x0000) 用 ZDP 表, 其余用 zcl_defs — 对齐 tshark 输出
            if result["aps_cluster"] is not None:
                if result["aps_profile"] == 0x0000:
                    result["aps_cluster_name"] = ZDP_CLUSTER_NAMES.get(result["aps_cluster"], "ZDP Cmd")
                else:
                    result["aps_cluster_name"] = zcl_defs.get_cluster_name(result["aps_cluster"])
            result["aps_counter"] = _h(getattr(aps, "counter", None))
            result["aps_src_ep"] = _h(getattr(aps, "src_endpoint", None))
            result["aps_dst_ep"] = _h(getattr(aps, "dst_endpoint", None))
            # APS 解密后明文 payload hex (ZDP/ZCL 详情展示用; 解析在 API 展示层, 见 files._fallback_zdp_tree)
            result["aps_payload_hex"] = aps_plain.hex() if aps_plain else None

        # APS Ack: aps_frametype==2 (scapy 字段, 不是 frame_control)
        if aps_ftype == 2:
            result["pkt_type"] = "APS Ack"

        # APS 命令帧 (aps_frametype==1): 手动字节解析 cmd_id + key_type.
        # 0x20/0x38 教训: 不依赖 scapy ZigbeeAppCommandPayload (解析有偏差),
        # 直接读明文 payload 字节 — 官方结构 (zigbee_packet_types.h):
        #   [0]=command_id, [1]=key_type (仅 TransportKey 0x05 有)
        if aps_ftype == 1 and aps_plain:
            cid = aps_plain[0]
            result["aps_cmd_id"] = cid
            # key_type 位置按命令结构 (对齐 tshark zbee_aps.cmd.key_type):
            # 0x05/0x08/0x0F: [cmd(1)][key_type(1)]; 0x10 Confirm: [cmd(1)][status(1)][key_type(1)]
            if cid in (0x05, 0x08, 0x0F) and len(aps_plain) >= 2:
                result["aps_cmd_key_type"] = aps_plain[1]
            elif cid == 0x10 and len(aps_plain) >= 3:
                result["aps_cmd_key_type"] = aps_plain[2]
            elif cid == 0x07 and len(aps_plain) >= 9:  # Remove Device
                # payload: [cmd_id(1)][target EUI64(8 LE)] — L1-4 踢人检测
                result["aps_cmd_remove_target"] = _format_eui(
                    int.from_bytes(aps_plain[1:9], "little"))
            elif aps_plain[0] == 0x06 and len(aps_plain) >= 2:  # Update Device
                # payload: [cmd_id(1)][status(1)] — 1=UNSECURED_JOIN, 2=DEVICE_LEFT
                result["aps_cmd_update_status"] = aps_plain[1]

        # ZCL 层 (profile != 0x0000 的 APS data 帧): 手动解析 ZCL header — 对齐 tshark.
        # 官方结构 (ZCL spec 2.3.1): fcf(1) [+manufacturer code 2B if fcf bit2] + tsn(1) + cmd_id(1)
        # fcf 位: bit0-1 frame type, bit2 = manufacturer specific, bit3 = direction
        #   (0=Client→Server, 1=Server→Client), bit4 = disable default response
        # (曾误用 bit1/bit2 — tshark 字段注册证实 dir=0x08/bit3, ms=bit2)
        # APS 加密帧解密明文从 profile 起 (FCF/counter 不加密) → ZCL 头偏移 6;
        # 非加密帧 aps_plain = aps.payload → ZCL 头偏移 0
        if (result["aps_profile"] not in (None, 0x0000) and aps_plain
                and len(aps_plain) >= 3):
            zcl_base = 6 if aps.haslayer(ZigbeeSecurityHeader) else 0
            zcl_fcf = aps_plain[zcl_base]
            zcl_off = zcl_base + 1
            if zcl_fcf & 0x04:  # bit2 = manufacturer specific → 额外 2 字节厂商码
                zcl_off += 2
            if len(aps_plain) > zcl_off:
                result["zcl_seq"] = aps_plain[zcl_off]
                if zcl_off + 1 < len(aps_plain):
                    result["zcl_cmd_id"] = aps_plain[zcl_off + 1]
                result["zcl_direction"] = (
                    "Server→Client" if (zcl_fcf >> 3) & 1 else "Client→Server")
                if result["zcl_cmd_id"] is not None:
                    result["zcl_cmd_name"] = zcl_defs.get_command_name(
                        result["aps_cluster"], result["zcl_cmd_id"])

    # Final pkt_type
    if result["pkt_type"] == "Unknown":
        result["pkt_type"] = _pkt_type(mac_frame_type, nwk, aps,
                                       result["decrypted"], nwk_cmd_id)

    return result


# ── Public API ──


def parse_cubx(path: str, include_mac_frames: bool = False,
               progress_cb: Callable[[int, int], None] | None = None,
               ) -> tuple[list[dict], int, int]:
    """解析 .cubx 文件 → (包列表, key新增数, key去重总数).

    Key 自动同步到 zigbee_pc_keys (去重, 幂等).
    包列表按 timestamp 排序, 格式兼容 tshark.parse_packets 输出.

    include_mac_frames=True: 额外保留 MAC 命令帧和 Beacon (L1-1/L1-2 入网检测需要,
    默认 False 与 tshark -Y zbee_nwk 对齐只保留 NWK 帧).
    progress_cb(done, total): 可选进度回调, 逐包解密循环中按块上报 (大文件解析可达
    数十秒, 调用方需借此显示真实进度, 否则进度条会静止在 0%).
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
        total_rows = len(rows)
        for idx, row in enumerate(rows):
            pkt_id, raw, ts, ch, lqi, rssi = row
            pkt = _raw_to_dict(
                bytes(raw), int(pkt_id), float(ts),
                int(ch), int(lqi), int(rssi),
                nwk_keys, link_keys,
            )
            # 只保留 NWK 帧 (与 tshark -Y zbee_nwk 对齐), 除非 include_mac_frames
            is_nwk = pkt.get("nwk_src") is not None or pkt.get("nwk_dst") is not None
            is_mac_relevant = (pkt.get("mac_cmd_id") is not None) or (pkt.get("mac_beacon_pan") is not None)
            if is_nwk or (include_mac_frames and is_mac_relevant):
                packets.append(pkt)
            # 进度上报 (每 500 包 + 末包, 避免每包回调开销)
            if progress_cb and (idx % 500 == 499 or idx == total_rows - 1):
                progress_cb(idx + 1, total_rows)

        packets.sort(key=lambda p: p["ts"])
        return packets, sync_result["added"], sync_result["total"]
    finally:
        db.close()
