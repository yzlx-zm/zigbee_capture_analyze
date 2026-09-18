"""U20-H 补充实测: Link Key 覆盖度 → 解密率 (直接影响 H 的价值论证).

问题: H 的意义是"Ubiqua Keys 表里的 Link Key 也同步进来" — 但 Link Key 的
解密收益能否量化? 本脚本用真实素材直接测:
  同素材 (中继入网抓包(1).cubx) 在两种密钥库下解析, 对比解密率:
    A) 仅预设 + 素材内嵌 Keys 表 (当前默认行为)
    B) A + 全部素材 cubx Keys 表的 Link Key 并集 (模拟"密钥库里有更多设备 link key")
素材 Key 表是 Ubiqua 自己写出的 (真实数据, 非构造)。
"""
from __future__ import annotations

import glob
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.abspath("."))

from backend import key_store, cubx_reader   # noqa: E402

BASE = r"C:\Users\Administrator\Desktop\zigbee_capture"
TARGET = os.path.join(BASE, "中继入网抓包(1).cubx")


def collect_link_keys() -> list[str]:
    """全部素材 cubx Keys 表的 LinkKey 并集 (排除预设)"""
    out: set[str] = set()
    for p in glob.glob(os.path.join(BASE, "**", "*.cubx"), recursive=True):
        try:
            db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            for t, v in db.execute("SELECT Type, Key FROM Keys"):
                if str(t) == "LinkKey" and v is not None:
                    h = bytes(v).hex().upper()
                    if h not in {x.upper() for x in key_store.PRESET_KEYS.values()}:
                        out.add(h)
            db.close()
        except Exception:
            continue
    return sorted(out)


def measure(label: str) -> dict:
    pkts, added, total = cubx_reader.parse_cubx(TARGET, include_mac_frames=True)
    st = key_store.get_match_stats(pkts)
    print(f"  {label}: 解密 {st['decrypted']}/{st['total_data_frames']} "
          f"= {st['decrypt_rate']*100:.1f}%  (内嵌同步 +{added}/总 {total})")
    print(f"     命中 key: {[k['label'] for k in st['matched_keys']]}")
    return st


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="u20_linkkey_")
    real = key_store.KEYS_FILE
    key_store.KEYS_FILE = os.path.join(tmpdir, "zigbee_pc_keys")
    try:
        print(f"素材: {os.path.basename(TARGET)}  (临时 key 库 {key_store.KEYS_FILE})")
        print("\n[A] 仅预设 + 素材内嵌 Keys 表")
        a = measure("A")
        links = collect_link_keys()
        print(f"\n[B] 追加 {len(links)} 个 Link Key (全部素材 Keys 表并集)")
        key_store.merge_from_ubiqua([{"type": "LinkKey", "hex_normalized": h} for h in links])
        b = measure("B")
        d = b["decrypted"] - a["decrypted"]
        print(f"\n差值: 解密 {a['decrypted']} → {b['decrypted']} ({d:+d} 帧, "
              f"{a['decrypt_rate']*100:.1f}% → {b['decrypt_rate']*100:.1f}%)")
        if d <= 0:
            print("结论: 本素材的设备 link key **不在**其他素材 Keys 表内 → "
                  "同步扩展对本素材无提升 (诚实标注; 收益取决于 Ubiqua Keys 表实际覆盖)")
        return 0
    finally:
        key_store.KEYS_FILE = real


if __name__ == "__main__":
    sys.exit(main())
