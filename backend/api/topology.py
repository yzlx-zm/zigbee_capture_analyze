"""拓扑 + 节点 API"""
from fastapi import APIRouter
from .files import get_packets, get_nodes
from .. import topology as topo

router = APIRouter()


@router.get("/topology/graph")
async def topology_graph():
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"nodes": [], "edges": [], "coord": None}
    return topo.build(pkts, nodes)


@router.get("/nodes")
async def node_list(search: str = ""):
    """节点列表, 可搜索"""
    nodes = get_nodes()
    result = []
    for aid, n in sorted(nodes.items()):
        label = f"0x{aid:04X}"
        if search:
            q = search.strip().lower()
            if q not in label.lower() and q not in str(aid):
                continue
        result.append({
            "aid": aid, "label": label,
            "seen": n["seen"], "pan": n["pan"],
            "is_coord": n["is_coord"],
            "type_list": n["type_list"][:8],
        })
    return result
