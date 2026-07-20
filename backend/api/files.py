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


@router.get("/import/status")
async def import_status():
    return {"total": len(_packets), "nodes": len(_nodes), "type": _file_type}
