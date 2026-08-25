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
EVENT_LEAVE = "leave"
EVENT_DEVICE_ANNOUNCE = "device_announce"
EVENT_IEEE_ADDR_REQ = "ieee_addr_req"


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
    # Leave 专属
    rejoin: bool = False
    request: bool = False
    remove_children: bool = False
    # Device Announce 专属
    eui64: int | None = None
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

def _get_packet_id(p: dict) -> int:
    """从 packet dict 提取帧号 (用于交叉引用)."""
    layers = p.get("raw_layers", {})
    frame = layers.get("frame", {})
    raw = frame.get("frame.number", "0")
    try:
        return int(raw) if isinstance(raw, str) else int(raw)
    except (ValueError, TypeError):
        return 0


def _h(val: str) -> int | None:
    """'0x0019' → 25, '' → None"""
    val = val.strip()
    return int(val, 16) if val else None


def _get_command_data(nwk: dict, cmd_name: str) -> dict | None:
    """从 NWK layers 中提取指定命令帧的 data dict."""
    for key in nwk:
        if key.startswith("Command Frame:") and cmd_name in key:
            data = nwk[key]
            return data if isinstance(data, dict) else None
    return None


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
        # ⚠️ 2026-08-25 修复: 直连 RR (relays 空) 是合法事件 — 设备直连协调器时
        # 无中继, relays 为空; 曾整帧跳过 → 直连设备 (卷帘 1F4A RR×4) 在拓扑消失
        if rr is None:
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


def extract_route_request_events(packets: list[dict]) -> list[RouteEvent]:
    """从 tshark 解析的包列表中提取所有 Route Request 事件.

    Route Request 是协调器主动向目标设备发起的下行路径探测.
    从 NWK Command Frame 中提取 destination、cost、many-to-one 标志等.
    """
    events: list[RouteEvent] = []
    for p in packets:
        if p.get("pkt_type") != "Route Request":
            continue
        src = p.get("nwk_src")
        if src is None:
            continue
        nwk = p.get("raw_layers", {}).get("zbee_nwk", {})
        cmd_data = _get_command_data(nwk, "Route Request")
        if cmd_data:
            dst = _h(cmd_data.get("zbee_nwk.cmd.route.dest", ""))
            cost = int(cmd_data.get("zbee_nwk.cmd.route.cost", "0"), 16)
        else:
            # cubx 路径: raw_layers 为空 (cubx_reader 不构造), 回退已解析载荷
            # route_req = {options, id, dest, cost} (cubx_reader._parse_route_request)
            rr = p.get("route_req")
            if not rr or rr.get("dest") is None:
                continue
            dst = rr["dest"]
            cost = rr.get("cost") or 0
        if dst is None:
            continue
        radius = p.get("nwk_radius", 0) or 0
        events.append(RouteEvent(
            timestamp=p["ts"],
            event_type=EVENT_ROUTE_REQUEST,
            src=src,
            dst=dst,
            radius=radius,
            dropped=False,  # passive sniffer can't directly observe drops; Phase 3
            pan=p.get("pan_src") or p.get("pan_dst"),
            packet_id=_get_packet_id(p),
        ))
    return events


def extract_network_status_events(packets: list[dict]) -> list[RouteEvent]:
    """从 tshark 解析的包列表中提取所有 Network Status 事件.

    Network Status 报告下行源路由失败——在哪跳因为什么原因断了.
    status_code 含义: 0x00=No Route, 0x01=Tree Link Failure, 0x0C=Many-to-One Failure 等.
    """
    events: list[RouteEvent] = []
    for p in packets:
        if p.get("pkt_type") != "Network Status":
            continue
        src = p.get("nwk_src")
        if src is None:
            continue
        nwk = p.get("raw_layers", {}).get("zbee_nwk", {})
        cmd_data = _get_command_data(nwk, "Network Status")
        if cmd_data:
            dst = p.get("nwk_dst")
            sc_raw = cmd_data.get("zbee_nwk.cmd.status", "")
            status_code = int(sc_raw, 16) if sc_raw else None
        else:
            # cubx 路径: raw_layers 为空, 回退已解析字段 (nwk_status_code/nwk_status_target)
            dst = p.get("nwk_dst") or p.get("nwk_status_target")
            status_code = p.get("nwk_status_code")
        if dst is None:
            continue
        events.append(RouteEvent(
            timestamp=p["ts"],
            event_type=EVENT_NETWORK_STATUS,
            src=src,
            dst=dst,
            status_code=status_code,
            pan=p.get("pan_src") or p.get("pan_dst"),
            packet_id=_get_packet_id(p),
        ))
    return events


