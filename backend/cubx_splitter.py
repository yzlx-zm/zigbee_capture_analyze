""".cubx 大包时间窗拆分 — 预扫 (秒级元数据) + 物理拆出同 schema 小 .cubx (U11).

设计依据 (总控 2026-08-13 实测 + schema 实证):
- 76MB 包全量 parse_cubx = 333.6s / 149,660 帧 → 大包需时间窗拆分再导入
- cubx = sqlite; 拆文件 = 建同 schema 新库 + 原样复制 Addresses/Keys/
  Metadata/Nodes + Packets 选窗 rows (保原 Id + sqlite_sequence 同步,
  Ubiqua 兼容最稳) — 4 个辅助表语义未完全掌握, 原样复制不解读
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# 直方图桶数 (帧密度展示)
_HIST_BINS = 60
# 复制/扫描进度上报粒度 (行)
_PROGRESS_ROWS = 50000


def prescan_cubx(path: str) -> dict:
    """预扫 .cubx 元数据 (不解析 Raw, 秒级返回).

    返回: total_frames / ts_first / ts_last / duration_s /
    histogram [{ts_start, count} x ~60] / channel 分布 / lqi-rssi 概要
    """
    cubx_path = Path(path).expanduser().resolve()
    if not cubx_path.is_file():
        raise FileNotFoundError(f"cubx 文件不存在: {cubx_path}")

    db = sqlite3.connect(f"{cubx_path.as_uri()}?mode=ro", uri=True)
    try:
        row = db.execute(
            "SELECT COUNT(*), MIN(Timestamp), MAX(Timestamp) FROM Packets"
        ).fetchone()
        total, ts_first, ts_last = row
        if total == 0:
            return {"total_frames": 0, "ts_first": None, "ts_last": None,
                    "duration_s": 0.0, "histogram": [], "channels": {},
                    "lqi": None, "rssi": None}

        duration = (ts_last - ts_first) if ts_last is not None else 0.0
        # 帧密度直方图: 等宽 ~60 桶 (单次流式扫描, 秒级)
        bins: list[dict] = []
        if duration > 0:
            bin_w = duration / _HIST_BINS
            counts = [0] * _HIST_BINS
            for (t,) in db.execute("SELECT Timestamp FROM Packets"):
                if t is None:
                    continue
                bi = int((t - ts_first) / bin_w)
                if bi >= _HIST_BINS:
                    bi = _HIST_BINS - 1
                counts[bi] += 1
            bins = [{"ts_start": ts_first + i * bin_w, "count": counts[i]}
                    for i in range(_HIST_BINS)]
        # channel 分布 (流式聚合)
        channels: dict[int, int] = {}
        for (ch,) in db.execute("SELECT Channel FROM Packets"):
            if ch is not None:
                channels[ch] = channels.get(ch, 0) + 1
        # lqi/rssi 概要 (流式聚合)
        lqi_vals = []  # 采样: 内存友好用计数+累加 (避免 15 万 int 列表)
        rssi_vals = []
        n_lqi = s_lqi = 0
        n_rssi = s_rssi = 0
        lqi_min = lqi_max = None
        rssi_min = rssi_max = None
        for (lqi, rssi) in db.execute("SELECT LQI, RSSI FROM Packets"):
            if lqi is not None:
                n_lqi += 1
                s_lqi += lqi
                lqi_min = lqi if lqi_min is None or lqi < lqi_min else lqi_min
                lqi_max = lqi if lqi_max is None or lqi > lqi_max else lqi_max
            if rssi is not None:
                n_rssi += 1
                s_rssi += rssi
                rssi_min = rssi if rssi_min is None or rssi < rssi_min else rssi_min
                rssi_max = rssi if rssi_max is None or rssi > rssi_max else rssi_max
        return {
            "total_frames": total,
            "ts_first": ts_first,
            "ts_last": ts_last,
            "duration_s": round(duration, 3),
            "histogram": bins,
            "channels": channels,
            "lqi": ({"avg": round(s_lqi / n_lqi, 1), "min": lqi_min, "max": lqi_max}
                    if n_lqi else None),
            "rssi": ({"avg": round(s_rssi / n_rssi, 1), "min": rssi_min, "max": rssi_max}
                     if n_rssi else None),
            "file_mb": round(cubx_path.stat().st_size / 1048576, 1),
        }
    finally:
        db.close()


def _fmt_window(ts: float) -> str:
    """epoch → MMDD_HHMM (产物命名, 本地时间; 用户定义 08-13: 分钟级窗口)"""
    return datetime.fromtimestamp(ts).strftime("%m%d_%H%M")


def _default_out_path(src_path: Path, ts_start: float, ts_end: float) -> str:
    """默认产物路径: <原名>_MMDD_HHMM-MMDD_HHMM.cubx, 同源多子包带序号 _01_.

    - 原名取源文件名 (拖拽暂存场景文件名已还原, 无随机前缀 — API 层处理)
    - 序号: 目标目录已有同窗口前缀 → 找下一个空序号 (同一分钟窗口重复
      拆分也递增不覆盖)
    """
    base = f"{src_path.stem}_{_fmt_window(ts_start)}-{_fmt_window(ts_end)}"
    idx = 1
    while True:
        name = base if idx == 1 else f"{base}_{idx:02d}"
        p = src_path.parent / f"{name}.cubx"
        if not p.exists():
            return str(p)
        idx += 1


def split_cubx(src: str, ts_start: float, ts_end: float, out_path: Optional[str] = None,
               progress_cb: Optional[Callable[[int, int], None]] = None) -> dict:
    """按时间窗拆出同 schema 小 .cubx.

    - 读原库 CREATE TABLE schema → 新库建同 schema
    - 全量复制 Addresses/Keys/Metadata/Nodes (原样, 不解读)
    - Packets 选 Timestamp ∈ [ts_start, ts_end], 保原 Id
    - sqlite_sequence 同步 (Packets Id 延续, Ubiqua 兼容)
    - progress_cb(done, total) 按扫描进度上报
    命名规范 (用户定义 08-13): <原名>_MMDD_HHMM-MMDD_HHMM.cubx, 同源文件
    多子包带序号 _01_/_02_ (同一分钟窗口重复拆分也递增不覆盖).
    返回 {in_frames, out_frames, out_path}
    """
    src_path = Path(src).expanduser().resolve()
    if not src_path.is_file():
        raise FileNotFoundError(f"cubx 文件不存在: {src_path}")
    if out_path is None:
        out_path = _default_out_path(src_path, ts_start, ts_end)
    out_p = Path(out_path).expanduser().resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    if out_p.exists():
        out_p.unlink()

    db = sqlite3.connect(f"{src_path.as_uri()}?mode=ro", uri=True)
    out = sqlite3.connect(str(out_p))
    try:
        # schema 复制 (CREATE TABLE 原样) — sqlite_sequence 是 sqlite 内部表,
        # 保留名不能 CREATE, 由 AUTOINCREMENT 自动创建
        for (ddl,) in db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
                " AND name != 'sqlite_sequence'"):
            out.execute(ddl)
        out.commit()
        # 辅助表全量复制 (Addresses/Keys/Metadata/Nodes — 原样不解读)
        for tbl in ("Addresses", "Keys", "Metadata", "Nodes"):
            try:
                cols = [r[1] for r in db.execute(f"PRAGMA table_info({tbl})")]
            except Exception:
                continue
            rows = db.execute(f"SELECT {', '.join(cols)} FROM {tbl}").fetchall()
            if rows:
                q = ",".join("?" * len(cols))
                out.executemany(f"INSERT INTO {tbl} ({', '.join(cols)}) VALUES ({q})", rows)
        out.commit()
        # Packets 选窗 (保原 Id + 进度上报)
        total = db.execute("SELECT COUNT(*) FROM Packets").fetchone()[0]
        in_frames = 0
        out_frames = 0
        cur = db.execute(
            "SELECT Id, Raw, Stack, Channel, Timestamp, TimeDelta, LQI, RSSI, Comment "
            "FROM Packets ORDER BY Id")
        while True:
            batch = cur.fetchmany(5000)
            if not batch:
                break
            in_frames += len(batch)
            sel = [r for r in batch
                   if r[4] is not None and ts_start <= r[4] < ts_end]
            if sel:
                out.executemany(
                    "INSERT INTO Packets (Id, Raw, Stack, Channel, Timestamp, TimeDelta,"
                    " LQI, RSSI, Comment) VALUES (?,?,?,?,?,?,?,?,?)", sel)
                out_frames += len(sel)
            if progress_cb and in_frames % _PROGRESS_ROWS < 5000:
                progress_cb(in_frames, total)
        if progress_cb:
            progress_cb(total, total)
        out.execute(
            "INSERT OR REPLACE INTO sqlite_sequence (name, seq) SELECT 'Packets', MAX(Id) "
            "FROM Packets")
        out.commit()
        return {"in_frames": total, "out_frames": out_frames, "out_path": str(out_p)}
    finally:
        out.close()
        db.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m backend.cubx_splitter <cubx> [ts_start ts_end]")
        sys.exit(1)
    t0 = time.time()
    res = prescan_cubx(sys.argv[1])
    print(f"prescan {res['total_frames']} 帧 / {res['duration_s']}s / {res['file_mb']}MB "
          f"({time.time() - t0:.1f}s)")
    if len(sys.argv) >= 4:
        r = split_cubx(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
        print(f"split: {r['out_frames']}/{r['in_frames']} 帧 → {r['out_path']}")
