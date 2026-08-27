"""拓扑 + 节点 API"""
import json

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from .files import get_packets, get_nodes, get_full_packets, _detail_dict
from .. import topology as topo
from .. import route_events as rev
from .. import zcl_defs

router = APIRouter()

# 全局事件时间线 (从导入的 packets 构建, packets 变化时重建)
_events_timeline: rev.RouteEventTimeline | None = None
_events_packet_count: int = 0  # 用于检测 packets 是否变化
_cache_ls_tables: dict | None = None  # Link Status 邻居表缓存
_cache_ls_key: tuple | None = None    # 邻居表缓存键 (包数, pan, t0, t1)
_cache_asym: list | None = None       # 不对称链路缓存
_cache_events: dict | None = None     # S3 (2026-08-27): events 端点整体缓存 (O(full)×4 重算)
_cache_events_key: tuple | None = None  # 缓存键 (pkts 数, full 数, pan, t0, t1)


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


def _behavior_map(full: list[dict], t0: float | None, t1: float | None) -> tuple[dict, float | None]:
    """单遍扫描节点行为信息 (U14): 每节点窗内 最后帧时间 / poll 间隔中位数 /
    rejoin 事件标记。late_cut = 窗末 25% 起点 (离线判定用)。

    依据: poll = MAC Data Request (mac_cmd_id=4, 仅 full_packets 含 MAC 帧);
    rejoin 事件 = NWK cmd 6/7 (Rejoin Req/Rsp) / ZDP 0x0013 (Device Announce) /
    MAC AssocResp (mac_cmd_id=2)。窗内语义 (无过滤 = 全量)。
    """
    info: dict[int, dict] = {}
    lo, hi = t0, t1
    if lo is None or hi is None:
        ts_all = [p.get("ts", 0) for p in full if p.get("ts")]
        if ts_all:
            lo = t0 if t0 is not None else min(ts_all)
            hi = t1 if t1 is not None else max(ts_all)
    late_cut = None
    if lo is not None and hi is not None and hi > lo:
        late_cut = lo + (hi - lo) * 0.75
    for p in full:
        ts = p.get("ts", 0)
        if t0 is not None and ts < t0:
            continue
        if t1 is not None and ts > t1:
            continue
        srcs = {p.get("nwk_src"), p.get("mac_src")} - {None}
        dsts = {p.get("nwk_dst"), p.get("mac_dst")} - {None}
        for aid in srcs | dsts:
            if not topo.is_unicast(aid):
                continue
            inf = info.setdefault(aid, {"last": None, "poll": [], "rejoin": False,
                                        "tx": 0, "rx": 0})
            if ts > (inf["last"] or 0):
                inf["last"] = ts
            if aid in srcs:
                inf["tx"] += 1
            if aid in dsts:
                inf["rx"] += 1
        # poll: 仅发送方 (SED 发 Data Request; 目标父节点不算 poll 间隔)
        if p.get("mac_cmd_id") == 4:
            for aid in srcs:
                if topo.is_unicast(aid):
                    info.setdefault(aid, {"last": None, "poll": [], "rejoin": False})
                    info[aid]["poll"].append(ts)
        # rejoin 事件 (方向语义, 2026-08-24 自审: AssocResp 协调器发出不算协调器重连):
        #   Rejoin Req (6) → src; Rejoin Rsp (7) → dst; Device Announce (0x0013) → src;
        #   AssocResp (mac 2) → dst
        if p.get("nwk_cmd_id") == 6 or p.get("aps_cluster") == 0x0013:
            for aid in srcs:
                if topo.is_unicast(aid):
                    info.setdefault(aid, {"last": None, "poll": [], "rejoin": False})
                    info[aid]["rejoin"] = True
        elif p.get("nwk_cmd_id") == 7 or p.get("mac_cmd_id") == 2:
            for aid in dsts:
                if topo.is_unicast(aid):
                    info.setdefault(aid, {"last": None, "poll": [], "rejoin": False})
                    info[aid]["rejoin"] = True
    out: dict[int, dict] = {}
    for aid, inf in info.items():
        gap = None
        if len(inf["poll"]) >= 2:
            poll_ts = sorted(inf["poll"])
            gaps = [b - a for a, b in zip(poll_ts, poll_ts[1:]) if b > a]
            if gaps:
                gaps.sort()
                gap = gaps[len(gaps) // 2]
        out[aid] = {"last": inf["last"], "poll_gap": gap,
                    "poll_count": len(inf["poll"]), "rejoin": inf["rejoin"],
                    "tx": inf.get("tx", 0), "rx": inf.get("rx", 0)}
    return out, late_cut


def _behavior_of(aid: int, inf: dict | None, late_cut: float | None,
                 device_type: str | None) -> str:
    """行为状态判定 (优先级: 重连中 > 离线 > 休眠 > 活跃; 无信息 = unknown)."""
    if inf is None:
        return "unknown"
    if aid == 0:
        return "active"  # 协调器是网络中心, 不适用休眠/离线/重连语义
    if inf["rejoin"]:
        return "rejoining"
    if inf["last"] is not None and late_cut is not None and inf["last"] < late_cut:
        return "offline"          # 窗后段 (末 25%) 无帧且此前有
    if device_type == "end_device" and inf["poll_count"] == 0:
        return "sleeping"         # 终端且窗内无 poll
    if inf["last"] is not None:
        return "active"
    return "unknown"


def _parent_map(full: list[dict], t0: float | None, t1: float | None,
                pan_int: int | None = None) -> dict:
    """U13: 协议级父链路证据 (单遍扫描, 窗内语义).

    - poll: MAC Data Request (mac_cmd_id=4) dst = 父节点 (芯科: SED 只向父 poll)
    - assoc: MAC AssocResp (mac_cmd_id=2) src = 父节点, dst = 入网设备
    只接受短地址 (mac_src/dst 长地址为 EUI64 字符串, 与节点短地址 key 不对应).
    后到证据覆盖先到 (父节点可能变化: 重入/切换).
    """
    parents: dict[int, dict] = {}

    def _short(v) -> int | None:
        return v if isinstance(v, int) and topo.is_unicast(v) else None

    for p in full:
        ts = p.get("ts", 0)
        if t0 is not None and ts < t0:
            continue
        if t1 is not None and ts > t1:
            continue
        if pan_int is not None and (p.get("pan_src") != pan_int and p.get("pan_dst") != pan_int):
            continue
        if p.get("mac_cmd_id") == 4:
            s, d = _short(p.get("mac_src")), _short(p.get("mac_dst"))
            if s is not None and d is not None:
                parents[s] = {"parent": d, "evidence": "poll"}
        elif p.get("mac_cmd_id") == 2:
            s, d = _short(p.get("mac_src")), _short(p.get("mac_dst"))
            if s is not None and d is not None:
                parents[d] = {"parent": s, "evidence": "assoc"}
    return parents


# ── S3-重构 (2026-08-27, 用户对齐: 上行链路为准构建拓扑) ──
# 链路证据四来源, 上行优先:
#   poll  MAC Data Request — src 的父 = dst (SED 只向父 poll, 铁证)
#   assoc MAC AssocResp — dst 的父 = src (入网时刻)
#   rr    Route Record — src→relays[0]→…→dst 全链下一跳 = 父 (上行实证)
#   down  源路由帧 (nwk_relays 非空) — chain=[src]+relays+[dst],
#         每个节点的父 = 链上前一个 (网关下行证据, 参与父子判定不上图)
# 优先级 poll > assoc > rr > down; 同优先级取最近。
_EVIDENCE_PRIO = {"poll": 0, "assoc": 1, "rr": 2, "down": 3}
_EVIDENCE_WINDOW = 30.0  # 证据窗 (秒); 窗内无证据 → 顺延前 30s (用户对齐)


def _link_evidence_parent(full: list[dict], t0: float | None, t1: float | None,
                          pan_int: int | None = None) -> dict:
    """四来源链路证据 → 每节点上行父 (证据窗 = [t0-30s, t1], 顺延前 30s).

    返回 {aid: {parent, evidence, ts}} — 每节点最高优先级 + 最近证据。
    用于节点 parent 字段 (U13 语义扩展: 原 poll/assoc 两来源 → 四来源).
    """
    ev: dict[int, tuple] = {}  # aid -> (priority, ts, parent, evidence)

    def _short(v):
        return v if isinstance(v, int) and topo.is_unicast(v) else None

    def _put(aid: int, prio: int, ts: float, parent: int, evidence: str) -> None:
        if aid == 0:
            return  # 协调器是根, 无父
        cur = ev.get(aid)
        if cur is None or prio < cur[0] or (prio == cur[0] and ts > cur[1]):
            ev[aid] = (prio, ts, parent, evidence)

    lo = (t0 - _EVIDENCE_WINDOW) if t0 is not None else None  # 顺延前 30s
    for p in full:
        ts = p.get("ts", 0)
        if lo is not None and ts < lo:
            continue
        if t1 is not None and ts > t1:
            continue
        if pan_int is not None and (p.get("pan_src") != pan_int and p.get("pan_dst") != pan_int):
            continue
        if p.get("mac_cmd_id") == 4:  # poll
            s, d = _short(p.get("mac_src")), _short(p.get("mac_dst"))
            if s is not None and d is not None:
                _put(s, _EVIDENCE_PRIO["poll"], ts, d, "poll")
        elif p.get("mac_cmd_id") == 2:  # assoc
            s, d = _short(p.get("mac_src")), _short(p.get("mac_dst"))
            if s is not None and d is not None:
                _put(d, _EVIDENCE_PRIO["assoc"], ts, s, "assoc")
        elif p.get("nwk_cmd_id") == 5:  # rr 上行链
            rr = p.get("route_record_relays") or {}
            relays = list(rr.get("relays") or [])
            src, dst = _short(p.get("nwk_src")), _short(p.get("nwk_dst"))
            if src is None or dst is None:
                continue
            chain = [src] + relays + [dst]
            for i in range(len(chain) - 1):
                _put(chain[i], _EVIDENCE_PRIO["rr"], ts, chain[i + 1], "rr")
        elif p.get("nwk_relays"):  # 源路由下行
            relays = list(p.get("nwk_relays") or [])
            s, d = _short(p.get("nwk_src")), _short(p.get("nwk_dst"))
            if s is None or d is None or not relays:
                continue
            chain = [s] + relays + [d]
            for i in range(1, len(chain)):  # 链上每节点父 = 前一个 (coord 本身跳过)
                _put(chain[i], _EVIDENCE_PRIO["down"], ts, chain[i - 1], "down")
    return {aid: {"parent": pr, "evidence": ev_name, "ts": ts}
            for aid, (prio, ts, pr, ev_name) in ev.items()}


def _online_map(full: list[dict], t0: float | None, t1: float | None,
                pan_int: int | None = None, device_types: dict | None = None) -> dict:
    """节点在线协议判定 (用户对齐: 有明确在线证据才正常渲染).

    - 终端 (end_device): 窗内有 poll (Data Request, src=自己) → 在线
    - 路由器/协调器/未知: 窗内有任何帧 (src/dst 含自己) → 在线
    - 无时间窗 (全量) → 全在线 (都出现过)
    返回 {aid: bool}。根因: 旧 inactive_nodes 基于事件集 (RR/Req/NS),
    终端持续 poll 不算事件 → 窗内活跃却被灰显 (用户反馈问题大)。
    """
    if t0 is None and t1 is None:
        return {}
    online: dict[int, bool] = {}
    seen_frame: dict[int, bool] = {}
    polled: set[int] = set()
    for p in full:
        ts = p.get("ts", 0)
        if t0 is not None and ts < t0:
            continue
        if t1 is not None and ts > t1:
            continue
        if pan_int is not None and (p.get("pan_src") != pan_int and p.get("pan_dst") != pan_int):
            continue
        if p.get("mac_cmd_id") == 4:
            s = p.get("mac_src")
            if isinstance(s, int) and topo.is_unicast(s):
                polled.add(s)
        for aid in (p.get("nwk_src"), p.get("nwk_dst"),
                    p.get("mac_src"), p.get("mac_dst")):
            if isinstance(aid, int) and topo.is_unicast(aid):
                seen_frame[aid] = True
    for aid in seen_frame:
        if (device_types or {}).get(aid) == "end_device":
            online[aid] = aid in polled  # 终端: 必须有 poll 证据
        else:
            online[aid] = True            # 路由/未知: 任何帧即在线
    return online


def _all_link_segments(full: list[dict], t0: float | None, t1: float | None,
                       max_gap: float = 30.0, pan_int: int | None = None) -> dict:
    """全图链路时刻分段 (U13 时刻游标重构, 2026-08-25): 单遍扫描每节点
    RR 路径 / poll 父 / assoc 父 / 源路由下行 的证据帧 → 分段
    (签名变化或 >max_gap 间隔 → 新段).
    返回 {aid: [ {kind, t0, t1, relays, dst, parent, evidence}, ... ]}
    T 时刻节点链路状态 = 分段中 t0<=T 的最近一段, 且 T-段末 <= 证据窗+顺延
    (前端 30s 窗语义, S3-重构 2026-08-27: 证据窗 30s + 顺延前 30s).

    S3 变更: ①max_gap 默认 60→30 (与证据窗一致, 用户对齐)
    ②加 assoc 父证据 ③加源路由下行证据 (nwk_relays, 仅作父子判定不上图)
    ④段带 evidence 字段 (poll/assoc/rr/down)."""
    frames: dict[int, list] = {}
    for p in full:
        ts = p.get("ts", 0)
        if t0 is not None and ts < t0:
            continue
        if t1 is not None and ts > t1:
            continue
        if pan_int is not None and (p.get("pan_src") != pan_int and p.get("pan_dst") != pan_int):
            continue
        if p.get("nwk_cmd_id") == 5 and p.get("nwk_src") is not None:
            rr = p.get("route_record_relays") or {}
            frames.setdefault(p["nwk_src"], []).append(
                (ts, "route", (p.get("nwk_dst"), tuple(rr.get("relays") or []))))
        elif p.get("mac_cmd_id") == 4 and p.get("mac_src") is not None \
                and isinstance(p.get("mac_dst"), int):
            frames.setdefault(p["mac_src"], []).append(
                (ts, "parent", ("parent", p["mac_dst"], "poll")))
        elif p.get("mac_cmd_id") == 2 and p.get("mac_src") is not None \
                and isinstance(p.get("mac_dst"), int):
            frames.setdefault(p["mac_dst"], []).append(
                (ts, "parent", ("parent", p["mac_src"], "assoc")))
        elif p.get("nwk_relays") and isinstance(p.get("nwk_src"), int) \
                and isinstance(p.get("nwk_dst"), int):
            # 源路由下行: chain=[src]+relays+[dst], 每节点父 = 前一个 (下行证据)
            chain = [p["nwk_src"]] + list(p.get("nwk_relays") or []) + [p["nwk_dst"]]
            for i in range(1, len(chain)):
                frames.setdefault(chain[i], []).append(
                    (ts, "parent", ("parent", chain[i - 1], "down")))
    out: dict[int, list] = {}
    for aid, fl in frames.items():
        segs: list[dict] = []
        cur: dict | None = None
        for ts, kind, sig in sorted(fl):
            if cur is None or kind != cur["kind"] or sig != cur["sig"] or ts - cur["t1"] > max_gap:
                if cur:
                    segs.append(cur)
                cur = {"kind": kind, "sig": sig, "t0": ts, "t1": ts}
            else:
                cur["t1"] = ts
        if cur:
            segs.append(cur)
        out[aid] = [{
            "kind": s["kind"], "t0": s["t0"], "t1": s["t1"],
            "relays": list(s["sig"][1]) if s["kind"] == "route" else None,
            "dst": s["sig"][0] if s["kind"] == "route" else None,
            "parent": s["sig"][1] if s["kind"] == "parent" else None,
            "evidence": s["sig"][2] if s["kind"] == "parent" else "rr",
        } for s in segs]
    return out


def _enrich_nodes(graph: dict, pkts: list[dict], pan_int: int | None,
                  t0: float | None, t1: float | None) -> None:
    """U14: 节点身份 (U9 同源统计) + 行为状态 (poll/rejoin 窗内单遍扫描).
    U13: 协议级父链路 (poll/assoc/RR 推断) + 下行 source-route 路径 (relay 反转).
    S3-重构 (2026-08-27): 父证据四来源 (poll>assoc>rr>down, 证据窗+顺延 30s)
    + online 协议判定 (终端 poll / 路由任意帧, 用户对齐).
    graph 与 events 两端点共用 — 拓扑页实际消费 events (2026-08-24 自审)."""
    full = get_full_packets()
    stats, _ls, _asym = _node_stats(pkts, pan_int)
    beh, late_cut = _behavior_map(full if full else pkts, t0, t1)
    parents = _link_evidence_parent(full if full else pkts, t0, t1, pan_int)
    # 在线判定 (协议证据): 终端须窗内有 poll; 路由/未知 = 窗内任意帧
    dev_types = {nd["aid"]: nd.get("device_type", "unknown") for nd in graph.get("nodes", [])}
    online = _online_map(full if full else pkts, t0, t1, pan_int, dev_types)
    # 下行 source-route: [dst] + reversed(relays) + [src] (芯科: concentrator 反转 relay 列表)
    downlink_map: dict[int, list[int]] = {}
    for rp in graph.get("route_paths", []):
        downlink_map[rp["src"]] = [rp["dst"]] + list(reversed(rp["relays"])) + [rp["src"]]
    for nd in graph.get("nodes", []):
        aid = nd["aid"]
        st = stats.get(aid)
        nd["manufacturer_name"] = st["manufacturer_name"] if st else None
        nd["model_id"] = st["model_id"] if st else None
        nd["eui64"] = st["eui64"] if st else None
        inf = beh.get(aid)
        nd["behavior"] = _behavior_of(aid, inf, late_cut, nd.get("device_type"))
        nd["poll_interval"] = inf["poll_gap"] if inf else None
        nd["tx_count"] = inf["tx"] if inf else 0
        nd["rx_count"] = inf["rx"] if inf else 0
        # S3: online 协议判定 — 有时间窗: 窗内无帧节点默认离线 (修复: 曾默认 True,
        # 前 4s 窗 78 节点全在线实锤); 无时间窗: 全在线 (都出现过)
        nd["online"] = online.get(aid, t0 is None and t1 is None)
        # U13: 父链路 (四来源优先级) + 下行路径
        pe = parents.get(aid)
        if pe is not None:
            nd["parent"] = pe["parent"]
            nd["parent_evidence"] = pe["evidence"]
        nd["downlink"] = downlink_map.get(aid)


@router.get("/topology/link-history")
async def link_history(aid: int, pan: str = Query(default=""),
                       time_start: float | None = Query(default=None),
                       time_end: float | None = Query(default=None)):
    """节点链路历史 (U13): RR 路径变更 + poll 父变更的分段时间线.

    每段 = 一段连续时间内稳定的链路证据 (签名变化或 >60s 间隔 → 新段);
    点段可看"当时走哪条链路", 替代播放动画 (用户 08-21 grilling 对齐).
    """
    pkts = get_packets()
    full = get_full_packets() or pkts
    pan_int = int(pan, 16) if pan else None

    segmap = _all_link_segments(full, time_start, time_end, pan_int=pan_int)
    segs = segmap.get(aid, [])
    if not segs:
        return {"aid": aid, "segments": [], "error": "无链路证据帧 (该节点无 RR/poll)"}
    out: list[dict] = []
    for s in segs:
        if s["kind"] == "route":
            path_str = f"0x{aid:04X} → " + (" → ".join(f"0x{r:04X}" for r in s["relays"]) if s["relays"] else "(直连)")
            out.append({"t0": s["t0"], "t1": s["t1"], "kind": "route",
                        "path_str": path_str, "relays": s["relays"], "dst": s["dst"]})
        else:
            out.append({"t0": s["t0"], "t1": s["t1"], "kind": "parent",
                        "path_str": f"父: 0x{s['parent']:04X}", "parent": s["parent"]})
    # ⚠️ S3 修复 (2026-08-27): 原缺 return → 端点恒返回 null → 前端 TypeError "加载失败";
    # 补 return 时契约 = {aid, segments} (前端 d.segments 取用) — 不能返回裸数组
    return {"aid": aid, "segments": out}


@router.get("/topology/graph")
async def topology_graph(pan: str = Query(default=""),
                         time_start: float | None = Query(default=None),
                         time_end: float | None = Query(default=None)):
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"nodes": [], "edges": [], "coord": None}
    pan_int = int(pan, 16) if pan else None
    graph = topo.build(pkts, nodes, filter_pan=pan_int,
                       time_start=time_start, time_end=time_end)
    _enrich_nodes(graph, pkts, pan_int, time_start, time_end)
    return graph


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
    # ⚠️ S3 (2026-08-27): 整体缓存 — 滑块拖动/时间窗切换每次请求都全量重算
    # (_node_stats/_behavior_map/_parent_map/_all_link_segments 均 O(full)),
    # 大包 (179 万帧) 时每个请求数秒; 键含包数/全量数/PAN/时间窗
    global _cache_events, _cache_events_key
    key = (len(pkts), len(get_full_packets() or pkts), pan_int, time_start, time_end)
    if _cache_events is not None and key == _cache_events_key:
        return _cache_events
    timeline = _ensure_events_timeline()
    ls_tables, asym = _build_phase3_supplements(pkts, pan_int, time_start, time_end)
    graph = rev.derive_topology(timeline, nodes, pan=pan_int,
                                t0=time_start, t1=time_end,
                                link_status_tables=ls_tables,
                                asymmetric_links=asym)
    _full_pkts = get_full_packets() or pkts
    # ══ S3-重构 (2026-08-27, 用户对齐: 拓扑绘制原理重梳理) ══
    # ① 节点全量: 时间窗切换节点不消失 (曾窗内事件集 → 下个窗消失/灰显, 用户反馈问题大)
    #    全量节点 = 全量事件节点 ∪ 链路证据帧节点 (poll/assoc/源路由 的参与节点)
    full_graph = rev.derive_topology(timeline, nodes, pan=pan_int)
    node_aids = {nd["aid"] for nd in full_graph["nodes"]}
    ev_nodes = _link_evidence_parent(_full_pkts, None, None, pan_int)
    for aid in ev_nodes:
        if aid in node_aids:
            continue
        n = nodes.get(aid, {})
        full_graph["nodes"].append({
            "aid": aid, "label": f"0x{aid:04X}", "seen": n.get("seen", 0),
            "pan": pan_int if pan_int is not None else n.get("pan"),
            "is_coord": aid == 0, "depth": -1, "parent": None, "children": [],
            "coord_traffic": 0, "type_list": n.get("type_list", [])[:10],
            "device_type": n.get("device_type", "unknown"),
        })
    graph["nodes"] = full_graph["nodes"]
    _enrich_nodes(graph, pkts, pan_int, time_start, time_end)  # U14 身份+行为 + S3 online/父证据
    # ② 链路时刻分段 (30s 窗 + assoc/down 证据): 前端拖动游标纯本地过滤
    graph["link_snapshots"] = _all_link_segments(_full_pkts, time_start, time_end,
                                                 pan_int=pan_int)
    _cache_events = graph
    _cache_events_key = key
    return graph


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


