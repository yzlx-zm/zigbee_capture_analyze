"""案例库 API — U12 诊断页学习机制 (场景 tab = 学习容器)

端点 (⚠️ 静态路径全部在动态 /{case_id} 之前注册 — FastAPI 按注册序匹配,
动态段先注册会截获静态路径, POST /annotate 曾被 /{case_id} 吞掉 404 实测):
- GET  /api/cases/scenarios   — 54 场景学习进度 (tab 渲染主数据)
- GET  /api/cases             — 案例列表 (?scenario= 过滤)
- POST /api/cases/annotate    — 当前导入包 + 标注 → 跑检测 → 案例入库
                                (PAN/设备/时间自动提取 + 自动场景命中 + 差距生成)
- POST /api/cases/similar     — 相似案例检索 (新包诊断时 "相似历史案例" 区)
- GET  /api/cases/gaps        — 差距报告 (检测 vs 标注未对齐 → 待完善清单)
- POST /api/cases/export      — 导出 zip (后台任务, 复用 U6 _start_import 互斥)
- POST /api/cases/import      — 导入 zip (后台任务)
- GET  /api/cases/download    — 下载导出 zip / 案例素材副本 (人工复验)
- GET  /api/cases/{id}        — 案例详情
- POST /api/cases/{id}        — 更新 (status/annotation/scenarios 人工修订)
- DELETE /api/cases/{id}      — 删除
"""
from __future__ import annotations

import os
import re

from fastapi import APIRouter, Form, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from .. import case_library as cl
from .files import get_packets, get_full_packets, get_nodes, _start_import, _task_update
from .topology import _diag_pkts, _pan_int

router = APIRouter(prefix="/cases")


@router.get("/scenarios")
async def scenarios():
    """场景学习进度: 已学 X/N + 每场景 (白话名/检测器覆盖/案例数)."""
    return cl.scenario_stats()


@router.get("")
async def list_cases(scenario: str = Query(default="")):
    """案例列表 (?scenario=L3-5 过滤归属; 输出摘要不带大数组)."""
    scen = scenario if scenario in cl.SCENARIOS else None
    return {"cases": [cl._case_brief(c) for c in cl.list_cases(scen)],
            "root_cause_suggestions": cl.ROOT_CAUSE_SUGGESTIONS,
            "severity_levels": cl.SEVERITY_LEVELS}


@router.get("/gaps")
async def gaps():
    """差距报告: 检测命中 vs 案例标注未对齐 → 场景聚合 (检测器改进优先级)."""
    return cl.gap_report()


class SimilarRequest(BaseModel):
    scenarios: list[str] = []
    phenomenon: str = ""
    root_cause: str = ""
    pan: int | None = None
    device_addr: int | None = None
    k: int = 5


@router.post("/similar")
async def similar(req: SimilarRequest):
    """相似案例检索 — 新包诊断时调用 (probe = 检测命中 + 标注摘要)."""
    results = cl.find_similar({
        "scenarios": req.scenarios,
        "phenomenon": req.phenomenon,
        "root_cause": req.root_cause,
        "pan": req.pan, "device_addr": req.device_addr,
    }, k=req.k or 5)
    return {"similar": results}


# ── 案例入库 (当前导入包 + 标注) ──

class AnnotateRequest(BaseModel):
    phenomenon: str
    root_cause: str = ""
    severity: str = "medium"
    environment: str = ""
    manual_scenarios: list[str] = []   # 人工确认归属 (与自动命中并集)
    pan: str = ""                      # hex 字符串 (自动预填值, 可改)
    device_addr: str = ""              # hex 字符串 (自动预填值, 可改)
    time_start: float | None = None
    time_end: float | None = None
    copy_material: bool = True
    source_path: str = ""              # 素材原路径 (本地路径导入时有; 上传导入为空)