def extract_leave_events(packets: list[dict]) -> list[RouteEvent]:
    """从 tshark 解析的包列表中提取所有 NWK Leave 事件.

    NWK Leave (cmd_id=0x04) 的语义:
      rejoin: 0=永久离开不复返, 1=离开后重入网
      request: 0=命令对方离开(踢设备), 1=申请自己离开
      children: 0=保留子节点, 1=连同子节点一起移出
    """
    events: list[RouteEvent] = []
    for p in packets:
        if p.get("pkt_type") != "Leave":
            continue
        src = p.get("nwk_src")
        dst = p.get("nwk_dst")
        if src is None:
            continue
        # ⚠️ 2026-08-05 修复: 部分设备自发 Leave 帧 cubx 解析 nwk_dst=None (解析缺口待查),
        # 此前被丢弃 → 离线诊断漏报设备离网 (中继包 6 条: B75C/F67F/737D/838D)。
        # 设备离网信号以 src 为准, dst 宽容按广播语义处理。
        if dst is None:
            dst = 0xFFFD  # Leave Announcement 广播语义 (宽容, 待查 cubx_reader 缺口)
        # Leave 标志: 兼容 tshark (raw_layers Command Frame 树) 与 cubx (平铺 nwk_leave_*)
        # ⚠️ 2026-08-05 修复: 此前仅 tshark 路径可用, cubx 素材 Leave 事件全丢 → 离线诊断失效
        nwk = p.get("raw_layers", {}).get("zbee_nwk", {})
        cmd_data = _get_command_data(nwk, "Leave")
        if cmd_data:
            rejoin = cmd_data.get("zbee_nwk.cmd.leave.rejoin", "0") == "1"
            request = cmd_data.get("zbee_nwk.cmd.leave.request", "0") == "1"
            remove_children = cmd_data.get("zbee_nwk.cmd.leave.children", "0") == "1"
        else:
            rejoin = p.get("nwk_leave_rejoin") == 1
            request = p.get("nwk_leave_request") == 1
            remove_children = p.get("nwk_leave_children") == 1
        # EUI64 从 NWK 层 source EUI64 提取 (被踢设备可能没发过 Device Announce)
        eui64 = None
        nwk_src64_str = p.get("nwk_src64", "")
        if nwk_src64_str and len(nwk_src64_str) == 16:
            try: eui64 = int(nwk_src64_str, 16)
            except ValueError: pass

        events.append(RouteEvent(
            timestamp=p["ts"],
            event_type=EVENT_LEAVE,
            src=src, dst=dst,
            rejoin=rejoin,
            request=request,
            remove_children=remove_children,
            eui64=eui64,
            pan=p.get("pan_src") or p.get("pan_dst"),
            packet_id=_get_packet_id(p),
        ))
    return events


def extract_device_announce_events(packets: list[dict]) -> list[RouteEvent]:
    """从 tshark 解析的包列表中提取所有 Device Announce 事件 (ZDP 0x0013).

    数据来源: ZDP cluster=0x0013, profile=0x0000.
    提供短地址 → EUI64 映射 (设备身份证).
    解析 EUI64 时注意字节序: ZDP payload 中 EUI64 为 little-endian.
    """
    events: list[RouteEvent] = []
    for p in packets:
        if "Device Announce" not in (p.get("pkt_type") or ""):
            continue
        src = p.get("nwk_src")
        dst = p.get("nwk_dst")
        if src is None:
            continue
        eui64_str = p.get("nwk_src64")
        eui64 = None
        if eui64_str and len(eui64_str) == 16:
            try:
                eui64 = int(eui64_str, 16)
            except ValueError:
                pass
        events.append(RouteEvent(
            timestamp=p["ts"],
            event_type=EVENT_DEVICE_ANNOUNCE,
            src=src, dst=dst or 0xFFFD,
            eui64=eui64,
            pan=p.get("pan_src") or p.get("pan_dst"),
            packet_id=_get_packet_id(p),
        ))
    return events


