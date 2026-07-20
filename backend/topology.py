"""拓扑分析 v2: 通信模式推断父子关系 + 中继树"""
from __future__ import annotations
from collections import defaultdict


def is_unicast(addr):
    return isinstance(addr, int) and 0x0000 <= addr < 0xFFF0


def build(packets: list[dict], nodes: dict[int, dict]) -> dict:
    # 1. 主PAN + 协调器
    pan_counts = defaultdict(int)
    for p in packets:
        pan = p["pan_src"] or p["pan_dst"]
        if pan: pan_counts[pan] += 1
    main_pan = max(pan_counts, key=pan_counts.get) if pan_counts else None
    coord = 0 if 0 in nodes else None
    if coord is None:
        for aid, n in nodes.items():
            if n["is_coord"] and n["pan"] == main_pan: coord = aid; break
    if coord is None and nodes: coord = min(nodes.keys())

    # 2. 通信矩阵
    traffic = defaultdict(int)
    for p in packets:
        s, d = p["nwk_src"], p["nwk_dst"]
        if is_unicast(s) and is_unicast(d): traffic[(s, d)] += 1

    # 3. 推断父子: 节点与coord通信→直连子节点; 其余节点找通信最多的已知parent
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

    # 6. 输出
    node_list = []
    for aid, n in sorted(nodes.items()):
        node_list.append({
            "aid": aid, "label": f"0x{aid:04X}",
            "seen": n["seen"], "pan": n["pan"],
            "is_coord": n["is_coord"],
            "depth": depths.get(aid, -1),
            "parent": parents.get(aid),
            "children": children.get(aid, []),
            "type_list": n["type_list"][:10],
        })

    edge_list = []
    for (s, d), link in sorted(links.items()):
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

    return {
        "nodes": node_list, "edges": edge_list,
        "coord": coord, "main_pan": main_pan,
        "pans": sorted(pan_counts.keys()),
        "tree_depths": dict(sorted(depth_counts.items())),
        "tree_node_count": len(depths),
        "leaf_count": leaf_count,
        "total_nodes": len(nodes), "total_edges": len(edge_list),
        "parents": {str(k): v for k, v in parents.items()},
    }
