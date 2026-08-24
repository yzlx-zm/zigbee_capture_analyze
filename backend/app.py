"""FastAPI 应用"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from . import config
from .api.router import api


class _NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """HTML 响应禁缓存 (2026-08-24 用户反馈修复: StaticFiles 无 Cache-Control,
    浏览器启发式缓存 index.html → 版本号递增失效, 前端修改用户永远看不到).
    js/css 仍走版本号 URL 机制; html 每次 ETag 协商 (文件变 → 重新下载)."""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        ct = resp.headers.get("content-type", "")
        if "text/html" in ct:
            resp.headers["Cache-Control"] = "no-cache"
        return resp


def create_app():
    app = FastAPI(title="Zigbee Analyzer", version="2.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(_NoCacheHTMLMiddleware)
    app.include_router(api)

    frontend = config.FRONTEND_DIR
    if not os.path.isdir(frontend) and getattr(sys, 'frozen', False):
        frontend = os.path.join(sys._MEIPASS, 'frontend')
    if os.path.isdir(frontend):
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
