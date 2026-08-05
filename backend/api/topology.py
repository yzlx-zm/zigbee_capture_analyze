"""拓扑 + 节点 API"""
from fastapi import APIRouter, Query
from .files import get_packets, get_nodes, get_full_packets
from .. import topology as topo
from .. import route_events as rev

router = APIRouter()

# 全局事件时间线 (从导入的 packets 构建, packets 变化时重建)
_events_timeline: rev.RouteEventTimeline | None = None
_events_packet_count: int = 0  # 用于检测 packets 是否变化
_cache_ls_tables: dict | None = None  # Link Status 邻居表缓存
_cache_ls_key: tuple | None = None    # 邻居表缓存键 (包数, pan, t0, t1)
_cache_asym: list | None = None       # 不对称链路缓存


def _build_phase3_supplements(pkts: list[dict], pan: int | None,
                              t0: float | None = None, t1: float | None = None) -> tuple[dict, list]:
    """构建 Link Status 邻居表 + 不对称链路 (复用 topology.py 已验证逻辑).

    支持时间窗口: 邻居表 = 窗口内 Link Status 帧累积 (物理层随时间演变).
    """
    global _cache_ls_tables, _cache_asym, _events_packet_count, _cache_ls_key
    # 缓存键含时间窗口 (不同窗口不同邻居表)
    key = (len(pkts), pan, t0, t1)
    if _cache_ls_tables is not None and key == _cache_ls_key:
        return _cache_ls_tables, _cache_asym or []
    # PAN 过滤
    if pan is not None:
        ls_pkts = [p for p in pkts if (p.get("pan_src") or p.get("pan_dst")) == pan]
    else:
        ls_pkts = pkts
    # 时间过滤
    if t0 is not None:
        ls_pkts = [p for p in ls_pkts if p.get("ts", 0) >= t0]
    if t1 is not None:
        ls_pkts = [p for p in ls_pkts if p.get("ts", 0) <= t1]
    _cache_ls_tables = topo._build_neighbor_tables(ls_pkts)
    _cache_asym = topo._detect_asymmetric(_cache_ls_tables)
    _cache_ls_key = key
    return _cache_ls_tables, _cache_asym


def _ensure_events_timeline() -> rev.RouteEventTimeline:
    """惰性构建事件时间线 (packets 不变时只构建一次)."""
    global _events_timeline, _events_packet_count
    pkts = get_packets()
    if _events_timeline is not None and len(pkts) == _events_packet_count:
        return _events_timeline
    # 重建事件 + 清除 LS 缓存
    global _cache_ls_tables, _cache_asym
    _cache_ls_tables = None
    _cache_asym = None
    _events_timeline = rev.RouteEventTimeline()
    _events_timeline.add(rev.extract_events(pkts))
    _events_packet_count = len(pkts)
    return _events_timeline


@router.get("/topology/graph")
async def topology_graph(pan: str = Query(default=""),
                         time_start: float | None = Query(default=None),
                         time_end: float | None = Query(default=None)):
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"nodes": [], "edges": [], "coord": None}
    pan_int = int(pan, 16) if pan else None
    return topo.build(pkts, nodes, filter_pan=pan_int,
                      time_start=time_start, time_end=time_end)


@router.get("/topology/events")
async def topology_from_events(pan: str = Query(default=""),
                               time_start: float | None = Query(default=None),
                               time_end: float | None = Query(default=None)):
    """事件时间线推导的拓扑 (Phase 3: 含 Link Status 邻居表)."""
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"nodes": [], "edges": [], "coord": None}
    pan_int = int(pan, 16) if pan else None
    timeline = _ensure_events_timeline()
    ls_tables, asym = _build_phase3_supplements(pkts, pan_int, time_start, time_end)
    return rev.derive_topology(timeline, nodes, pan=pan_int,
                               t0=time_start, t1=time_end,
                               link_status_tables=ls_tables,
                               asymmetric_links=asym)


@router.get("/diag/offline")
async def diag_offline(pan: str = Query(default=""),
                       time_start: float | None = Query(default=None),
                       time_end: float | None = Query(default=None)):
    """设备离线诊断: Leave burst + rejoin 推断 + 诊断结论."""
    pkts = get_packets()
    if not pkts:
        return {"devices": [], "summary": {"total_devices_left": 0}}
    pan_int = int(pan, 16) if pan else None
    timeline = _ensure_events_timeline()
    nodes = get_nodes()
    return rev.aggregate_offline_diagnosis(timeline, nodes=nodes, pan=pan_int,
                                           t0=time_start, t1=time_end)


@router.get("/diag/l1")
async def diag_l1():
    """L1 入网检测: Beacon Request 命中率 (L1-1) + Association 流程 (L1-2).

    需要 cubx 导入 (含 MAC 帧). pcap 导入无 MAC 帧 → 返回不可判定.
    """
    from ..detectors import l1 as l1_detector
    full = get_full_packets()
    if not full:
        return {"error": "无数据 (需导入 .cubx 文件)"}
    return l1_detector.detect(full)


@router.get("/diag/l2")
async def diag_l2():
    """L2 在线维持检测: L2-1 终端频繁离线 (poll 间隔超时 / Leave-Rejoin 循环).

    需要含 MAC 帧的素材 (DataRequest 提取).
    """
    from ..detectors import l2 as l2_detector
    full = get_full_packets()
    if not full:
        return {"error": "无数据 (需导入 .cubx 文件)"}
    return l2_detector.detect(full)


