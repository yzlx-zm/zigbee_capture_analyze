"""拓扑分析 v3: 协议数据驱动 (Link Status + Route Record) + 不对称链路检测"""
from __future__ import annotations
from collections import defaultdict


def is_unicast(addr):
    return isinstance(addr, int) and 0x0000 <= addr < 0xFFF0


# ── 子模块: Link Status 邻居表累积 ──

def _build_neighbor_tables(packets: list[dict]) -> dict[int, dict[int, dict]]:
    """扫描所有 Link Status 帧, 累积每个设备的完整邻居表.

    返回: {device_addr: {nb_addr: {in_cost, out_cost, last_seen_ts, count}}}

    - in_cost/out_cost 取最新值 (抓包中最后一次出现的 Link Status)
    - last_seen_ts: 最后一次看到此邻居关系的 Unix 时间戳
    - count: 此邻居关系在抓包中出现的次数
    """
    neighbor_tables: dict[int, dict[int, dict]] = defaultdict(dict)

    for p in packets:
        if p.get("pkt_type") != "Link Status":
            continue
        neighbors = p.get("link_status_neighbors")
        if not neighbors:
            continue
        src = p.get("nwk_src")
        if src is None:
            continue
        ts = p.get("ts", 0)
        for nb in neighbors:
            addr = nb.get("addr")
            if addr is None:
                continue
            existing = neighbor_tables[src].get(addr)
            if existing:
                existing["in_cost"] = nb["in_cost"]
                existing["out_cost"] = nb["out_cost"]
                existing["last_seen_ts"] = max(existing["last_seen_ts"], ts)
                existing["count"] += 1
            else:
                neighbor_tables[src][addr] = {
                    "in_cost": nb["in_cost"],
                    "out_cost": nb["out_cost"],
                    "last_seen_ts": ts,
                    "count": 1,
                }

    return dict(neighbor_tables)


# ── 子模块: Route Record 路径提取 ──

def _build_route_paths(packets: list[dict]) -> list[dict]:
    """扫描所有 Route Record 帧, 提取完整的多跳中继路径 (保留历史变更).

    返回: [{src, dst, relays, hop_count, path_str, first_ts, last_ts, frame_count, is_current}]

    - 同一 (src+relays+dst) 的多次出现聚合为一条路径, 记录时间范围和帧数
    - 同一 src 的多条不同路径全部保留 (反映路由变更)
    - is_current: 该 src 的最后一条路径 (最新路由)
    """
    # 聚合: dedup_key → {first_ts, last_ts, frame_count}
    path_meta: dict[tuple, dict] = {}

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

        relays = rr["relays"]
        dedup_key = (src, tuple(relays), dst)
        ts = p.get("ts", 0)

        if dedup_key in path_meta:
            meta = path_meta[dedup_key]
            meta["first_ts"] = min(meta["first_ts"], ts)
            meta["last_ts"] = max(meta["last_ts"], ts)
            meta["frame_count"] += 1
        else:
            path_meta[dedup_key] = {
                "first_ts": ts,
                "last_ts": ts,
                "frame_count": 1,
            }

    # 构建路径列表
    paths = []
    for (src, relays_tuple, dst), meta in path_meta.items():
        relays = list(relays_tuple)
        full_path = [src] + relays + [dst]
        path_str = " → ".join(f"0x{a:04X}" for a in full_path)

        paths.append({
            "src": src,
            "dst": dst,
            "relays": relays,
            "hop_count": len(relays) + 1,
            "path_str": path_str,
            "first_ts": meta["first_ts"],
            "last_ts": meta["last_ts"],
            "frame_count": meta["frame_count"],
        })

    # 按首次出现时间排序
    paths.sort(key=lambda x: x["first_ts"])

    # 标记每条 src 的最新路径 (is_current)
    src_latest: dict[int, float] = {}
    for p in paths:
        s = p["src"]
        if s not in src_latest or p["first_ts"] > src_latest[s]:
            src_latest[s] = p["first_ts"]
    for p in paths:
        p["is_current"] = (p["first_ts"] == src_latest.get(p["src"]))

    return paths


# ── 子模块: 不对称链路检测 ──

