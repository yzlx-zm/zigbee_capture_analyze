"""API 路由"""
from fastapi import APIRouter
from .files import router as f_router
from .topology import router as t_router

api = APIRouter(prefix="/api")
api.include_router(f_router, tags=["import"])
api.include_router(t_router, tags=["topology"])