def _node_stats(pkts: list[dict], pan_int: int | None) -> tuple[dict, dict, dict]:
    """单遍扫描节点统计 + 邻居表/不对称 (node_list 与节点画像导出共用).

    每节点: seen/首末 ts/类型计数/LQI/RSSI/EUI64/端点/控制命令统计 (含代表帧索引)。
    clusters key = (cluster, cmd, dir) → {count, cmd_name, first_pkt_id, last_pkt_id}
    (U15: 示例帧 = 最近一帧 last_pkt_id; 导出样本 = first+last 各一帧)
    """
    stats: dict[int, dict] = {}
    for i, p in enumerate(pkts):
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
                     "type_counts": {}, "lqis": [], "rssis": [], "eui64": None,
                     # U9: 端点 / 控制命令统计 / 设备身份 (Basic 属性)
                     "endpoints": {}, "clusters": {},
                     "manufacturer_name": None, "model_id": None}
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
        # ── U9: 端点 / 设备身份 / 控制命令统计 (按帧独立, aid 去重防重复 —
        #    4-aid 循环里 mac_src==nwk_src 时同帧同 aid 会重复计数, 素材实证修正 08-12) ──
        for aid in {p.get("nwk_src"), p.get("nwk_dst")} - {None}:
            s = stats.get(aid)
            if s is None:
                continue
            if aid == p.get("nwk_src"):
                if p.get("aps_src_ep") is not None:
                    ep = p["aps_src_ep"]
                    s["endpoints"][ep] = s["endpoints"].get(ep, 0) + 1
                # Basic 身份: 节点作为响方 (Read Attr Rsp) 的 0x0004/0x0005 首个非空
                if s["manufacturer_name"] is None or s["model_id"] is None:
                    for r in (p.get("zcl_attr_reads") or []):
                        if r["status"] == 0 and isinstance(r["value"], str) and r["value"]:
                            if r["attr_id"] == 0x0004 and s["manufacturer_name"] is None:
                                s["manufacturer_name"] = r["value"]
                            elif r["attr_id"] == 0x0005 and s["model_id"] is None:
                                s["model_id"] = r["value"]
            else:
                if p.get("aps_dst_ep") is not None:
                    ep = p["aps_dst_ep"]
                    s["endpoints"][ep] = s["endpoints"].get(ep, 0) + 1
            # ZCL 命令统计 (cluster, cmd, dir) — 命令名用解析层快照; U15: 记代表帧索引
            if p.get("zcl_cmd_id") is not None:
                key = (p.get("aps_cluster"), p["zcl_cmd_id"], p.get("zcl_direction"))
                if key not in s["clusters"]:
                    s["clusters"][key] = {"count": 0, "cmd_name": p.get("zcl_cmd_name"),
                                          "first_pkt_id": i, "last_pkt_id": i}
                else:
                    s["clusters"][key]["last_pkt_id"] = i
                s["clusters"][key]["count"] += 1

    # 邻居表 + 不对称链路 (Phase 3 已验证逻辑, 含缓存)
    ls_tables, asym = _build_phase3_supplements(pkts, pan_int)
    asym_levels = {frozenset((a["a"], a["b"])): a["level"] for a in asym}
    return stats, ls_tables, asym_levels


