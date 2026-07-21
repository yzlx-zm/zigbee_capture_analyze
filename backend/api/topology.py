"""拓扑 + 节点 API"""
from fastapi import APIRouter, Query
from .files import get_packets, get_nodes
from .. import topology as topo

router = APIRouter()


@router.get("/topology/graph")
async def topology_graph(pan: str = Query(default="")):
    pkts = get_packets()
    nodes = get_nodes()
    if not pkts:
        return {"nodes": [], "edges": [], "coord": None}
    pan_int = int(pan, 16) if pan else None
    return topo.build(pkts, nodes, filter_pan=pan_int)


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
        result.append({
            "aid": aid, "label": label,
            "seen": n["seen"], "pan": n["pan"] if not pan_int else pan_int,
            "is_coord": aid == 0,
            "type_list": n["type_list"][:8],
        })
    return result
