# -*- coding: utf-8 -*-
"""审计: 当前设备类型推断 vs 协议级信号 (素材实证)

对照表 (每个节点):
- 当前类型: files._extract_nodes_from_packets 输出
- poll:      MAC Data Request (cmd_id=4) 次数 — SED 专有信号 (无需解密)
- LS:        Link Status 发送次数 — FFD 专有信号
- Route:     Route Request/Reply/Record 发送次数 — FFD 专有信号
- DA cap:    Device Announce (0x0013) capability 字节 bit1 (0x02=FFD, 0=RFD)
"""
import sys, collections, os

sys.path.insert(0, r"D:\ai_agent\zigbee_capture_analyze")
from backend import cubx_reader as cr
from backend.api.files import _extract_nodes_from_packets

MATERIALS = [
    r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\2-群控压测问题包.cubx",
    r"C:\Users\Administrator\Desktop\zigbee_capture\test2-ubiqua-export.cubx",
    r"C:\Users\Administrator\Desktop\zigbee_capture\G32_0626.cubx",
]


def audit(path: str):
    print(f"\n{'='*90}\n素材: {os.path.basename(path)}")
    pkts, added, total = cr.parse_cubx(path, include_mac_frames=True)
    net = [p for p in pkts if p.get("nwk_src") is not None or p.get("nwk_dst") is not None]
    print(f"解析 {len(pkts)} 包 (NWK 可见 {len(net)})")

    nodes = _extract_nodes_from_packets(net)

    # ── 独立协议级信号重算 (不依赖推断逻辑) ──
    poll_by: collections.Counter = collections.Counter()
    ls_by: collections.Counter = collections.Counter()
    route_by: collections.Counter = collections.Counter()
    route_ptype: dict[int, collections.Counter] = {}
    da_cap: dict[int, list[int]] = {}
    da_count: collections.Counter = collections.Counter()
    for p in pkts:
        if p.get("mac_cmd_id") == 4 and p.get("mac_src") is not None:
            poll_by[p["mac_src"]] += 1
        pt = p.get("pkt_type") or ""
        if "Link Status" in pt and p.get("nwk_src") is not None:
            ls_by[p["nwk_src"]] += 1
        if any(x in pt for x in ("Route Request", "Route Reply", "Route Record")) and p.get("nwk_src") is not None:
            route_by[p["nwk_src"]] += 1
            route_ptype.setdefault(p["nwk_src"], collections.Counter())[pt] += 1
        if p.get("aps_cluster") == 0x0013 and p.get("aps_payload_hex"):
            da_count[p["nwk_src"]] += 1
            try:
                pl = bytes.fromhex(p["aps_payload_hex"])
                if len(pl) >= 12:
                    da_cap.setdefault(p["nwk_src"], []).append(pl[11])
            except ValueError:
                pass

    # ── 输出 ──
    lines = [f"{'AID':<6}{'PAN':<6}{'当前类型':<12}{'poll':<7}{'LS':<5}{'Route':<7}{'DA':<4}{'DA cap (bit1: FFD/RFD)'}"]
    flagged = []
    for aid in sorted(nodes):
        n = nodes[aid]
        dt = n["device_type"]
        caps = da_cap.get(aid, [])
        cap_str = ",".join("FFD" if c & 0x02 else "RFD" for c in caps) or "-"
        polls = poll_by.get(aid, 0)
        ls = ls_by.get(aid, 0)
        route = route_by.get(aid, 0)
        pan = n.get("pan")
        lines.append(f"0x{aid:04X} 0x{pan:04X} {dt:<12}{polls:<7}{ls:<5}{route:<7}{da_count.get(aid,0):<4}{cap_str}")

        # 信号判定 (参考标准): 冲突时 poll 优先 (poll=SED 专有, 强信号)
        da_ffd = caps and all(c & 0x02 for c in caps)
        da_rfd = caps and all(not (c & 0x02) for c in caps)
        ffd_sig = ls > 0 or (route > 0 and polls == 0) or da_ffd
        sed_sig = polls > 0 or da_rfd
        ref = "router" if ffd_sig else ("end_device" if sed_sig else "unknown")
        if dt != ref:
            flagged.append((aid, dt, ref))

    lines.append(f"\n→ 与参考判定不一致: {len(flagged)} 个节点")
    for aid, dt, ref in flagged:
        extra = ""
        if route_by.get(aid, 0) > 0 and poll_by.get(aid, 0) > 0:
            extra = "  冲突信号 route=" + dict(route_ptype.get(aid, {})).__str__()
        lines.append(f"   0x{aid:04X}: 当前={dt} 参考={ref}{extra}")
    return "\n".join(lines)


if __name__ == "__main__":
    out = []
    for m in MATERIALS:
        try:
            out.append(audit(m))
        except Exception as e:
            out.append(f"\n素材 {os.path.basename(m)} 失败: {e!r}")
    with open(os.path.join(os.path.dirname(__file__), "device-type-audit.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("done -> .scratch/verification/device-type-audit.txt")