@router.post("/annotate")
async def annotate(req: AnnotateRequest):
    """当前导入包 + 标注 → 案例入库.

    流程 (grilling 对齐): 跑检测 (PAN 过滤同诊断页) → 自动场景命中 +
    人工确认并集 → 案例 JSON 落盘 + 素材副本 → 差距报告数据随案例自带
    (gap_report 即时聚合, 无需另存)。
    """
    packets = get_packets()
    if not packets:
        return JSONResponse({"error": "无导入数据 (需先导入抓包)"}, 400)
    # 归属场景校验
    bad = [s for s in req.manual_scenarios if s not in cl.SCENARIOS]
    if bad:
        return JSONResponse({"error": f"未知场景: {bad}"}, 400)
    # 跑检测 (PAN 过滤复用诊断页 _diag_pkts — 多 PAN 素材不串网)
    pkts = _diag_pkts(req.pan)
    if not pkts:
        return JSONResponse({"error": "该 PAN 下无帧 (检查 PAN 选择)"}, 400)
    from ..detectors import l1 as l1_detector, l2 as l2_detector
    from ..detectors import l3 as l3_detector, l6 as l6_detector
    l1_result = l1_detector.detect(pkts)
    l2_result = l2_detector.detect(pkts)
    l3_result = l3_detector.detect(pkts, l1_result=l1_result)
    l6_result = l6_detector.detect(pkts, l3_result=l3_result)
    det = cl.extract_detection({**l1_result, **l2_result, **l3_result, **l6_result})
    det["manual_scenarios"] = req.manual_scenarios

    # 自动元数据 (预扫思路: PAN/时间窗/帧数从导入数据提取; 用户可改字段优先)
    win = [p["ts"] for p in pkts]
    time_range = [req.time_start if req.time_start is not None else (min(win) if win else None),
                  req.time_end if req.time_end is not None else (max(win) if win else None)]
    dev_int = None
    if req.device_addr:
        try:
            dev_int = int(req.device_addr, 16)
        except ValueError:
            dev_int = None
    # source_file: 上传导入时 _pcap_paths 存文件名 (files.py 全局)
    from . import files as _files
    source_file = ""
    if _files._pcap_paths:
        source_file = os.path.basename(_files._pcap_paths[0])
    meta = {
        "pan": _pan_int(req.pan),
        "device_addr": dev_int,
        "time_range": time_range,
        "frames": len(pkts),
        "source_file": source_file,
    }
    src_path = req.source_path if (req.source_path and os.path.isfile(req.source_path)) else None
    try:
        case = cl.add_case(req.model_dump(), det, meta,
                           source_path=src_path, copy_material=req.copy_material)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, 400)
    return {"ok": True, "case": cl._case_brief(case),
            "gap_report": cl.gap_report()}


# ── 导出/导入传播 (后台任务, 复用 U6 _start_import 互斥) ──

# 导出产物/素材副本下载白名单: 必须在 cases/ 目录内 (防任意文件下载)
def _safe_in_cases(path: str) -> bool:
    try:
        p = os.path.realpath(path)
        return os.path.isfile(p) and p.startswith(str(cl.cases_dir().resolve()))
    except OSError:
        return False


@router.post("/export")
async def export_cases(case_ids: str = Form(default="")):
    """案例库导出 zip (后台线程; case_ids 逗号分隔可选子集)."""
    ids = [s for s in re.split(r"[,\s]+", case_ids) if s] or None

    def _run(task_id: str) -> dict:
        _task_update(task_id, stage="案例库打包", percent=30)
        out = cl.export_cases(case_ids=ids)
        _task_update(task_id, stage="案例库打包", percent=100)
        return {"out_path": out, "out_name": os.path.basename(out)}

    return _start_import(_run)


@router.post("/import")
async def import_cases_zip(file: UploadFile = File(...), merge: int = Form(default=1)):
    """导入案例 zip (上传; 后台线程; merge=1 同 id 保留本地)."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    tmp.close()
    with open(tmp.name, "wb") as out:
        while data := await file.read(1024 * 1024):
            out.write(data)

    def _run(task_id: str) -> dict:
        _task_update(task_id, stage="案例库导入", percent=40)
        try:
            r = cl.import_cases(tmp.name, merge=bool(merge))
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        _task_update(task_id, stage="案例库导入", percent=100)
        return r

    return _start_import(_run)


@router.get("/download")
async def cases_download(path: str = Query(default="")):
    """下载导出 zip / 案例素材副本 (人工复验; 限 cases/ 目录内)."""
    if not path or not _safe_in_cases(path):
        return JSONResponse({"error": "仅支持案例库目录内文件"}, 400)
    return FileResponse(path, filename=os.path.basename(path),
                        media_type="application/octet-stream")


# ── 动态路由 (静态路径之后注册) ──

@router.get("/{case_id}")
async def case_detail(case_id: str):
    c = cl.get_case(case_id)
    if not c:
        return JSONResponse({"error": f"案例 {case_id} 不存在"}, 404)
    return c


class CaseUpdate(BaseModel):
    status: str | None = None
    annotation: dict | None = None
    scenarios: list[str] | None = None


@router.post("/{case_id}")
async def case_update(case_id: str, req: CaseUpdate):
    """人工修订 (状态流转 new→reviewed→closed / 标注更正 / 归属调整)."""
    if req.status and req.status not in ("new", "reviewed", "closed"):
        return JSONResponse({"error": "status 必须是 new/reviewed/closed"}, 400)
    if req.scenarios is not None:
        bad = [s for s in req.scenarios if s not in cl.SCENARIOS]
        if bad:
            return JSONResponse({"error": f"未知场景: {bad}"}, 400)
    c = cl.update_case(case_id, req.model_dump(exclude_none=True))
    if not c:
        return JSONResponse({"error": f"案例 {case_id} 不存在"}, 404)
    return {"ok": True, "case": c}


@router.delete("/{case_id}")
async def case_delete(case_id: str):
    if not cl.delete_case(case_id):
        return JSONResponse({"error": f"案例 {case_id} 不存在"}, 404)
    return {"ok": True}
