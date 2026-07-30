"""路由事件时间线 — 协议数据驱动的拓扑推导 (替代静态 topology.build())

事件模型:
  RouteEvent     — 统一的路由事件记录
  RouteEventTimeline — 内存事件存储, 按时间排序, 支持窗口查询和拓扑推导

当前阶段: Phase 1 — Route Record 提取; Route Request/Network Status 后续填充。

参考: CONTEXT.md 领域词汇表; akubela-zigbee-analyser _capture_probe.py Event model
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .topology import is_unicast


# ── Event Types ──

# 可扩展的事件类型常量
EVENT_ROUTE_RECORD = "route_record"
EVENT_ROUTE_REQUEST = "route_request"
EVENT_NETWORK_STATUS = "network_status"


@dataclass
class RouteEvent:
    """统一的路由事件记录.

    不同 event_type 使用不同的专属字段:
      route_record:   relays (中继路径, 设备→协调器方向)
      route_request:  radius, dropped, dropped_at_hop
      network_status: status_code
    """
    timestamp: float
    event_type: str
    src: int
    dst: int
    # Route Record 专属
    relays: list[int] = field(default_factory=list)
    # Route Request 专属
    radius: int | None = None
    dropped: bool = False
    dropped_at_hop: int | None = None
    # Network Status 专属
    status_code: int | None = None
    # 公共
    packet_id: int = 0
    pan: int | None = None


# ── Timeline ──

class RouteEventTimeline:
    """内存事件存储 — 按 timestamp 排序, 支持时间窗口和类型过滤."""

    def __init__(self):
        self.events: list[RouteEvent] = []

    def add(self, events: list[RouteEvent]) -> None:
        """批量追加事件, 保持时间排序."""
        self.events.extend(events)
        self.events.sort(key=lambda e: e.timestamp)

    def query(self,
              t0: float | None = None,
              t1: float | None = None,
              event_types: list[str] | None = None) -> list[RouteEvent]:
        """时间窗口 + 类型过滤.

        t0=None 表示不限制下限; t1=None 表示不限制上限.
        event_types=None 表示返回所有类型.
        """
        result = self.events
        if t0 is not None:
            result = [e for e in result if e.timestamp >= t0]
        if t1 is not None:
            result = [e for e in result if e.timestamp <= t1]
        if event_types is not None:
            type_set = set(event_types)
            result = [e for e in result if e.event_type in type_set]
        return result

    @property
    def first_ts(self) -> float | None:
        return self.events[0].timestamp if self.events else None

    @property
    def last_ts(self) -> float | None:
        return self.events[-1].timestamp if self.events else None

    def __len__(self) -> int:
        return len(self.events)


# ── Extraction ──

def extract_route_record_events(packets: list[dict]) -> list[RouteEvent]:
    """从 tshark 解析的包列表中提取所有 Route Record 事件.

    tshark._frame_to_dict 已将 route_record_relays 提取为 {count, relays: [addr, ...]}.
    relays 列表已通过 -T fields 补充, 保证完整性 (JSON 多实例字段只保留最后一个的问题已修复).
    """
    events: list[RouteEvent] = []
    for p in packets:
        if p.get("pkt_type") != "Route Record":
            continue
        rr = p.get("route_record_relays")
        if not rr or not rr.get("relays"):
            continue
        src = p.get("nwk_src")
        dst = p.get("nwk_dst")
        if src is None or dst is None:
            continue
        events.append(RouteEvent(
            timestamp=p["ts"],
            event_type=EVENT_ROUTE_RECORD,
            src=src,
            dst=dst,
            relays=list(rr["relays"]),  # 防御性拷贝
            pan=p.get("pan_src") or p.get("pan_dst"),
            packet_id=_get_packet_id(p),
        ))
    return events


def _get_packet_id(p: dict) -> int:
    """从 packet dict 提取帧号 (用于交叉引用)."""
    layers = p.get("raw_layers", {})
    frame = layers.get("frame", {})
    raw = frame.get("frame.number", "0")
    try:
        return int(raw) if isinstance(raw, str) else int(raw)
    except (ValueError, TypeError):
        return 0


# ── Topology Derivation (Phase 1: Route Record only) ──

def derive_topology(timeline: RouteEventTimeline,
                    nodes: dict[int, dict],
                    pan: int | None = None,
                    t0: float | None = None,
                    t1: float | None = None) -> dict:
    """从事件时间线推导拓扑图, 输出格式兼容 topology.build().

    当前 Phase 1 仅使用 Route Record 事件构建 path 和 node 列表.
    后续 Phase 2-3 加入 Route Request / Network Status 后会丰富方向语义.
    """
    events = timeline.query(t0, t1, [EVENT_ROUTE_RECORD])

    # PAN 过滤
    if pan is not None:
        events = [e for e in events if e.pan == pan]

    # Route paths — 聚合 (src + relays + dst) 去重
    path_meta: dict[tuple, dict] = {}
    for e in events:
        dedup_key = (e.src, tuple(e.relays), e.dst)
        if dedup_key in path_meta:
            meta = path_meta[dedup_key]
            meta["first_ts"] = min(meta["first_ts"], e.timestamp)
            meta["last_ts"] = max(meta["last_ts"], e.timestamp)
            meta["frame_count"] += 1
        else:
            path_meta[dedup_key] = {
                "first_ts": e.timestamp,
                "last_ts": e.timestamp,
                "frame_count": 1,
            }

    route_paths = []
    for (src, relays_tuple, dst), meta in path_meta.items():
        relays = list(relays_tuple)
        full_path = [src] + relays + [dst]
        path_str = " → ".join(f"0x{a:04X}" for a in full_path)
        active = not ((t0 is not None and meta["last_ts"] < t0)
                      or (t1 is not None and meta["first_ts"] > t1))
        route_paths.append({
            "src": src,
            "dst": dst,
            "relays": relays,
            "hop_count": len(relays) + 1,
            "path_str": path_str,
            "first_ts": meta["first_ts"],
            "last_ts": meta["last_ts"],
            "frame_count": meta["frame_count"],
            "is_current": True,  # Phase 1 暂不区分
            "active": active,
        })

    route_paths.sort(key=lambda x: x["first_ts"])

    # 标记 is_current (同一 src 的最新路径)
    src_latest: dict[int, float] = {}
    for rp in route_paths:
        s = rp["src"]
        if s not in src_latest or rp["first_ts"] > src_latest[s]:
            src_latest[s] = rp["first_ts"]
    for rp in route_paths:
        rp["is_current"] = (rp["first_ts"] == src_latest.get(rp["src"]))

    # PAN 统计
    pan_counts = defaultdict(int)
    active_aids = set()
    for e in events:
        if e.pan:
            pan_counts[e.pan] += 1
        active_aids.add(e.src)
        active_aids.add(e.dst)
        active_aids.update(e.relays)
    main_pan = max(pan_counts, key=pan_counts.get) if pan_counts else None
    if pan is None and main_pan is not None:
        pan = main_pan

    # 节点列表 (从 event participants + nodes dict 合并)
    node_list = []
    for aid in sorted(active_aids):
        n = nodes.get(aid, {})
        node_list.append({
            "aid": aid,
            "label": f"0x{aid:04X}",
            "seen": n.get("seen", 0),
            "pan": pan,
            "is_coord": aid == 0,
            "depth": -1,  # 后续 BFS 由前端计算
            "parent": None,
            "children": [],
            "coord_traffic": 0,
            "type_list": n.get("type_list", [])[:10],
            "device_type": n.get("device_type", "unknown"),
        })

    # 边: Route Record 每跳 (粗略, 后续 Link Status 补充)
    edge_list = []
    edge_seen = set()
    for rp in route_paths:
        full = [rp["src"]] + rp["relays"] + [rp["dst"]]
        for i in range(len(full) - 1):
            s, d = full[i], full[i + 1]
            if s in active_aids and d in active_aids:
                ek = (min(s, d), max(s, d))
                if ek not in edge_seen:
                    edge_seen.add(ek)
                    edge_list.append({
                        "src": s, "dst": d,
                        "count": 1,
                        "success_rate": 1.0,
                        "is_link_status": False,
                        "is_parent_child": False,
                    })

    pan_list = [{"pan": p, "count": c, "label": f"0x{p:04X}"}
                for p, c in sorted(pan_counts.items(), key=lambda x: -x[1])[:50]]

    return {
        "pan_list": pan_list,
        "nodes": node_list,
        "edges": edge_list,
        "coord": 0,
        "main_pan": main_pan,
        "pans": sorted(pan_counts.keys()),
        "tree_depths": {},
        "tree_node_count": len(active_aids),
        "leaf_count": 0,
        "total_nodes": len(nodes),
        "total_edges": len(edge_list),
        "parents": {},
        # 协议数据 (Phase 1: 仅 Route Record; Phase 2+ 会丰富)
        "neighbor_tables": {},
        "route_paths": route_paths,
        "asymmetric_links": [],
    }
