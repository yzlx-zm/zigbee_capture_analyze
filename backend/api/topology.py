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
        # seen count: per-PAN if filter is set
        if pan_int is not None:
            pkts = get_packets()
            nd_seen = sum(1 for p in pkts if (p["nwk_src"]==aid or p["nwk_dst"]==aid or p["mac_src"]==aid or p["mac_dst"]==aid) and ((p["pan_src"]==pan_int or p["pan_dst"]==pan_int)))
        else:
            nd_seen = n["seen"]
        result.append({
            "aid": aid, "label": label,
            "seen": nd_seen, "pan": n["pan"] if not pan_int else pan_int,
            "is_coord": aid == 0,
            "type_list": n["type_list"][:8],
            "device_type": n.get("device_type", "unknown"),
        })
    return result
