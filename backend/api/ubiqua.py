"""Ubiqua 集成 API"""
from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from .. import ubiqua_api as ua

router = APIRouter(prefix="/ubiqua")


@router.get("/status")
async def ubiqua_status():
    """Ubiqua 连接状态 + sniffer 状态 + 包数"""
    client = ua.get_client()
    status = client.get_status()
    return {
        "connected": status.connected,
        "host": status.host,
        "port": status.port,
        "sniffer_id": status.sniffer_id,
        "sniffer_name": status.sniffer_name,
        "is_started": status.is_started,
        "channel": status.channel,
        "packet_count": status.packet_count,
        "error": status.error,
    }


@router.post("/connect")
async def ubiqua_connect(host: str = Form(default="localhost"), port: int = Form(default=19501)):
    """连接 Ubiqua"""
    client = ua.get_client(host, port)
    ok = client.ping()
    if ok:
        return {"ok": True, "host": host, "port": port}
    else:
        return JSONResponse({"ok": False, "error": f"无法连接 {host}:{port}"}, 503)


@router.get("/packets")
async def ubiqua_packets(offset: int = 0, limit: int = 100):
    """从 Ubiqua 读取原始包列表"""
    client = ua.get_client()
    pkts = client.get_packets(offset, limit)
    if pkts is None:
        return JSONResponse({"error": "无法读取包数据"}, 503)
    return {"packets": pkts, "count": len(pkts), "offset": offset, "limit": limit}


@router.post("/sniffer/start")
async def ubiqua_start(channel: int = Form(default=26)):
    """启动抓包"""
    client = ua.get_client()
    status = client.get_status()
    if not status.connected:
        return JSONResponse({"error": "Ubiqua 未连接"}, 503)
    if not status.sniffer_id:
        return JSONResponse({"error": "未找到 sniffer"}, 404)
    ok = client.start_sniffer(status.sniffer_id, channel)
    return {"ok": ok, "sniffer_id": status.sniffer_id, "channel": channel}


@router.post("/sniffer/stop")
async def ubiqua_stop():
    """停止抓包"""
    client = ua.get_client()
    status = client.get_status()
    if not status.connected or not status.sniffer_id:
        return JSONResponse({"error": "Ubiqua 未连接或无 sniffer"}, 503)
    ok = client.stop_sniffer(status.sniffer_id)
    return {"ok": ok}


@router.post("/capture/clear")
async def ubiqua_clear():
    """清空 Traffic View"""
    client = ua.get_client()
    ok = client.clear_capture()
    return {"ok": ok}


@router.post("/capture/save")
async def ubiqua_save(filepath: str = Form(...)):
    """保存当前抓包为 cubx"""
    client = ua.get_client()
    ok = client.save_capture(filepath)
    return {"ok": ok, "filepath": filepath}


@router.post("/capture/export-csv")
async def ubiqua_export_csv(filepath: str = Form(...)):
    """导出当前抓包为 CSV"""
    client = ua.get_client()
    ok = client.export_csv(filepath)
    return {"ok": ok, "filepath": filepath}


@router.get("/keys")
async def ubiqua_keys():
    """Ubiqua 密钥列表 (XML 解析后返回)"""
    client = ua.get_client()
    keys = client.list_keys()
    if keys is None:
        return JSONResponse({"error": "无法读取密钥 (Ubiqua 不可达)"}, 503)
    nwk = [k for k in keys if k.get("type") == "NetworkKey"]
    return {"keys": keys, "count": len(keys), "network_keys": len(nwk)}


@router.get("/filters")
async def ubiqua_filters():
    """Ubiqua 过滤器列表"""
    client = ua.get_client()
    filters = client.list_filters()
    if filters is None:
        return JSONResponse({"error": "无法读取过滤器"}, 503)
    return {"filters": filters, "count": len(filters)}


@router.post("/filters/toggle")
async def ubiqua_toggle_filter(filter_name: str = Form(...), enable: bool = Form(default=True)):
    """启用/禁用过滤器"""
    client = ua.get_client()
    if enable:
        ok = client.enable_filter(filter_name)
    else:
        ok = client.disable_filter(filter_name)
    return {"ok": ok, "filter": filter_name, "enabled": enable}