def extract_ieee_addr_req_events(packets: list[dict]) -> list[RouteEvent]:
    """从 tshark 解析的包列表中提取 IEEE Addr Req 事件 (ZDP 0x0001).

    协调器在离网前密集查询设备 IEEE 地址 —— 作为离网的前置行为标记.
    """
    events: list[RouteEvent] = []
    for p in packets:
        if p.get("pkt_type") != "ZDP: IEEE Addr Req":
            continue
        src = p.get("nwk_src")
        dst = p.get("nwk_dst")
        if src is None or dst is None:
            continue
        events.append(RouteEvent(
            timestamp=p["ts"],
            event_type=EVENT_IEEE_ADDR_REQ,
            src=src, dst=dst,
            pan=p.get("pan_src") or p.get("pan_dst"),
            packet_id=_get_packet_id(p),
        ))
    return events


def extract_events(packets: list[dict], suppress_duplicates: bool = True) -> list[RouteEvent]:
    """统一提取: 所有路由事件, 可选重复帧抑制."""
    events: list[RouteEvent] = []
    events.extend(extract_route_record_events(packets))
    events.extend(extract_route_request_events(packets))
    events.extend(extract_network_status_events(packets))
    events.extend(extract_leave_events(packets))
    events.extend(extract_device_announce_events(packets))
    events.extend(extract_ieee_addr_req_events(packets))
    events.sort(key=lambda e: e.timestamp)

    if suppress_duplicates and events:
        deduped: list[RouteEvent] = []
        recent: dict[tuple, float] = {}
        for e in events:
            if e.event_type == EVENT_ROUTE_RECORD:
                key = (e.event_type, e.src, e.dst, tuple(e.relays))
            else:
                key = (e.event_type, e.src, e.dst)
            last_ts = recent.get(key)
            if last_ts is not None and e.timestamp - last_ts <= 0.020:
                continue
            recent[key] = e.timestamp
            deduped.append(e)
        return deduped

    return events


# ── Topology Derivation ──

