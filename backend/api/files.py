"""导入 API — CSV / pcap / cubx (解析走后台线程, 前端轮询真实进度)"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 项目根 (自重启端点 cwd 用)
BASE_DIR = str(Path(__file__).resolve().parents[2])

from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse

from .. import zcl_defs
from .. import tuya_proto as _tuya_proto

_tuya_proto.register(zcl_defs.PAYLOAD_PARSERS)  # U15: 注册涂鸦 0xEF00 载荷解析器

router = APIRouter()

_packets: list[dict] = []
_nodes: dict[int, dict] = {}
_ack_match_cache: tuple = (None, None)   # (packets 引用 id, {ack_pid: orig_pid}) — 导入后失效
_transaction_cache: tuple = (None, None)  # U16-7a 事务链缓存 (packets 引用 id, peers dict)
_rr_path_cache: tuple = (None, None)      # U16-4b 上行路径缓存 (packets 引用 id, {(src,dst): [paths]})
_file_type: str = ""
_verify_report: dict | None = None  # 校验报告
_parser_verify_report: dict | None = None  # 解析正确性校验报告 (P6) — 导入后自动跑
_pcap_paths: list[str] = []         # 最近一次导入的 pcap 路径
_last_ubiqua_sync: dict | None = None  # 最近一次 Ubiqua key 同步结果
_last_import_summary: dict | None = None  # 最近一次导入摘要 (含文件名, 前端切页恢复用)

# ── 后台导入任务 (真实进度) ──
_import_tasks: dict[str, dict] = {}   # task_id -> {status, stage, percent, result/error}
_import_running: bool = False         # 并发防护: 同一时刻只允许一个导入任务
_import_lock = threading.Lock()


def _task_update(task_id: str, **fields) -> None:
    """更新任务状态 (GIL 下单 dict 赋值原子)"""
    task = _import_tasks.get(task_id)
    if task is not None:
        task.update(fields)


def _start_import(fn) -> dict:
    """启动后台导入线程, 返回 {ok, task_id} 或 400 错误 (已有任务运行中)"""
    global _import_running
    with _import_lock:
        if _import_running:
            return {"error": "已有导入任务进行中, 请等待完成"}
        _import_running = True
        task_id = uuid.uuid4().hex[:12]
        _import_tasks[task_id] = {"status": "running", "stage": "启动", "percent": 0}

    def _run():
        global _import_running
        try:
            result = fn(task_id)
            _task_update(task_id, status="done", stage="完成", percent=100, result=result)
        except Exception as e:
            _task_update(task_id, status="error", stage="失败", error=str(e))
        finally:
            _import_running = False
            # 任务表容量控制: 只留最近 20 条
            if len(_import_tasks) > 20:
                for k in [k for k, t in list(_import_tasks.items()) if t["status"] in ("done", "error")]:
                    if len(_import_tasks) <= 20:
                        break
                    del _import_tasks[k]

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "task_id": task_id}


@router.post("/cubx/prescan")
async def cubx_prescan(path: str = Form(...)):
    """U11: .cubx 预扫 (秒级元数据, 不解析 Raw) — 大包时间窗拆分流程第一步"""
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, 400)
    try:
        from .. import cubx_splitter as _cs
        return _cs.prescan_cubx(path)
    except Exception as e:
        return JSONResponse({"error": f"预扫失败: {e}"}, 500)


_CUBX_STAGE_DIR = os.path.join(tempfile.gettempdir(), "cubx_stage")


@router.post("/cubx/upload-stage")
async def cubx_upload_stage(file: UploadFile = File(...)):
    """U11: 大 cubx 上传暂存 (拖拽路径) — 保存到暂存目录 + 预扫, 返回 {path, prescan}.

    暂存文件不随导入完成删除, 由下次 stage 时清理旧文件 (容量控制).
    后续 split 或 local-cubx 导入均以返回的 path 为输入.
    """
    # S1 (2026-08-26): 文件名取 basename — 恶意/异常文件名含路径分隔符会逃出
    # 暂存目录 (路径穿越, P2); 浏览器通常剥路径, 但 API 层不依赖客户端
    fname = os.path.basename(getattr(file, "filename", "stage.cubx"))
    if not fname.lower().endswith(".cubx"):
        return JSONResponse({"error": "仅支持 .cubx 文件"}, 400)
    os.makedirs(_CUBX_STAGE_DIR, exist_ok=True)
    # 容量控制: 清理上次暂存 (只保留本次)
    for old in Path(_CUBX_STAGE_DIR).glob("*.cubx"):
        try:
            old.unlink()
        except OSError:
            pass
    # 命名规范 (用户定义 08-13): 暂存文件名还原原文件名 (去掉随机前缀, 防
    # 拆分产物命名带 bd106075_ 前缀); 暂存目录内同名会冲突, 冲突时保留前缀
    staged = os.path.join(_CUBX_STAGE_DIR, fname)
    if os.path.exists(staged):
        staged = os.path.join(_CUBX_STAGE_DIR, f"{uuid.uuid4().hex[:8]}_{fname}")
    try:
        with open(staged, "wb") as out:
            while data := await file.read(1024 * 1024):
                out.write(data)
        from .. import cubx_splitter as _cs
        prescan = _cs.prescan_cubx(staged)
        return {"path": staged, "prescan": prescan}
    except Exception as e:
        try:
            os.unlink(staged)
        except OSError:
            pass
        return JSONResponse({"error": f"暂存失败: {e}"}, 500)


@router.post("/cubx/split")
async def cubx_split(path: str = Form(...), ts_start: float = Form(...),
                     ts_end: float = Form(...)):
    """U11: 时间窗拆分 — **只拆不导** (2026-08-13 用户定义核对:
    连续拆多子包 + 手动选择导入; 拆分走后台任务复用 _start_import 互斥,
    返回 {in_frames, out_frames, out_path}; 导入由用户对子包逐个触发
    /api/import/local-cubx)."""
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, 400)
    if ts_end <= ts_start:
        return JSONResponse({"error": "时间窗无效: ts_end 必须大于 ts_start"}, 400)

    def _run(task_id: str) -> dict:
        from .. import cubx_splitter as _cs
        _task_update(task_id, stage="时间窗拆分", percent=0)
        # S1 (2026-08-26): 接线 progress_cb — 此前拆分任务 percent 恒 0
        # (前端顶栏全程显示 0%, P2)
        def _cb(done: int, total: int) -> None:
            _task_update(task_id, stage="时间窗拆分",
                         percent=min(int(done / total * 90), 90))
        try:
            r = _cs.split_cubx(path, ts_start, ts_end, progress_cb=_cb)
        except Exception as e:
            raise RuntimeError(f"拆分失败: {e}") from e
        _task_update(task_id, stage="时间窗拆分", percent=100)
        return {"in_frames": r["in_frames"], "out_frames": r["out_frames"],
                "out_path": r["out_path"]}

    return _start_import(_run)


@router.get("/cubx/download")
async def cubx_download(path: str = Query(default="")):
    """U11: 下载拆分产物 (人工复验, 如 Ubiqua 打开).

    允许: 暂存目录内 .cubx (拖拽场景) 或匹配拆分命名模式的 .cubx
    (<原名>_<YYYYMMDD_HHMMSS>-<YYYYMMDD_HHMMSS>.cubx, 本地路径场景).
    本工具为本地单用户, 命名模式校验防误下任意文件.
    """
    from fastapi.responses import FileResponse
    import re
    p = Path(path)
    try:
        p_resolved = p.resolve()
        stage_resolved = Path(_CUBX_STAGE_DIR).resolve()
        in_stage = p_resolved.parent == stage_resolved
        # S1 修复 (2026-08-26): 拆分命名正则与 cubx_splitter 实际命名对齐 —
        # 实际为 _MMDD_HHMM-MMDD_HHMM (4+4 位) + 同窗重复序号 _01; 此前按工单
        # 描述 YYYYMMDD_HHMMSS (8+6) 写正则, 本地路径拆产物下载恒 400 (P1)
        split_named = bool(re.search(
            r"_\d{4}_\d{4}-\d{4}_\d{4}(_\d{2})?\.cubx$|_\d{8}_\d{6}-\d{8}_\d{6}\.cubx$",
            p_resolved.name))
        if not (p_resolved.is_file() and p_resolved.suffix.lower() == ".cubx"
                and (in_stage or split_named)):
            return JSONResponse({"error": "仅支持拆分产物 .cubx (暂存目录或拆分命名)"}, 400)
        return FileResponse(str(p_resolved), filename=p_resolved.name,
                            media_type="application/octet-stream")
    except Exception as e:
        return JSONResponse({"error": f"下载失败: {e}"}, 500)


@router.post("/system/restart")
async def system_restart():
    """U11 用户需求: 导入卡死时的后端自重启 (网页可触发的重启按钮).

    实现: 起独立 powershell 进程 — taskkill 当前后端 PID → 等待 2s (端口
    释放) → Start-Process 重启 backend (detached, 模式已验证可靠).
    powershell 是后端子进程, taskkill 只杀后端 PID, 脚本继续执行.
    返回 {"ok": True} 后前端轮询等待 + 自动刷新.
    """
    import subprocess
    # S1 (2026-08-26): 端口从启动参数解析, 不硬编码 8720 (P2) —
    # 非默认端口启动时重启后端口漂移会导致前端失联
    port = 8720
    args = sys.argv or []
    for i, a in enumerate(args):
        if a == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                pass
    script = (f"taskkill /F /PID {os.getpid()} | Out-Null; "
              f"Start-Sleep 2; "
              f"Start-Process -WindowStyle Hidden -FilePath '{sys.executable}' "
              f"-ArgumentList '-m','backend','--port','{port}' "
              f"-WorkingDirectory '{BASE_DIR}'")
    try:
        subprocess.Popen(["powershell", "-Command", script],
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return {"ok": True, "message": "后端重启中, 约 5 秒后可用"}
    except Exception as e:
        return JSONResponse({"error": f"重启失败: {e}"}, 500)


@router.get("/import/parser-verify")
async def parser_verify_status():
    """解析正确性校验报告 (P6) — 导入后自动跑, 前端切页恢复用"""
    global _parser_verify_report
    return _parser_verify_report or {"passed": None, "message": "尚未执行解析校验"}


@router.get("/import/progress")
async def import_progress(task_id: str):
    """查询后台导入任务进度"""
    task = _import_tasks.get(task_id)
    if task is None:
        return {"status": "unknown"}
    # 只返回前端需要的字段 (result 随 done 一并返回, 免二次请求)
    return {
        "status": task.get("status"),
        "stage": task.get("stage", ""),
        "percent": task.get("percent", 0),
        "result": task.get("result"),
        "error": task.get("error"),
    }


def _sync_ubiqua_keys() -> dict | None:
    """导入前从 Ubiqua 同步 Network Key (localhost:19501).

    Ubiqua 不可达 / 无新 key → 返回 None, 静默跳过, 不阻断导入。
    成功 → 返回 {"synced": 新增数, "total_keys": 去重总数}。
    """
    try:
        from .. import ubiqua_api
        from .. import key_store
        client = ubiqua_api.get_client()  # localhost:19501
        if not client.ping():
            return None
        keys = client.get_network_keys()
        if not keys:
            return None
        result = key_store.merge_from_ubiqua(keys)
        return {"synced": result["added"], "total_keys": result["total"]}
    except Exception:
        return None


def get_packets():
    return _packets


def get_nodes():
    return _nodes


def _parse_clock_time(time_str: str, base_ts: float) -> float | None:
    """将 HH:MM:SS 时钟时间解析为绝对 Unix 时间戳 (**本地时间**)。

    ⚠️ 时区修复 (08-13): 曾按 UTC 日期映射 (utcfromtimestamp + timegm) —
    前端时间线修复为本地时间后, 前后端差 8h → 时间过滤全部空结果。
    现在基于抓包第一帧的**本地**日期映射 (与前端 tlToTs/显示一致)。
    不做跨午夜修正 — 若早于抓包开始则自然包含所有包（无更早数据）。"""
    parts = time_str.split(":")
    if len(parts) < 2:
        return None
    h, m = int(parts[0]), int(parts[1])
    s = int(parts[2]) if len(parts) > 2 else 0
    clock_sec = h * 3600 + m * 60 + s
    base_dt = datetime.fromtimestamp(base_ts)   # 本地时间
    midnight = base_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight.timestamp() + clock_sec


# S1 自审 (2026-08-26, 用户需求): CSV 导入已删除 — 只保留抓包导入
# (pcap/cubx)。原 /import/files (CSV 上传) + /import/local (CSV 本地路径)
# + _run_csv_import/_run_csv_local + csv_reader 引用全部移除。


@router.delete("/import/clear")
async def import_clear():
    global _packets, _nodes, _file_type, _verify_report, _pcap_paths, _last_ubiqua_sync, _last_import_summary, _full_packets, _parser_verify_report
    _packets = []; _nodes = {}; _file_type = ""; _verify_report = None; _pcap_paths = []
    _last_ubiqua_sync = None; _last_import_summary = None; _full_packets = []
    global _parser_verify_report
    _parser_verify_report = None
    return {"ok": True}


# ── pcap 导入 (tshark 解析) ──

@router.post("/import/pcap")
async def import_pcap(files: list[UploadFile] = File(...)):
    """上传 pcap 文件 (支持多文件), tshark 批量解析 + 合并 (后台线程)"""
    import tempfile
    tmp_paths = []
    fnames = []
    for f in files:
        tmp = tempfile.NamedTemporaryFile(suffix=".pcap", delete=False)
        tmp.close()
        with open(tmp.name, "wb") as out:
            while data := await f.read(1024 * 1024):
                out.write(data)
        tmp_paths.append(tmp.name)
        fnames.append(getattr(f, "filename", ""))
    if not tmp_paths:
        return JSONResponse({"error": "未选择文件"}, 400)
    return _start_import(lambda tid: _run_pcap_import(tid, tmp_paths, fnames))

def _run_pcap_import(task_id: str, tmp_paths: list[str], fnames: list[str]) -> dict:
    """后台: pcap 解析 + 校验 (进度: 同步→解析→MAC 帧→校验 6 项)"""
    global _packets, _nodes, _file_type, _full_packets, _verify_report, _last_ubiqua_sync, _pcap_paths, _parser_verify_report
    from .. import tshark as _tshark
    try:
        # 导入前透明同步 Ubiqua Network Key (不可达则静默跳过)
        _task_update(task_id, stage="同步 Ubiqua Key", percent=10)
        _last_ubiqua_sync = _sync_ubiqua_keys()

        # tshark 解析 (按文件推进)
        _packets = []
        total = len(tmp_paths)
        for i, p in enumerate(tmp_paths):
            pkts = _tshark.parse_packets([p])
            _packets.extend(pkts)
            _task_update(task_id, stage=f"tshark 解析 ({i + 1}/{total})",
                         percent=15 + int((i + 1) / total * 25))
        if not _packets:
            raise RuntimeError("无有效数据 (可能不是 Zigbee 抓包)")
        _packets.sort(key=lambda p: p["ts"])
        _file_type = "pcap"
        _pcap_paths = [os.path.abspath(p) for p in tmp_paths]

        # 全量帧 (含 MAC 命令帧/Beacon) — L1 检测需要
        _task_update(task_id, stage="解析 MAC 帧", percent=45)
        try:
            _full_packets = []
            tshark_path = _tshark.find_tshark()
            for p in tmp_paths:
                _full_packets.extend(_tshark.parse_mac_frames(tshark_path, p))
            _full_packets.extend(_packets)
            _full_packets.sort(key=lambda p: p["ts"])
        except Exception:
            _full_packets = list(_packets)
        # 设备类型推断需要全量帧 (SED poll 是 MAC 帧, 不在 _packets)
        _nodes = _extract_nodes_from_packets(_packets, _full_packets)

        # 运行校验 (6 项逐项上报进度, 50→95)
        _task_update(task_id, stage="校验", percent=50)
        try:
            from .. import verify as _verify
            def _vcb(idx, total_checks, label):
                _task_update(task_id, stage=f"校验: {label}", percent=50 + int((idx + 1) / total_checks * 45))
            _verify_report = _verify.run_verification(_pcap_paths, _packets, progress_cb=_vcb)
        except Exception:
            _verify_report = {"passed": False, "error": "校验执行异常"}

        # 解析正确性校验 (P6): pcap 路径 tshark 权威对比 (后台默认, 分层)
        # 权威对比用 _packets (NWK-only, 与 tshark -Y zbee_nwk 同 filter); 自洽校验用全量
        try:
            from .. import parser_verify as _pv
            _parser_verify_report = _pv.run_parser_verify(
                _packets, "pcap", source_path=_pcap_paths[0] if _pcap_paths else None)
        except Exception:
            _parser_verify_report = {"ok": False, "passed": False, "failure_type": "warn",
                                     "checks": {}, "error": "解析校验执行异常"}

        return _import_result(", ".join(fnames))
    finally:
        for p in tmp_paths:
            try: os.unlink(p)
            except OSError: pass


@router.post("/import/local-pcap")
async def import_local_pcap(paths: str = Form(...)):
    """本地 pcap 路径导入 (逗号分隔多个, 后台线程)"""
    path_list = [p.strip() for p in paths.split(",") if p.strip()]
    if not path_list:
        return JSONResponse({"error": "未提供路径"}, 400)

    missing = [p for p in path_list if not os.path.exists(p)]
    if missing:
        return JSONResponse({"error": f"路径不存在: {', '.join(missing)}"}, 400)

    return _start_import(lambda tid: _run_pcap_local(tid, path_list))

def _run_pcap_local(task_id: str, path_list: list[str]) -> dict:
    """后台: 本地 pcap 路径解析 + 校验 (与上传流程一致)"""
    global _packets, _nodes, _file_type, _full_packets, _verify_report, _last_ubiqua_sync, _pcap_paths, _parser_verify_report
    from .. import tshark as _tshark
    try:
        _task_update(task_id, stage="同步 Ubiqua Key", percent=10)
        _last_ubiqua_sync = _sync_ubiqua_keys()

        _packets = []
        total = len(path_list)
        for i, p in enumerate(path_list):
            pkts = _tshark.parse_packets([p])
            _packets.extend(pkts)
            _task_update(task_id, stage=f"tshark 解析 ({i + 1}/{total})",
                         percent=15 + int((i + 1) / total * 25))
        _packets.sort(key=lambda p: p["ts"])
        _file_type = "pcap"
        _pcap_paths = path_list

        _task_update(task_id, stage="解析 MAC 帧", percent=45)
        try:
            _full_packets = []
            tshark_path = _tshark.find_tshark()
            for p in path_list:
                _full_packets.extend(_tshark.parse_mac_frames(tshark_path, p))
            _full_packets.extend(_packets)
            _full_packets.sort(key=lambda p: p["ts"])
        except Exception:
            _full_packets = list(_packets)
        # U16-7 全量化 (2026-08-25 用户裁定): _packets = 全量帧 (含 MAC Cmd/Beacon/Ack)
        _packets = _full_packets
        # 设备类型推断需要全量帧 (SED poll 是 MAC 帧, 不在 _packets)
        _nodes = _extract_nodes_from_packets(_packets, _full_packets)

        _task_update(task_id, stage="校验", percent=50)
        try:
            from .. import verify as _verify
            def _vcb(idx, total_checks, label):
                _task_update(task_id, stage=f"校验: {label}", percent=50 + int((idx + 1) / total_checks * 45))
            _verify_report = _verify.run_verification(_pcap_paths, _packets, progress_cb=_vcb)
        except Exception:
            _verify_report = {"passed": False, "error": "校验执行异常"}

        # 解析正确性校验 (P6): pcap 路径 tshark 权威对比 (后台默认, 分层)
        try:
            from .. import parser_verify as _pv
            _parser_verify_report = _pv.run_parser_verify(
                _packets, "pcap", source_path=_pcap_paths[0] if _pcap_paths else None)
        except Exception:
            _parser_verify_report = {"ok": False, "passed": False, "failure_type": "warn",
                                     "checks": {}, "error": "解析校验执行异常"}

        return _import_result(os.path.basename(path_list[0]))
    except RuntimeError as e:
        raise e


# ── cubx 导入 (scapy 自解析) ──

_full_packets: list[dict] = []  # cubx 全量帧 (含 MAC 命令帧/Beacon, 供 L1 检测)


def get_full_packets():
    """全量帧 (含 MAC 帧, 仅 cubx 导入时有)."""
    return _full_packets


@router.post("/import/cubx")
async def import_cubx(files: list[UploadFile] = File(...)):
    """上传 .cubx 文件, scapy 自解析 (key 内嵌 + LQI/RSSI, 后台线程)"""
    import tempfile
    tmp_paths = []
    fnames = []
    for f in files:
        tmp = tempfile.NamedTemporaryFile(suffix=".cubx", delete=False)
        tmp.close()
        with open(tmp.name, "wb") as out:
            while data := await f.read(1024 * 1024):
                out.write(data)
        tmp_paths.append(tmp.name)
        fnames.append(getattr(f, "filename", ""))
    if not tmp_paths:
        return JSONResponse({"error": "未选择文件"}, 400)
    return _start_import(lambda tid: _run_cubx_import(tid, tmp_paths, fnames))

def _run_cubx_import(task_id: str, tmp_paths: list[str], fnames: list[str]) -> dict:
    """后台: cubx 解析 (scapy 自解析, 无 tshark 校验; 进度按文件推进)"""
    global _packets, _nodes, _file_type, _pcap_paths, _last_ubiqua_sync, _full_packets, _parser_verify_report
    from .. import cubx_reader as _cubx
    try:
        all_pkts = []
        all_full = []
        total = len(tmp_paths)
        for i, tp in enumerate(tmp_paths):
            # 全量解析 (含 MAC 帧) — L1 检测需要 Beacon/Assoc 帧
            # parse_cubx 大文件可达数十秒, 传 progress_cb 按包上报真实进度 (10-90%)
            def _cb(done: int, total_rows: int, i: int = i, total: int = total) -> None:
                base = 10 + int(i / total * 80)
                span = max(int(1 / total * 80), 1)
                _task_update(task_id, stage=f"cubx 解析 ({i + 1}/{total})",
                             percent=min(base + int(done / total_rows * span), 10 + int((i + 1) / total * 80)))
            pkts, added, total_keys = _cubx.parse_cubx(tp, include_mac_frames=True, progress_cb=_cb)
            all_full.extend(pkts)
            # U16-7 全量化 (用户裁定 08-25): _packets = 全量帧 (含 poll/Beacon 等 MAC 帧),
            # 时间线「报文」展示完整包; 检测器已用 full, 解析器/契约不变
            all_pkts.extend(pkts)
            _last_ubiqua_sync = {"synced": added, "total_keys": total_keys}
        if not all_pkts:
            raise RuntimeError("无有效数据")

        _packets = all_pkts
        _full_packets = all_full
        # 设备类型推断需要全量帧 (SED poll 是 MAC 帧, 不在 _packets)
        _nodes = _extract_nodes_from_packets(_packets, _full_packets)
        _file_type = "cubx"
        _pcap_paths = fnames or tmp_paths

        # 解析正确性校验 (P6): cubx 路径自洽校验 — 后台默认自动跑
        try:
            from .. import parser_verify as _pv
            _parser_verify_report = _pv.run_parser_verify(_full_packets or _packets, "cubx")
        except Exception:
            _parser_verify_report = {"ok": False, "passed": False, "failure_type": "warn",
                                     "checks": {}, "error": "解析校验执行异常"}

        return _import_result(", ".join(fnames))
    finally:
        for p in tmp_paths:
            try: os.unlink(p)
            except OSError: pass


@router.post("/import/local-cubx")
async def import_local_cubx(path: str = Form(...)):
    """本地 .cubx 路径导入 (后台线程)"""
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, 400)
    return _start_import(lambda tid: _run_cubx_local(tid, path))

def _run_cubx_local(task_id: str, path: str) -> dict:
    """后台: 本地 cubx 路径解析"""
    global _packets, _nodes, _file_type, _pcap_paths, _last_ubiqua_sync, _full_packets, _parser_verify_report
    from .. import cubx_reader as _cubx
    _task_update(task_id, stage="cubx 解析", percent=30)
    try:
        def _cb(done: int, total_rows: int) -> None:
            _task_update(task_id, stage="cubx 解析",
                         percent=30 + int(done / total_rows * 60))
        pkts, added, total = _cubx.parse_cubx(path, include_mac_frames=True, progress_cb=_cb)
    except Exception as e:
        raise RuntimeError(str(e)) from e
    _last_ubiqua_sync = {"synced": added, "total_keys": total}
    _full_packets = pkts
    # U16-7 全量化 (用户裁定 08-25): _packets = 全量帧 (含 poll/Beacon 等 MAC 帧)
    _packets = pkts
    _nodes = _extract_nodes_from_packets(_packets, _full_packets)
    _file_type = "cubx"
    _pcap_paths = [path]

    # 解析正确性校验 (P6): cubx 路径自洽校验 — 后台默认自动跑
    try:
        from .. import parser_verify as _pv
        _parser_verify_report = _pv.run_parser_verify(_full_packets or _packets, "cubx")
    except Exception:
        _parser_verify_report = {"ok": False, "passed": False, "failure_type": "warn",
                                 "checks": {}, "error": "解析校验执行异常"}

    return _import_result()


def _extract_nodes_from_packets(packets: list[dict], full_packets: list[dict] | None = None) -> dict[int, dict]:
    """从 pcap 包列表中提取节点 (兼容 csv_reader.extract_nodes 格式).

    full_packets: 含 MAC 命令帧的全量包 (可选) — SED poll 信号 (MAC Data Request)
    是纯 MAC 帧无 NWK 头, 被 packets 的 NWK 可见过滤排除, 必须从全量列表采集。
    """
    nodes: dict[int, dict] = {}
    pan_counts: dict[int, dict[int, int]] = {}
    # 设备类型信号收集 (2026-08-06 重构, 协议级依据 + 素材实证, 详见 U7 ticket):
    # - Link Status (nwk_cmd 8): 规范仅 FFD 周期广播 → router 强信号
    # - Route Reply (nwk_cmd 2): 仅具备路由能力的设备可回应 → router 弱信号
    # - Route Request (nwk_cmd 1) / Route Record (nwk_cmd 5) 不作 router 信号 —
    #   素材实证: G32 SED 0xEE48 (poll×1933) 发 RREQ×4; 群控包 SED 锁 0x82A0/0xD6D3
    #   发 Route Record (路由源自己上报, 帧里中继列表才是路由器)
    # - MAC Data Request (cmd 4, SED 轮询): 仅 SED 会 poll 父节点 → end_device 强信号
    # - Device Announce (ZDP 0x0013) capability bit1 (0x02): 设备入网自声明 FFD/RFD (权威;
    #   cubx 路径 aps_payload_hex 可得, pcap 路径待解析器补 APS 明文, 见 P5)
    has_link_status: set[int] = set()
    has_route_reply: set[int] = set()
    has_route_relay: set[int] = set()   # U13: RR 中继 = FFD 强信号 (只有路由器转发 RR, SED 不转发任何帧)
    has_poll: set[int] = set()
    cap_declared: dict[int, str] = {}   # aid → "router"/"end_device" (入网时 capability 声明)

    for p in packets:
        pan = p["pan_src"] or p["pan_dst"]
        for addr in (p["mac_src"], p["mac_dst"], p["nwk_src"], p["nwk_dst"]):
            if addr is None or addr > 0xFFF7:
                continue
            if addr not in nodes:
                nodes[addr] = {"aid": addr, "seen": 0, "pan": None, "is_coord": False, "type_list": []}
                pan_counts[addr] = {}
            nodes[addr]["seen"] += 1
            if p["pkt_type"] and p["pkt_type"] not in nodes[addr]["type_list"]:
                nodes[addr]["type_list"].append(p["pkt_type"])
            if pan:
                pan_counts[addr][pan] = pan_counts[addr].get(pan, 0) + 1
            if addr == 0:
                nodes[addr]["is_coord"] = True

    # 设备类型信号采集 (nwk_cmd_id 协议级字段; mac_cmd_id 4 = SED 轮询) —
    # poll 帧无 NWK 头, 必须用 full_packets 全量列表
    for p in (full_packets if full_packets is not None else packets):
        nwk_src = p.get("nwk_src")
        nwk_cmd = p.get("nwk_cmd_id")
        if nwk_cmd == 8 and nwk_src is not None:
            has_link_status.add(nwk_src)
        elif nwk_cmd == 2 and nwk_src is not None:
            has_route_reply.add(nwk_src)
        # U13: RR 中继 = FFD 强信号 (素材实证 2026-08-25: 卷帘包 0x906C 中继被漏判 —
        # 只有路由器转发 Route Record, SED 不转发任何帧; RR relay 列表即转发路径)
        for relay in (p.get("route_record_relays") or {}).get("relays", []):
            if isinstance(relay, int) and relay <= 0xFFF7:
                has_route_relay.add(relay)
        if p.get("mac_cmd_id") == 4 and p.get("mac_src") is not None:
            has_poll.add(p["mac_src"])
        # Device Announce (ZDP 0x0013) capability: [seq][nwk:2][eui64:8][cap:1], cap 在 pl[11]
        if nwk_src is not None and p.get("aps_cluster") == 0x0013 and p.get("aps_payload_hex"):
            try:
                _pl = bytes.fromhex(p["aps_payload_hex"])
                if len(_pl) >= 12:
                    cap_declared[nwk_src] = "router" if (_pl[11] & 0x02) else "end_device"
            except ValueError:
                pass

    for aid, pc in pan_counts.items():
        if pc:
            nodes[aid]["pan"] = max(pc, key=pc.get)

    # 设备类型推断 (2026-08-06 重构 + 2026-08-25 修正):
    # ① FFD 行为铁证 (LS/RREP/RR中继) → router
    # ② Device Announce capability 自声明 (权威, 用户反馈: 广播帧已声明中继却判不出) → 按声明
    # ③ poll 行为推断 → end_device
    # ④ 无信号 → unknown
    # ⚠️ 曾把 capability 排在 poll 之后: 中继在间接传输场景也会发 poll (MAC Data Request
    # 取 pending 数据), poll 压过自声明导致误判终端 — 自声明是设备入网时的权威声明, 优先
    for aid in nodes:
        if aid == 0:
            nodes[aid]["device_type"] = "coordinator"
            continue
        ffd_ev = (aid in has_link_status or aid in has_route_reply
                  or aid in has_route_relay)  # U13: +RR 中继 (FFD 强信号)
        sed_ev = aid in has_poll
        if ffd_ev:
            nodes[aid]["device_type"] = "router"
        elif aid in cap_declared:
            nodes[aid]["device_type"] = cap_declared[aid]
        elif sed_ev:
            nodes[aid]["device_type"] = "end_device"
        else:
            # 无信号不可判定: RxOnWhenIdle 的 SED 不 poll; 路由器 LS 可能未捕获/未解密 — 如实标 unknown
            nodes[aid]["device_type"] = "unknown"

    return nodes


def _import_result(filename: str | None = None) -> dict:
    """构建导入结果响应, 并持久化摘要到 _last_import_summary (前端切页恢复用)."""
    from .. import key_store as _ks
    global _verify_report, _last_import_summary
    types = {}
    for p in _packets:
        t = p["pkt_type"] or "Unknown"
        types[t] = types.get(t, 0) + 1
    decrypt_stats = _ks.get_match_stats(_packets)
    result = {
        "ok": True,
        "packets": len(_packets),
        "nodes": len(_nodes),
        "file_type": _file_type,
        "filename": filename or (os.path.basename(_pcap_paths[0]) if _pcap_paths else ""),
        "by_type": dict(sorted(types.items(), key=lambda x: -x[1])[:20]),
        "decrypt_stats": decrypt_stats,
        "verify": _verify_report,  # 校验报告
        "parser_verify": _parser_verify_report,  # 解析正确性校验 (P6)
        "ubiqua_sync": _last_ubiqua_sync,  # Ubiqua key 同步结果 (None=不可达)
    }
    # 持久化摘要 (后端内存, 不受前端页面切换影响)
    # S1 修复 (2026-08-26): 补 parser_verify — 此前摘要缺此项, 切页恢复时
    # sr() 渲染无 P6 卡, 且 fresh import 后卡不出现 (前端独立 fetch 竞态, P2)
    _last_import_summary = {
        "packets": result["packets"], "nodes": result["nodes"],
        "file_type": result["file_type"], "filename": result["filename"],
        "by_type": result["by_type"], "decrypt_stats": result["decrypt_stats"],
        "verify": result["verify"], "ubiqua_sync": result["ubiqua_sync"],
        "parser_verify": result["parser_verify"],  # S1: P6 卡随摘要持久化
        # U11: 拆分产物下载信息持久化 (切页回来结果区恢复下载按钮)
        "split_out_path": result.get("split_out_path"),
        "split_out_frames": result.get("split_out_frames"),
    }
    return result


@router.get("/import/last")
async def import_last():
    """最近一次导入摘要 (前端切页恢复用, 后端内存持久)."""
    if _last_import_summary is None:
        return {"ok": False}
    return {"ok": True, **_last_import_summary}


@router.get("/import/verify")
async def import_verify():
    """获取最近的校验报告"""
    global _verify_report
    if _verify_report is None:
        return {"passed": None, "message": "尚未执行校验"}
    return _verify_report


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
            # 改进 (08-13): 秒级窗口含末秒小数 (选 09:46:27 应含 09:46:27.xxx)
            ts_end = _parse_clock_time(time_end, base_ts) + 0.999
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
            # ⚠️ P1 契约修复 (2026-08-06): cubx 现保留广播地址 (0xFFFC/0xFFFD/0xFFFF),
            # 邻居统计必须排除 ≥0xFFF0, 否则广播帧把 0xFFFC 当成 peer 出现虚拟节点
            peer = None
            if p.get("nwk_src") == addr_int and p.get("nwk_dst") and p["nwk_dst"] < 0xFFF0:
                peer = p["nwk_dst"]
            elif p.get("nwk_dst") == addr_int and p.get("nwk_src") and p["nwk_src"] < 0xFFF0:
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
    report = None
    if _verify_report:
        report = {"passed": _verify_report.get("passed")}
    return {"total": len(_packets), "nodes": len(_nodes), "type": _file_type,
            "ts_start": ts_start, "ts_end": ts_end, "verify_ok": report}


@router.get("/packets")
async def packet_list(addr: str = "", pan: str = "",
                      time_start: str = "", time_end: str = "",
                      pkt_type: str = "",
                      hide_undecrypted: int = 0,
                      limit: int = 500, offset: int = 0):
    """查询原始包列表，可按地址/PAN/时间过滤，返回分页+总数

    hide_undecrypted=1: 过滤掉未解密帧 (U16-2 前端默认传 1)"""
    addr_int = int(addr, 16) if addr else None
    pan_int = int(pan, 16) if pan else None
    # Parse time: HH:MM:SS clock time → absolute timestamp
    ts_start = None; ts_end = None
    if _packets and (time_start or time_end):
        base_ts = _packets[0]["ts"]
        if time_start:
            ts_start = _parse_clock_time(time_start, base_ts)
        if time_end:
            # 改进 (08-13): 秒级窗口含末秒小数
            ts_end = _parse_clock_time(time_end, base_ts) + 0.999
    # Filter — 保留原始索引用于后续单帧查询
    matched: list[tuple[int, dict]] = []
    for idx, p in enumerate(_packets):
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
        if pkt_type and p.get("pkt_type", "") != pkt_type:
            continue
        # U16-7 未解密语义 (08-25 用户裁定全量化后): 只隐藏「有 NWK 安全但解密失败」的帧;
        # poll/Beacon 等纯 MAC 帧天然明文 (无 nwk_security) 不隐藏
        if hide_undecrypted and not p.get("decrypted") and p.get("nwk_security"):
            continue
        matched.append((idx, p))
    total = len(matched)
    page = matched[offset:offset + limit]
    return {
        "packets": [{
            "id": orig_idx,
            "packet_id": p.get("packet_id"),  # 抓包原始帧号 (时间线帧号列; 与 id 是同一帧的两个标识)
            "ts": p["ts"], "ch": p.get("ch", 0), "pkt_type": p.get("pkt_type", ""),
            "mac_src": p.get("mac_src"), "mac_dst": p.get("mac_dst"),
            "nwk_src": p.get("nwk_src"), "nwk_dst": p.get("nwk_dst"),
            "pan_src": p.get("pan_src"), "pan_dst": p.get("pan_dst"),
            "nwk_security": p.get("nwk_security"),  # 前端 🔒 判定: 仅 NWK 安全未解密标锁
            "security": p.get("security", ""), "status": p.get("status", ""),
            "aps_cluster": p.get("aps_cluster"),
            "aps_cluster_name": p.get("aps_cluster_name"),
            "aps_cmd_name": p.get("aps_cmd_name"),   # APS 命令名 (时间线类型列显示)
            "zcl_cmd_name": p.get("zcl_cmd_name"),
            "decrypted": p.get("decrypted", False),
            "summary": _packet_summary_short(p),  # U16-3 摘要列 (类型列替代)
            "nwk_relays": p.get("nwk_relays"),  # U16-4 路径列 (下行 source route 中继列表)
            "path_relays": (p.get("nwk_relays") or _uplink_relays_for(p, _get_uplink_path_index())),  # U16-4b 上行反转补路径
            "aps_counter": p.get("aps_counter"),  # U16-5 APS Ctr 列 (消息回复对应分析)
            "layer": _packet_layer(p),  # U16-6 层级着色 (zcl/aps/nwk/mac/mac_dreq/other)
            # NWK 命令级字段 (时间线事件标记用; tshark/cubx 双路径已输出)
            "nwk_cmd_id": p.get("nwk_cmd_id"),
            "nwk_leave_rejoin": p.get("nwk_leave_rejoin"),
            "nwk_leave_request": p.get("nwk_leave_request"),
            "nwk_leave_children": p.get("nwk_leave_children"),
        } for orig_idx, p in page],
        "total": total, "limit": limit, "offset": offset,
    }


# ── U16-3 时间线摘要列: 精简名表 (MAC 命令名以 scapy dot15d4.py:327 源码级为准:
# 4=DataReq, 3=DisassocNotify — 旧表 3/4/5/8 错位, 08-25 修正) ──
_SUMMARY_MAC_CMD = {1: "AssocReq", 2: "AssocResp", 3: "DisassocNotify",
                    4: "DataReq", 5: "PANIDConflict", 6: "OrphanNotify",
                    7: "BeaconReq", 8: "CoordRealign", 9: "GTSReq"}
_SUMMARY_NS_CODE = {0x00: "NO_ROUTE", 0x01: "TREE_LINK_FAIL", 0x02: "LINK_FAIL",
                    0x03: "LOW_BATTERY", 0x04: "NO_ROUTE_CAP", 0x05: "NO_INDIRECT_CAP",
                    0x0B: "SOURCE_ROUTE_FAIL", 0x0C: "MTORR_FAIL"}


# NWK 命令类 pkt_type (加密 NWK 命令帧 nwk_cmd_id 为 None, 需按 pkt_type 兜底归 nwk)
_NWK_CMD_TYPES = {"Link Status", "Route Request", "Route Reply", "Route Record",
                  "Network Status", "Leave", "Rejoin Request", "Rejoin Response",
                  "NWK Cmd"}


def _packet_layer(p: dict) -> str:
    """U16-6 层级判定 (ticket 对齐决策 #6): zcl > nwk > aps > mac > other.

    - zcl: zcl_cmd_id 非空 (ZCL 命令帧)
    - nwk: nwk_cmd_id 非空, 或 pkt_type 为 NWK 命令类 (加密命令帧兜底)
    - aps: aps_cmd_id/aps_cluster 非空 (ZDP 命令/APS Ack)
    - mac: mac_cmd_id 非空; DataReq (4=DataReq, scapy dot15d4.py 源码级; 终端轮询) 细分 mac_dreq 标红
    - other: 无层级信息 (Beacon/ACK/未解密 Data 等)
    """
    if p.get("zcl_cmd_id") is not None:
        return "zcl"
    if p.get("nwk_cmd_id") is not None or p.get("pkt_type") in _NWK_CMD_TYPES:
        return "nwk"
    if p.get("aps_cmd_id") is not None or p.get("aps_cluster") is not None:
        return "aps"
    if p.get("mac_frame_type") == 2:  # ACK 帧 (2026-08-25 用户裁定保留)
        return "mac"
    if p.get("mac_cmd_id") == 4:  # DataReq (轮询) — 旧 3 错位修正 (scapy 源码级)
        return "mac_dreq"
    if p.get("mac_cmd_id") is not None:
        return "mac"
    return "other"


def _packet_summary_short(p: dict) -> str:
    """时间线摘要列 (U16-3): 精简语义摘要 — pkt_type + ZCL 命令名/方向 + 关键标志.

    参考 scripts/export_ai_dataset.packet_summary 简化, 只取列表可读信息,
    不引入完整 AI 摘要复杂度. 列表端点对返回页逐条生成 (非全量).
    """
    from ..cubx_reader import NWK_COMMAND_NAMES
    parts: list[str] = []
    cid = p.get("nwk_cmd_id")
    if cid is not None:
        name = NWK_COMMAND_NAMES.get(cid, f"NWK 0x{cid:02X}")
        if name == "Leave":
            flags = []
            if p.get("nwk_leave_rejoin"):
                flags.append("rejoin")
            if p.get("nwk_leave_request"):
                flags.append("request")
            if p.get("nwk_leave_children"):
                flags.append("children")
            parts.append("Leave " + ",".join(flags) if flags else "Leave")
        elif name == "Network Status" and p.get("nwk_status_code") is not None:
            code = p["nwk_status_code"]
            parts.append(f"NS {_SUMMARY_NS_CODE.get(code, f'0x{code:02X}')}")
        elif name == "Route Record":
            rr = p.get("route_record_relays")
            n = len(rr.get("relays", [])) if isinstance(rr, dict) else 0
            parts.append(f"Route Record relay={n}")
        elif name == "Link Status":
            ln = p.get("link_status_neighbors")
            parts.append(f"Link Status nb={len(ln)}" if ln is not None else "Link Status")
        else:
            parts.append(name)
    elif p.get("aps_cmd_name"):
        parts.append(p["aps_cmd_name"])
    if p.get("zcl_cmd_name"):
        # 08-25 用户反馈: 摘要去掉簇 ID 与方向 (方向可从 NWK Src/Dst 推断, 簇 ID 详情面板有)
        parts.append(f"ZCL {p['zcl_cmd_name']}")
    if p.get("mac_cmd_id") is not None:
        mc = p["mac_cmd_id"]
        # 加密 MAC 命令帧 cmd_id 是密文首字节 (>9 垃圾值, P1 同类) → 不显示假名字
        parts.append(_SUMMARY_MAC_CMD.get(mc) if mc in _SUMMARY_MAC_CMD else "MAC Cmd")
    if p.get("mac_frame_type") == 2:
        # ACK 帧 (2026-08-25 用户裁定保留): 无载荷, 仅标注 pending 位 (协调器有数据待取)
        parts.append("MAC Ack" + (" pending" if p.get("mac_ack_pending") else ""))
    return " | ".join(parts) if parts else (p.get("pkt_type") or "Unknown")


@router.get("/packets/types")
async def packet_types():
    """全部 pkt_type 全量统计 (时间线类型下拉动态化用, 不截断)."""
    types: dict[str, int] = {}
    for p in _packets:
        t = p.get("pkt_type") or "Unknown"
        types[t] = types.get(t, 0) + 1
    return {"types": [{"name": k, "count": v}
                      for k, v in sorted(types.items(), key=lambda x: -x[1])]}


def _fallback_layers(p: dict) -> dict:
    """cubx 路径 raw_layers 为空 → 从平铺字段构造简化层树 (时间线详情面板兼容).

    ⚠️ U5 修复: cubx 解析器 (scapy) 输出平铺字段, 不生成 tshark 风格 raw_layers 层树,
    此前 cubx 素材的帧详情只有头部 (MAC/NWK/APS 全空)。本函数在 API 层做展示兼容,
    不改解析器 (P5 字段缺口工单流边界外)。字段名对齐前端 tlShowDetail 的取值。
    """
    from ..cubx_reader import NWK_COMMAND_NAMES
    layers: dict = {}

    # ── MAC (wpan) ──
    if (p.get("mac_src") is not None or p.get("mac_dst") is not None
            or p.get("pan_src") is not None or p.get("mac_seq") is not None):
        wpan: dict = {}
        if p.get("mac_fcs_ok") is not None:
            wpan["wpan.fcs_ok"] = "1" if p["mac_fcs_ok"] else "0"
        mft = (p.get("mac_frame_type") or 1) & 0x07
        wpan["wpan.fcf"] = f"0x{mft:04X}"
        if p.get("mac_seq") is not None:
            wpan["wpan.seq_no"] = str(p["mac_seq"])
        if p.get("pan_dst") is not None:
            wpan["wpan.dst_pan"] = f"{p['pan_dst']:04x}"
        if p.get("mac_dst") is not None:
            wpan["wpan.dst16"] = f"{p['mac_dst']:04x}"
        if p.get("mac_src") is not None:
            wpan["wpan.src16"] = f"{p['mac_src']:04x}"
        # MAC 命令帧/Beacon 明细 (L1-1/L1-2 入网流程关键: AssocReq/AssocResp/BeaconReq)
        if p.get("mac_cmd_id") is not None:
            wpan["wpan.cmd_id"] = str(p["mac_cmd_id"])
        if p.get("mac_ack_pending") is not None:
            wpan["wpan.ack_pending"] = str(p["mac_ack_pending"])
        if p.get("mac_src64"):
            wpan["wpan.src64"] = p["mac_src64"]
        if p.get("mac_dst64"):
            wpan["wpan.dst64"] = p["mac_dst64"]
        if p.get("mac_beacon_pan") is not None:
            wpan["wpan.beacon_pan"] = f"{p['mac_beacon_pan']:04x}"
        if p.get("mac_beacon_permit") is not None:
            wpan["wpan.beacon_permit"] = str(p["mac_beacon_permit"])
        layers["wpan"] = wpan

    # ── NWK ──
    if p.get("nwk_src") is not None or p.get("nwk_dst") is not None or p.get("nwk_security"):
        nwk: dict = {}
        if p.get("nwk_dst") is not None:
            nwk["zbee_nwk.dst"] = f"0x{p['nwk_dst']:04X}"
        if p.get("nwk_src") is not None:
            nwk["zbee_nwk.src"] = f"0x{p['nwk_src']:04X}"
        if p.get("nwk_radius") is not None:
            nwk["zbee_nwk.radius"] = str(p["nwk_radius"])
        if p.get("nwk_seq") is not None:
            nwk["zbee_nwk.seqno"] = str(p["nwk_seq"])
        nwk["zbee_nwk.fcf_tree"] = {"zbee_nwk.security": "1" if p.get("nwk_security") else "0"}
        # NWK 命令 → "Command Frame: <名>" 子树 (前端 isNwkCmd 检测 + 命令明细渲染)
        cmd_id = p.get("nwk_cmd_id")
        cmd_name = NWK_COMMAND_NAMES.get(cmd_id) if cmd_id is not None else None
        if cmd_name and p.get("pkt_type") == cmd_name:
            cmd_tree = _fallback_nwk_cmd_tree(cmd_name, p)
            if cmd_tree:
                nwk[f"Command Frame: {cmd_name}"] = cmd_tree
        layers["zbee_nwk"] = nwk

    # ── Security Header (NWK 安全帧) ──
    sec_fields: dict = {}
    if p.get("sec_level") is not None:
        sec_fields["zbee.sec.sec_level"] = str(p["sec_level"])
    if p.get("sec_frame_counter") is not None:
        sec_fields["zbee.sec.counter"] = str(p["sec_frame_counter"])
    if p.get("sec_mic"):
        sec_fields["zbee.sec.mic"] = p["sec_mic"]
    if p.get("sec_key_label"):
        sec_fields["zbee.sec.decryption_key"] = p["sec_key_label"]
    if sec_fields:
        sec_fields["zbee.sec.field"] = "1"  # 前端以该字段存在与否决定是否渲染安全头
        layers["ZigBee Security Header"] = sec_fields

    # ── APS (Data 帧) ──
    if (p.get("aps_cluster") is not None or p.get("aps_profile") is not None
            or p.get("aps_cmd_id") is not None or p.get("aps_ack_req") is not None):
        # 含命令帧/可靠性字段 (2026-08-06): 命令帧无 cluster/profile, 此前整个 APS 区被跳过
        aps: dict = {}
        if p.get("aps_profile") is not None:
            aps["zbee_aps.profile"] = f"0x{p['aps_profile']:04X}"
        if p.get("aps_cluster") is not None:
            aps["zbee_aps.cluster"] = f"0x{p['aps_cluster']:04X}"
            if p.get("aps_profile") == 0x0000:
                aps["zbee_aps.zdp_cluster"] = f"0x{p['aps_cluster']:04X}"
        if p.get("aps_src_ep") is not None:
            aps["zbee_aps.src"] = str(p["aps_src_ep"])
        if p.get("aps_dst_ep") is not None:
            aps["zbee_aps.dst"] = str(p["aps_dst_ep"])
        if p.get("aps_counter") is not None:
            aps["zbee_aps.counter"] = str(p["aps_counter"])
        # APS 命令帧明细 (L1-3 密钥流程: TransportKey/Confirm 的 key_type; L1-4: Remove/Update)
        if p.get("aps_cmd_id") is not None:
            aps["zbee_aps.cmd_id"] = f"0x{p['aps_cmd_id']:02X}"
            if p.get("aps_cmd_name"):
                aps["zbee_aps.cmd_name"] = p["aps_cmd_name"]
            if p.get("aps_cmd_key_type") is not None:
                aps["zbee_aps.cmd_key_type"] = f"0x{p['aps_cmd_key_type']:02X}"
            if p.get("aps_cmd_remove_target"):
                aps["zbee_aps.cmd_remove_target"] = p["aps_cmd_remove_target"]
            if p.get("aps_cmd_update_status") is not None:
                aps["zbee_aps.cmd_update_status"] = str(p["aps_cmd_update_status"])
        # APS 可靠性字段 (2026-08-06: L3-1 配对基础)
        if p.get("aps_ack_req") is not None:
            aps["zbee_aps.ack_req"] = "1" if p["aps_ack_req"] else "0"
        if p.get("ack_format") is not None:
            aps["zbee_aps.ack_format"] = str(p["ack_format"])
        layers["zbee_aps"] = aps

    # ── ZCL ──
    if p.get("zcl_cmd_id") is not None:
        zcl: dict = {"zbee_zcl.cmd.id": f"0x{p['zcl_cmd_id']:02X}"}
        if p.get("zcl_seq") is not None:
            zcl["zbee_zcl.cmd.tsn"] = str(p["zcl_seq"])
        if p.get("zcl_direction") is not None:
            zcl["Frame Control Field"] = {"zbee_zcl.dir": str(p["zcl_direction"])}
        # U15: 命令载荷原始 hex (字段级解析结果在响应顶层 zcl_payload_parsed)
        if p.get("zcl_payload_hex") is not None:
            zcl["zbee_zcl.payload.hex"] = p["zcl_payload_hex"]
        layers["zbee_zcl"] = zcl

    # ── ZDP (profile 0x0000) — cubx 路径 aps_payload_hex 解析载荷明细 ──
    if p.get("aps_profile") == 0x0000 and p.get("aps_cluster") is not None:
        zdp = _fallback_zdp_tree(p["aps_cluster"], p.get("aps_payload_hex"))
        if zdp:
            layers["zbee_zdp"] = zdp

    return layers


def _fallback_zdp_tree(cluster_id: int, payload_hex: str | None) -> dict | None:
    """ZDP 命令载荷 → zbee_zdp 子树 (字段名对齐前端 zdpLabels, 详情面板展示).

    ZDP 载荷结构: [seq:1][命令数据]; 短地址 = LE16, EUI64 = LE64。
    覆盖常见命令: Device Announce (0x0013) / NWK Addr Req (0x0000) /
    IEEE Addr Req (0x0001) / 各类 Desc/EP Req / Mgmt LQI Req / Addr Resp。
    """
    if not payload_hex:
        return None
    try:
        pl = bytes.fromhex(payload_hex)
    except ValueError:
        return None
    if not pl:
        return None
    tree: dict = {"zbee_zdp.seqno": str(pl[0])}

    def _eui(b: bytes) -> str:
        return "0x" + int.from_bytes(b, "little").to_bytes(8, "big").hex().upper()

    def _cap_desc(cap: int) -> str:
        parts = []
        if cap & 0x01:
            parts.append("备选协调器")
        parts.append("路由器/协调器" if cap & 0x02 else "终端设备")
        if cap & 0x04:
            parts.append("主电源")
        if cap & 0x08:
            parts.append("RxOnWhenIdle")
        if cap & 0x20:
            parts.append("安全能力")
        return " · ".join(parts) + f" (0x{cap:02X})"

    # 0x0013 Device Announce: [seq][nwk:2][eui64:8][cap:1]
    if cluster_id == 0x0013 and len(pl) >= 12:
        tree["zbee_zdp.zdp_cmd_nwk_addr"] = f"0x{int.from_bytes(pl[1:3], 'little'):04X}"
        tree["zbee_zdp.zdp_cmd_eui64"] = _eui(pl[3:11])
        tree["zbee_zdp.zdp_cmd_capability"] = _cap_desc(pl[11])
    # 0x0000 NWK Addr Req: [seq][eui64:8][req_type:1][start:1]
    elif cluster_id == 0x0000 and len(pl) >= 11:
        tree["zbee_zdp.zdp_cmd_eui64"] = _eui(pl[1:9])
        tree["zbee_zdp.zdp_cmd_req_type"] = "单设备应答" if pl[9] == 0 else "扩展应答"
        tree["zbee_zdp.zdp_cmd_start_index"] = str(pl[10])
    # 0x0001 IEEE Addr Req: [seq][nwk:2][req_type:1][start:1]
    elif cluster_id == 0x0001 and len(pl) >= 5:
        tree["zbee_zdp.zdp_cmd_nwk_addr"] = f"0x{int.from_bytes(pl[1:3], 'little'):04X}"
        tree["zbee_zdp.zdp_cmd_req_type"] = "单设备应答" if pl[3] == 0 else "扩展应答"
        tree["zbee_zdp.zdp_cmd_start_index"] = str(pl[4])
    # 0x0002/3/4/5/6, 0x0010 Desc/EP Req: [seq][nwk:2]
    elif cluster_id in (0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0010) and len(pl) >= 3:
        tree["zbee_zdp.zdp_cmd_nwk_addr"] = f"0x{int.from_bytes(pl[1:3], 'little'):04X}"
    # 0x0031 Mgmt LQI Req: [seq][start:1]
    elif cluster_id == 0x0031 and len(pl) >= 2:
        tree["zbee_zdp.zdp_cmd_start_index"] = str(pl[1])
    # 0x8000/0x8001 Addr Resp: [seq][status:1][eui64:8][nwk:2][num_assoc:1][start:1]
    elif cluster_id in (0x8000, 0x8001) and len(pl) >= 14:
        tree["zbee_zdp.status"] = f"0x{pl[1]:02X}"
        tree["zbee_zdp.zdp_cmd_eui64"] = _eui(pl[2:10])
        tree["zbee_zdp.zdp_cmd_nwk_addr"] = f"0x{int.from_bytes(pl[10:12], 'little'):04X}"
        tree["zbee_zdp.zdp_cmd_num_assoc"] = str(pl[12])
        tree["zbee_zdp.zdp_cmd_start_index"] = str(pl[13])
    # 0x8002 Node Desc Resp: [seq][status:1][nwk:2]
    elif cluster_id == 0x8002 and len(pl) >= 4:
        tree["zbee_zdp.status"] = f"0x{pl[1]:02X}"
        tree["zbee_zdp.zdp_cmd_nwk_addr"] = f"0x{int.from_bytes(pl[2:4], 'little'):04X}"

    return tree if len(tree) > 1 else None


def _fallback_nwk_cmd_tree(cmd_name: str, p: dict) -> dict | None:
    """平铺字段 → Command Frame 子树 (对齐 tshark zbee_nwk.cmd.* 字段名, 前端按名取值)."""
    if cmd_name == "Link Status" and p.get("link_status_neighbors"):
        tree: dict = {}
        for i, nb in enumerate(p["link_status_neighbors"], 1):
            tree[f"Link {i}"] = {
                "zbee_nwk.cmd.link.address": f"0x{nb['addr']:04X}",
                "zbee_nwk.cmd.link.incoming_cost": str(nb["in_cost"]),
                "zbee_nwk.cmd.link.outgoing_cost": str(nb["out_cost"]),
            }
        return tree or None
    if cmd_name == "Network Status" and p.get("nwk_status_code") is not None:
        tree = {"zbee_nwk.cmd.status": f"0x{p['nwk_status_code']:02X}"}
        if p.get("nwk_status_target") is not None:
            tree["zbee_nwk.cmd.route.dest"] = f"0x{p['nwk_status_target']:04X}"
        return tree
    if cmd_name == "Route Request" and p.get("route_req"):
        rr = p["route_req"]
        return {
            "zbee_nwk.cmd.route.opts": f"0x{rr['options']:02X}",
            "zbee_nwk.cmd.route.id": str(rr["id"]),
            "zbee_nwk.cmd.route.dest": f"0x{rr['dest']:04X}",
            "zbee_nwk.cmd.route.cost": str(rr["cost"]),
        }
    if cmd_name == "Route Reply" and p.get("route_reply"):
        rp = p["route_reply"]
        return {
            "zbee_nwk.cmd.route.opts": f"0x{rp['options']:02X}",
            "zbee_nwk.cmd.route.id": str(rp["id"]),
            "zbee_nwk.cmd.route.orig": f"0x{rp['originator']:04X}",
            "zbee_nwk.cmd.route.resp": f"0x{rp['responder']:04X}",
            "zbee_nwk.cmd.route.cost": str(rp["cost"]),
        }
    if cmd_name == "Leave":
        return {
            "zbee_nwk.cmd.leave.rejoin": "1" if p.get("nwk_leave_rejoin") else "0",
            "zbee_nwk.cmd.leave.request": "1" if p.get("nwk_leave_request") else "0",
            "zbee_nwk.cmd.leave.children": "1" if p.get("nwk_leave_children") else "0",
        }
    if cmd_name == "Route Record" and p.get("route_record_relays"):
        rr = p["route_record_relays"]
        tree = {"zbee_nwk.cmd.relay_count": str(rr.get("count", 0))}
        for i, addr in enumerate(rr.get("relays", []), 1):
            tree[f"zbee_nwk.cmd.relay_device_{i}"] = f"0x{addr:04X}"
        return tree
    return None


# APS Ack 配对 — 共享模块 (backend/aps_pairing.py, 详情端点与 L3-1 检测器共用)
from ..aps_pairing import build_ack_match as _build_ack_match  # noqa: E402
from ..aps_pairing import build_transaction_peers as _build_transaction_peers  # noqa: E402


def _get_ack_match() -> tuple[dict, dict]:
    """惰性构建 + 缓存 (以 _packets 引用 id 失效, 重新导入自动重建)."""
    global _ack_match_cache
    ref, pairs = _ack_match_cache
    if ref != id(_packets) or pairs is None:
        pairs = _build_ack_match(_packets)
        _ack_match_cache = (id(_packets), pairs)
    return pairs


def _get_transaction_peers() -> dict:
    """U16-7a 事务链惰性构建 + 缓存 (与 _get_ack_match 同模式, 首次详情访问构建一次)."""
    global _transaction_cache
    ref, peers = _transaction_cache
    if ref != id(_packets) or peers is None:
        peers = _build_transaction_peers(_packets)
        _transaction_cache = (id(_packets), peers)
    return peers


def _get_uplink_path_index() -> dict:
    """U16-4b 上行路径索引 (惰性缓存): {(src,dst): [{relays, first_ts, last_ts}]}.

    素材实证 (08-25): 中继素材 RR 帧 relays 几乎全空 (31 帧仅 3 帧非空), 下行 source
    route 丰富 (546 帧) → 上行路径用 U13 同源方法「下行 source-route 反转」:
    上行帧 (设备→协调器) 查下行 (dst→src) 的 source route, 中继列表反转即为上行路径.
    同 (src,dst) 多路径 (路由变更) 全保留, 时间窗匹配取最近.
    """
    global _rr_path_cache
    ref, idx = _rr_path_cache
    if ref != id(_packets) or idx is None:
        agg: dict = {}
        for p in _packets:
            relays = p.get("nwk_relays")
            src, dst = p.get("nwk_src"), p.get("nwk_dst")
            if not relays or src is None or dst is None:
                continue
            key = (src, dst)
            ts = p.get("ts", 0.0)
            lst = agg.get(key)
            if lst is None:
                agg[key] = [{"relays": relays, "first_ts": ts, "last_ts": ts}]
            else:
                for m in lst:
                    if m["relays"] == relays:
                        m["first_ts"] = min(m["first_ts"], ts)
                        m["last_ts"] = max(m["last_ts"], ts)
                        break
                else:
                    lst.append({"relays": relays, "first_ts": ts, "last_ts": ts})
        idx = agg
        _rr_path_cache = (id(_packets), idx)
    return idx


def _uplink_relays_for(p: dict, idx: dict) -> list | None:
    """上行帧 p 的路径中继: 查下行 (dst,src) source route 反转 (时间窗匹配 → 兜底最新)."""
    src, dst = p.get("nwk_src"), p.get("nwk_dst")
    if src is None or dst is None:
        return None
    cands = idx.get((dst, src))  # 反向: 下行 dst→src
    if not cands:
        return None
    ts = p.get("ts", 0.0)
    for m in cands:
        if m["first_ts"] <= ts <= m["last_ts"] + 2.0:
            return list(reversed(m["relays"]))
    return list(reversed(max(cands, key=lambda m: m["last_ts"])["relays"]))


def _detail_dict(p: dict, pkt_id: int) -> dict:
    """单帧详情组装 (packet_detail 与节点画像导出共用).

    - layers: 完整协议层树 (cubx 路径为 fallback 构造)
    - zcl_payload_parsed: ZCL 命令载荷字段级解析 (U15)
      {parser, mode, fields: [{field, value, note}], hex} | None (无 ZCL 载荷)
    """
    layers = p.get("raw_layers") or {}
    if not layers:
        layers = _fallback_layers(p)  # cubx 路径 raw_layers 为空 → 平铺字段构造 (U5)
    # U15: ZCL 命令载荷字段级解析 — 标准簇 schema → 涂鸦注册表 → 字节偏移兜底
    zcl_parsed = None
    if p.get("zcl_payload_hex") is not None:
        ph = p["zcl_payload_hex"]
        pl = bytes.fromhex(ph) if ph else b""
        zcl_parsed = zcl_defs.parse_zcl_payload(
            p.get("aps_cluster"), p.get("zcl_cmd_id"), p.get("zcl_frame_type"),
            pl, p.get("zcl_direction"))
    return {
        "id": pkt_id,
        "packet_id": p.get("packet_id"),  # 抓包原始帧号 (与列表端点 id 对应同一帧)
        "ts": p["ts"],
        "pkt_type": p.get("pkt_type", ""),
        "decrypted": p.get("decrypted", False),
        "security": p.get("security", ""),
        "layers": layers,  # 完整 tshark JSON 层树 (cubx 路径为 fallback 构造)
        # ZCL 按簇正确解析的命令名 (前端详情 ZCL 层优先使用, 避免前端混合表误标)
        "zcl_cmd_name": p.get("zcl_cmd_name"),
        "aps_cluster_name": p.get("aps_cluster_name"),
        # U9 改进 (08-13): Read Attr Rsp 属性记录 (详情 ZCL 层展示 厂商/型号 等)
        "zcl_attr_reads": p.get("zcl_attr_reads"),
        "zcl_payload_parsed": zcl_parsed,  # U15 载荷字段级解析
    }


@router.get("/packets/{pkt_id}")
async def packet_detail(pkt_id: int):
    """单帧协议树 — 返回 raw_layers 完整 JSON"""
    if pkt_id < 0 or pkt_id >= len(_packets):
        return JSONResponse({"error": f"包 ID {pkt_id} 不存在 (共 {len(_packets)} 帧)"}, 404)
    p = _packets[pkt_id]
    d = _detail_dict(p, pkt_id)
    # APS Ack 配对 (ack 帧 → 被确认帧; 数据帧 → 确认它的 ack 帧)
    ack_to_orig, orig_to_ack = _get_ack_match()
    ack_pair = None
    if p.get("pkt_type") == "APS Ack":
        orig = ack_to_orig.get(pkt_id)
        if orig is not None:
            ack_pair = {"kind": "ack_to", "peer_id": orig,
                        "text": f"确认了帧 #{orig}"}
    else:
        got = orig_to_ack.get(pkt_id)
        if got is not None:
            ack_pair = {"kind": "ack_from", "peer_id": got[0],
                        "text": f"被帧 #{got[0]} 确认"}
    d["aps_ack_pair"] = ack_pair  # APS Ack 配对 (2026-08-06)
    # U16-7a 事务链: 命令帧 → (ack + ZCL 响应帧列表) (2026-08-25)
    tr = _get_transaction_peers().get(pkt_id)
    if tr:
        d["transaction"] = tr
    return d