@router.get("/nodes")
async def node_list(search: str = Query(default=""), pan: str = Query(default="")):
    """节点列表 + 每节点详情 (U3: 首末时间/类型计数/EUI64/LQI-RSSI/邻居表).

    - EUI64/LQI/RSSI 仅 cubx 导入有 (nwk_src64/lqi/rssi 字段), CSV 返回 None
    - 邻居表复用 _build_phase3_supplements (Link Status 累积, 含不对称标记)
    """
    pkts = get_packets()
    nodes = get_nodes()
    pan_int = int(pan, 16) if pan else None
    stats, ls_tables, asym_levels = _node_stats(pkts, pan_int)

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
        # U9: 端点/命令统计输出 (频率降序)
        endpoints = sorted(st["endpoints"].items(), key=lambda kv: -kv[1]) if st else []
        clusters_out = []
        if st:
            for (cl, cmd, d), v in sorted(st["clusters"].items(), key=lambda kv: -kv[1]["count"]):
                clusters_out.append({
                    "cluster": cl,
                    "cluster_name": zcl_defs.get_cluster_name(cl),
                    "cmd": cmd,
                    "cmd_name": v["cmd_name"],
                    "dir": d,
                    "count": v["count"],
                    # U15: 示例帧 (最近一帧) / 导出样本帧 (最早+最近)
                    "sample_pkt_id": v.get("last_pkt_id"),
                    "first_pkt_id": v.get("first_pkt_id"),
                })
        result.append({
            "aid": aid, "label": label,
            "seen": st["seen"] if st else 0,
            "pan": n["pan"] if not pan_int else pan_int,
            "is_coord": aid == 0,
            "type_list": n["type_list"][:8],
            "device_type": n.get("device_type", "unknown"),
            "manufacturer_name": st["manufacturer_name"] if st else None,
            "model_id": st["model_id"] if st else None,
            "_has_id": bool(st and (st["manufacturer_name"] or st["model_id"])),  # U9 排序键
            "detail": {
                "first_ts": st["first"] if st else None,
                "last_ts": st["last"] if st else None,
                "type_counts": st["type_counts"] if st else {},
                "eui64": st["eui64"] if st else None,
                "lqi": _metric_stats(st["lqis"]) if st else None,
                "rssi": _metric_stats(st["rssis"]) if st else None,
                "neighbors": neighbors,
                "endpoints": [{"ep": ep, "count": c} for ep, c in endpoints],
                "clusters": clusters_out,
            },
        })
    # U9 (08-12, 用户要求): 有厂商/型号的节点置顶 (免翻找), 稳定排序保持地址序
    result.sort(key=lambda n: 0 if n.get("_has_id") else 1)
    for n in result:
        n.pop("_has_id", None)
    return result