@router.get("/diag/l6")
async def diag_l6():
    """L6 SED 专项检测: L6-S3 间接事务过期 (Network Status 0x06).

    与 L3 检测合并计算交叉提示 (G32 案例: 0x06 是 0x0C 下行失败的 SED 侧表现).
    """
    from ..detectors import l3 as l3_detector
    from ..detectors import l6 as l6_detector
    full = get_full_packets()
    if not full:
        return {"error": "无数据 (需导入 .cubx 文件)"}
    l3_result = l3_detector.detect(full)
    return l6_detector.detect(full, l3_result=l3_result)


@router.get("/diag/l3")
async def diag_l3():
    """L3 运营期检测: L3-5 源路由/MTORR 失效 (Network Status 0x0B/0x0C).

    与 L1 检测合并计算交叉提示 (838D 案例: L1-3 密钥循环 = L3-5 根因的表象).
    """
    from ..detectors import l1 as l1_detector
    from ..detectors import l3 as l3_detector
    full = get_full_packets()
    if not full:
        return {"error": "无数据 (需导入 .cubx 文件)"}
    l1_result = l1_detector.detect(full)
    return l3_detector.detect(full, l1_result=l1_result)


def _metric_stats(vals: list) -> dict | None:
    """LQI/RSSI 统计 {min, avg, max}; 无数据 (CSV 导入无此字段) 返回 None."""
    if not vals:
        return None
    return {"min": min(vals), "avg": round(sum(vals) / len(vals)), "max": max(vals)}


@router.get("/nodes")
async def node_list(search: str = Query(default=""), pan: str = Query(default="")):
    """节点列表 + 每节点详情 (U3: 首末时间/类型计数/EUI64/LQI-RSSI/邻居表).

    - EUI64/LQI/RSSI 仅 cubx 导入有 (nwk_src64/lqi/rssi 字段), CSV 返回 None
    - 邻居表复用 _build_phase3_supplements (Link Status 累积, 含不对称标记)
    """
    pkts = get_packets()
    nodes = get_nodes()
    pan_int = int(pan, 16) if pan else None

    # 单遍扫描: seen/首末 ts/类型计数/LQI/RSSI/EUI64 (与旧 per-node sum 语义一致, O(pkts))
    stats: dict[int, dict] = {}
    for p in pkts:
        if pan_int is not None and (p.get("pan_src") != pan_int and p.get("pan_dst") != pan_int):
            continue
        ts = p.get("ts") or 0
        t = p.get("pkt_type") or "Unknown"
        for aid in (p.get("mac_src"), p.get("mac_dst"), p.get("nwk_src"), p.get("nwk_dst")):
            if not topo.is_unicast(aid):
                continue
            s = stats.get(aid)
            if s is None:
                s = {"seen": 0, "first": None, "last": None,
                     "type_counts": {}, "lqis": [], "rssis": [], "eui64": None}
                stats[aid] = s
            s["seen"] += 1
            if s["first"] is None or ts < s["first"]:
                s["first"] = ts
            if s["last"] is None or ts > s["last"]:
                s["last"] = ts
            s["type_counts"][t] = s["type_counts"].get(t, 0) + 1
            if p.get("lqi") is not None:
                s["lqis"].append(p["lqi"])
            if p.get("rssi") is not None:
                s["rssis"].append(p["rssi"])
            # EUI64 只取节点自己作为源地址的帧 (nwk_src64 优先, 其次 mac_src64)
            if s["eui64"] is None:
                if aid == p.get("nwk_src") and p.get("nwk_src64"):
                    s["eui64"] = p["nwk_src64"]
                elif aid == p.get("mac_src") and p.get("mac_src64"):
                    s["eui64"] = p["mac_src64"]

    # 邻居表 + 不对称链路 (Phase 3 已验证逻辑, 含缓存)
    ls_tables, asym = _build_phase3_supplements(pkts, pan_int)
    asym_levels = {frozenset((a["a"], a["b"])): a["level"] for a in asym}

    result = []
    for aid, n in sorted(nodes.items()):
        label = f"0x{aid:04X}"
        if search:
            q = search.strip().lower()
            if q not in label.lower() and q not in str(aid):
                continue
        # PAN filter: either node belongs to this PAN, or it's 0x0000 (always shown)
        if pan_int is not None:
            if n["pan"] != pan_int and aid != 0:
                continue
        st = stats.get(aid)
        neighbors = [
            {"addr": na, "label": f"0x{na:04X}",
             "in_cost": v["in_cost"], "out_cost": v["out_cost"],
             "count": v["count"], "last_seen": v["last_seen_ts"],
             "asym": asym_levels.get(frozenset((aid, na)))}
            for na, v in sorted(ls_tables.get(aid, {}).items())
        ]
        result.append({
            "aid": aid, "label": label,
            "seen": st["seen"] if st else 0,
            "pan": n["pan"] if not pan_int else pan_int,
            "is_coord": aid == 0,
            "type_list": n["type_list"][:8],
            "device_type": n.get("device_type", "unknown"),
            "detail": {
                "first_ts": st["first"] if st else None,
                "last_ts": st["last"] if st else None,
                "type_counts": st["type_counts"] if st else {},
                "eui64": st["eui64"] if st else None,
                "lqi": _metric_stats(st["lqis"]) if st else None,
                "rssi": _metric_stats(st["rssis"]) if st else None,
                "neighbors": neighbors,
            },
        })
    return result
