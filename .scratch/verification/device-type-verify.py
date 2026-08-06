# -*- coding: utf-8 -*-
"""设备类型推断修复验证 (2026-08-06)

模拟真实调用链: _extract_nodes_from_packets(_packets 过滤, _full_packets 全量)
断言基于协议级事实 + 素材已知身份:
- 群控包: 16 锁 (1s 轮询 SED) → end_device; 中继 19950/0x4DEE + 0xE091 → router
- G32: 0xEE48 (poll×1933, L6-S3 实证 SED) → end_device; LS 发送者 → router; 零信号 → unknown
- test2: 整网零信号 → 全部 unknown (不得再整网 end_device)
- 入网素材: Device Announce capability 偏移验证 (与 _fallback_zdp_tree 展示交叉验证)
"""
import sys, os, json

sys.path.insert(0, r"D:\ai_agent\zigbee_capture_analyze")
from backend import cubx_reader as cr
from backend.api.files import _extract_nodes_from_packets, _fallback_zdp_tree

GROUP_CONTROL = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\2-群控压测问题包.cubx"
TEST2 = r"C:\Users\Administrator\Desktop\zigbee_capture\test2-ubiqua-export.cubx"
G32 = r"C:\Users\Administrator\Desktop\zigbee_capture\G32_0626.cubx"
JOIN = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.cubx"

# 已知锁 (SED, 1s 轮询) — 素材台账 + P1 分析确认 16 锁
LOCKS = [0x2418, 0x3B94, 0x4072, 0x49B3, 0x53A3, 0x6D43, 0xA7A8, 0xB130,
         0xB868, 0xBC9B, 0xC998, 0xD15E, 0xDE15, 0xE71A, 0x82A0, 0xD6D3]

passed = failed = 0


def check(cond, msg):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {msg}")
    else:
        failed += 1
        print(f"  ❌ {msg}")


# ═══ 1. 群控包 ═══
print("═══ 1. 群控压测问题包 (PAN 0xA736, 16 锁 SED + 中继 19950) ═══")
pkts, _, _ = cr.parse_cubx(GROUP_CONTROL, include_mac_frames=True)
net = [p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
nodes = _extract_nodes_from_packets(net, pkts)

main_pan = 0xA736
pan_nodes = {a: n for a, n in nodes.items() if n.get("pan") == main_pan}
print(f"  PAN 0xA736 节点数: {len(pan_nodes)}")

for lock in LOCKS:
    dt = nodes.get(lock, {}).get("device_type")
    check(dt == "end_device", f"锁 0x{lock:04X} → {dt} (期望 end_device)")
check(nodes.get(0x4DEE, {}).get("device_type") == "router", f"中继 0x4DEE → {nodes.get(0x4DEE,{}).get('device_type')} (期望 router)")
check(nodes.get(0xE091, {}).get("device_type") == "router", f"0xE091 → {nodes.get(0xE091,{}).get('device_type')} (期望 router)")
check(nodes.get(0x0000, {}).get("device_type") == "coordinator", "协调器 0x0000 → coordinator")

# ═══ 2. G32 ═══
print("═══ 2. G32_0626 (0xEE48 实证 SED) ═══")
pkts, _, _ = cr.parse_cubx(G32, include_mac_frames=True)
net = [p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
nodes = _extract_nodes_from_packets(net, pkts)
expect = {0x0000: "coordinator", 0x5D3C: "router", 0xBE5A: "router", 0xEFC2: "router",
          0xEE48: "end_device", 0x4488: "unknown", 0xA185: "unknown", 0xD4F2: "unknown"}
for aid, want in expect.items():
    got = nodes.get(aid, {}).get("device_type")
    check(got == want, f"0x{aid:04X} → {got} (期望 {want})")

# ═══ 3. test2 (整网零信号 → unknown) ═══
print("═══ 3. test2-ubiqua-export (早期'大量终端节点'素材) ═══")
pkts, _, _ = cr.parse_cubx(TEST2, include_mac_frames=True)
net = [p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
nodes = _extract_nodes_from_packets(net, pkts)
check(nodes.get(0x0000, {}).get("device_type") == "coordinator", "0x0000 → coordinator")
check(nodes.get(0x0071, {}).get("device_type") == "router", f"0x0071 (LS×19) → {nodes.get(0x0071,{}).get('device_type')} (期望 router)")
n_end = sum(1 for n in nodes.values() if n.get("device_type") == "end_device")
n_unk = sum(1 for n in nodes.values() if n.get("device_type") == "unknown")
n_rt = sum(1 for n in nodes.values() if n.get("device_type") == "router")
print(f"  分布: end_device={n_end}, unknown={n_unk}, router={n_rt}, 总 {len(nodes)}")
check(n_end == 0, f"无信号节点不再误判终端 (end_device 数 = {n_end}, 期望 0)")
check(n_unk > 0, f"无信号节点改为 unknown ({n_unk} 个)")

# ═══ 4. 入网素材: DA capability 偏移验证 ═══
print("═══ 4. 1-标准入网抓包-2 (Device Announce capability 偏移验证) ═══")
pkts, _, _ = cr.parse_cubx(JOIN, include_mac_frames=True)
net = [p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
nodes = _extract_nodes_from_packets(net, pkts)
da_frames = [p for p in pkts if p.get("aps_cluster") == 0x0013 and p.get("aps_payload_hex")]
print(f"  Device Announce 帧: {len(da_frames)}")
for p in da_frames[:6]:
    pl = bytes.fromhex(p["aps_payload_hex"])
    nwk = p.get("nwk_src")
    cap = pl[11] if len(pl) >= 12 else None
    tree = _fallback_zdp_tree(0x0013, p["aps_payload_hex"]) or {}
    cap_desc = (tree.get("zbee_zdp.zdp_cmd_capability") or "").split(" (")[0]
    declared = "router" if (cap is not None and cap & 0x02) else ("end_device" if cap is not None else "?")
    dt = nodes.get(nwk, {}).get("device_type")
    print(f"  0x{nwk:04X}: cap=0x{cap:02X} ({cap_desc}) → 推断 {dt}")
    if cap is not None:
        check(dt == declared, f"0x{nwk:04X} capability 声明 {declared} 与推断 {dt} 一致")

print(f"\n═══ 结果: {passed} 通过 / {failed} 失败 ═══")
sys.exit(1 if failed else 0)