# ── U15: 节点画像导出 (JSON + MD, 含代表帧分层解析) ──
_LAYER_TITLES = {"zbee_wpan": "MAC (802.15.4)", "zbee_nwk": "NWK 网络层",
                 "ZigBee Security Header": "安全头", "zbee_aps": "APS 应用层",
                 "zbee_zcl": "ZCL 应用层", "zbee_zdp": "ZDP"}


def _layers_to_md(layers: dict) -> list[str]:
    """协议层树 → Markdown 行 (层标题 + 扁平字段; 嵌套子树展开一层)."""
    lines: list[str] = []
    for lname, lfields in layers.items():
        title = _LAYER_TITLES.get(lname, lname)
        lines.append(f"**{title}**")
        if not isinstance(lfields, dict):
            continue
        for k, v in lfields.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    if not isinstance(sv, (dict, list)):
                        lines.append(f"- `{k}.{sk}`: {sv}")
            elif not isinstance(v, (dict, list)):
                lines.append(f"- `{k}`: {v}")
    return lines


def _node_profile(aid: int, n: dict, st: dict) -> dict:
    """节点画像 JSON (含端点/命令统计; 不含帧样本 — 样本由调用方附)."""
    return {
        "aid": aid,
        "label": f"0x{aid:04X}",
        "pan": n.get("pan"),
        "device_type": n.get("device_type", "unknown"),
        "eui64": st.get("eui64"),
        "manufacturer_name": st.get("manufacturer_name"),
        "model_id": st.get("model_id"),
        "seen": st["seen"],
        "first_ts": st.get("first"),
        "last_ts": st.get("last"),
        "endpoints": [{"ep": ep, "count": c}
                      for ep, c in sorted(st["endpoints"].items(), key=lambda kv: -kv[1])],
        "clusters": [],
    }


