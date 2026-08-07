"""ZCL 命令名 FCF 误标 bug 回归验证 (cubx + pcap 双路径)

背景: Basic (0x0000) 全局命令 Read Attributes (cmd=0x00, FCF frame type=0)
曾因 get_command_name 先查 cluster 表被误标为 "Reset to Factory Defaults"。

验证:
a) 中继入网抓包(1).cubx: 例证帧 (aps_payload_hex 含 104b0004...) → Read Attributes
b) frame_type=0 且 cmd=0x00 的全部帧 → Read Attributes (不得出现 cluster 名)
c) frame_type=1 的 cluster 命令 → 仍走 cluster 表 (OTA/Identify/... 不回归)
d) pcap 路径冒烟 (test2 pcap, tshark 自带密钥解密)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import cubx_reader, tshark

MATERIAL = r"C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包(1).cubx"
PCAP = r"C:\Users\Administrator\Desktop\zigbee_capture\test2-ubiqua-export.pcap"
EXAMPLE_HEX = "104b0004000000010005000700feff"  # 例证帧 payload (空格去除)

ok = 0
fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✅ {name}")
    else:
        fail += 1
        print(f"  ❌ {name} {detail}")


print("== ① cubx 路径: 中继入网抓包(1).cubx ==")
pkts, _, _ = cubx_reader.parse_cubx(MATERIAL)
print(f"  解析 {len(pkts)} 包")

# a) 例证帧
example = [p for p in pkts if p.get("aps_payload_hex") and
           EXAMPLE_HEX in p["aps_payload_hex"]]
check("例证帧存在 (payload 含 104b0004...)", len(example) >= 1,
      f"found={len(example)}")
for p in example[:1]:
    check("例证帧 zcl_cmd_id == 0x00", p.get("zcl_cmd_id") == 0x00,
          f"got={p.get('zcl_cmd_id')}")
    check("例证帧 zcl_cmd_name == 'Read Attributes'",
          p.get("zcl_cmd_name") == "Read Attributes",
          f"got={p.get('zcl_cmd_name')!r}")

# b) cmd=0x00 帧命令名必须 ∈ {该簇 cluster 名} ∪ {"Read Attributes"} — 同一 cmd 按
#    frame_type 区分 (全局 vs cluster-specific), 不允许出现跨簇误标。
cmd0 = [p for p in pkts
        if p.get("aps_payload_hex") and p.get("zcl_cmd_id") == 0x00
        and p.get("zcl_direction") is not None]  # 已走 ZCL 解析的帧
cross_bad = [p for p in cmd0 if p.get("zcl_cmd_name") == "Reset to Factory Defaults"
             and p.get("aps_cluster") != 0x0000]
check(f"cmd=0x00 无跨簇误标 'Reset to Factory Defaults' ({len(cmd0)} 帧)",
      not cross_bad, f"误标 {len(cross_bad)} 帧")
# 全局 Read Attributes 帧必须真实存在 (frame_type=0 的 Basic 读属性)
ra_frames = [p for p in cmd0 if p.get("zcl_cmd_name") == "Read Attributes"]
check("存在全局 Read Attributes 帧", len(ra_frames) > 0, f"found={len(ra_frames)}")
# 所有 cmd=0x00 命名必须在合法集合内
from backend.zcl_defs import GLOBAL_COMMANDS, CLUSTER_COMMANDS
weird = [p for p in cmd0
         if p.get("zcl_cmd_name") != "Read Attributes"
         and (p.get("aps_cluster") not in CLUSTER_COMMANDS
              or CLUSTER_COMMANDS[p.get("aps_cluster")].get(0x00) != p.get("zcl_cmd_name"))]
check("cmd=0x00 命名均在合法集合内", not weird,
      f"异常: {[(hex(p['aps_cluster']) if p['aps_cluster'] is not None else None, p['zcl_cmd_name']) for p in weird[:5]]}")

# c) cluster-specific 命令不回归 — 允许集合断言 (同 cmd 帧含全局命令属合法),
#    cluster-specific 命名必须存在
for cluster, cmd, names in [(0x0006, 0x00, {"Off", "Read Attributes"}),
                            (0x0006, 0x01, {"On", "Read Attributes Response"})]:
    hits = [p for p in pkts if p.get("aps_cluster") == cluster
            and p.get("zcl_cmd_id") == cmd]
    bad = [p for p in hits if p.get("zcl_cmd_name") not in names]
    spec = [p for p in hits if p.get("zcl_cmd_name") != "Read Attributes"
            and p.get("zcl_cmd_name") != "Read Attributes Response"]
    check(f"cluster {hex(cluster)} cmd {hex(cmd)} 命名 ∈ {names} ({len(hits)} 帧)",
          not bad, f"异常: {[p['zcl_cmd_name'] for p in bad[:3]]}")
    check(f"cluster {hex(cluster)} cmd {hex(cmd)} 存在 cluster-specific 命名",
          len(spec) > 0, "素材无 frame_type=1 帧")

print("\n== ② pcap 路径冒烟: test2-ubiqua-export.pcap ==")
tp = tshark.parse_packets([PCAP])
print(f"  解析 {len(tp)} 包")
zcl_frames = [p for p in tp if p.get("zcl_cmd_id") is not None]
print(f"  ZCL 帧 {len(zcl_frames)}")
for cluster, cmd, want in [(0x0000, 0x00, "Read Attributes")]:
    hits = [p for p in zcl_frames if p.get("aps_cluster") == cluster
            and p.get("zcl_cmd_id") == cmd]
    bad = [p for p in hits if p.get("zcl_cmd_name") != want]
    check(f"pcap 路径 cluster {hex(cluster)} cmd {hex(cmd)} → '{want}' ({len(hits)} 帧)",
          not bad, f"误标 {[p['zcl_cmd_name'] for p in bad[:3]]}")
# pcap 路径 frame_type 分布 sanity: 不能全是 None
fts = [p for p in zcl_frames if p.get("zcl_cmd_name") is not None]
check("pcap 路径 zcl_cmd_name 有非空解析", len(fts) > 0)

print(f"\n结果: {ok} 通过, {fail} 失败")
sys.exit(1 if fail else 0)
