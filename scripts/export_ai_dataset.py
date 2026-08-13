"""Export a .cubx capture into an AI-readable dataset.

Reuses backend.cubx_reader.parse_cubx for the heavy lifting
(.cubx sqlite -> MAC/NWK/APS/ZCL parsed dicts + AES decryption), then
serializes the result into:

  metadata.json        capture-level stats, PAN list, security summary
  packets.jsonl        every parsed frame, full field set (key material redacted)
  events.jsonl         compact semantic events, all PANs
  events_target.jsonl  compact semantic events, target PAN only
  interactions.json    nodes, EUI64<->short address map, edge counts
  timeline.md          chronological transcript, all PANs
  timeline_target.md   chronological transcript, target PAN only
  digest.md            LLM-friendly summary (nodes / edges / key events)

Usage:
  python scripts/export_ai_dataset.py <capture.cubx> [--out DIR] [--target-pan HEX]

Key-store writes are isolated to <out>/.keys so the system Wireshark
zigbee_pc_keys file is not modified. Network/link key values are never
exported; TransportKey / RequestKey / VerifyKey payloads are also omitted.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import cubx_reader  # noqa: E402
from backend import key_store as _ks  # noqa: E402
from backend.aps_pairing import build_ack_match  # noqa: E402

NWK_COMMAND_NAMES = cubx_reader.NWK_COMMAND_NAMES

# Project-consistent MAC command names (see backend/detectors/l1.py).
MAC_CMD_NAMES = {
    1: "AssocReq",
    2: "AssocResp",
    3: "CoordRealign",
    4: "DataReq",
    5: "PanIdConflict",
    6: "OrphanNotif",
    7: "BeaconReq",
    8: "GTSReq",
    9: "GTSResp",
}

NWK_STATUS_NAMES = {
    0x00: "NO_ROUTE_AVAILABLE",
    0x01: "TREE_LINK_FAILURE",
    0x02: "NON_TREE_LINK_FAILURE",
    0x03: "LOW_BATTERY_LEVEL",
    0x04: "NO_ROUTING_CAPACITY",
    0x05: "NO_INDIRECT_CAPACITY",
    0x0B: "SOURCE_ROUTE_FAILURE",
    0x0C: "MTORR_FAILURE",
}

KEY_MANAGEMENT_APS_CMDS = {0x05, 0x08, 0x0F, 0x10}  # TransportKey/RequestKey/VerifyKey/Confirm
KEY_TYPE_NAMES = {
    0: "data/link",
    1: "network",
    2: "transport",
    3: "load",
    4: "verify",
}

CSV_COLUMNS = [
    "seq",
    "packet_id",
    "dt_ms",
    "time_abs_local",
    "time_unix",
    "pan",
    "channel",
    "length",
    "protocol",
    "frame_type",
    "mac_src",
    "mac_dst",
    "mac_src64",
    "mac_dst64",
    "mac_seq",
    "mac_cmd_id",
    "mac_cmd_name",
    "nwk_src",
    "nwk_dst",
    "nwk_src64",
    "nwk_dst64",
    "nwk_seq",
    "nwk_radius",
    "nwk_security",
    "nwk_fcf",
    "nwk_flags",
    "nwk_discover_route",
    "nwk_proto_version",
    "nwk_relay_count",
    "nwk_relay_index",
    "nwk_relays",
    "nwk_cmd_id",
    "nwk_cmd_name",
    "nwk_status_code",
    "nwk_status_target",
    "aps_fcf",
    "aps_security",
    "aps_ack_req",
    "aps_cmd_id",
    "aps_cmd_name",
    "aps_cluster",
    "aps_cluster_name",
    "aps_profile",
    "aps_src_ep",
    "aps_dst_ep",
    "aps_counter",
    "zcl_cmd_id",
    "zcl_cmd_name",
    "zcl_direction",
    "rssi",
    "lqi",
    "security_status",
    "decrypted",
    "decrypt_note",
    "ack_peer_seq",
    "summary",
]


# ---------- helpers ----------

def fmt_addr(v) -> str | None:
    if v is None:
        return None
    try:
        return f"0x{int(v) & 0xFFFF:04X}"
    except (TypeError, ValueError):
        return str(v)


def fmt_eui(v) -> str | None:
    if not v:
        return None
    s = str(v).lower().replace("0x", "").replace(":", "")
    return s if len(s) == 16 else str(v)


def _jsonable(v):
    if isinstance(v, bytes):
        return v.hex()
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def _redact(pkt: dict) -> dict:
    """Strip key material before serializing."""
    d = dict(pkt)
    d.pop("sec_key", None)
    d.pop("raw_layers", None)
    if d.get("aps_cmd_id") in KEY_MANAGEMENT_APS_CMDS:
        d["aps_payload_hex"] = None
    if isinstance(d.get("mac_cmd_payload"), bytes):
        d["mac_cmd_payload"] = d["mac_cmd_payload"].hex()
    return _jsonable(d)


def _pan_of(pkt: dict) -> int | None:
    return pkt.get("pan_src") or pkt.get("pan_dst")


def _src_of(pkt: dict) -> int | None:
    return pkt.get("nwk_src") if pkt.get("nwk_src") is not None else pkt.get("mac_src")


def _dst_of(pkt: dict) -> int | None:
    return pkt.get("nwk_dst") if pkt.get("nwk_dst") is not None else pkt.get("mac_dst")


def _capability_text(cap: int) -> str:
    parts = []
    if cap & 0x01:
        parts.append("alternate_coordinator")
    parts.append("router" if cap & 0x02 else "end_device")
    if cap & 0x04:
        parts.append("mains_powered")
    if cap & 0x08:
        parts.append("rx_on_when_idle")
    if cap & 0x20:
        parts.append("security_capable")
    return ", ".join(parts) or f"0x{cap:02X}"


def protocol_of(pkt: dict) -> str:
    if pkt.get("nwk_cmd_id") is not None:
        return "ZigBee NWK"
    if pkt.get("aps_cmd_id") is not None:
        return "ZigBee APS"
    if pkt.get("zcl_cmd_id") is not None or pkt.get("zcl_seq") is not None:
        return "ZigBee APS/ZCL"
    if pkt.get("aps_cluster") is not None:
        return "ZigBee APS"
    if pkt.get("mac_cmd_id") is not None:
        return "ZigBee MAC"
    if pkt.get("mac_frame_type") == 0:
        return "ZigBee MAC (Beacon)"
    if pkt.get("mac_frame_type") == 3:
        return "ZigBee MAC"
    return "ZigBee"


def csv_record(pkt: dict, ack_peer_seq: int | None = None) -> dict:
    nwk_cmd_id = pkt.get("nwk_cmd_id")
    aps_cmd_id = pkt.get("aps_cmd_id")
    return {
        "seq": pkt.get("seq"),
        "packet_id": pkt.get("packet_id"),
        "dt_ms": pkt.get("dt_ms"),
        "time_abs_local": datetime.fromtimestamp(pkt["ts"]).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "time_unix": round(pkt["ts"], 6),
        "pan": fmt_addr(pkt.get("pan")),
        "channel": pkt.get("ch"),
        "length": pkt.get("frame_len"),
        "protocol": protocol_of(pkt),
        "frame_type": pkt.get("pkt_type") or "Unknown",
        "mac_src": fmt_addr(pkt.get("mac_src")),
        "mac_dst": fmt_addr(pkt.get("mac_dst")),
        "mac_src64": fmt_eui(pkt.get("mac_src64")),
        "mac_dst64": fmt_eui(pkt.get("mac_dst64")),
        "mac_seq": pkt.get("mac_seq"),
        "mac_cmd_id": pkt.get("mac_cmd_id"),
        "mac_cmd_name": MAC_CMD_NAMES.get(pkt.get("mac_cmd_id")) if pkt.get("mac_cmd_id") is not None else None,
        "nwk_src": fmt_addr(pkt.get("nwk_src")),
        "nwk_dst": fmt_addr(pkt.get("nwk_dst")),
        "nwk_src64": fmt_eui(pkt.get("nwk_src64")),
        "nwk_dst64": fmt_eui(pkt.get("nwk_dst64")),
        "nwk_seq": pkt.get("nwk_seq"),
        "nwk_radius": pkt.get("nwk_radius"),
        "nwk_security": bool(pkt.get("nwk_security")),
        "nwk_fcf": pkt.get("nwk_fcf"),
        "nwk_flags": pkt.get("nwk_flags"),
        "nwk_discover_route": pkt.get("nwk_discover_route"),
        "nwk_proto_version": pkt.get("nwk_proto_version"),
        "nwk_relay_count": pkt.get("nwk_relay_count"),
        "nwk_relay_index": pkt.get("nwk_relay_index"),
        "nwk_relays": (
            ",".join(fmt_addr(a) or "" for a in pkt["nwk_relays"])
            if pkt.get("nwk_relays")
            else None
        ),
        "nwk_cmd_id": nwk_cmd_id,
        "nwk_cmd_name": NWK_COMMAND_NAMES.get(nwk_cmd_id) if nwk_cmd_id is not None else None,
        "nwk_status_code": pkt.get("nwk_status_code"),
        "nwk_status_target": fmt_addr(pkt.get("nwk_status_target")),
        "aps_fcf": pkt.get("aps_fcf"),
        "aps_security": pkt.get("aps_security"),
        "aps_ack_req": pkt.get("aps_ack_req"),
        "aps_cmd_id": aps_cmd_id,
        "aps_cmd_name": pkt.get("aps_cmd_name"),
        "aps_cluster": pkt.get("aps_cluster"),
        "aps_cluster_name": pkt.get("aps_cluster_name"),
        "aps_profile": pkt.get("aps_profile"),
        "aps_src_ep": pkt.get("aps_src_ep"),
        "aps_dst_ep": pkt.get("aps_dst_ep"),
        "aps_counter": pkt.get("aps_counter"),
        "zcl_cmd_id": pkt.get("zcl_cmd_id"),
        "zcl_cmd_name": pkt.get("zcl_cmd_name"),
        "zcl_direction": pkt.get("zcl_direction"),
        "rssi": pkt.get("rssi"),
        "lqi": pkt.get("lqi"),
        "security_status": pkt.get("security") or "unsecured",
        "decrypted": bool(pkt.get("decrypted")),
        "decrypt_note": pkt.get("decrypt_note"),
        "ack_peer_seq": ack_peer_seq,
        "summary": packet_summary(pkt, ack_peer_seq),
    }


def write_csv(path: Path, packets: list[dict], ack_peer: dict[int, int | None]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for i, p in enumerate(packets):
            writer.writerow(csv_record(p, ack_peer.get(i)))


def decode_zdp(cluster_id: int, payload_hex: str | None) -> dict | None:
    """Decode common ZDP request/response payloads into simple dicts."""
    if not payload_hex:
        return None
    try:
        pl = bytes.fromhex(payload_hex)
    except ValueError:
        return None
    if not pl:
        return None

    def eui(b: bytes) -> str:
        return f"{int.from_bytes(b, 'little'):016x}"

    # Device Announce: [seq][nwk:2][eui64:8][cap:1]
    if cluster_id == 0x0013 and len(pl) >= 12:
        cap = pl[11]
        return {
            "cmd": "device_announce",
            "nwk_addr": int.from_bytes(pl[1:3], "little"),
            "eui64": eui(pl[3:11]),
            "capability": cap,
            "capability_text": _capability_text(cap),
        }
    # NWK Addr Req: [seq][eui64:8][req_type][start]
    if cluster_id == 0x0000 and len(pl) >= 11:
        return {
            "cmd": "nwk_addr_req",
            "eui64": eui(pl[1:9]),
            "req_type": "single" if pl[9] == 0 else "extended",
            "start_index": pl[10],
        }
    # IEEE Addr Req: [seq][nwk:2][req_type][start]
    if cluster_id == 0x0001 and len(pl) >= 5:
        return {
            "cmd": "ieee_addr_req",
            "nwk_addr": int.from_bytes(pl[1:3], "little"),
            "req_type": "single" if pl[3] == 0 else "extended",
            "start_index": pl[4],
        }
    # Desc/EP requests: [seq][nwk:2]
    if cluster_id in (0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0010) and len(pl) >= 3:
        cmd = {
            0x0002: "node_desc_req",
            0x0003: "power_desc_req",
            0x0004: "simple_desc_req",
            0x0005: "active_ep_req",
            0x0006: "match_desc_req",
            0x0010: "end_dev_announce",
        }[cluster_id]
        out: dict = {"cmd": cmd, "nwk_addr": int.from_bytes(pl[1:3], "little")}
        if cluster_id == 0x0004 and len(pl) >= 4:
            out["endpoint"] = pl[3]
        return out
    # Addr responses: [seq][status][eui64:8][nwk:2][num_assoc][start]
    if cluster_id in (0x8000, 0x8001) and len(pl) >= 14:
        return {
            "cmd": "nwk_addr_resp" if cluster_id == 0x8000 else "ieee_addr_resp",
            "status": pl[1],
            "eui64": eui(pl[2:10]),
            "nwk_addr": int.from_bytes(pl[10:12], "little"),
            "num_assoc": pl[12],
            "start_index": pl[13],
        }
    # Node Desc Resp: [seq][status][nwk:2]
    if cluster_id == 0x8002 and len(pl) >= 4:
        return {
            "cmd": "node_desc_resp",
            "status": pl[1],
            "nwk_addr": int.from_bytes(pl[2:4], "little"),
        }
    # Simple Desc Resp: [seq][status][nwk:2][len][simple descriptor...]
    if cluster_id == 0x8004 and len(pl) >= 7:
        sd_len = pl[4]
        sd = pl[5:5 + sd_len]
        out = {
            "cmd": "simple_desc_resp",
            "status": pl[1],
            "nwk_addr": int.from_bytes(pl[2:4], "little"),
            "desc_len": sd_len,
        }
        if len(sd) >= 6:
            out["endpoint"] = sd[0]
            out["profile"] = int.from_bytes(sd[2:4], "little")
            out["device_id"] = int.from_bytes(sd[4:6], "little")
        return out
    # Active EP Resp: [seq][status][nwk:2][count][eps...]
    if cluster_id == 0x8005 and len(pl) >= 5:
        count = pl[4]
        return {
            "cmd": "active_ep_resp",
            "status": pl[1],
            "nwk_addr": int.from_bytes(pl[2:4], "little"),
            "endpoints": list(pl[5:5 + count]),
        }
    # Match Desc Resp: [seq][status][nwk:2][count][eps...]
    if cluster_id == 0x8006 and len(pl) >= 5:
        count = pl[4]
        return {
            "cmd": "match_desc_resp",
            "status": pl[1],
            "nwk_addr": int.from_bytes(pl[2:4], "little"),
            "endpoints": list(pl[5:5 + count]),
        }
    return None


def packet_summary(pkt: dict, ack_peer_seq: int | None = None) -> str:
    parts: list[str] = []
    t = pkt.get("pkt_type") or "Unknown"

    if pkt.get("nwk_cmd_id") is not None:
        cid = pkt["nwk_cmd_id"]
        name = NWK_COMMAND_NAMES.get(cid, f"NWK Cmd 0x{cid:02X}")
        if name == "Route Request" and pkt.get("route_req"):
            rr = pkt["route_req"]
            mto = " mto" if pkt.get("nwk_route_request_mto") else ""
            parts.append(
                f"{name} id={rr.get('id')} dest=0x{rr.get('dest', 0):04X} cost={rr.get('cost')}{mto}"
            )
        elif name == "Route Reply" and pkt.get("route_reply"):
            rp = pkt["route_reply"]
            parts.append(
                f"{name} id={rp.get('id')} orig=0x{rp.get('originator', 0):04X} resp=0x{rp.get('responder', 0):04X} cost={rp.get('cost')}"
            )
        elif name == "Network Status" and pkt.get("nwk_status_code") is not None:
            code = pkt["nwk_status_code"]
            code_name = NWK_STATUS_NAMES.get(code, f"0x{code:02X}")
            target = pkt.get("nwk_status_target")
            parts.append(f"{name} {code_name} target=0x{target:04X}" if target is not None else f"{name} {code_name}")
        elif name == "Leave":
            flags = []
            if pkt.get("nwk_leave_rejoin"):
                flags.append("rejoin")
            if pkt.get("nwk_leave_request"):
                flags.append("request")
            if pkt.get("nwk_leave_children"):
                flags.append("children")
            parts.append(f"{name} {','.join(flags)}" if flags else name)
        elif name == "Route Record" and pkt.get("route_record_relays"):
            rr = pkt["route_record_relays"]
            relays = rr.get("relays", [])
            parts.append(f"{name} relays={len(relays)} " + ",".join(f"0x{a:04X}" for a in relays[:8]))
        elif name == "Link Status" and pkt.get("link_status_neighbors") is not None:
            parts.append(f"{name} neighbors={len(pkt['link_status_neighbors'])}")
        else:
            parts.append(name)
    elif pkt.get("aps_cmd_name"):
        cmd = pkt["aps_cmd_name"]
        if pkt.get("aps_cmd_key_type") is not None:
            kt = pkt["aps_cmd_key_type"]
            kt_name = KEY_TYPE_NAMES.get(kt, f"0x{kt:02X}")
            cmd += f" key_type={kt_name}"
        parts.append(cmd)
    elif pkt.get("aps_cluster_name"):
        cluster = pkt["aps_cluster_name"]
        if cluster != "ZDP Cmd":
            parts.append(cluster)
        elif pkt.get("aps_cluster") is not None:
            parts.append(f"ZDP Cmd 0x{pkt['aps_cluster']:04X}")

    if pkt.get("zcl_cmd_name"):
        zcl = pkt["zcl_cmd_name"]
        direction = pkt.get("zcl_direction")
        seq = pkt.get("zcl_seq")
        extra = " ".join(x for x in (direction, f"seq={seq}" if seq is not None else None) if x)
        parts.append(f"ZCL {zcl} {extra}".rstrip())

    zdp = pkt.get("zdp")
    if zdp:
        if zdp.get("cmd") == "device_announce":
            parts.append(
                f"announce nwk=0x{zdp['nwk_addr']:04X} eui={zdp['eui64']} {zdp['capability_text']}"
            )
        elif zdp.get("cmd") in ("nwk_addr_req", "ieee_addr_req"):
            key = "eui" if "eui64" in zdp else "nwk"
            parts.append(f"{zdp['cmd']} {key}={zdp.get('eui64') or fmt_addr(zdp.get('nwk_addr'))}")
        elif zdp.get("cmd") in ("nwk_addr_resp", "ieee_addr_resp"):
            parts.append(
                f"{zdp['cmd']} status=0x{zdp['status']:02X} nwk=0x{zdp['nwk_addr']:04X} eui={zdp['eui64']}"
            )
        elif zdp.get("cmd") == "active_ep_resp":
            parts.append(f"active_ep status=0x{zdp['status']:02X} eps={zdp['endpoints']}")
        elif zdp.get("cmd") == "simple_desc_resp":
            parts.append(
                f"simple_desc status=0x{zdp['status']:02X} ep={zdp.get('endpoint')} profile=0x{zdp.get('profile', 0):04X} dev=0x{zdp.get('device_id', 0):04X}"
            )

    if pkt.get("mac_cmd_id") is not None:
        cid = pkt["mac_cmd_id"]
        name = MAC_CMD_NAMES.get(cid, f"MAC Cmd 0x{cid:02X}")
        parts.append(name)
        if pkt.get("mac_src64") and pkt.get("nwk_src") is None:
            parts.append(f"src_eui={pkt['mac_src64']}")
        if pkt.get("mac_dst64") and pkt.get("nwk_dst") is None:
            parts.append(f"dst_eui={pkt['mac_dst64']}")

    if pkt.get("mac_beacon_pan") is not None:
        parts.append(f"beacon_pan=0x{pkt['mac_beacon_pan']:04X} permit={pkt.get('mac_beacon_permit')}")

    if pkt.get("security") == "Encrypted":
        note = pkt.get("decrypt_note") or "unknown"
        kt = pkt.get("sec_key_type")
        kt_s = KEY_TYPE_NAMES.get(kt, f"0x{kt:02X}") if kt is not None else None
        parts.append(f"Encrypted({note})" + (f" key_type={kt_s}" if kt_s else ""))

    if ack_peer_seq is not None:
        parts.append(f"ack_of_seq={ack_peer_seq}")

    return " | ".join(parts) if parts else t


def enrich_packets(packets: list[dict]) -> list[dict]:
    if not packets:
        return packets
    ts0 = packets[0]["ts"]
    for i, p in enumerate(packets):
        p["seq"] = i
        p["dt_ms"] = round((p["ts"] - ts0) * 1000.0, 3)
        p["zdp"] = (
            decode_zdp(p.get("aps_cluster"), p.get("aps_payload_hex"))
            if p.get("aps_profile") == 0
            else None
        )
        p["pan"] = _pan_of(p)
        p["src"] = _src_of(p)
        p["dst"] = _dst_of(p)
    return packets


def isolate_key_store(out_dir: Path) -> None:
    key_dir = out_dir / ".keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    key_file = key_dir / "zigbee_pc_keys"
    if not key_file.exists():
        appdata = os.environ.get("APPDATA")
        if appdata:
            src = Path(appdata) / "Wireshark" / "zigbee_pc_keys"
            if src.is_file():
                try:
                    shutil.copyfile(src, key_file)
                except OSError:
                    pass
    _ks.WIRESHARK_CONFIG_DIR = str(key_dir)
    _ks.KEYS_FILE = str(key_file)


# ---------- graph ----------

def build_graph(packets: list[dict], target_pan: int | None):
    nodes: dict[tuple[int | None, int], dict] = {}
    edges: dict[tuple[int | None, int, int], dict] = {}
    broadcast: Counter = Counter()
    eui_to_addrs: dict[str, set[tuple[int, int | None]]] = defaultdict(set)

    for p in packets:
        pan = _pan_of(p)
        ts = p["ts"]
        addrs = {
            a
            for a in (p.get("nwk_src"), p.get("nwk_dst"), p.get("mac_src"), p.get("mac_dst"))
            if isinstance(a, int) and 0 <= a < 0xFFF0
        }
        for a in addrs:
            node = _get_node(nodes, a, ts, pan)
            node["types"][p.get("pkt_type") or "Unknown"] += 1
            if p.get("aps_cluster_name"):
                node["clusters"][p["aps_cluster_name"]] += 1
            if p.get("nwk_cmd_id") == 8:
                node["link_status"] = True
            if p.get("nwk_cmd_id") == 2:
                node["route_reply"] = True
            if p.get("mac_cmd_id") == 4:
                node["poll"] = True
            zdp = p.get("zdp")
            if a == p.get("nwk_src") and zdp and zdp.get("cmd") == "device_announce":
                node["announce_cap"] = "router" if zdp["capability"] & 0x02 else "end_device"

        # EUI64 <-> short address mappings
        nwk_src = p.get("nwk_src")
        nwk_src64 = fmt_eui(p.get("nwk_src64"))
        if nwk_src is not None and nwk_src < 0xFFF0 and nwk_src64:
            _get_node(nodes, nwk_src, ts, pan)["eui64s"].add(nwk_src64)
            eui_to_addrs[nwk_src64].add((nwk_src, pan))
        mac_src = p.get("mac_src")
        mac_src64 = fmt_eui(p.get("mac_src64"))
        if mac_src is not None and mac_src < 0xFFF0 and mac_src64:
            _get_node(nodes, mac_src, ts, pan)["eui64s"].add(mac_src64)
            eui_to_addrs[mac_src64].add((mac_src, pan))
        mac_dst = p.get("mac_dst")
        mac_dst64 = fmt_eui(p.get("mac_dst64"))
        if mac_dst is not None and mac_dst < 0xFFF0 and mac_dst64:
            _get_node(nodes, mac_dst, ts, pan)["eui64s"].add(mac_dst64)
            eui_to_addrs[mac_dst64].add((mac_dst, pan))
        zdp = p.get("zdp")
        if zdp and "eui64" in zdp and "nwk_addr" in zdp:
            nwk_addr = zdp["nwk_addr"]
            if nwk_addr < 0xFFF0:
                _get_node(nodes, nwk_addr, ts, pan)["eui64s"].add(zdp["eui64"])
                eui_to_addrs[zdp["eui64"]].add((nwk_addr, pan))

        # Edges between real short addresses.
        src = _src_of(p)
        dst = _dst_of(p)
        if src is not None and dst is not None and 0 <= src < 0xFFF0 and 0 <= dst < 0xFFF0 and src != dst:
            key = (pan, src, dst)
            edge = edges.setdefault(
                key,
                {
                    "src": src,
                    "dst": dst,
                    "pan": pan,
                    "types": Counter(),
                    "clusters": Counter(),
                    "first_ts": ts,
                    "last_ts": ts,
                },
            )
            edge["types"][p.get("pkt_type") or "Unknown"] += 1
            if p.get("aps_cluster_name"):
                edge["clusters"][p["aps_cluster_name"]] += 1
            edge["first_ts"] = min(edge["first_ts"], ts)
            edge["last_ts"] = max(edge["last_ts"], ts)
        elif src is not None and 0 <= src < 0xFFF0 and (dst is None or dst >= 0xFFF0):
            broadcast[(src, dst if dst is not None else -1, pan)] += 1

    node_list = []
    for (pan, a), n in nodes.items():
        if a == 0:
            role = "coordinator"
        elif n["link_status"] or n["route_reply"]:
            role = "router"
        elif n["poll"]:
            role = "end_device"
        elif n["announce_cap"]:
            role = n["announce_cap"]
        else:
            role = "unknown"
        node_list.append(
            {
                "addr": fmt_addr(a),
                "pan": fmt_addr(pan) if pan is not None else None,
                "eui64s": sorted(n["eui64s"]),
                "role": role,
                "packets": sum(n["types"].values()),
                "first_ts": round(n["first_ts"], 6),
                "last_ts": round(n["last_ts"], 6),
                "by_type": dict(n["types"].most_common()),
                "clusters": [c for c, _ in n["clusters"].most_common(20)],
            }
        )
    node_list.sort(key=lambda x: (-x["packets"], x["addr"], x["pan"] or ""))

    edge_list = []
    for (pan, src, dst), e in edges.items():
        edge_list.append(
            {
                "src": fmt_addr(src),
                "dst": fmt_addr(dst),
                "pan": fmt_addr(pan) if pan is not None else None,
                "packets": sum(e["types"].values()),
                "first_ts": round(e["first_ts"], 6),
                "last_ts": round(e["last_ts"], 6),
                "by_type": dict(e["types"].most_common()),
                "clusters": [c for c, _ in e["clusters"].most_common(10)],
            }
        )
    edge_list.sort(key=lambda x: -x["packets"])

    eui_mappings = [
        {
            "eui64": eui,
            "mappings": [
                {"short_addr": fmt_addr(a), "pan": fmt_addr(pan) if pan is not None else None}
                for a, pan in sorted(addrs, key=lambda x: (x[0], x[1] is None, x[1]))
            ],
        }
        for eui, addrs in sorted(eui_to_addrs.items())
    ]

    broadcast_list = [
        {
            "src": fmt_addr(src),
            "dst": "broadcast/0x%04X" % (dst if dst >= 0 else 0xFFFF),
            "pan": fmt_addr(pan) if pan is not None else None,
            "packets": count,
        }
        for (src, dst, pan), count in broadcast.most_common(50)
    ]

    return {
        "nodes": node_list,
        "edges": edge_list,
        "eui_mappings": eui_mappings,
        "broadcast": broadcast_list,
        "target_pan": fmt_addr(target_pan) if target_pan is not None else None,
    }


def _get_node(
    nodes: dict[tuple[int | None, int], dict],
    addr: int,
    ts: float,
    pan: int | None,
) -> dict:
    key = (pan, addr)
    node = nodes.get(key)
    if node is None:
        node = {
            "pan": pan,
            "addr": addr,
            "eui64s": set(),
            "types": Counter(),
            "clusters": Counter(),
            "first_ts": ts,
            "last_ts": ts,
            "link_status": False,
            "route_reply": False,
            "poll": False,
            "announce_cap": None,
        }
        nodes[key] = node
    else:
        node["first_ts"] = min(node["first_ts"], ts)
        node["last_ts"] = max(node["last_ts"], ts)
    return node


# ---------- serialization ----------

def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def event_record(pkt: dict, ack_peer_seq: int | None = None) -> dict:
    mac = None
    if pkt.get("mac_frame_type") is not None or pkt.get("mac_cmd_id") is not None:
        mac = {
            "frame_type": pkt.get("mac_frame_type"),
            "seq": pkt.get("mac_seq"),
            "src": fmt_addr(pkt.get("mac_src")),
            "dst": fmt_addr(pkt.get("mac_dst")),
            "src_eui64": fmt_eui(pkt.get("mac_src64")),
            "dst_eui64": fmt_eui(pkt.get("mac_dst64")),
            "cmd_id": pkt.get("mac_cmd_id"),
            "cmd_name": MAC_CMD_NAMES.get(pkt.get("mac_cmd_id"), None) if pkt.get("mac_cmd_id") is not None else None,
            "beacon_pan": pkt.get("mac_beacon_pan"),
            "beacon_permit": pkt.get("mac_beacon_permit"),
        }
    nwk = None
    if pkt.get("nwk_src") is not None or pkt.get("nwk_dst") is not None:
        nwk = {
            "src": fmt_addr(pkt.get("nwk_src")),
            "dst": fmt_addr(pkt.get("nwk_dst")),
            "seq": pkt.get("nwk_seq"),
            "radius": pkt.get("nwk_radius"),
            "src_eui64": fmt_eui(pkt.get("nwk_src64")),
            "security": bool(pkt.get("nwk_security")),
            "cmd_id": pkt.get("nwk_cmd_id"),
            "cmd_name": NWK_COMMAND_NAMES.get(pkt.get("nwk_cmd_id")) if pkt.get("nwk_cmd_id") is not None else None,
            "status_code": pkt.get("nwk_status_code"),
            "status_target": fmt_addr(pkt.get("nwk_status_target")),
            "link_status_neighbors": pkt.get("link_status_neighbors"),
            "route_record_relays": pkt.get("route_record_relays"),
        }
    aps = None
    if pkt.get("aps_cluster") is not None or pkt.get("aps_cmd_id") is not None:
        aps = {
            "cluster": pkt.get("aps_cluster"),
            "cluster_name": pkt.get("aps_cluster_name"),
            "profile": pkt.get("aps_profile"),
            "counter": pkt.get("aps_counter"),
            "src_ep": pkt.get("aps_src_ep"),
            "dst_ep": pkt.get("aps_dst_ep"),
            "cmd_id": pkt.get("aps_cmd_id"),
            "cmd_name": pkt.get("aps_cmd_name"),
            "cmd_key_type": pkt.get("aps_cmd_key_type"),
            "payload_hex": pkt.get("aps_payload_hex") if pkt.get("aps_cmd_id") not in KEY_MANAGEMENT_APS_CMDS else None,
        }
    zcl = None
    if pkt.get("zcl_cmd_id") is not None or pkt.get("zcl_seq") is not None:
        zcl = {
            "cmd_id": pkt.get("zcl_cmd_id"),
            "cmd_name": pkt.get("zcl_cmd_name"),
            "direction": pkt.get("zcl_direction"),
            "seq": pkt.get("zcl_seq"),
            "attr_reads": pkt.get("zcl_attr_reads"),
        }
    sec = {
        "status": pkt.get("security") or "unsecured",
        "decrypted": bool(pkt.get("decrypted")),
        "note": pkt.get("decrypt_note"),
        "key_label": pkt.get("sec_key_label"),
        "key_type": pkt.get("sec_key_type"),
        "frame_counter": pkt.get("sec_frame_counter"),
        "mic": pkt.get("sec_mic"),
    }
    return {
        "seq": pkt.get("seq"),
        "packet_id": pkt.get("packet_id"),
        "ts": round(pkt["ts"], 6),
        "dt_ms": pkt.get("dt_ms"),
        "pan": fmt_addr(pkt.get("pan")),
        "type": pkt.get("pkt_type") or "Unknown",
        "src": fmt_addr(_src_of(pkt)),
        "dst": fmt_addr(_dst_of(pkt)),
        "ch": pkt.get("ch"),
        "lqi": pkt.get("lqi"),
        "rssi": pkt.get("rssi"),
        "mac": mac,
        "nwk": nwk,
        "aps": aps,
        "zcl": zcl,
        "zdp": pkt.get("zdp"),
        "sec": sec,
        "ack_peer_seq": ack_peer_seq,
        "summary": packet_summary(pkt, ack_peer_seq),
    }


def collect_key_events(packets: list[dict]) -> list[dict]:
    events: list[dict] = []
    permit_state: dict[int, int] = {}
    for p in packets:
        pan = _pan_of(p)
        ts = p["ts"]
        dt = p.get("dt_ms")
        src = fmt_addr(_src_of(p))
        dst = fmt_addr(_dst_of(p))
        summary = packet_summary(p)

        if p.get("mac_beacon_permit") is not None:
            prev = permit_state.get(pan)
            if prev != p["mac_beacon_permit"]:
                events.append(
                    {
                        "dt_ms": dt,
                        "packet_id": p["packet_id"],
                        "event": "beacon_permit",
                        "pan": fmt_addr(pan),
                        "src": src,
                        "detail": f"permit={p['mac_beacon_permit']}",
                    }
                )
                permit_state[pan] = p["mac_beacon_permit"]
        if p.get("mac_cmd_id") in (1, 2):
            events.append(
                {
                    "dt_ms": dt,
                    "packet_id": p["packet_id"],
                    "event": "association",
                    "pan": fmt_addr(pan),
                    "src": src,
                    "dst": dst,
                    "detail": summary,
                }
            )
        if p.get("aps_cmd_id") is not None:
            events.append(
                {
                    "dt_ms": dt,
                    "packet_id": p["packet_id"],
                    "event": "aps_key_management",
                    "pan": fmt_addr(pan),
                    "src": src,
                    "dst": dst,
                    "detail": summary,
                }
            )
        if p.get("aps_cluster") == 0x0013:
            events.append(
                {
                    "dt_ms": dt,
                    "packet_id": p["packet_id"],
                    "event": "device_announce",
                    "pan": fmt_addr(pan),
                    "src": src,
                    "dst": dst,
                    "detail": summary,
                }
            )
        if p.get("nwk_cmd_id") is not None:
            events.append(
                {
                    "dt_ms": dt,
                    "packet_id": p["packet_id"],
                    "event": "nwk_command",
                    "pan": fmt_addr(pan),
                    "src": src,
                    "dst": dst,
                    "detail": summary,
                }
            )
        if p.get("aps_cluster") in (
            0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006,
            0x8000, 0x8001, 0x8002, 0x8004, 0x8005, 0x8006,
        ):
            events.append(
                {
                    "dt_ms": dt,
                    "packet_id": p["packet_id"],
                    "event": "zdp",
                    "pan": fmt_addr(pan),
                    "src": src,
                    "dst": dst,
                    "detail": summary,
                }
            )
    return events


def write_timeline(path: Path, packets: list[dict], title: str, ack_peer: dict) -> None:
    lines = [
        f"# {title}",
        "",
        f"- 帧数: {len(packets)}",
        f"- 起始 ts: {packets[0]['ts']:.6f}" if packets else "- 空",
        f"- 结束 ts: {packets[-1]['ts']:.6f}" if packets else "",
        "",
        "## 时间线",
        "",
        "格式: [相对毫秒] #序号 类型 源 -> 目标 PAN 摘要",
        "",
    ]
    for p in packets:
        idx = p.get("seq")
        dt = p.get("dt_ms")
        src = fmt_addr(_src_of(p)) or "-"
        dst = fmt_addr(_dst_of(p)) or "-"
        pan = fmt_addr(_pan_of(p)) or "-"
        ack_seq = ack_peer.get(idx)
        summary = packet_summary(p, ack_seq)
        lines.append(
            f"[{dt:>10.1f}ms] #{idx:>5} {p.get('pkt_type') or 'Unknown':<26} {src:>7} -> {dst:<7} PAN={pan:<6} {summary}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_digest(
    path: Path,
    capture_name: str,
    packets: list[dict],
    graph: dict,
    key_events: list[dict],
    target_pan: int | None,
) -> None:
    ts0 = packets[0]["ts"]
    ts1 = packets[-1]["ts"]
    total = len(packets)
    decrypted = sum(1 for p in packets if p.get("decrypted"))
    encrypted = sum(1 for p in packets if p.get("security") == "Encrypted")
    types = Counter(p.get("pkt_type") or "Unknown" for p in packets)
    target_pan_s = fmt_addr(target_pan) if target_pan is not None else None
    target_nodes = [n for n in graph["nodes"] if n["pan"] == target_pan_s] if target_pan_s else graph["nodes"]
    target_edges = [e for e in graph["edges"] if e["pan"] == target_pan_s] if target_pan_s else graph["edges"]
    target_key_events = [ev for ev in key_events if ev.get("pan") == target_pan_s] if target_pan_s else key_events
    lines = [
        f"# {capture_name} — AI 摘要",
        "",
        "## 抓包概览",
        "",
        f"- 帧数: {total}",
        f"- 时长: {ts1 - ts0:.3f}s ({ts1 - ts0:.1f} 秒)",
        f"- 起始 ts: {ts0:.6f}",
        f"- 结束 ts: {ts1:.6f}",
        f"- 解密帧: {decrypted} / 加密未解密: {encrypted} / 未加密: {total - decrypted - encrypted}",
        f"- 目标 PAN: {fmt_addr(target_pan) if target_pan is not None else '未指定'}",
        f"- 目标 PAN 帧数: {sum(1 for p in packets if _pan_of(p) == target_pan) if target_pan is not None else total}",
        "",
        "## 帧类型分布",
        "",
    ]
    if target_pan is not None:
        types = Counter(p.get("pkt_type") or "Unknown" for p in packets if _pan_of(p) == target_pan)
    for name, count in types.most_common(25):
        lines.append(f"- {name}: {count}")
    lines += ["", "## 节点", ""]
    lines.append("| 短地址 | EUI64 | 角色 | PAN | 帧数 | 首次 | 末次 |")
    lines.append("|---|---|---|---|---|---|---|")
    for n in target_nodes[:40]:
        euis = ", ".join(n["eui64s"][:2]) or "-"
        first = f"{n['first_ts'] - ts0:.1f}s"
        last = f"{n['last_ts'] - ts0:.1f}s"
        lines.append(
            f"| {n['addr']} | {euis} | {n['role']} | {n['pan'] or '-'} | {n['packets']} | {first} | {last} |"
        )
    lines += ["", "## 节点交互（按帧数排序）", ""]
    lines.append("| 源 | 目标 | 帧数 | PAN | 主要类型 | 主要 Cluster | 时间范围 |")
    lines.append("|---|---|---|---|---|---|---|")
    for e in target_edges[:40]:
        top_type = max(e["by_type"], key=e["by_type"].get) if e["by_type"] else "-"
        top_cluster = e["clusters"][0] if e["clusters"] else "-"
        first = f"{e['first_ts'] - ts0:.1f}s"
        last = f"{e['last_ts'] - ts0:.1f}s"
        lines.append(
            f"| {e['src']} | {e['dst']} | {e['packets']} | {e['pan'] or '-'} | {top_type} | {top_cluster} | {first} → {last} |"
        )
    if target_pan is not None:
        lines.append("")
        lines.append("> 其他 PAN 的节点/交互完整数据见 interactions.json。")
    lines += ["", "## 关键时序事件", ""]
    for ev in target_key_events[:200]:
        dt = ev["dt_ms"]
        lines.append(
            f"- `[+{dt:>9.1f}ms]` #{ev['packet_id']} **{ev['event']}** PAN={ev['pan'] or '-'} {ev.get('src') or '-'} → {ev.get('dst') or '-'} — {ev['detail']}"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(out_dir: Path, target_pan: int | None) -> None:
    text = """# AI 数据包说明

