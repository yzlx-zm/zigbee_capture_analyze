"""P1 双路径字段契约对比 — cubx_reader vs tshark 输出字段全集/值差异.

用法: python .scratch/verification/p1-contract/compare_paths.py
素材: 验证可用-记录\\1-标准入网抓包-2 (cubx + pcap 同素材)
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend import cubx_reader, tshark  # noqa: E402

CUBX = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.cubx"
PCAP = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.pcap"


def main() -> None:
    print("== 解析 cubx (include_mac_frames=True) ==")
    cubx_pkts, _, _ = cubx_reader.parse_cubx(CUBX, include_mac_frames=True)
    print(f"cubx 包数: {len(cubx_pkts)}")

    print("\n== 解析 pcap (tshark) ==")
    tsh_path = tshark.find_tshark()
    assert tsh_path, "tshark 未找到"
    print(f"tshark: {tsh_path}")
    pcap_pkts = tshark.parse_packets([PCAP], tsh_path)
    mac_frames = tshark.parse_mac_frames(tsh_path, PCAP)
    print(f"pcap NWK 帧数: {len(pcap_pkts)}, MAC 帧数: {len(mac_frames)}")

    # ── 1. 字段全集 (key 集合) 对比 ──
    cubx_keys = set()
    for p in cubx_pkts:
        cubx_keys |= set(p.keys())
    pcap_keys = set()
    for p in pcap_pkts:
        pcap_keys |= set(p.keys())
    for p in mac_frames:
        pcap_keys |= set(p.keys())

    print("\n## 1. 字段全集差异")
    only_cubx = sorted(cubx_keys - pcap_keys)
    only_pcap = sorted(pcap_keys - cubx_keys)
    print(f"cubx 独有 ({len(only_cubx)}): {only_cubx}")
    print(f"pcap 独有 ({len(only_pcap)}): {only_pcap}")

    # ── 2. 非 None 率对比 (同字段, 两路径谁填谁空) ──
    print("\n## 2. 关键字段非 None 率 (cubx vs pcap)")
    all_keys = sorted(cubx_keys | pcap_keys)
    print(f"{'字段':<26}{'cubx':>12}{'pcap':>12}")
    for k in all_keys:
        cubx_filled = sum(1 for p in cubx_pkts if p.get(k) is not None)
        pcap_filled = sum(1 for p in pcap_pkts if p.get(k) is not None)
        if k in ("raw_layers", "ts", "ch", "packet_id"):
            continue
        flag = ""
        if k in only_cubx or k in only_pcap:
            flag = "  <-- 集合差异"
        elif (cubx_filled == 0) != (pcap_filled == 0):
            flag = "  <-- 填充差异"
        elif cubx_filled > 0 and pcap_filled > 0 and cubx_filled != pcap_filled:
            flag = "  <-- 数量差异"
        print(f"{k:<26}{cubx_filled:>10}/{len(cubx_pkts):<5}{pcap_filled:>10}/{len(pcap_pkts):<5}{flag}")

    # ── 3. pkt_type 分布对比 ──
    print("\n## 3. pkt_type 分布")
    cubx_dist = Counter(p["pkt_type"] for p in cubx_pkts)
    pcap_dist = Counter(p["pkt_type"] for p in pcap_pkts)
    all_types = sorted(set(cubx_dist) | set(pcap_dist))
    print(f"{'pkt_type':<30}{'cubx':>8}{'pcap':>8}")
    for t in all_types:
        diff = "  <--" if cubx_dist.get(t, 0) != pcap_dist.get(t, 0) else ""
        print(f"{t:<30}{cubx_dist.get(t, 0):>8}{pcap_dist.get(t, 0):>8}{diff}")

    # ── 4. nwk_security / security / status 取值分布 ──
    print("\n## 4. security/status/nwk_security 分布")
    for k in ("security", "status", "nwk_security"):
        cv = Counter(str(p.get(k)) for p in cubx_pkts)
        pv = Counter(str(p.get(k)) for p in pcap_pkts)
        allv = sorted(set(cv) | set(pv))
        print(f"--- {k} ---")
        for v in allv:
            print(f"  {v!r:<20} cubx={cv.get(v, 0):>6}  pcap={pv.get(v, 0):>6}")


if __name__ == "__main__":
    main()
