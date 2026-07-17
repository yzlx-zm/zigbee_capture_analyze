"""导入 API — tshark 解析 pcap/pcapng/cubx"""
from __future__ import annotations

import os

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from .. import tshark
from .. import config

router = APIRouter()

# 全局存储
_packets: list[dict] = []
_nodes: dict[str, dict] = {}
_stats: dict = {}


def get_packets():
    return _packets


def get_nodes():
    return _nodes


def get_stats():
    return _stats


@router.post("/import/local")
async def import_local(path: str = Form(...)):
    global _packets, _nodes, _stats
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, 400)

    files = []
    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        for f in sorted(os.listdir(path)):
            fp = os.path.join(path, f)
            if os.path.isfile(fp) and f.endswith(('.pcap', '.pcapng', '.cubx')):
                files.append(fp)
    if not files:
        return JSONResponse({"error": "未找到 pcap/pcapng/cubx 文件"}, 400)

    # .cubx → 提取密钥
    keys = []
    for fp in files:
        if fp.lower().endswith('.cubx'):
            import sqlite3
            try:
                conn = sqlite3.connect(fp)
                for row in conn.execute("SELECT Key FROM Keys"):
                    if isinstance(row[0], bytes):
                        keys.append(row[0].hex())
                conn.close()
            except Exception:
                pass

    key_str = keys[0] if keys else ""

    # tshark 解析所有文件
    all_pkts = []
    for fp in files:
        try:
            pkts = tshark.read_pcap(fp, key_str)
            all_pkts.extend(pkts)
        except Exception as e:
            pass

    all_pkts.sort(key=lambda p: p["ts"])
    _packets = all_pkts
    _nodes = tshark.extract_nodes(all_pkts)

    # 统计
    types = {}
    for p in all_pkts:
        t = "Beacon" if p["is_beacon"] else \
            "NWK Cmd" if p["nwk_frame_type"] == 1 else \
            "NWK Data" if p["nwk_frame_type"] == 0 else \
            "MAC" if "wpan" in p["proto"] else "Other"
        types[t] = types.get(t, 0) + 1

    _stats = {
        "total": len(all_pkts),
        "nodes": len(_nodes),
        "by_type": types,
        "time_start": all_pkts[0]["ts"] if all_pkts else 0,
        "time_end": all_pkts[-1]["ts"] if all_pkts else 0,
    }
    return {"ok": True, "packets": len(all_pkts), "stats": _stats}


@router.get("/import/status")
async def import_status():
    return _stats
