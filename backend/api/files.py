"""导入 API — CSV / pcap / cubx (解析走后台线程, 前端轮询真实进度)"""
from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from .. import csv_reader

router = APIRouter()

_packets: list[dict] = []
_nodes: dict[int, dict] = {}
_file_type: str = ""
_verify_report: dict | None = None  # 校验报告
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
    """将 HH:MM:SS 时钟时间解析为绝对 Unix 时间戳 (UTC)。
    基于抓包第一帧的 UTC 日期，将时钟时间映射到当天 UTC 绝对时间。
    不做跨午夜修正 — 若早于抓包开始则自然包含所有包（无更早数据）。"""
    import calendar as _cal
    parts = time_str.split(":")
    if len(parts) < 2:
        return None
    h, m = int(parts[0]), int(parts[1])
    s = int(parts[2]) if len(parts) > 2 else 0
    clock_sec = h * 3600 + m * 60 + s
    base_dt_utc = datetime.utcfromtimestamp(base_ts)
    midnight_utc = base_dt_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_ts = _cal.timegm(midnight_utc.timetuple())
    return midnight_ts + clock_sec



@router.post("/import/files")
async def import_upload(files: list[UploadFile] = File(...)):
    import tempfile
    tmp_paths = []
    for f in files:
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.close()
        with open(tmp.name, "wb") as out:
            while data := await f.read(1024 * 1024):
                out.write(data)
        tmp_paths.append(tmp.name)
    return _start_import(lambda tid: _run_csv_import(tid, tmp_paths))

def _run_csv_import(task_id: str, tmp_paths: list[str]) -> dict:
    """后台: CSV 解析 (无 tshark, 进度: 读取→解析→节点)"""
    global _packets, _nodes, _file_type
    try:
        _task_update(task_id, stage="读取文件", percent=10)
        all_pkts = []
        total = len(tmp_paths)
        for i, path in enumerate(tmp_paths):
            pkts = csv_reader.read_csv(path)
            all_pkts.extend(pkts)
            _task_update(task_id, stage="解析 CSV", percent=10 + int((i + 1) / total * 60))
        if not all_pkts:
            raise RuntimeError("无有效数据")
        all_pkts.sort(key=lambda p: p["ts"])
        _task_update(task_id, stage="提取节点", percent=80)
        _packets = all_pkts
        _nodes = csv_reader.extract_nodes(all_pkts)
        _file_type = "csv"
        types = {}
        for p in all_pkts:
            t = p["pkt_type"] or "Unknown"
            types[t] = types.get(t, 0) + 1
        _task_update(task_id, stage="完成", percent=100)
        return {"ok": True, "packets": len(all_pkts), "nodes": len(_nodes),
                "file_type": "csv", "by_type": dict(sorted(types.items(), key=lambda x: -x[1])[:20])}
    finally:
        for p in tmp_paths:
            try: os.unlink(p)
            except OSError: pass



@router.post("/import/local")
async def import_local(path: str = Form(...)):
    if not os.path.exists(path):
        return JSONResponse({"error": f"路径不存在: {path}"}, 400)

    ext = os.path.splitext(path)[1].lower()
    if ext in (".pcap", ".pcapng"):
        return JSONResponse({"error": "pcap 格式暂不支持，请用 Ubiqua 导出 CSV"}, 400)
    elif ext == ".cubx":
        return JSONResponse({"error": "cubx 格式暂不支持，请用 Ubiqua 导出 CSV"}, 400)
    elif ext != ".csv":
        return JSONResponse({"error": f"不支持的文件格式: {ext}"}, 400)

    return _start_import(lambda tid: _run_csv_local(tid, path))

