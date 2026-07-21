"""导入 API — CSV / pcap / cubx"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from .. import csv_reader

router = APIRouter()

_packets: list[dict] = []
_nodes: dict[int, dict] = {}
_file_type: str = ""


def get_packets():
    return _packets


def get_nodes():
    return _nodes


def _parse_clock_time(time_str: str, base_ts: float) -> float | None:
    """将 HH:MM:SS 时钟时间解析为绝对 Unix 时间戳 (UTC)。
    基于抓包第一帧的 UTC 日期，将时钟时间映射到当天 UTC 绝对时间。
    不做跨午夜修正 — 若早于抓包开始则自然包含所有包（无更早数据）。"""
    import calendar as _cal
    parts = time_str.split(":")
    if len(parts) < 2:
        return None
    h, m = int(parts[0]), int(parts[1])
    s = int(parts[2]) if len(parts) > 2 else 0
    clock_sec = h * 3600 + m * 60 + s
    base_dt_utc = datetime.utcfromtimestamp(base_ts)
    midnight_utc = base_dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_ts = _cal.timegm(midnight_utc.timetuple())
    return midnight_ts + clock_sec



@router.post("/import/files")
async def import_upload(files: list[UploadFile] = File(...)):
    global _packets, _nodes, _file_type
    import tempfile
    all_pkts = []
    for f in files:
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            with open(tmp_path, "wb") as out:
                while data := await f.read(1024 * 1024):
                    out.write(data)
            pkts = csv_reader.read_csv(tmp_path)
            all_pkts.extend(pkts)
        finally:
            try: os.unlink(tmp_path)
            except OSError: pass
    if not all_pkts:
        return JSONResponse({"error": "无有效数据"}, 400)
    all_pkts.sort(key=lambda p: p["ts"])
    _packets = all_pkts
    _nodes = csv_reader.extract_nodes(all_pkts)
    _file_type = "csv"
    types = {}
    for p in all_pkts:
        t = p["pkt_type"] or "Unknown"
        types[t] = types.get(t, 0) + 1
    return {"ok": True, "packets": len(all_pkts), "nodes": len(_nodes),
            "file_type": "csv", "by_type": dict(sorted(types.items(), key=lambda x: -x[1])[:20])}



@router.post("/import/local")
async def import_local(path: str = Form(...)):
    global _packets, _nodes, _file_type
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, 400)

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".csv":
            _packets = csv_reader.read_csv(path)
            _file_type = "csv"
        elif ext in (".pcap", ".pcapng"):
            return JSONResponse({"error": "pcap 格式暂不支持，请用 Ubiqua 导出 CSV"}, 400)
        elif ext == ".cubx":
            return JSONResponse({"error": "cubx 格式暂不支持，请用 Ubiqua 导出 CSV"}, 400)
        else:
            return JSONResponse({"error": f"不支持的文件格式: {ext}"}, 400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

    _nodes = csv_reader.extract_nodes(_packets)
    types = {}
    for p in _packets:
        t = p["pkt_type"] or "Unknown"
        types[t] = types.get(t, 0) + 1

    return {
        "ok": True,
        "packets": len(_packets),
        "nodes": len(_nodes),
        "file_type": _file_type,
        "by_type": dict(sorted(types.items(), key=lambda x: -x[1])[:20]),
    }


@router.delete("/import/clear")
async def import_clear():
    global _packets, _nodes, _file_type
    _packets = []; _nodes = {}; _file_type = ""
    return {"ok": True}


@router.get("/packets/summary")
async def packet_summary(addr: str = "", pan: str = "",
                         time_start: str = "", time_end: str = ""):
    """事件摘要 — 按地址→设备行为 / 按PAN→整体统计"""
    addr_int = int(addr, 16) if addr else None
    pan_int = int(pan, 16) if pan else None
    ts_start = None; ts_end = None
    if _packets and (time_start or time_end):
        base_ts = _packets[0]["ts"]
        if time_start:
            ts_start = _parse_clock_time(time_start, base_ts)
        if time_end:
            ts_end = _parse_clock_time(time_end, base_ts)
    # Collect matching packets
    matched = []
    for p in _packets:
        if addr_int is not None:
            if p["nwk_src"] != addr_int and p["nwk_dst"] != addr_int and p["mac_src"] != addr_int and p["mac_dst"] != addr_int:
                continue
        if pan_int is not None:
            if p["pan_src"] != pan_int and p["pan_dst"] != pan_int:
                continue
        if ts_start is not None and p["ts"] < ts_start: continue
        if ts_end is not None and p["ts"] > ts_end: continue
        matched.append(p)
    # Build summary
    if addr_int is not None:
        # Device behavior summary for one specific address
        type_counts = {}
        peers = {}
        for p in matched:
            t = p.get("pkt_type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1
            # Find communication peer
            peer = None
            if p.get("nwk_src") == addr_int and p.get("nwk_dst") and p["nwk_dst"] != 0xFFFF:
                peer = p["nwk_dst"]
            elif p.get("nwk_dst") == addr_int and p.get("nwk_src") and p["nwk_src"] != 0xFFFF:
                peer = p["nwk_src"]
            if peer is not None:
                peers[peer] = peers.get(peer, 0) + 1
        top_peers = sorted(peers.items(), key=lambda x: -x[1])[:5]
        return {
            "type": "device",
            "addr": f"0x{addr_int:04X}",
            "total_packets": len(matched),
            "type_counts": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
            "top_peers": [{"addr": f"0x{p:04X}", "count": c} for p, c in top_peers],
        }
    else:
        # PAN overall statistics
        type_counts = {}
        device_counts = {}
        for p in matched:
            t = p.get("pkt_type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1
            for addr in (p.get("nwk_src"), p.get("nwk_dst"), p.get("mac_src"), p.get("mac_dst")):
                if isinstance(addr, int) and 0x0000 <= addr < 0xFFF0:
                    device_counts[addr] = device_counts.get(addr, 0) + 1
        top_devices = sorted(device_counts.items(), key=lambda x: -x[1])[:20]
        return {
            "type": "pan",
            "pan": f"0x{pan_int:04X}" if pan_int else "全部",
            "total_packets": len(matched),
            "type_counts": dict(sorted(type_counts.items(), key=lambda x: -x[1])[:15]),
            "active_devices": len(device_counts),
            "top_devices": [{"addr": f"0x{d:04X}", "count": c} for d, c in top_devices],
        }


@router.get("/import/status")
async def import_status():
    ts_start = _packets[0]["ts"] if _packets else None
    ts_end = _packets[-1]["ts"] if _packets else None
    return {"total": len(_packets), "nodes": len(_nodes), "type": _file_type,
            "ts_start": ts_start, "ts_end": ts_end}


@router.get("/packets")
async def packet_list(addr: str = "", pan: str = "",
                      time_start: str = "", time_end: str = "",
                      limit: int = 500, offset: int = 0):
    """查询原始包列表，可按地址/PAN/时间过滤，返回分页+总数"""
    addr_int = int(addr, 16) if addr else None
    pan_int = int(pan, 16) if pan else None
    # Parse time: HH:MM:SS clock time → absolute timestamp
    ts_start = None; ts_end = None
    if _packets and (time_start or time_end):
        base_ts = _packets[0]["ts"]
        if time_start:
            ts_start = _parse_clock_time(time_start, base_ts)
        if time_end:
            ts_end = _parse_clock_time(time_end, base_ts)
    # Filter
    matched = []
    for p in _packets:
        if addr_int is not None:
            if p["nwk_src"] != addr_int and p["nwk_dst"] != addr_int and p["mac_src"] != addr_int and p["mac_dst"] != addr_int:
                continue
        if pan_int is not None:
            if p["pan_src"] != pan_int and p["pan_dst"] != pan_int:
                continue
        if ts_start is not None and p["ts"] < ts_start:
            continue
        if ts_end is not None and p["ts"] > ts_end:
            continue
        matched.append(p)
    total = len(matched)
    page = matched[offset:offset + limit]
    return {
        "packets": [{
            "ts": p["ts"], "ch": p.get("ch", 0), "pkt_type": p.get("pkt_type", ""),
            "mac_src": p.get("mac_src"), "mac_dst": p.get("mac_dst"),
            "nwk_src": p.get("nwk_src"), "nwk_dst": p.get("nwk_dst"),
            "pan_src": p.get("pan_src"), "pan_dst": p.get("pan_dst"),
            "security": p.get("security", ""), "status": p.get("status", ""),
        } for p in page],
        "total": total, "limit": limit, "offset": offset,
    }