def derive_topology(timeline: RouteEventTimeline,
                    nodes: dict[int, dict],
                    pan: int | None = None,
                    t0: float | None = None,
                    t1: float | None = None,
                    link_status_tables: dict | None = None,
                    asymmetric_links: list[dict] | None = None,
                    ) -> dict:
    """从事件时间线推导拓扑图, 输出格式兼容 topology.build().

    Phase 2 加入 Route Request (下行探测) 和 Network Status (下行失败):
      route_paths    — Route Record 上行实证路径
      route_probes   — Route Request 下行探测记录
      route_failures — Network Status 下行失败定位
    Phase 3: 接受外部构建的 link_status_tables + asymmetric_links (非事件数据).
    """
    rr_events = timeline.query(t0, t1, [EVENT_ROUTE_RECORD])
    req_events = timeline.query(t0, t1, [EVENT_ROUTE_REQUEST])
    ns_events = timeline.query(t0, t1, [EVENT_NETWORK_STATUS])

    # ── 主 PAN 自动选择 + 过滤 (2026-08-25 修复: 曾在过滤后赋值 → pan=None 时不过滤,
    # 多 PAN 聚合抓包全部混杂显示; 每 PAN 协调器都是 0x0000, 混在一起拓扑错乱) ──
    if pan is None:
        _pan_counts: defaultdict = defaultdict(int)
        for e in rr_events + req_events + ns_events:
            if e.pan:
                _pan_counts[e.pan] += 1
        if _pan_counts:
            pan = max(_pan_counts, key=_pan_counts.get)

    if pan is not None:
        rr_events = [e for e in rr_events if e.pan == pan]
        req_events = [e for e in req_events if e.pan == pan]
        ns_events = [e for e in ns_events if e.pan == pan]

    # ── Route Paths (上行实证) ──
    path_meta: dict[tuple, dict] = {}
    for e in rr_events:
        dedup_key = (e.src, tuple(e.relays), e.dst)
        if dedup_key in path_meta:
            meta = path_meta[dedup_key]
            meta["first_ts"] = min(meta["first_ts"], e.timestamp)
            meta["last_ts"] = max(meta["last_ts"], e.timestamp)
            meta["frame_count"] += 1
        else:
            path_meta[dedup_key] = {
                "first_ts": e.timestamp, "last_ts": e.timestamp, "frame_count": 1,
            }

    route_paths = []
    for (src, relays_tuple, dst), meta in path_meta.items():
        relays = list(relays_tuple)
        full_path = [src] + relays + [dst]
        path_str = " → ".join(f"0x{a:04X}" for a in full_path)
        active = not ((t0 is not None and meta["last_ts"] < t0)
                      or (t1 is not None and meta["first_ts"] > t1))
        route_paths.append({
            "src": src, "dst": dst, "relays": relays,
            "hop_count": len(relays) + 1,
            "path_str": path_str,
            "first_ts": meta["first_ts"], "last_ts": meta["last_ts"],
            "frame_count": meta["frame_count"],
            "is_current": True, "active": active,
            "direction": "upstream_proven",
        })

    route_paths.sort(key=lambda x: x["first_ts"])
    src_latest: dict[int, float] = {}
    for rp in route_paths:
        s = rp["src"]
        if s not in src_latest or rp["first_ts"] > src_latest[s]:
            src_latest[s] = rp["first_ts"]
    for rp in route_paths:
        rp["is_current"] = (rp["first_ts"] == src_latest.get(rp["src"]))

    # ── Route Probes (下行探测) ──
    probe_meta: dict[tuple, dict] = {}
    for e in req_events:
        dedup_key = (e.src, e.dst)
        if dedup_key in probe_meta:
            pmeta = probe_meta[dedup_key]
            pmeta["first_ts"] = min(pmeta["first_ts"], e.timestamp)
            pmeta["last_ts"] = max(pmeta["last_ts"], e.timestamp)
            pmeta["count"] += 1
        else:
            probe_meta[dedup_key] = {
                "first_ts": e.timestamp, "last_ts": e.timestamp,
                "count": 1, "radius": e.radius or 0,
            }
    route_probes = []
    for (src, dst), pmeta in probe_meta.items():
        active = not ((t0 is not None and pmeta["last_ts"] < t0)
                      or (t1 is not None and pmeta["first_ts"] > t1))
        route_probes.append({
            "src": src, "dst": dst,
            "path_str": f"0x{src:04X} → 0x{dst:04X} (radius={pmeta['radius']})",
            "first_ts": pmeta["first_ts"], "last_ts": pmeta["last_ts"],
            "count": pmeta["count"], "radius": pmeta["radius"],
            "active": active,
            "direction": "downstream_probed",
        })
    route_probes.sort(key=lambda x: x["first_ts"])

    # ── Route Failures (下行失败) ──
    route_failures = []
    for e in ns_events:
        active = not ((t0 is not None and e.timestamp < t0)
                      or (t1 is not None and e.timestamp > t1))
        route_failures.append({
            "src": e.src, "dst": e.dst,
            "status_code": e.status_code,
            "status_name": _status_name(e.status_code),
            "path_str": f"0x{e.src:04X} → 0x{e.dst:04X} [status=0x{e.status_code:02X}]",
            "timestamp": e.timestamp,
            "active": active,
            "direction": "downstream_failed",
        })

    # ── PAN 统计 ──
    pan_counts = defaultdict(int)
    active_aids: set[int] = set()
    for e in rr_events:
        if e.pan: pan_counts[e.pan] += 1
        active_aids.add(e.src); active_aids.add(e.dst)
        active_aids.update(e.relays)
    for e in req_events:
        if e.pan: pan_counts[e.pan] += 1
        active_aids.add(e.src); active_aids.add(e.dst)
    for e in ns_events:
        if e.pan: pan_counts[e.pan] += 1
        active_aids.add(e.src); active_aids.add(e.dst)
    main_pan = max(pan_counts, key=pan_counts.get) if pan_counts else None
    if pan is None and main_pan is not None:
        pan = main_pan

    # ── 节点 ──
    node_list = []
    for aid in sorted(active_aids):
        if not is_unicast(aid):
            continue  # 广播地址 (RREQ dst=0xFFFC 广播探测) 不当节点
        n = nodes.get(aid, {})
        node_list.append({
            "aid": aid, "label": f"0x{aid:04X}",
            "seen": n.get("seen", 0), "pan": pan,
            "is_coord": aid == 0, "depth": -1,
            "parent": None, "children": [], "coord_traffic": 0,
            "type_list": n.get("type_list", [])[:10],
            "device_type": n.get("device_type", "unknown"),
        })

    # ── 边: Route Record 逐跳 ──
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
                        "src": s, "dst": d, "count": 1,
                        "success_rate": 1.0,
                        "is_link_status": False, "is_parent_child": False,
                    })

    pan_list = [{"pan": p, "count": c, "label": f"0x{p:04X}"}
                for p, c in sorted(pan_counts.items(), key=lambda x: -x[1])[:50]]

    return {
        "pan_list": pan_list,
        "nodes": node_list, "edges": edge_list,
        "coord": 0, "main_pan": main_pan,
        "pans": sorted(pan_counts.keys()),
        "tree_depths": {}, "tree_node_count": len(active_aids),
        "leaf_count": 0, "total_nodes": len(nodes),
        "total_edges": len(edge_list), "parents": {},
        "neighbor_tables": link_status_tables or {},
        "route_paths": route_paths,
        "route_probes": route_probes,
        "route_failures": route_failures,
        "asymmetric_links": asymmetric_links or [],
    }