def _detect_asymmetric(neighbor_tables: dict[int, dict[int, dict]]) -> list[dict]:
    """交叉比对邻居表中的双向 cost, 检测不对称链路.

    对每对 (A,B), 比较 A→B 的 out_cost 与 B→A 的 in_cost:
    - diff <= 1: "OK" (对称)
    - diff <= 3: "WEAK" (弱不对称)
    - diff > 3:  "ASYMM" (严重不对称)

    返回: [{a, b, a_to_b_cost, b_to_a_cost, diff, level}]
    """
    results = []
    seen_pairs = set()

    for a, nb_a in neighbor_tables.items():
        for b, info_ab in nb_a.items():
            pair = tuple(sorted([a, b]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # A 看 B 的 out_cost
            a_to_b_out = info_ab.get("out_cost", 0)
            # B 看 A 的 in_cost (站在 B 角度, A 是 B 的邻居, B→A 的 out_cost 就是 A 看 B 的 in_cost)
            info_ba = neighbor_tables.get(b, {}).get(a)
            if info_ba is None:
                continue  # 只有单向数据, 无法比较

            b_to_a_out = info_ba.get("out_cost", 0)
            # 使用 out_cost 比较: A→B 链路质量 vs B→A 链路质量
            diff = abs(a_to_b_out - b_to_a_out)

            if diff <= 1:
                level = "OK"
            elif diff <= 3:
                level = "WEAK"
            else:
                level = "ASYMM"

            results.append({
                "a": a, "b": b,
                "a_to_b_cost": a_to_b_out,
                "b_to_a_cost": b_to_a_out,
                "diff": diff,
                "level": level,
            })

    results.sort(key=lambda x: -x["diff"])
    return results


# ── 主函数 ──

def build(packets: list[dict], nodes: dict[int, dict], filter_pan: int | None = None,
         time_start: float | None = None, time_end: float | None = None) -> dict:
    # 0. 时间过滤
    if time_start is not None:
        packets = [p for p in packets if p["ts"] >= time_start]
    if time_end is not None:
        packets = [p for p in packets if p["ts"] <= time_end]

    # 1. PAN + 协调器
    pan_counts = defaultdict(int)
    for p in packets:
        pan = p["pan_src"] or p["pan_dst"]
        if pan: pan_counts[pan] += 1
    main_pan = max(pan_counts, key=pan_counts.get) if pan_counts else None
    coord = 0

    # 2. 通信矩阵 (只取当前PAN的包)
    traffic = defaultdict(int)
    for p in packets:
        if filter_pan is not None:
            ppan = p["pan_src"] or p["pan_dst"]
            if ppan != filter_pan: continue
        s, d = p["nwk_src"], p["nwk_dst"]
        if is_unicast(s) and is_unicast(d): traffic[(s, d)] += 1

    # 3. coord通信量(用于排序)
    coord_traffic = {}
    if coord is not None:
        for (s, d), cnt in traffic.items():
            if s == coord: coord_traffic[d] = coord_traffic.get(d, 0) + cnt
            if d == coord: coord_traffic[s] = coord_traffic.get(s, 0) + cnt

    # 4. 推断父子: 节点与coord通信→直连子节点; 其余节点找通信最多的已知parent
    parents = {}; children = defaultdict(list)
    if coord is not None:
        children[coord] = []
        for aid in nodes:
            if aid == coord: continue
            to_coord = traffic.get((aid, coord), 0) + traffic.get((coord, aid), 0)
            if to_coord >= 5:
                parents[aid] = coord; children[coord].append(aid)

        remaining = [aid for aid in nodes if aid != coord and aid not in parents]
        for aid in remaining:
            best = None; best_cnt = 0
            for (s, d), cnt in traffic.items():
                peer = None
                if s == aid and d in parents: peer = d
                elif d == aid and s in parents: peer = s
                if peer and cnt > best_cnt: best_cnt = cnt; best = peer
            if best and best_cnt >= 3:
                parents[aid] = best; children[best].append(aid)

    # 4. 深度
    depths = {}
    if coord is not None: depths[coord] = 0
    for c in children.get(coord, []): depths[c] = 1
    changed = True
    while changed:
        changed = False
        for p, kids in children.items():
            if p in depths:
                for k in kids:
                    if k not in depths: depths[k] = depths[p] + 1; changed = True

    # 5. 链路评分
    links = {}
    for (s, d), total in traffic.items():
        if total < 2: continue
        links[(s, d)] = {"count": total, "decrypted": 0, "encrypted": 0,
                          "is_link_status": False, "is_parent_child": False}
    for p in packets:
        s, d = p["nwk_src"], p["nwk_dst"]
        if not (is_unicast(s) and is_unicast(d)): continue
        key = (s, d)
        if key not in links: continue
        st = p.get("status", "").strip()
        if st == "Decrypted": links[key]["decrypted"] += 1
        elif st == "Encrypted" or p.get("security", "").strip(): links[key]["encrypted"] += 1
        if "Link Status" in p.get("pkt_type", ""): links[key]["is_link_status"] = True

    for child, parent in parents.items():
        for key in [(parent, child), (child, parent)]:
            if key in links: links[key]["is_parent_child"] = True

    # 6. 输出 — 只输出有通信活动的节点（在traffic中出现的）
    active_nodes = set()
    for (s, d) in traffic:
        active_nodes.add(s)
        active_nodes.add(d)
    if filter_pan is not None:
        # Also include nodes whose PAN matches
        for aid, n in nodes.items():
            if n.get("pan") == filter_pan:
                active_nodes.add(aid)
    node_list = []
    for aid in sorted(active_nodes):
        n = nodes.get(aid, {"seen":0,"pan":None,"is_coord":False,"type_list":[]})
        # When filtering by PAN, all nodes get that PAN; and seen count is PAN-scoped
        node_pan = filter_pan if filter_pan is not None else n["pan"]
        if filter_pan is not None:
            pan_seen = sum(1 for p in packets if (p["nwk_src"]==aid or p["nwk_dst"]==aid or p["mac_src"]==aid or p["mac_dst"]==aid) and ((p["pan_src"]==filter_pan or p["pan_dst"]==filter_pan)))
            node_seen = pan_seen
        else:
            node_seen = n["seen"]
        ct = coord_traffic.get(aid, 0)
        node_list.append({
            "aid": aid, "label": f"0x{aid:04X}",
            "seen": node_seen, "pan": node_pan,
            "is_coord": aid == 0,
            "depth": depths.get(aid, -1),
            "parent": parents.get(aid),
            "children": sorted(children.get(aid, []), key=lambda c: -coord_traffic.get(c, 0)),
            "coord_traffic": ct,
            "type_list": n["type_list"][:10],
            "device_type": n.get("device_type", "unknown"),
        })

    edge_list = []
    for (s, d), link in sorted(links.items()):
        if s not in active_nodes or d not in active_nodes: continue
        total = link["count"]
        edge_list.append({
            "src": s, "dst": d,
            "count": total,
            "success_rate": round(link["decrypted"] / total, 3) if total else 0,
            "is_link_status": link["is_link_status"],
            "is_parent_child": link["is_parent_child"],
        })

    depth_counts = defaultdict(int)
    for d in depths.values(): depth_counts[d] += 1
    leaf_count = sum(1 for aid in children if not children[aid])

    pan_list = [{"pan": p, "count": c, "label": f"0x{p:04X}"} for p, c in sorted(pan_counts.items(), key=lambda x: -x[1])[:50]]

    # ── 新增: 协议数据驱动的拓扑 ──
    neighbor_tables = _build_neighbor_tables(packets)
    route_paths = _build_route_paths(packets)
    asymmetric_links = _detect_asymmetric(neighbor_tables)

    return {
        "pan_list": pan_list,
        "nodes": node_list, "edges": edge_list,
        "coord": coord, "main_pan": main_pan,
        "pans": sorted(pan_counts.keys()),
        "tree_depths": dict(sorted(depth_counts.items())),
        "tree_node_count": len(depths),
        "leaf_count": leaf_count,
        "total_nodes": len(nodes), "total_edges": len(edge_list),
        "parents": {str(k): v for k, v in parents.items()},
        # 新增协议数据
        "neighbor_tables": neighbor_tables,
        "route_paths": route_paths,
        "asymmetric_links": asymmetric_links,
    }
