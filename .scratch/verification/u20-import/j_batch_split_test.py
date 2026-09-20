"""U20-J 验证: 批量拆 (一次扫描多段) — 段数/帧数守恒/上限/耗时/PAN 组合.

守恒口径: 子包物理帧数之和 == 源窗口内帧数 (无重叠无遗漏); 逐段窗口与
[ts_start+i*seg, ts_start+(i+1)*seg) 一致, 末段截断到 ts_end。
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.join(os.path.abspath("."), ".scratch", "verification", "u20-import"))

from backend import cubx_splitter   # noqa: E402

MATERIAL = r"D:\tmp\u20\group.cubx"        # 群控 4.9MB / 108474 帧 / 44 分钟
OUTDIR = r"D:\tmp\u20\batch"
FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"  {'✅' if cond else '❌'} {label}{(' — ' + detail) if detail else ''}")
    if not cond:
        FAILS.append(label)


def window_frames(path: str, t0: float, t1: float, pan: int | None = None) -> int:
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    n = 0
    for (raw, ts) in db.execute("SELECT Raw, Timestamp FROM Packets"):
        if ts is None or ts < t0 or ts > t1:
            continue
        if pan is not None and not cubx_splitter.row_in_pan(raw, pan):
            continue
        n += 1
    db.close()
    return n


def main() -> int:
    if os.path.isdir(OUTDIR):
        shutil.rmtree(OUTDIR)
    src = os.path.join(OUTDIR, "group.cubx")
    os.makedirs(OUTDIR, exist_ok=True)
    shutil.copy(MATERIAL, src)
    db = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    t0, t1 = db.execute("SELECT MIN(Timestamp), MAX(Timestamp) FROM Packets").fetchone()
    total = db.execute("SELECT COUNT(*) FROM Packets").fetchone()[0]
    db.close()
    span_min = (t1 - t0) / 60
    print(f"素材 {os.path.basename(src)}: {total} 帧 / {span_min:.1f} 分钟")

    print("\n[1] 5 分钟段批量拆 (整窗)")
    t_start = time.time()
    r = cubx_splitter.split_cubx_multi(src, t0, t1, 5 * 60)
    dt = time.time() - t_start
    segs = r["segments"]
    expect_n = int((t1 - t0) // 300) + (1 if (t1 - t0) % 300 else 0)
    print(f"    耗时 {dt:.1f}s (单次扫描) / 段数 {len(segs)} / 合计 {r['out_frames']} 帧")
    check(len(segs) == expect_n, f"段数 = ceil({span_min:.1f}/5) = {expect_n}",
          f"实际 {len(segs)}")
    check(r["out_frames"] == total, "子包帧数之和 = 源总帧数 (无重叠无遗漏)",
          f"{r['out_frames']} vs {total}")
    check(r["truncated_last"] is True, "末段不足一段长 → truncated_last=True",
          f"末段 {segs[-1]['minutes']} 分钟")
    # 逐段窗口边界与帧数
    bad_win, bad_cnt = 0, 0
    for i, s in enumerate(segs):
        exp_s = t0 + i * 300
        exp_e = min(t0 + (i + 1) * 300, t1)
        if abs(s["win_start"] - exp_s) > 1e-6 or abs(s["win_end"] - exp_e) > 1e-6:
            bad_win += 1
        n = window_frames(src, s["win_start"], s["win_end"])
        # 半开区间: 段内帧数 = [s, e) 计数 (末段闭) — 与实现一致
        if i < len(segs) - 1:
            n_exact = window_frames(src, s["win_start"], s["win_end"]) - \
                window_frames(src, s["win_end"], s["win_end"])
        else:
            n_exact = n
        if s["frames"] != n_exact:
            bad_cnt += 1
            if bad_cnt <= 3:
                print(f"    段{i} 帧数不符: 子包 {s['frames']} vs 窗口 {n_exact}")
    check(bad_win == 0, "各段窗口边界 = [t0+i*seg, min(t0+(i+1)*seg, t1)]")
    check(bad_cnt == 0, "各段帧数 = 该段窗口内帧数")

    print("\n[2] 子包可独立解析 + 辅助表/序列对齐")
    from backend import cubx_reader
    ok_parse = 0
    for s in segs[:3]:
        pkts, _, _ = cubx_reader.parse_cubx(s["out_path"], include_mac_frames=True)
        ok_parse += 1 if pkts else 0
    check(ok_parse == min(3, len(segs)), f"抽查 {ok_parse} 段可解析")
    d = sqlite3.connect(f"file:{segs[0]['out_path']}?mode=ro", uri=True)
    aux = {t: d.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
           for t in ("Keys", "Metadata")}
    seq = d.execute("SELECT seq FROM sqlite_sequence WHERE name='Packets'").fetchone()
    d.close()
    check(aux["Keys"] > 0 and aux["Metadata"] > 0, f"辅助表随子包复制 {aux}")
    check(seq is not None and seq[0] > 0, f"sqlite_sequence 对齐 {seq}")

    print("\n[3] 段数上限保护")
    try:
        cubx_splitter.split_cubx_multi(src, t0, t1, 60)
        check(False, "1 分钟段 (44 段) 应被拒绝")
    except ValueError as e:
        check("超过上限" in str(e), "超额报错清晰", str(e)[:80])

    print("\n[4] PAN + 分段组合 (只拆一个网络)")
    pan = 0xA736
    t_start = time.time()
    r2 = cubx_splitter.split_cubx_multi(src, t0, t1, 10 * 60, pan=pan)
    dt2 = time.time() - t_start
    exp = window_frames(src, t0, t1, pan)
    print(f"    耗时 {dt2:.1f}s / {len(r2['segments'])} 段 / 合计 {r2['out_frames']} 帧 (窗口内该 PAN {exp} 帧)")
    check(r2["out_frames"] == exp, "PAN 过滤后帧数守恒", f"{r2['out_frames']} vs {exp}")
    # 抽验子包纯度: 第一段内所有帧都属于该 PAN
    db = sqlite3.connect(f"file:{r2['segments'][0]['out_path']}?mode=ro", uri=True)
    bad = sum(0 if cubx_splitter.row_in_pan(raw, pan) else 1
              for (raw,) in db.execute("SELECT Raw FROM Packets"))
    db.close()
    check(bad == 0, f"子包内无非该 PAN 帧 (抽查第 1 段, 违规 {bad})")

    print(f"\n结果: {'全部通过' if not FAILS else '失败项 ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
