"""U20-I 对账: 预扫 PAN 分布 (轻量扫描) vs 权威解析后统计 (逐 PAN).

口径: 帧属于 PAN p ⟺ pan_dst == p or pan_src == p
  - 轻量侧: cubx_splitter.scan_pans (只读 Raw 前 16 字节)
  - 权威侧: cubx_reader.parse_cubx 解析结果逐帧判定 (即导入过滤的真实口径)
差异来源只应是 scapy 同样拒绝寻址的畸形帧 (不进数据)。
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.abspath("."))

from backend import cubx_reader, cubx_splitter   # noqa: E402

MATERIALS = [
    ("中继入网抓包(1)", r"C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包(1).cubx"),
    ("群控压测", r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\2-群控压测问题包.cubx"),
    ("标准入网", r"C:\Users\Administrator\Desktop\zigbee_capture\验证可用-记录\1-标准入网抓包-2.cubx"),
]


def authoritative_counts(path: str) -> tuple[dict[int, int], int]:
    pkts, _, _ = cubx_reader.parse_cubx(path, include_mac_frames=True)
    cnt: dict[int, int] = {}
    for p in pkts:
        seen = set()
        for pan in (p.get("pan_dst"), p.get("pan_src")):
            if pan is not None and pan not in seen:
                seen.add(pan)
                cnt[pan] = cnt.get(pan, 0) + 1
    return cnt, len(pkts)


def main() -> int:
    bad = 0
    for name, path in MATERIALS:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        t0 = time.time()
        light = {x["pan"]: x["frames"] for x in cubx_splitter.scan_pans(db)}
        scan_s = time.time() - t0
        total = db.execute("SELECT COUNT(*) FROM Packets").fetchone()[0]
        db.close()
        auth, n_pkt = authoritative_counts(path)
        diffs = {k: (light.get(k, 0), auth.get(k, 0))
                 for k in set(light) | set(auth) if light.get(k, 0) != auth.get(k, 0)}
        tot_light = sum(light.values())
        tot_auth = sum(auth.values())
        print(f"\n== {name}: {total} 物理帧 / 解析保留 {n_pkt} 帧 / 轻量扫描 {scan_s:.2f}s")
        print(f"   轻量 PAN 计数 合计 {tot_light} / 权威 合计 {tot_auth} / 差异 PAN 数 {len(diffs)}")
        for k, (a, b) in sorted(diffs.items(), key=lambda x: -abs(x[1][0] - x[1][1]))[:6]:
            print(f"     PAN 0x{k:04X}: 轻量 {a} vs 权威 {b}  (差 {a - b:+d})")
        # 主 PAN 逐项核对 (帧数前 3)
        for pan, _ in sorted(light.items(), key=lambda x: -x[1])[:3]:
            a, b = light.get(pan, 0), auth.get(pan, 0)
            flag = "✅" if a == b else "⚠️"
            print(f"   {flag} 主 PAN 0x{pan:04X}: 轻量 {a} / 权威 {b}")
            if a != b:
                bad += 1
    print(f"\n结果: {'主 PAN 计数全部一致' if not bad else f'{bad} 项主 PAN 计数不一致'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
