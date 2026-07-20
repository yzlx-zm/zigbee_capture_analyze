"""导入 API — CSV / pcap / cubx"""
from __future__ import annotations

import os

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


@router.get("/import/status")
async def import_status():
    return {"total": len(_packets), "nodes": len(_nodes), "type": _file_type}


@router.get("/packets")
async def packet_list(addr: str = "", pan: str = "", limit: int = 500, offset: int = 0):
    """查询原始包列表，可按地址或PAN过滤"""
    result = []
    addr_int = int(addr, 16) if addr else None
    pan_int = int(pan, 16) if pan else None
    for p in _packets:
        if addr_int is not None:
            if p["nwk_src"] != addr_int and p["nwk_dst"] != addr_int and p["mac_src"] != addr_int and p["mac_dst"] != addr_int:
                continue
        if pan_int is not None:
            if p["pan_src"] != pan_int and p["pan_dst"] != pan_int:
                continue
        result.append(p)
        if len(result) >= offset + limit:
            break
    page = result[offset:offset + limit]
    # Convert to serializable format
    return [{
        "ts": p["ts"], "ch": p.get("ch", 0), "pkt_type": p.get("pkt_type", ""),
        "mac_src": p.get("mac_src"), "mac_dst": p.get("mac_dst"),
        "nwk_src": p.get("nwk_src"), "nwk_dst": p.get("nwk_dst"),
        "pan_src": p.get("pan_src"), "pan_dst": p.get("pan_dst"),
        "security": p.get("security", ""), "status": p.get("status", ""),
    } for p in page]
