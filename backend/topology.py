"""拓扑分析 v2: 通信模式推断父子关系 + 中继树"""
from __future__ import annotations
from collections import defaultdict


def is_unicast(addr):
    return isinstance(addr, int) and 0x0000 <= addr < 0xFFF0


def build(packets: list[dict], nodes: dict[int, dict], filter_pan: int | None = None) -> dict:
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
            "children": children.get(aid, []),
            "coord_traffic": ct,
            "type_list": n["type_list"][:10],
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
    }
