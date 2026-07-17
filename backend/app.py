"""FastAPI 应用"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from . import config
from .api.router import api


def create_app():
    app = FastAPI(title="Zigbee Analyzer", version="2.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(api)

    frontend = config.FRONTEND_DIR
    if not os.path.isdir(frontend) and getattr(sys, 'frozen', False):
        frontend = os.path.join(sys._MEIPASS, 'frontend')
    if os.path.isdir(frontend):
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
