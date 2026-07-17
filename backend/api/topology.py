"""拓扑 API"""
from __future__ import annotations

from fastapi import APIRouter

from .files import get_packets, get_nodes

router = APIRouter()


@router.get("/topology/graph")
async def topology_graph():
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"nodes": [], "edges": [], "coord": None, "pans": []}

    # BFS 树: 从0x0000开始
    coord = "0x0000" if "0x0000" in nodes else (list(nodes.keys())[0] if nodes else None)
    tree = {}
    if coord:
        tree[coord] = 0

    # 边: 从Link Status提取
    edges = []
    from collections import defaultdict
    neighbors = defaultdict(dict)

    for p in pkts:
        if p["nwk_frame_type"] == 1:  # NWK Cmd
            if p.get("nwk_cmd_id") == 0x01:  # Link Status
                src = p["nwk_src"]
                # tshark会解析cmd payload但我们用简化方式
                # Link Status entries在JSON的zbee_nwk.cmd帧中
                if src in nodes:
                    pass  # tshark JSON不直接展平Link Status entries, 后续优化

    # 构建结果
    node_list = []
    for addr, n in sorted(nodes.items()):
        node_list.append({
            "id": n["aid"],
            "label": addr,
            "eui64": n["eui64"],
            "dev_type": n.get("dev_type", "?"),
            "seen": n["seen"],
            "is_coord": n["is_coord"],
            "pan": n["pan"],
            "depth": n["depth"],
            "in_tree": addr in tree,
            "tree_depth": tree.get(addr, -1),
        })

    return {
        "nodes": node_list,
        "edges": edges,
        "coord": int(coord, 16) if coord else None,
        "pans": list(set(n["pan"] for n in nodes.values() if n["pan"])),
    }


@router.get("/topology/tree")
async def topology_tree(pan: str = ""):
    """返回BFS 树结构"""
    nodes = get_nodes()
    pkts = get_packets()
    # 过滤 PAN
    if pan:
        pan_int = int(pan, 16)
        pan_str = f"0x{pan_int:04X}"
        nodes = {k: v for k, v in nodes.items() if v["pan"] == pan_str}
        if not nodes:
            return {"tree": {}, "nodes": []}

    # BFS
    coord = "0x0000" if "0x0000" in nodes else next(iter(nodes))
    tree = {coord: []}
    visited = {coord}
    queue = [coord]
    while queue:
        cur = queue.pop(0)
        for p in pkts:
            if p["nwk_src"] == cur and p["nwk_dst"] not in visited and p["nwk_dst"] in nodes:
                child = p["nwk_dst"]
                tree.setdefault(cur, []).append(child)
                tree.setdefault(child, [])
                visited.add(child)
                queue.append(child)
    return {"tree": tree, "nodes": [{**n, "label": k} for k, n in nodes.items()]}
