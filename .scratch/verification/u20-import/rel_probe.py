"""U20-I 预研: 轻量"Zigbee 相关性"判定的可行性摸底 (仅诊断用, 不进产品代码)."""
from __future__ import annotations

import os
import sqlite3
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath("."))
from backend import cubx_reader   # noqa: E402


def layout(raw):
    """→ (dst_pan, src_pan, nwk_off, ftype)"""
    if not raw or len(raw) < 5:
        return None, None, None, None
    fcf = raw[0] | (raw[1] << 8)
    ft = fcf & 7
    if ft >= 4 or ft == 2:
        return None, None, None, None
    dm = (fcf >> 10) & 3
    sm = (fcf >> 14) & 3
    pc = (fcf >> 6) & 1
    if dm == 1 or sm == 1:
        return None, None, None, None
    body = len(raw) - 2
    off = 3
    dp = sp = None
    if ft == 0:
        if sm == 0 or body < off + 2 + (8 if sm == 3 else 2) + 2:
            return None, None, None, None
        return None, raw[off] | (raw[off + 1] << 8), off + 2 + (8 if sm == 3 else 2), 0
    if dm:
        if body < off + 2 + (8 if dm == 3 else 2):
            return None, None, None, None
        dp = raw[off] | (raw[off + 1] << 8)
        off += 2 + (8 if dm == 3 else 2)
    if sm:
        if pc and dm:
            sp = dp
        elif body >= off + 2:
            sp = raw[off] | (raw[off + 1] << 8)
        else:
            return None, None, None, None
        off += (8 if sm == 3 else 2)
    if sp is None:
        sp = dp
    return dp, sp, off, ft


def relevant(raw, off, ft):
    if ft in (0, 3):
        return True
    if off is None or len(raw) - 2 < off + 2:
        return False
    nf = raw[off] | (raw[off + 1] << 8)
    return (nf & 0x03) <= 1 and ((nf >> 2) & 0x0F) <= 3


def main(path: str) -> None:
    pkts, _, _ = cubx_reader.parse_cubx(path, include_mac_frames=True)
    kept = {q.get("packet_id"): q for q in pkts}
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = db.execute("SELECT Id, Raw FROM Packets ORDER BY Id").fetchall()
    db.close()
    c = Counter()
    ex = []
    for pid, raw in rows:
        raw = bytes(raw)
        d, s, off, ft = layout(raw)
        q = kept.get(pid)
        if q is None:
            continue
        has_nwk = q.get("nwk_src") is not None or q.get("nwk_dst") is not None
        rel = relevant(raw, off, ft)
        if not rel and has_nwk:
            fcf = raw[0] | (raw[1] << 8)
            c[(ft, (fcf >> 10) & 3, (fcf >> 14) & 3, (fcf >> 6) & 1, len(raw))] += 1
            if len(ex) < 5:
                nf = (raw[off] | (raw[off + 1] << 8)) if (off is not None and len(raw) - 2 >= off + 2) else None
                ex.append((pid, "fcf=%04X" % fcf, "off=%s" % off,
                           "nwkfcf=%s" % (hex(nf) if nf is not None else None),
                           raw[:16].hex(), q.get("pkt_type"), q.get("nwk_src")))
    print(f"{os.path.basename(path)}: 有 NWK 但轻量判定 False 的帧 {sum(c.values())}")
    for k, v in c.most_common(8):
        print("   (ft, dm, sm, pc, len)", k, "→", v)
    for e in ex:
        print("   ex", e)


if __name__ == "__main__":
    main(sys.argv[1])