def _run_csv_local(task_id: str, path: str) -> dict:
    """后台: CSV 本地路径解析"""
    global _packets, _nodes, _file_type
    _task_update(task_id, stage="解析 CSV", percent=30)
    try:
        _packets = csv_reader.read_csv(path)
    except Exception as e:
        raise RuntimeError(str(e)) from e
    _file_type = "csv"
    _task_update(task_id, stage="提取节点", percent=80)
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
    global _packets, _nodes, _file_type, _verify_report, _pcap_paths, _last_ubiqua_sync, _last_import_summary, _full_packets
    _packets = []; _nodes = {}; _file_type = ""; _verify_report = None; _pcap_paths = []
    _last_ubiqua_sync = None; _last_import_summary = None; _full_packets = []
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
    global _packets, _nodes, _file_type, _full_packets, _verify_report, _last_ubiqua_sync, _pcap_paths
    from .. import tshark as _tshark
    try:
        # 导入前透明同步 Ubiqua Network Key (不可达则静默跳过)
        _task_update(task_id, stage="同步 Ubiqua Key", percent=8)
        _last_ubiqua_sync = _sync_ubiqua_keys()

        # tshark 解析 (按文件推进)
        _packets = []
        total = len(tmp_paths)
        for i, p in enumerate(tmp_paths):
            pkts = _tshark.parse_packets([p])
            _packets.extend(pkts)
            _task_update(task_id, stage=f"tshark 解析 ({i + 1}/{total})",
                         percent=12 + int((i + 1) / total * 28))
        if not _packets:
            raise RuntimeError("无有效数据 (可能不是 Zigbee 抓包)")
        _packets.sort(key=lambda p: p["ts"])
        _nodes = _extract_nodes_from_packets(_packets)
        _file_type = "pcap"
        _pcap_paths = [os.path.abspath(p) for p in tmp_paths]

        # 全量帧 (含 MAC 命令帧/Beacon) — L1 检测需要
        _task_update(task_id, stage="解析 MAC 帧", percent=42)
        try:
            _full_packets = []
            tshark_path = _tshark.find_tshark()
            for p in tmp_paths:
                _full_packets.extend(_tshark.parse_mac_frames(tshark_path, p))
            _full_packets.extend(_packets)
            _full_packets.sort(key=lambda p: p["ts"])
        except Exception:
            _full_packets = list(_packets)

        # 运行校验 (6 项逐项上报进度, 50→95)
        _task_update(task_id, stage="校验", percent=50)
        try:
            from .. import verify as _verify
            def _vcb(idx, total_checks, label):
                _task_update(task_id, stage=f"校验: {label}", percent=50 + int((idx + 1) / total_checks * 45))
            _verify_report = _verify.run_verification(_pcap_paths, _packets, progress_cb=_vcb)
        except Exception:
            _verify_report = {"passed": False, "error": "校验执行异常"}

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
    global _packets, _nodes, _file_type, _full_packets, _verify_report, _last_ubiqua_sync, _pcap_paths
    from .. import tshark as _tshark
    try:
        _task_update(task_id, stage="同步 Ubiqua Key", percent=8)
        _last_ubiqua_sync = _sync_ubiqua_keys()

        _packets = []
        total = len(path_list)
        for i, p in enumerate(path_list):
            pkts = _tshark.parse_packets([p])
            _packets.extend(pkts)
            _task_update(task_id, stage=f"tshark 解析 ({i + 1}/{total})",
                         percent=12 + int((i + 1) / total * 28))
        _packets.sort(key=lambda p: p["ts"])
        _nodes = _extract_nodes_from_packets(_packets)
        _file_type = "pcap"
        _pcap_paths = path_list

        _task_update(task_id, stage="解析 MAC 帧", percent=42)
        try:
            _full_packets = []
            tshark_path = _tshark.find_tshark()
            for p in path_list:
                _full_packets.extend(_tshark.parse_mac_frames(tshark_path, p))
            _full_packets.extend(_packets)
            _full_packets.sort(key=lambda p: p["ts"])
        except Exception:
            _full_packets = list(_packets)

        _task_update(task_id, stage="校验", percent=50)
        try:
            from .. import verify as _verify
            def _vcb(idx, total_checks, label):
                _task_update(task_id, stage=f"校验: {label}", percent=50 + int((idx + 1) / total_checks * 45))
            _verify_report = _verify.run_verification(_pcap_paths, _packets, progress_cb=_vcb)
        except Exception:
            _verify_report = {"passed": False, "error": "校验执行异常"}

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
    global _packets, _nodes, _file_type, _pcap_paths, _last_ubiqua_sync, _full_packets
    from .. import cubx_reader as _cubx
    try:
        all_pkts = []
        all_full = []
        total = len(tmp_paths)
        for i, tp in enumerate(tmp_paths):
            # 全量解析 (含 MAC 帧) — L1 检测需要 Beacon/Assoc 帧
            pkts, added, total_keys = _cubx.parse_cubx(tp, include_mac_frames=True)
            all_full.extend(pkts)
            # _packets 只保留 NWK 帧 (与 tshark 对齐, 避免 verify 帧数不匹配)
            all_pkts.extend(p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None)
            _last_ubiqua_sync = {"synced": added, "total_keys": total_keys}
            _task_update(task_id, stage=f"cubx 解析 ({i + 1}/{total})",
                         percent=10 + int((i + 1) / total * 80))
        if not all_pkts:
            raise RuntimeError("无有效数据")

        _packets = all_pkts
        _full_packets = all_full
        _nodes = _extract_nodes_from_packets(_packets)
        _file_type = "cubx"
        _pcap_paths = fnames or tmp_paths

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
    global _packets, _nodes, _file_type, _pcap_paths, _last_ubiqua_sync, _full_packets
    from .. import cubx_reader as _cubx
    _task_update(task_id, stage="cubx 解析", percent=30)
    try:
        pkts, added, total = _cubx.parse_cubx(path, include_mac_frames=True)
    except Exception as e:
        raise RuntimeError(str(e)) from e
    _last_ubiqua_sync = {"synced": added, "total_keys": total}
    _full_packets = pkts
    _packets = [p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
    _nodes = _extract_nodes_from_packets(_packets)
    _file_type = "cubx"
    _pcap_paths = [path]
    return _import_result()


def _extract_nodes_from_packets(packets: list[dict]) -> dict[int, dict]:
    """从 pcap 包列表中提取节点 (兼容 csv_reader.extract_nodes 格式)"""
    nodes: dict[int, dict] = {}
    pan_counts: dict[int, dict[int, int]] = {}
    # 跟踪设备类型信号
    has_link_status: set[int] = set()
    has_route: set[int] = set()
    has_device_announce: set[int] = set()

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

        # 设备类型信号收集
        pkt_type = p.get("pkt_type", "")
        nwk_src = p.get("nwk_src")
        if "Link Status" in pkt_type and nwk_src is not None:
            has_link_status.add(nwk_src)
        if any(x in pkt_type for x in ("Route Request", "Route Reply", "Route Record")) and nwk_src is not None:
            has_route.add(nwk_src)
        if "Device Announce" in pkt_type and nwk_src is not None:
            has_device_announce.add(nwk_src)

    for aid, pc in pan_counts.items():
        if pc:
            nodes[aid]["pan"] = max(pc, key=pc.get)

    # 设备类型推断
    for aid in nodes:
        if aid == 0:
            nodes[aid]["device_type"] = "coordinator"
        elif aid in has_link_status or aid in has_route:
            nodes[aid]["device_type"] = "router"
        elif aid in has_device_announce:
            nodes[aid]["device_type"] = "router"  # Device Announce 通常是 Router
        else:
            # 只有 Data 帧, 从未发过 Link Status → 可能是 End Device
            nodes[aid]["device_type"] = "end_device"

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
        "ubiqua_sync": _last_ubiqua_sync,  # Ubiqua key 同步结果 (None=不可达)
    }
    # 持久化摘要 (后端内存, 不受前端页面切换影响)
    _last_import_summary = {
        "packets": result["packets"], "nodes": result["nodes"],
        "file_type": result["file_type"], "filename": result["filename"],
        "by_type": result["by_type"], "decrypt_stats": result["decrypt_stats"],
        "verify": result["verify"], "ubiqua_sync": result["ubiqua_sync"],
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
            ts_end = _parse_clock_time(time_end, base_ts)
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
            peer = None
            if p.get("nwk_src") == addr_int and p.get("nwk_dst") and p["nwk_dst"] != 0xFFFF:
                peer = p["nwk_dst"]
            elif p.get("nwk_dst") == addr_int and p.get("nwk_src") and p["nwk_src"] != 0xFFFF:
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
                      limit: int = 500, offset: int = 0):
    """查询原始包列表，可按地址/PAN/时间过滤，返回分页+总数"""
    addr_int = int(addr, 16) if addr else None
    pan_int = int(pan, 16) if pan else None
    # Parse time: HH:MM:SS clock time → absolute timestamp
    ts_start = None; ts_end = None
    if _packets and (time_start or time_end):
        base_ts = _packets[0]["ts"]
        if time_start:
            ts_start = _parse_clock_time(time_start, base_ts)
        if time_end:
            ts_end = _parse_clock_time(time_end, base_ts)
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
        matched.append((idx, p))
    total = len(matched)
    page = matched[offset:offset + limit]
    return {
        "packets": [{
            "id": orig_idx,
            "ts": p["ts"], "ch": p.get("ch", 0), "pkt_type": p.get("pkt_type", ""),
            "mac_src": p.get("mac_src"), "mac_dst": p.get("mac_dst"),
            "nwk_src": p.get("nwk_src"), "nwk_dst": p.get("nwk_dst"),
            "pan_src": p.get("pan_src"), "pan_dst": p.get("pan_dst"),
            "security": p.get("security", ""), "status": p.get("status", ""),
            "aps_cluster": p.get("aps_cluster"),
            "aps_cluster_name": p.get("aps_cluster_name"),
            "zcl_cmd_name": p.get("zcl_cmd_name"),
            "decrypted": p.get("decrypted", False),
        } for orig_idx, p in page],
        "total": total, "limit": limit, "offset": offset,
    }


@router.get("/packets/{pkt_id}")
async def packet_detail(pkt_id: int):
    """单帧协议树 — 返回 raw_layers 完整 JSON"""
    if pkt_id < 0 or pkt_id >= len(_packets):
        return JSONResponse({"error": f"包 ID {pkt_id} 不存在 (共 {len(_packets)} 帧)"}, 404)
    p = _packets[pkt_id]
    return {
        "id": pkt_id,
        "ts": p["ts"],
        "pkt_type": p.get("pkt_type", ""),
        "decrypted": p.get("decrypted", False),
        "security": p.get("security", ""),
        "layers": p.get("raw_layers"),  # 完整 tshark JSON 层树
    }
