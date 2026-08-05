# -*- coding: utf-8 -*-
"""P6 校验器抓错能力测试 — 故意破坏解析输出, 校验器必须 FAIL (防 0x20/0x38 类误读).

运行: python tests/test_parser_verify.py
素材: 验证可用-记录\\1-标准入网抓包-2.pcap (健康素材, 权威对比 100% 基准)
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import parser_verify as pv
from backend import tshark as _tshark

PCAP = r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.pcap"
assert os.path.exists(PCAP), f"素材不存在: {PCAP}"

PASS = 0
FAIL = 0


def case(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}: {detail}")


print(f"=== P6 校验器抓错能力测试 (素材: {os.path.basename(PCAP)}) ===\n")

# ── 基准: 正常解析 → 应通过 ──
pkts = _tshark.parse_packets([PCAP])
r0 = pv.run_parser_verify(pkts, "pcap", PCAP)
print("基准 (正常解析):")
case("passed=True", r0["passed"], f"got {r0}")
case("非 parse_mismatch", r0.get("failure_type") != "parse_mismatch", f"got {r0.get('failure_type')}")
ta = r0["checks"].get("tshark_authoritative", {})
case("权威对比匹配", ta.get("passed", False), f"got {ta.get('actual')}")

# ── 破坏 1: aps_cmd_id 误读 (模拟 0x20/0x38) → 必须 FAIL + parse_mismatch ──
bad1 = copy.deepcopy(pkts)
n_cmd = 0
for p in bad1:
    if p.get("aps_cmd_id") is not None:
        p["aps_cmd_id"] = 0x20  # 误读成保留命令
        n_cmd += 1
assert n_cmd > 0, "素材里应有 APS 命令帧"
r1 = pv.run_parser_verify(bad1, "pcap", PCAP)
print(f"\n破坏 1: aps_cmd_id 全改 0x20 ({n_cmd} 帧, 模拟 0x20/0x38 误读):")
case("passed=False", not r1["passed"], f"got passed={r1['passed']}")
case("failure_type=parse_mismatch", r1.get("failure_type") == "parse_mismatch",
     f"got {r1.get('failure_type')}")

# ── 破坏 2: nwk_dst 改错 → 必须 FAIL ──
bad2 = copy.deepcopy(pkts)
for p in bad2:
    if p.get("nwk_dst") is not None:
        p["nwk_dst"] = 0xFFFF
r2 = pv.run_parser_verify(bad2, "pcap", PCAP)
print("\n破坏 2: nwk_dst 全改 0xFFFF:")
case("passed=False", not r2["passed"], f"got passed={r2['passed']}")
case("failure_type=parse_mismatch", r2.get("failure_type") == "parse_mismatch",
     f"got {r2.get('failure_type')}")

# ── 破坏 3: nwk_seq 改错 → 必须 FAIL ──
bad3 = copy.deepcopy(pkts)
for p in bad3:
    if p.get("nwk_seq") is not None:
        p["nwk_seq"] = (p["nwk_seq"] + 1) % 256
r3 = pv.run_parser_verify(bad3, "pcap", PCAP)
print("\n破坏 3: nwk_seq 全 +1:")
case("passed=False", not r3["passed"], f"got passed={r3['passed']}")

# ── 破坏 4: 时间戳全错 → 0 匹配 → 不锁定 (校验工具自身故障不误锁) ──
bad4 = copy.deepcopy(pkts)
for p in bad4:
    p["ts"] += 1000.0  # 匹配键全失败
r4 = pv.run_parser_verify(bad4, "pcap", PCAP)
print("\n破坏 4: 时间戳 +1000s (模拟匹配键故障):")
case("passed=True (不锁定)", r4["passed"], f"got passed={r4['passed']}")
case("非 parse_mismatch", r4.get("failure_type") != "parse_mismatch",
     f"got {r4.get('failure_type')}")

# ── 破坏 5: 未知 pkt_type 泛滥 → 自洽校验必须抓到 (parse_mismatch) ──
bad5 = copy.deepcopy(pkts)
for p in bad5:
    p["pkt_type"] = "Unknown"
r5 = pv.run_parser_verify(bad5, "pcap", PCAP)
print("\n破坏 5: pkt_type 全改 Unknown:")
case("passed=False", not r5["passed"], f"got passed={r5['passed']}")
case("failure_type=parse_mismatch", r5.get("failure_type") == "parse_mismatch",
     f"got {r5.get('failure_type')}")

# ── 汇总 ──
print(f"\n{'='*50}")
print(f"结果: {PASS} 通过 / {FAIL} 失败")
if FAIL:
    print("❌ 存在失败用例 — 校验器未满足要求")
    sys.exit(1)
print("✅ 全部通过 — 校验器能抓住: 命令ID误读 / 地址错误 / 序列错误 / 类型错乱; 且自身故障不误锁")
