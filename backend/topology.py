"""拓扑分析: BFS树 + 链路评分 + 节点统计"""
from __future__ import annotations

from collections import defaultdict


def build(packets: list[dict], nodes: dict[int, dict]) -> dict:
    """从CSV包列表构建拓扑"""

    # 1. 主PAN检测
    pan_counts: dict[int, int] = defaultdict(int)
    for p in packets:
        pan = p["pan_src"] or p["pan_dst"]
        if pan:
            pan_counts[pan] += 1
    main_pan = max(pan_counts, key=pan_counts.get) if pan_counts else None

    # 2. 协调器: 主PAN中的0x0000 或任意0x0000 或最小ID
    coord = None
    if 0 in nodes:
        coord = 0
    if coord is None:
        for aid, n in nodes.items():
            if n["is_coord"] and n["pan"] == main_pan:
                coord = aid; break
    if coord is None and nodes:
        coord = min(nodes.keys())

    # 3. 邻居关系: 从Link Status + 任意NWK通信推断
    # Link Status 包: src → dst 是邻居声明
    links: dict[tuple, dict] = {}  # (src, dst) -> {count, decrypted, encrypted}
    for p in packets:
        src = p["nwk_src"]
        dst = p["nwk_dst"]
        if not (is_unicast(src) and is_unicast(dst)):
            continue
        key = (src, dst)
        if key not in links:
            links[key] = {"count": 0, "decrypted": 0, "encrypted": 0, "failed": 0, "is_link_status": False}
        links[key]["count"] += 1
        sec = p.get("security", "").lower()
        if "decrypted" in sec:
            links[key]["decrypted"] += 1
        elif "encrypted" in sec or "normal" in sec:
            links[key]["encrypted"] += 1
        else:
            links[key]["failed"] += 1
        if "Link Status" in p.get("pkt_type", ""):
            links[key]["is_link_status"] = True

    # 4. BFS树
    tree: dict[int, int] = {}  # aid -> depth
    if coord is not None:
        tree[coord] = 0
        visited = {coord}
        queue = [coord]
        while queue:
            cur = queue.pop(0)
            for (s, d), link in links.items():
                if link["count"] < 2:
                    continue
                nb = None
                if s == cur and d not in visited:
                    nb = d
                elif d == cur and s not in visited:
                    nb = s
                if nb is not None and nb not in tree:
                    tree[nb] = tree[cur] + 1
                    visited.add(nb)
                    queue.append(nb)

    # 5. 层级统计
    depth_counts: dict[int, int] = defaultdict(int)
    for d in tree.values():
        depth_counts[d] += 1
    leaf_count = sum(1 for aid in tree if not any(
        (s == aid or d == aid) and nb != aid and nb in tree
        for (s, d), _ in links.items()
        for nb in (s, d)
    ))

    # 6. 节点列表输出
    node_list = []
    for aid, n in sorted(nodes.items()):
        in_tree = aid in tree
        node_list.append({
            "aid": aid,
            "label": f"0x{aid:04X}",
            "seen": n["seen"],
            "pan": n["pan"],
            "is_coord": n["is_coord"],
            "in_tree": in_tree,
            "depth": tree.get(aid, -1),
            "type_list": n["type_list"][:10],
        })

    # 7. 链路列表（带评分）
    edge_list = []
    for (s, d), link in sorted(links.items()):
        if link["count"] < 2:
            continue
        total = link["count"]
        success_rate = link["decrypted"] / total if total > 0 else 0
        edge_list.append({
            "src": s, "dst": d,
            "count": total,
            "decrypted": link["decrypted"],
            "encrypted": link["encrypted"],
            "failed": link["failed"],
            "success_rate": round(success_rate, 3),
            "is_link_status": link["is_link_status"],
        })

    return {
        "nodes": node_list,
        "edges": edge_list,
        "coord": coord,
        "main_pan": main_pan,
        "pans": sorted(pan_counts.keys()),
        "tree_depths": dict(sorted(depth_counts.items())),
        "tree_node_count": len(tree),
        "leaf_count": leaf_count,
        "total_nodes": len(nodes),
        "total_edges": len(edge_list),
    }


def is_unicast(addr: int | None) -> bool:
    return isinstance(addr, int) and 0x0000 <= addr < 0xFFF0
