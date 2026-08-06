# -*- coding: utf-8 -*-
"""P1 修复回归验证 — 群控素材 + 标准入网素材 (双路径)"""
import sys, io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from collections import Counter
from backend.cubx_reader import parse_cubx
from backend.frame_dedup import dedup_packets, dedup_stats

GROUP_PATH = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\2-群控压测问题包.cubx"
JOIN_PATH = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.cubx"

ok = []
def check(name, cond, detail=""):
    ok.append(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")

print("== ① 0x28 伪命令修复 ==")
packets, _, _ = parse_cubx(GROUP_PATH, include_mac_frames=True)
z28 = [p for p in packets if p.get('nwk_cmd_id') == 0x28]
check("0x28 伪命令清零 (≥0xFFF0 PAN 帧不报伪 cmd)", len(z28) <= 1, f"实际 {len(z28)} (允许 1 条真实未加密厂商命令)")

print("\n== ② RR nwk_dst 广播保留 (对齐 tshark) ==")
rr = [p for p in packets if p.get('pkt_type') == 'Route Request']
check("RR nwk_dst = 0xFFFC", all(p.get('nwk_dst') == 65532 for p in rr), f"共 {len(rr)} 条")

print("\n== ③ 帧去重 ==")
stats = dedup_stats(packets)
check("全局去重生效", stats['duplicates'] > 4000, f"{stats['original']} -> {stats['deduped']} (去重 {stats['duplicates']} 帧)")
ul_before = len([p for p in packets if p.get('zcl_cmd_id') == 1 and p.get('aps_cluster_name') == 'Door Lock'])
deduped2 = dedup_packets(packets)
ul_after = len([p for p in deduped2 if p.get('zcl_cmd_id') == 1 and p.get('aps_cluster_name') == 'Door Lock'])
tx = set((p.get('nwk_dst'), p.get('nwk_seq')) for p in deduped2 if p.get('zcl_cmd_id') == 1 and p.get('aps_cluster_name') == 'Door Lock')
check("Unlock 同跳去重 634→461 (37% 重复捕获)", ul_after == 461, f"{ul_before} -> {ul_after}")
check("事务数 399 (分析层语义, 两跳合并)", len(tx) == 399, f"唯一事务 {len(tx)}")

print("\n== ④ 去重后投递率 (54995/33440 结论不变) ==")
deduped = dedup_packets(packets)
unlocks = [p for p in deduped if p.get('zcl_cmd_id') == 1 and p.get('aps_cluster_name') == 'Door Lock']
sent = {}
for p in unlocks:
    sent.setdefault((p.get('nwk_dst'), p.get('nwk_seq')), p)
delivered = set()
for p in unlocks:
    if p.get('mac_dst') == p.get('nwk_dst') and p.get('mac_dst') not in (None, ''):
        delivered.add((p.get('nwk_dst'), p.get('nwk_seq')))
sent_cnt = Counter(k[0] for k in sent)
deliv_cnt = Counter(k[0] for k in delivered)
for dst in (54995, 33440):
    s, d = sent_cnt[dst], deliv_cnt.get(dst, 0)
    check(f"锁 {dst} 投递率 {'62%' if dst == 54995 else '67%'}", d/s == (15/24 if dst == 54995 else 16/24), f"{d}/{s}")
total_sent = sum(sent_cnt.values())
total_deliv = sum(deliv_cnt.values())
check("去重后发送尝试 399", total_sent == 399, f"实际 {total_sent}")

print("\n== ⑤ 标准入网素材解析 (cubx 路径无回归) ==")
jp, _, _ = parse_cubx(JOIN_PATH, include_mac_frames=True)
check("标准入网解析正常", len(jp) > 100, f"{len(jp)} 帧")
mac4 = [p for p in jp if p.get('mac_cmd_id') == 4]
check("DataRequest 提取正常", len(mac4) >= 20, f"{len(mac4)} 条")

print("\n== ⑥ tshark 路径冒烟 (pcap 素材) ==")
import backend.tshark as tshark_mod
pcap_path = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.pcap"
try:
    tp = tshark_mod.parse_packets([pcap_path])
    check("tshark 解析正常", len(tp) > 50, f"{len(tp)} 帧")
    nwk_ids = Counter(p.get('nwk_cmd_id') for p in tp if p.get('nwk_cmd_id') is not None)
    check("tshark nwk_cmd_id 提取", len(nwk_ids) > 0, str(dict(nwk_ids)))
    rr_t = [p for p in tp if p.get('pkt_type') == 'Route Request']
    if rr_t:
        check("tshark RR nwk_dst 广播保留", all(p.get('nwk_dst') == 65532 for p in rr_t), f"{len(rr_t)} 条 dst={set(p.get('nwk_dst') for p in rr_t)}")
except Exception as e:
    check("tshark 解析", False, f"异常: {e}")

print("\n" + ("=" * 40))
print(f"总结果: {sum(ok)}/{len(ok)} PASS")
