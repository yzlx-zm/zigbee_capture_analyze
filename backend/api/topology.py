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
_cache_asym: list | None = None       # 不对称链路缓存


def _build_phase3_supplements(pkts: list[dict], pan: int | None) -> tuple[dict, list]:
    """构建 Link Status 邻居表 + 不对称链路 (复用 topology.py 已验证逻辑)."""
    global _cache_ls_tables, _cache_asym, _events_packet_count
    # 简单缓存: packets 未变化时复用
    if _cache_ls_tables is not None and len(pkts) == _events_packet_count:
        return _cache_ls_tables, _cache_asym or []
    # PAN 过滤
    if pan is not None:
        ls_pkts = [p for p in pkts if (p.get("pan_src") or p.get("pan_dst")) == pan]
    else:
        ls_pkts = pkts
    _cache_ls_tables = topo._build_neighbor_tables(ls_pkts)
    _cache_asym = topo._detect_asymmetric(_cache_ls_tables)
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
    ls_tables, asym = _build_phase3_supplements(pkts, pan_int)
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


@router.get("/nodes")
async def node_list(search: str = Query(default=""), pan: str = Query(default="")):
    nodes = get_nodes()
    pan_int = int(pan, 16) if pan else None
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
        # seen count: per-PAN if filter is set
        if pan_int is not None:
            pkts = get_packets()
            nd_seen = sum(1 for p in pkts if (p["nwk_src"]==aid or p["nwk_dst"]==aid or p["mac_src"]==aid or p["mac_dst"]==aid) and ((p["pan_src"]==pan_int or p["pan_dst"]==pan_int)))
        else:
            nd_seen = n["seen"]
        result.append({
            "aid": aid, "label": label,
            "seen": nd_seen, "pan": n["pan"] if not pan_int else pan_int,
            "is_coord": aid == 0,
            "type_list": n["type_list"][:8],
            "device_type": n.get("device_type", "unknown"),
        })
    return result
