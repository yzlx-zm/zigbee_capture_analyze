"""P3 双向一致性验证 — 旧路径 (全量解析+过滤) vs 新路径 (预筛+并行+过滤)

断言: 两路径保留帧的指纹序列 (packet_id/类型/关键字段) 完全一致。
素材: 常规素材全量双向; 大包 (69MB+) 前 N 帧双向 + 性能计时。
"""
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import cubx_reader
from backend.cubx_reader import _raw_to_dict

BASE = r"C:\Users\Administrator\Desktop\zigbee_capture"

MATERIALS = [
    ("中继入网抓包(1)", f"{BASE}\\中继入网抓包(1).cubx", None),
    ("群控压测问题包", f"{BASE}\\验证可用-记录\\2-群控压测问题包.cubx", None),
    ("test2-ubiqua", f"{BASE}\\test2-ubiqua-export.cubx", None),
    ("标准入网抓包-2", f"{BASE}\\验证可用-记录\\1-标准入网抓包-2.cubx", None),
    ("大包 29MB 全量", f"{BASE}\\07251230_26.cubx", None),
    ("大包 69MB 子集", f"{BASE}\\07250055.cubx", 50000),
    ("大包 112MB 子集", f"{BASE}\\07300951_26.cubx", 50000),
    ("大包 249MB 子集", f"{BASE}\\07240934_26.cubx", 50000),
]


def old_parse(rows, include_mac_frames, nwk_keys, link_keys):
    """旧路径: 全量 _raw_to_dict + 原过滤逻辑 (改造前行为)"""
    packets = []
    for pkt_id, raw, ts, ch, lqi, rssi in rows:
        pkt = _raw_to_dict(bytes(raw), int(pkt_id), float(ts),
                           int(ch), int(lqi), int(rssi), nwk_keys, link_keys)
        is_nwk = pkt.get("nwk_src") is not None or pkt.get("nwk_dst") is not None
        is_mac_relevant = (pkt.get("mac_cmd_id") is not None) or (pkt.get("mac_beacon_pan") is not None)
        if is_nwk or (include_mac_frames and is_mac_relevant):
            packets.append(pkt)
    packets.sort(key=lambda p: p["ts"])
    return packets


def fingerprint(pkts):
    return [(p["packet_id"], p["pkt_type"], p["nwk_src"], p["nwk_dst"],
             p.get("aps_cluster"), p.get("zcl_cmd_id"), p.get("zcl_cmd_name"),
             p.get("mac_cmd_id"), p.get("mac_beacon_pan"),
             p.get("mac_seq"), p.get("nwk_seq"), p.get("security"))
            for p in pkts]


def main():
    ok = fail = 0
    for name, path, limit in MATERIALS:
        print(f"\n== {name} (limit={limit}) ==")
        db = sqlite3.connect(f"{Path(path).as_uri()}?mode=ro", uri=True)
        if limit:
            rows = db.execute(
                "SELECT Id, Raw, Timestamp, Channel, LQI, RSSI FROM Packets ORDER BY Id LIMIT ?",
                (limit,)).fetchall()
        else:
            rows = db.execute(
                "SELECT Id, Raw, Timestamp, Channel, LQI, RSSI FROM Packets ORDER BY Id").fetchall()
        nwk_keys, link_keys = cubx_reader._load_all_keys(db)
        db.close()
        print(f"  物理帧: {len(rows)}")

        # 旧路径 (全量串行)
        t0 = time.time()
        old = old_parse(rows, True, nwk_keys, link_keys)
        t_old = time.time() - t0
        # 新路径 (parse_cubx 内部: 预筛 + 自适应并行/串行) — include_mac_frames=True
        t0 = time.time()
        new, _, _ = cubx_reader.parse_cubx(path, include_mac_frames=True)
        t_new = time.time() - t0
        print(f"  旧路径 {t_old:5.1f}s ({len(old)} 帧) | 新路径 {t_new:5.1f}s ({len(new)} 帧) | 提速 {t_old/max(t_new,0.01):.2f}x")

        # 新路径解析全量 — 子集素材 (limit) 时按旧路径保留的 packet_id 集合截取,
        # 顺序按 ts 相对序 (子集内相对顺序与全量一致)
        if limit:
            old_ids = {p["packet_id"] for p in old}
            new = [p for p in new if p["packet_id"] in old_ids]

        fp_old, fp_new = fingerprint(old), fingerprint(new)
        if fp_old == fp_new:
            print("  ✅ 指纹逐位一致")
            ok += 1
        else:
            # 定位首个差异
            for i, (a, b) in enumerate(zip(fp_old, fp_new)):
                if a != b:
                    print(f"  ❌ 首差异 @ {i}: 旧={a} 新={b}")
                    break
            else:
                print(f"  ❌ 长度不一致: 旧={len(fp_old)} 新={len(fp_new)}")
            fail += 1

    print(f"\n结果: {ok} 通过 / {fail} 失败")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