def _cmd_label(cl: int | None, cl_name: str | None, cmd: int | None,
               cmd_name: str | None, d: str | None) -> str:
    c = cl_name or (f"0x{cl:04X}" if cl is not None else "?")
    m = cmd_name or (f"0x{cmd:02X}" if cmd is not None else "?")
    return f"{c} · {m} ({d or '?'})"


@router.get("/nodes/{aid}/export")
async def node_export(aid: int):
    """节点画像导出 (U15): JSON + MD 双份, 含每类控制命令代表帧的分层解析.

    代表帧: 每命令最早 1 帧 + 最近 1 帧 (确定性, 不随导出顺序变化)。
    JSON 含 2 帧完整解析; MD 每命令 1 帧 (最近帧), 精简可读。
    """
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"error": "无数据 (需先导入抓包)"}
    if aid not in nodes:
        return JSONResponse({"error": f"节点 0x{aid:04X} 不存在"}, 404)
    stats, _ls, _asym = _node_stats(pkts, None)
    st = stats.get(aid)
    if st is None:
        return JSONResponse({"error": f"节点 0x{aid:04X} 无帧数据"}, 404)
    n = nodes[aid]

    from datetime import datetime as _dt

    def _ts(t):
        return _dt.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S") if t else "?"

    profile = _node_profile(aid, n, st)
    # 画像 (人读重点: 厂商/型号/EUI64/地址/端点 — 协议对接第一步)
    md_lines: list[str] = [
        f"# 节点画像 0x{aid:04X}",
        "",
        f"**厂商 ID**: {st.get('manufacturer_name') or 'N/A'}  |  "
        f"**设备 ID**: {st.get('model_id') or 'N/A'}  |  "
        f"**EUI64**: {st.get('eui64') or 'N/A'}",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 短地址 | 0x{aid:04X} |",
        f"| PAN | 0x{n.get('pan', 0):04X} |",
        f"| 设备类型 | {n.get('device_type', 'unknown')} |",
        f"| 出现 | {st['seen']} 帧 ({_ts(st.get('first'))} ~ {_ts(st.get('last'))}) |",
    ]
    if st["endpoints"]:
        md_lines += ["", "## 端点"]
        md_lines += [f"- EP 0x{ep:02X}: {c} 帧" for ep, c in
                     sorted(st["endpoints"].items(), key=lambda kv: -kv[1])]
    md_lines += ["", "## 控制命令统计", "", "| 簇 | 命令 | 方向 | 频率 |", "|---|---|---|---|"]

    for (cl, cmd, d), v in sorted(st["clusters"].items(), key=lambda kv: -kv[1]["count"]):
        cl_name = zcl_defs.get_cluster_name(cl)
        entry = {"cluster": cl, "cluster_name": cl_name, "cmd": cmd,
                 "cmd_name": v["cmd_name"], "dir": d, "count": v["count"], "samples": []}
        # 代表帧: 最早 + 最近 (索引即 _packets 下标, packet_detail 同源)
        seen_ids = {}
        for pid in (v.get("first_pkt_id"), v.get("last_pkt_id")):
            if pid is None or pid in seen_ids or not (0 <= pid < len(pkts)):
                continue
            seen_ids[pid] = 1
            entry["samples"].append(_detail_dict(pkts[pid], pid))
        profile["clusters"].append(entry)
        md_lines.append(
            f"| {cl_name or f'0x{cl:04X}' if cl is not None else '?'} | "
            f"{v['cmd_name'] or f'0x{cmd:02X}' if cmd is not None else '?'} | "
            f"{d or '-'} | {v['count']} |")

    # ── 代表帧样本 (MD 人读精简: 只保留 APS 层 + ZCL 载荷, 协议对接要点;
    #    MAC/NWK/安全头属抓包链路细节, 非控制协议内容 — 用户反馈 08-24) ──
    md_lines += ["", "## 代表帧样本", "",
                 "> 每命令取最近 1 帧, 只列 APS 层与 ZCL 载荷解析 (协议对接需要的内容)。",
                 "> 完整分层视图请用节点页 📄 示例 或 JSON 导出。"]

    def _sample_md(s: dict, label: str) -> list[str]:
        """单帧精简样本: 帧头 + APS 层 + ZCL 层 + 载荷解析表."""
        ln: list[str] = []
        ts_txt = _ts(s.get("ts"))
        ln.append("")
        ln.append(f"#### 帧 #{s['id']} @ {ts_txt} ({s.get('pkt_type')})")
        aps = (s.get("layers") or {}).get("zbee_aps") or {}
        cl = s.get("aps_cluster_name") or (aps.get("zbee_aps.cluster") or "-")
        ln += [
            "**APS 应用层**",
            f"- cluster: `{aps.get('zbee_aps.cluster', '-')}` ({cl})",
            f"- 端点: src={aps.get('zbee_aps.src', '-')} → dst={aps.get('zbee_aps.dst', '-')}",
            f"- counter: {aps.get('zbee_aps.counter', '-')}",
        ]
        zcl = (s.get("layers") or {}).get("zbee_zcl") or {}
        if zcl:
            ln += ["**ZCL 应用层**",
                   f"- 命令: `{zcl.get('zbee_zcl.cmd.id', '-')}` ({s.get('zcl_cmd_name') or '-'})"
                   f" · tsn: {zcl.get('zbee_zcl.cmd.tsn', '-')}"]
        pp = s.get("zcl_payload_parsed")
        if pp is not None:
            ln += ["", f"**载荷解析 ({pp.get('parser') or '无载荷'})**"]
            if pp.get("fields"):
                ln += ["| 字段 | 值 | 说明 |", "|---|---|---|"]
                for f in pp["fields"]:
                    ln.append(f"| {f['field']} | {f['value']} | {f.get('note', '')} |")
            else:
                ln.append("- (无参数)")
            if pp.get("hex"):
                ln += ["", f"载荷 hex: `{pp['hex']}`"]
        return ln

    for idx, entry in enumerate(profile["clusters"], 1):
        label = _cmd_label(entry["cluster"], entry["cluster_name"],
                           entry["cmd"], entry["cmd_name"], entry["dir"])
        # MD 每命令只取最近 1 帧 (样本选取确定性: 最近帧 = last_pkt_id)
        sample = entry["samples"][-1] if entry["samples"] else None
        if sample is None:
            md_lines += ["", f"### {idx}. {label} (×{entry['count']})", "- (无代表帧)"]
            continue
        md_lines += ["", f"### {idx}. {label} (×{entry['count']})"]
        md_lines += _sample_md(sample, label)
        md_lines.append("")

    md = "\n".join(md_lines)
    return {"json": json.dumps(profile, ensure_ascii=False, indent=2), "md": md}