本目录由 scripts/export_ai_dataset.py 从 .cubx 抓包生成。

- metadata.json — 抓包元信息、PAN 统计、解密情况
- packets.jsonl — 每帧完整字段（密钥值已脱敏）
- events.jsonl — 紧凑语义事件（全 PAN）
- events_target.jsonl — 目标 PAN 事件
- interactions.json — 节点 / EUI64 映射 / 交互边统计
- timeline.md — 全 PAN 时间线
- timeline_target.md — 目标 PAN 时间线
- digest.md — 推荐 AI 直接阅读的摘要（节点、交互、关键事件）

密钥材料（Network/Link Key 值、TransportKey 载荷）已从导出中移除。
"""
    if target_pan is not None:
        text += f"\n本次目标 PAN: 0x{target_pan:04X}\n"
    text += "\n- packets.csv / packets_target.csv: Wireshark-style CSV (all columns)\n"
    (out_dir / "README.md").write_text(text, encoding="utf-8")


# ---------- main ----------

def infer_target_pan(packets: list[dict]) -> int | None:
    pan_dec: dict[int, int] = defaultdict(int)
    pan_all: dict[int, int] = defaultdict(int)
    for p in packets:
        pan = _pan_of(p)
        if pan is None:
            continue
        pan_all[pan] += 1
        if p.get("decrypted"):
            pan_dec[pan] += 1
    if pan_dec:
        return max(pan_dec, key=pan_dec.get)
    return max(pan_all, key=pan_all.get) if pan_all else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Export .cubx capture to AI-readable dataset")
    ap.add_argument("capture", type=Path, help="path to .cubx file")
    ap.add_argument("--out", type=Path, default=None, help="output directory (default: exports/ai/<capture-name>)")
    ap.add_argument("--target-pan", type=lambda s: int(s, 16), default=None, help="target PAN hex, e.g. 580C")
    ap.add_argument("--no-mac-frames", action="store_true", help="exclude MAC command frames / beacons")
    args = ap.parse_args()

    capture = Path(args.capture).expanduser().resolve()
    if not capture.is_file():
        sys.exit(f"capture not found: {capture}")
    if capture.suffix.lower() != ".cubx":
        print(f"warning: expected .cubx, got {capture.suffix or '(none)'}", file=sys.stderr)

    out_dir = args.out
    if out_dir is None:
        out_dir = ROOT / "exports" / "ai" / (capture.stem + "_ai")
    out_dir = out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    isolate_key_store(out_dir)

    def progress(done: int, total: int) -> None:
        if done % 1000 == 0 or done == total:
            print(f"parsing {done}/{total}", file=sys.stderr)

    print(f"parsing {capture.name} ...", file=sys.stderr)
    packets, keys_added, keys_total = cubx_reader.parse_cubx(
        str(capture),
        include_mac_frames=not args.no_mac_frames,
        progress_cb=progress,
    )
    packets = enrich_packets(packets)
    print(f"parsed {len(packets)} packets", file=sys.stderr)

    target_pan = args.target_pan if args.target_pan is not None else infer_target_pan(packets)

    ack_to_orig, orig_to_ack = build_ack_match(packets)
    ack_peer: dict[int, int] = {}
    for idx, p in enumerate(packets):
        if p.get("pkt_type") == "APS Ack":
            peer = ack_to_orig.get(idx)
        else:
            peer_info = orig_to_ack.get(idx)
            peer = peer_info[0] if peer_info else None
        ack_peer[idx] = peer

    events = [event_record(p, ack_peer.get(i)) for i, p in enumerate(packets)]
    graph = build_graph(packets, target_pan)
    key_events = collect_key_events(packets)

    write_jsonl(out_dir / "packets.jsonl", [_redact(p) for p in packets])
    write_jsonl(out_dir / "events.jsonl", events)
    write_csv(out_dir / "packets.csv", packets, ack_peer)
    if target_pan is not None:
        target_events = [e for e in events if e.get("pan") == fmt_addr(target_pan)]
        write_jsonl(out_dir / "events_target.jsonl", target_events)
        target_packets = [p for p in packets if _pan_of(p) == target_pan]
        write_csv(out_dir / "packets_target.csv", target_packets, ack_peer)
    else:
        target_events = []
        target_packets = []

    (out_dir / "interactions.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ts0 = packets[0]["ts"] if packets else None
    ts1 = packets[-1]["ts"] if packets else None
    pan_stats = defaultdict(lambda: {"packets": 0, "decrypted": 0, "first_ts": None, "last_ts": None})
    for p in packets:
        pan = _pan_of(p)
        if pan is None:
            continue
        s = pan_stats[pan]
        s["packets"] += 1
        s["decrypted"] += int(bool(p.get("decrypted")))
        s["first_ts"] = min(s["first_ts"], p["ts"]) if s["first_ts"] is not None else p["ts"]
        s["last_ts"] = max(s["last_ts"], p["ts"]) if s["last_ts"] is not None else p["ts"]
    metadata = {
        "source_file": str(capture),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parser": "backend.cubx_reader.parse_cubx + scripts/export_ai_dataset.py",
        "packets": len(packets),
        "ts_first": ts0,
        "ts_last": ts1,
        "duration_s": round(ts1 - ts0, 6) if ts0 is not None and ts1 is not None else None,
        "channels": sorted({p.get("ch") for p in packets if p.get("ch") is not None}),
        "target_pan": fmt_addr(target_pan) if target_pan is not None else None,
        "keys_loaded": keys_total,
        "keys_added": keys_added,
        "security": {
            "decrypted": sum(1 for p in packets if p.get("decrypted")),
            "encrypted": sum(1 for p in packets if p.get("security") == "Encrypted"),
            "unsecured": sum(1 for p in packets if not p.get("decrypted") and p.get("security") != "Encrypted"),
        },
        "packet_types": dict(Counter(p.get("pkt_type") or "Unknown" for p in packets).most_common()),
        "pan_stats": [
            {
                "pan": fmt_addr(pan),
                "packets": s["packets"],
                "decrypted": s["decrypted"],
                "first_ts": s["first_ts"],
                "last_ts": s["last_ts"],
            }
            for pan, s in sorted(pan_stats.items(), key=lambda x: -x[1]["packets"])
        ],
        "files": [
            "metadata.json", "packets.jsonl", "packets.csv", "events.jsonl",
            "events_target.jsonl", "packets_target.csv", "interactions.json",
            "timeline.md", "timeline_target.md", "digest.md", "README.md",
        ],
    }
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_timeline(out_dir / "timeline.md", packets, f"{capture.stem} 全 PAN 时间线", ack_peer)
    if target_pan is not None:
        write_timeline(
            out_dir / "timeline_target.md",
            target_packets,
            f"{capture.stem} 目标 PAN 0x{target_pan:04X} 时间线",
            ack_peer,
        )

    write_digest(
        out_dir / "digest.md",
        capture.stem,
        packets,
        graph,
        key_events,
        target_pan,
    )
    write_readme(out_dir, target_pan)

    # The isolated key-store copy was only needed during parsing; remove it so
    # the export directory never contains key material.
    key_dir = out_dir / ".keys"
    if key_dir.exists():
        shutil.rmtree(key_dir)

    print(f"done: {out_dir}", file=sys.stderr)
    print(
        json.dumps(
            {
                "out": str(out_dir),
                "packets": len(packets),
                "target_pan": fmt_addr(target_pan) if target_pan is not None else None,
                "events": len(events),
                "target_events": len(target_events),
                "target_packets": len(target_packets),
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
                "key_events": len(key_events),
                "decrypted": metadata["security"]["decrypted"],
                "encrypted": metadata["security"]["encrypted"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