def _status_name(code: int | None) -> str:
    """Network Status 失败码 → 可读名称."""
    if code is None:
        return "unknown"
    names = {
        0x00: "No Route Available",
        0x01: "Tree Link Failure",
        0x02: "Non-Tree Link Failure",
        0x03: "Low Battery",
        0x04: "No Routing Capacity",
        0x05: "No Indirect Capacity",
        0x06: "Indirect Transaction Expiry",
        0x07: "Target Device Unavailable",
        0x08: "Target Address Unallocated",
        0x09: "Parent Link Failure",
        0x0A: "Validate Route",
        0x0B: "Source Route Failure",
        0x0C: "Many-to-One Route Failure",
        0x0D: "Address Conflict",
        0x0E: "Verify Addresses",
        0x0F: "PAN Identifier Update",
        0x10: "Network Address Update",
        0x11: "Bad Frame Counter",
        0x12: "Bad Key Sequence Number",
    }
    return names.get(code, f"Unknown(0x{code:02X})")


# ── 诊断聚合 ──

LEAVE_BURST_WINDOW = 5.0       # Leave 帧合并为波次的时间窗口 (秒)
REJOIN_DETECTION_WINDOW = 30.0  # Leave 后检测 Device Announce 的时间窗口 (秒)


def aggregate_offline_diagnosis(
    timeline: RouteEventTimeline,
    nodes: dict[int, dict] | None = None,
    pan: int | None = None,
    t0: float | None = None,
    t1: float | None = None,
) -> dict:
    """从事件时间线聚合设备离线诊断数据.

    流程:
      1. 提取 Leave + Device Announce + Network Status 事件
      2. 按设备分组
      3. Leave 帧按 5s 窗口合并为 bursts
      4. Leave 后 30s 内 Device Announce → rejoin_attempt
      5. 生成每个设备的诊断结论
    """
    leave_events = timeline.query(t0, t1, [EVENT_LEAVE])
    announce_events = timeline.query(t0, t1, [EVENT_DEVICE_ANNOUNCE])
    ns_events = timeline.query(t0, t1, [EVENT_NETWORK_STATUS])
    ieee_events = timeline.query(t0, t1, [EVENT_IEEE_ADDR_REQ])

    if pan is not None:
        leave_events = [e for e in leave_events if e.pan == pan]
        announce_events = [e for e in announce_events if e.pan == pan]
        ns_events = [e for e in ns_events if e.pan == pan]
        ieee_events = [e for e in ieee_events if e.pan == pan]

    if not leave_events:
        return {
            "devices": [],
            "summary": {"total_devices_left": 0, "kicked": 0,
                        "voluntary": 0, "with_rejoin": 0},
            "conclusion": "未发现设备离网事件 (当前抓包没有 NWK Leave 帧)",
            "evidence": [],
            "evidence_total": 0,
        }

    # 按设备分组 Leave 事件
    # ⚠️ 2026-08-05 修复: 排除 src=0x0000 (TC/协调器) — TC 的 Leave 帧全是管理指令
    # (TC→设备 单播, 如中继包 TC→0x737D ×336), 不是 TC 自己离开; 误归导致
    # 协调器被报为"17 波主动暂离" (用户实测发现)
    device_leaves: dict[int, list[RouteEvent]] = {}
    for e in leave_events:
        if e.src == 0x0000:
            continue
        device_leaves.setdefault(e.src, []).append(e)

    devices = []
    for aid, leaves in sorted(device_leaves.items()):
        leaves.sort(key=lambda e: e.timestamp)

        # Burst 检测 (5s 窗口)
        bursts = []
        current_burst = [leaves[0]]
        for e in leaves[1:]:
            if e.timestamp - current_burst[-1].timestamp <= LEAVE_BURST_WINDOW:
                current_burst.append(e)
            else:
                bursts.append(current_burst)
                current_burst = [e]
        bursts.append(current_burst)

        burst_data = []
        for bi, burst in enumerate(bursts):
            first = burst[0]
            bd = {
                "first_ts": burst[0].timestamp,
                "last_ts": burst[-1].timestamp,
                "count": len(burst),
                "rejoin": first.rejoin,
                "request": first.request,
                "children": first.remove_children,
                "type": _leave_type_name(first),
                "burst_index": bi + 1,
            }
            burst_data.append(bd)

        # Rejoin 检测: Leave 后 REJOIN_DETECTION_WINDOW 秒内的 Device Announce
        rejoin_attempts = []
        for bi, burst in enumerate(bursts):
            burst_end = burst[-1].timestamp
            matching_anns = [e for e in announce_events
                             if e.src == aid
                             and burst_end < e.timestamp <= burst_end + REJOIN_DETECTION_WINDOW]
            if matching_anns:
                rejoin_attempts.append({
                    "after_burst": bi + 1,
                    "announce_count": len(matching_anns),
                    "first_ts": matching_anns[0].timestamp,
                    "last_ts": matching_anns[-1].timestamp,
                    "delay_seconds": round(matching_anns[0].timestamp - burst_end, 1),
                })

        # 前置事件: Leave 前 NS + IEEE Addr Req
        pre_ns = [e for e in ns_events if e.src == aid and e.timestamp < bursts[0][0].timestamp]
        pre_ieee = [e for e in ieee_events if e.dst == aid and e.timestamp < bursts[0][0].timestamp]

        # 诊断结论 + 设备身份
        announce_for_device = [e for e in announce_events if e.src == aid]
        node_info = (nodes or {}).get(aid, {})
        dt = node_info.get("device_type", "router") or "router"

        # EUI64: Device Announce 优先, Leave帧的nwk_src64作为fallback
        eui64_hex = None
        if announce_for_device and announce_for_device[0].eui64:
            eui64_hex = f"{announce_for_device[0].eui64:016x}"
        else:
            for e in leaves:
                if e.eui64:
                    eui64_hex = f"{e.eui64:016x}"
                    break

        last_burst = bursts[-1]
        has_rejoin = len(rejoin_attempts) > 0

        devices.append({
            "aid": aid,
            "label": f"0x{aid:04X}",
            "eui64": eui64_hex,
            "device_type": dt,
            "leave_bursts": burst_data,
            "rejoin_attempts": rejoin_attempts,
            "pre_events": {
                "network_status_count": len(pre_ns),
                "ieee_addr_req_count": len(pre_ieee),
                "first_ns_ts": pre_ns[0].timestamp if pre_ns else None,
                "first_ieee_ts": pre_ieee[0].timestamp if pre_ieee else None,
            },
            "diagnosis": _build_diagnosis(burst_data, rejoin_attempts,
                                          not bool([e for e in announce_events
                                                     if e.src == aid
                                                     and e.timestamp > last_burst[-1].timestamp
                                                     + REJOIN_DETECTION_WINDOW])),
        })

    # 汇总
    summary = {
        "total_devices_left": len(devices),
        "kicked": sum(1 for d in devices if d["diagnosis"]["leave_type"] == "kicked"),
        "voluntary": sum(1 for d in devices
                         if d["diagnosis"]["leave_type"] in ("voluntary_permanent", "voluntary_rejoin")),
        "with_rejoin": sum(1 for d in devices if d["diagnosis"]["has_rejoin_attempt"]),
    }

    # 结论 (简短易懂, 诚实) + 证据表 (人工复核, 2026-08-05 需求)
    if devices:
        conclusion = (f"{len(devices)} 台设备离网: {summary['kicked']} 台被踢, "
                      f"{summary['voluntary']} 台主动离开, {summary['with_rejoin']} 台尝试重入")
    else:
        conclusion = "未发现设备离网事件"
    evidence = []
    for e in leave_events[:8]:
        evidence.append({"ts": round(e.timestamp, 3), "packet_id": None, "type": "NWK Leave",
                         "detail": f"0x{e.src:04X} → 0x{e.dst:04X}"})
    for e in announce_events[:4]:
        evidence.append({"ts": round(e.timestamp, 3), "packet_id": None, "type": "Device Announce",
                         "detail": f"0x{e.src:04X} → 广播"})
    evidence_total = len(evidence)
    evidence = evidence[:15]

    return {"devices": devices, "summary": summary,
            "conclusion": conclusion, "evidence": evidence,
            "evidence_total": evidence_total}


