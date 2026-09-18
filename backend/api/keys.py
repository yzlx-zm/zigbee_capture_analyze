"""密钥管理 API — zigbee_pc_keys 的 CRUD + 统计"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import key_store as _ks
from .files import get_packets

router = APIRouter()


class KeyAddRequest(BaseModel):
    key: str   # 支持 FC:90:D2... 或 FC90D263... 等格式
    label: str


@router.get("/keys")
async def list_keys():
    """获取所有已配置 Key + 命中统计"""
    keys = _ks.read_all_keys()
    pkts = get_packets()
    stats = _ks.get_match_stats(pkts) if pkts else None
    return {
        "keys": keys,
        "stats": stats,
    }


@router.post("/keys")
async def add_key(req: KeyAddRequest):
    """添加一个 NWK Key"""
    try:
        result = _ks.add_key(req.key, req.label)
        return {"ok": True, **result}
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, 400)


@router.delete("/keys/{label}")
async def delete_key(label: str):
    """删除一个 Key (预设 Key 不可删除)"""
    try:
        ok = _ks.remove_key(label)
        if not ok:
            return JSONResponse({"ok": False, "error": f"标签 '{label}' 不存在"}, 404)
        return {"ok": True}
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, 400)


@router.post("/keys/refresh-ubiqua")
async def refresh_ubiqua_keys():
    """U20-H: 手动从 Ubiqua 刷新密钥 (全类型: Network + Link Key).

    导入前会自动同步一次 (静默); 本端点供用户显式刷新 + 看到同步结果。
    Ubiqua 未运行 → 503 + 明确提示 (不静默, 手动入口需告知原因)。
    幂等: 按 hex 去重, 重复点击只更新统计。
    """
    from .files import _sync_ubiqua_keys
    r = _sync_ubiqua_keys()
    if not r.get("connected"):
        return JSONResponse({"ok": False, "error": r.get("error") or "Ubiqua 未运行", **r}, 503)
    return {"ok": True, **r}


@router.post("/keys/reprocess")
async def reprocess():
    """重新统计 Key 命中 (数据变化后更新)"""
    pkts = get_packets()
    if not pkts:
        return JSONResponse({"ok": False, "error": "无数据"}, 400)
    stats = _ks.get_match_stats(pkts)
    return {"ok": True, "stats": stats}
