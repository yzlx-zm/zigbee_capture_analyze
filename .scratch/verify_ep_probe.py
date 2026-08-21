# 快速验证: dimmer 入网素材中 manu_name/model_id 与端点/控制 cluster 数据可得性
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
from backend.cubx_reader import parse_cubx
from collections import Counter

path = r"C:/Users/Administrator/Desktop/zigbee_capture/设备控制分析-训练素材/需求32533_simon_dimmer_涂鸦入网_ce5b.cubx"
ret = parse_cubx(path)
# ret 可能是 tuple/list 嵌套; 摊平出所有 dict
pkts = []
def flat(x):
    if isinstance(x, dict): pkts.append(x)
    elif isinstance(x, (list, tuple)):
        for i in x: flat(i)
flat(ret)
print(f"总帧数: {len(pkts)}")

read_attr = Counter(); read_attr_req = Counter()
zdp = Counter(); zcl_cmds = Counter()
manu_raw = []; ep_src = Counter(); ep_dst = Counter()

for p in pkts:
    cid = p.get("zcl_cmd_id")
    cl = p.get("aps_cluster")
    cln = p.get("aps_cluster_name") or (None if cl is None else hex(cl))
    plain = p.get("aps_plain")
    if cid is not None:
        zcl_cmds[(cln, cid, p.get("zcl_direction"))] += 1
        if cid == 0x01 and cl == 0x0000: read_attr[cln] += 1
        if cid == 0x00 and cl == 0x0000: read_attr_req[cln] += 1
    if p.get("nwk_cmd_id") is not None: zdp[p.get("nwk_cmd_id")] += 1
    if p.get("aps_cmd_id") is not None: zdp[p.get("aps_cmd_id")] += 1
    if p.get("aps_src_ep") is not None: ep_src[p["aps_src_ep"]] += 1
    if p.get("aps_dst_ep") is not None: ep_dst[p["aps_dst_ep"]] += 1
    if plain and isinstance(plain, (bytes, bytearray)):
        b = bytes(plain).lower()
        for marker in (b"simon", b"tuya", b"dimmer", b"switch", b"lamp"):
            if marker in b:
                manu_raw.append((cl, cid, marker.decode()))

print("\n[Read Attr Rsp 0x01 / Req 0x00 cluster 分布]:", dict(read_attr), dict(read_attr_req))
print("\n[ZDP/APS 命令统计]:", dict(zdp.most_common(15)))
print("\n[ZCL 命令统计 (cluster, cmd, dir)] 前 20:")
for k, v in zcl_cmds.most_common(20): print(f"  {k}: {v}")
print("\n[aps_src_ep 统计]:", dict(ep_src.most_common()))
print("[aps_dst_ep 统计]:", dict(ep_dst.most_common()))
print("\n[ASCII 厂商串命中]:", manu_raw[:10])