def _leave_type_name(event: RouteEvent) -> str:
    """Leave 标志组合 → 类型名."""
    if event.request:
        return "voluntary_rejoin" if event.rejoin else "voluntary_permanent"
    else:
        return "kicked_rejoin" if event.rejoin else "kicked"


def _build_diagnosis(bursts: list[dict], rejoin_attempts: list[dict],
                     final_departed: bool) -> dict:
    """根据 burst 和 rejoin 数据生成诊断结论."""
    first = bursts[0]
    leave_type = first["type"]
    has_rejoin = len(rejoin_attempts) > 0
    final_status = "departed_permanently" if final_departed else "possibly_rejoined"

    # 生成可读摘要
    type_names = {"kicked": "被踢出网络", "kicked_rejoin": "被踢(允许重入)",
                  "voluntary_permanent": "主动永久离网", "voluntary_rejoin": "主动暂离"}
    parts = [type_names.get(leave_type, leave_type)]
    if has_rejoin:
        delays = [str(r["delay_seconds"]) + "s" for r in rejoin_attempts]
        parts.append(f"有重入网尝试 ({', '.join(delays)}后)")
    if len(bursts) > 1:
        parts.append(f"{len(bursts)}波离网")
    if final_departed:
        parts.append("最终彻底离开")
    else:
        parts.append("最终可能已重入网")

    return {
        "leave_type": leave_type,
        "has_rejoin_attempt": has_rejoin,
        "final_status": final_status,
        "burst_count": len(bursts),
        "summary": "，".join(parts),
    }
