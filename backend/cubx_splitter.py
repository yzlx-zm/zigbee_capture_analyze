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
# 批量拆分段数上限 (U20-J: 防误操作产生海量文件)
MAX_SEGMENTS = 20


def mac_pan_ids(raw: bytes | None) -> tuple[int | None, int | None]:
    """Raw 帧头 → (dst_pan, src_pan); 只读 MAC FCF + 寻址字段, 不跑协议栈 (U20-I).

    语义与权威解析器 (cubx_reader._raw_to_dict) 逐帧对齐, 依据 IEEE 802.15.4
    FCF 定义 + scapy dot15d4 源码级规则:
    - 帧类型 2 (ACK) / 4-7 (Reserved) → 无寻址字段
    - 寻址模式 1 (Reserved) → scapy 无法寻址, 不猜测
    - 信标 (类型 0): 仅 SrcPAN + SrcAddr, 且需容纳 2 字节 Superframe Spec
      (素材实证: 15 字节信标 scapy 解析失败 → 无 PAN)
    - 尾部 2 字节 FCS 不计入寻址 (Dot15d4FCS)
    - 寻址块长度不足 → 不越界臆测 (None)
    - pan_src 兜底 = pan_dst (对齐 cubx_reader.py `src_panid or dst_panid`)
    对账 (U20 验证, 与权威解析器逐帧比对): 群控 1/108474、中继 1/8626、
    标准入网 1/887 不一致 — 残余均为 scapy 同样拒绝寻址的畸形帧。
    """
    if not raw or len(raw) < 5:
        return None, None
    fcf = raw[0] | (raw[1] << 8)
    ftype = fcf & 0x07
    if ftype >= 4 or ftype == 2:
        return None, None
    pan_comp = (fcf >> 6) & 1
    dst_mode = (fcf >> 10) & 0x03
    src_mode = (fcf >> 14) & 0x03
    # 保留寻址模式 (1) → scapy 无法寻址; 信标无 dst 地址, dst 位仅当噪声
    # (素材实证 join2 id=135: 信标 dst_mode=1 但 scapy 正常解出 SrcPAN)
    if src_mode == 1 or (dst_mode == 1 and ftype != 0):
        return None, None
    body = len(raw) - 2          # 扣 FCS
    off = 3                      # FCF(2) + seq(1)
    dst_pan = src_pan = None
    if ftype == 0:               # Beacon
        if src_mode == 0:
            return None, None
        if body < off + 2 + (8 if src_mode == 3 else 2) + 2:   # +Superframe Spec
            return None, None
        return None, raw[off] | (raw[off + 1] << 8)
    if dst_mode:
        if body < off + 2 + (8 if dst_mode == 3 else 2):
            return None, None
        dst_pan = raw[off] | (raw[off + 1] << 8)
        off += 2 + (8 if dst_mode == 3 else 2)
    if src_mode:
        if pan_comp and dst_mode:
            src_pan = dst_pan
        elif body >= off + 2:
            src_pan = raw[off] | (raw[off + 1] << 8)
        else:
            return None, None
    if src_pan is None:
        src_pan = dst_pan
    return dst_pan, src_pan


def zigbee_relevant(raw: bytes | None) -> bool:
    """轻量"该帧会被解析器保留"判定 (U20-I: PAN 计数只算真正进数据的帧).

    依据解析器保留规则 (parse_cubx: 有 Zigbee NWK 或 MAC 命令/信标/ACK 帧):
    - 帧类型 0/3 (Beacon/MAC 命令) → 保留
    - 帧类型 2 (ACK) → 保留 (无 PAN, 不计入分布)
    - 帧类型 1 (Data) → 寻址块后须有合法 NWK 头 (FCF 帧类型 ≤1 且协议版本 ≤3)
    素材实测 (群控 108474 帧): 有 NWK 的帧被误判 False 的数量 = 0;
    排除的主要是异协议/畸形帧 (如中继包 PAN 0x47E4 的 45 帧扩展地址垃圾帧,
    解析器完全不保留) — 这类 PAN 此前会出现在列表里但导入结果为空帧, 属误导。
    """
    if not raw or len(raw) < 5:
        return False
    fcf = raw[0] | (raw[1] << 8)
    ftype = fcf & 0x07
    if ftype in (0, 2, 3):
        return True
    if ftype >= 4:
        return False
    off = _nwk_offset(fcf)
    if off is None or len(raw) - 2 < off + 2:
        return False
    nwk_fcf = raw[off] | (raw[off + 1] << 8)
    return (nwk_fcf & 0x03) <= 1 and ((nwk_fcf >> 2) & 0x0F) <= 3


def _nwk_offset(fcf: int) -> int | None:
    """MAC 寻址块结束偏移 (即 NWK 头起点); 无法确定 → None"""
    ftype = fcf & 0x07
    if ftype >= 4 or ftype == 2:
        return None
    dst_mode = (fcf >> 10) & 0x03
    src_mode = (fcf >> 14) & 0x03
    if src_mode == 1 or (dst_mode == 1 and ftype != 0):
        return None
    off = 3
    if ftype == 0:      # Beacon: SrcPAN + SrcAddr + Superframe Spec
        if src_mode == 0:
            return None
        return off + 2 + (8 if src_mode == 3 else 2) + 2
    if dst_mode:
        off += 2 + (8 if dst_mode == 3 else 2)
    if src_mode:
        if (fcf >> 6) & 1 and dst_mode:
            pass                      # src PAN 省略 (压缩 = dst PAN)
        else:
            off += 2
        off += 8 if src_mode == 3 else 2
    return off


def scan_pans(db: sqlite3.Connection) -> list[dict]:
    """PAN 分布 (轻量扫描: 只取 Raw 前 16 字节, 不解析协议) — U20-I.

    返回按帧数降序 [{pan, frames}]; 帧同时含 dst/src PAN 时两者各计一次
    (与"帧属于哪个 PAN"的过滤语义一致: dst==pan or src==pan)。
    只统计解析器会保留的帧 (zigbee_relevant) — 异协议/畸形帧不虚增计数。
    """
    counts: dict[int, int] = {}
    for (raw,) in db.execute("SELECT substr(Raw, 1, 32) FROM Packets"):
        if not zigbee_relevant(raw):
            continue
        d, s = mac_pan_ids(raw)
        if d is not None:
            counts[d] = counts.get(d, 0) + 1
        if s is not None and s != d:
            counts[s] = counts.get(s, 0) + 1
    return [{"pan": p, "frames": c} for p, c in sorted(counts.items(), key=lambda x: -x[1])]


def row_in_pan(raw: bytes | None, pan: int | None) -> bool:
    """帧是否属于 PAN (pan=None → 全量, 不过滤)

    与 scan_pans 同口径: 先过 zigbee_relevant (解析器不保留的帧不计入/不保留),
    避免子包混入导入时必被丢弃的异协议/畸形帧。
    """
    if pan is None:
        return True
    if not zigbee_relevant(raw):
        return False
    d, s = mac_pan_ids(raw)
    return d == pan or s == pan


def prescan_cubx(path: str) -> dict:
    """预扫 .cubx 元数据 (不解析 Raw, 秒级返回).

    返回: total_frames / ts_first / ts_last / duration_s /
    histogram [{ts_start, count} x ~60] / channel 分布 / lqi-rssi 概要 /
    pans [{pan, frames}] (U20-I: 多 PAN 混杂包过滤用; 单 PAN 时也只有 1 项)
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
                    "lqi": None, "rssi": None, "pans": []}

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
            "pans": scan_pans(db),   # U20-I: PAN 分布 (轻量: 只读 Raw 前 16 字节)
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
               progress_cb: Optional[Callable[[int, int], None]] = None,
               pan: Optional[int] = None) -> dict:
    """按时间窗拆出同 schema 小 .cubx.

    - 读原库 CREATE TABLE schema → 新库建同 schema
    - 全量复制 Addresses/Keys/Metadata/Nodes (原样, 不解读)
    - Packets 选 Timestamp ∈ [ts_start, ts_end], 保原 Id
    - pan 非空时只保留该 PAN 的帧 (U20-I: 轻量 MAC 头判定, 与导入侧过滤同口径)
    - sqlite_sequence 同步 (Packets Id 延续, Ubiqua 兼容)
    - progress_cb(done, total) 按扫描进度上报
    命名规范 (用户定义 08-13): <原名>_MMDD_HHMM-MMDD_HHMM.cubx, 同源文件
    多子包带序号 _01_/_02_ (同一分钟窗口重复拆分也递增不覆盖).
    返回 {in_frames, out_frames, out_path, pan}
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
        _copy_aux_tables(db, out)
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
            # S1 (2026-08-26): 半开区间 [ts_start, ts_end) 会把恰在 ts_end 的帧
            # 丢弃 (滑块最大值 = ts_last 时末帧必丢, P2) — 改为闭区间
            sel = [r for r in batch
                   if r[4] is not None and ts_start <= r[4] <= ts_end
                   and row_in_pan(r[1], pan)]
            if sel:
                _insert_packets(out, sel)
                out_frames += len(sel)
            if progress_cb and in_frames % _PROGRESS_ROWS < 5000:
                progress_cb(in_frames, total)
        if progress_cb:
            progress_cb(total, total)
        out.execute(
            "INSERT OR REPLACE INTO sqlite_sequence (name, seq) SELECT 'Packets', MAX(Id) "
            "FROM Packets")
        out.commit()
        return {"in_frames": total, "out_frames": out_frames, "out_path": str(out_p),
                "pan": pan}
    finally:
        out.close()
        db.close()


def split_cubx_multi(src: str, ts_start: float, ts_end: float, seg_seconds: float,
                     pan: Optional[int] = None, max_segments: int = MAX_SEGMENTS,
                     progress_cb: Optional[Callable[[int, int], None]] = None) -> dict:
    """按段长一次拆出 N 个子包 (U20-J) — **单次扫描**分批写入, 不循环调用单窗拆分.

    - 段划分: [ts_start + i*seg, ts_start + (i+1)*seg) 半开 (无重叠无遗漏),
      末段到 ts_end 为止 (不足一段长按实际截断, 返回值 truncated_last 标注)
    - 段数上限 max_segments (默认 20): 超出直接报错, 不产生海量文件
    - pan 非空 → 只保留该 PAN 的帧 (与单窗拆分/导入同口径)
    - 每个子包: 同 schema + 辅助表全量复制 + 保原 Id + sqlite_sequence 对齐
    返回 {in_frames, out_frames, segments:[{out_path, frames, win_start, win_end,
          minutes}], pan, seg_minutes, truncated_last}
    """
    src_path = Path(src).expanduser().resolve()
    if not src_path.is_file():
        raise FileNotFoundError(f"cubx 文件不存在: {src_path}")
    if ts_end <= ts_start:
        raise ValueError("时间窗无效: ts_end 必须大于 ts_start")
    if seg_seconds <= 0:
        raise ValueError("段长必须大于 0")
    span = ts_end - ts_start
    n_seg = int(span // seg_seconds) + (1 if span % seg_seconds else 0)
    n_seg = max(n_seg, 1)
    if n_seg > max_segments:
        raise ValueError(
            f"段数过多: 该范围 {span/60:.1f} 分钟按 {seg_seconds/60:.1f} 分钟拆分得 "
            f"{n_seg} 段, 超过上限 {max_segments} 段 — 请增大段长或缩小范围")

    # 段边界 (半开; 末段闭到 ts_end)
    bounds: list[tuple[float, float]] = []
    for i in range(n_seg):
        s = ts_start + i * seg_seconds
        e = min(ts_start + (i + 1) * seg_seconds, ts_end)
        bounds.append((s, e))

    db = sqlite3.connect(f"{src_path.as_uri()}?mode=ro", uri=True)
    outs: list[sqlite3.Connection] = []
    paths: list[str] = []
    try:
        for (s, e) in bounds:
            p = _default_out_path(src_path, s, e)
            paths.append(p)
            conn = sqlite3.connect(p)
            _copy_aux_tables(db, conn)      # 每个子包同 schema + 辅助表
            outs.append(conn)

        total = db.execute("SELECT COUNT(*) FROM Packets").fetchone()[0]
        counts = [0] * n_seg
        in_frames = 0
        cur = db.execute(
            "SELECT Id, Raw, Stack, Channel, Timestamp, TimeDelta, LQI, RSSI, Comment "
            "FROM Packets ORDER BY Id")
        while True:
            batch = cur.fetchmany(5000)
            if not batch:
                break
            in_frames += len(batch)
            buckets: dict[int, list[tuple]] = {}
            for r in batch:
                ts = r[4]
                if ts is None or ts < ts_start or ts > ts_end:
                    continue
                if not row_in_pan(r[1], pan):
                    continue
                idx = int((ts - ts_start) // seg_seconds)
                if idx >= n_seg:
                    idx = n_seg - 1                     # ts == ts_end → 末段
                buckets.setdefault(idx, []).append(r)
            for idx, rows in buckets.items():
                _insert_packets(outs[idx], rows)
                counts[idx] += len(rows)
            if progress_cb and in_frames % _PROGRESS_ROWS < 5000:
                progress_cb(in_frames, total)
        if progress_cb:
            progress_cb(total, total)
        for i, conn in enumerate(outs):
            conn.execute(
                "INSERT OR REPLACE INTO sqlite_sequence (name, seq) SELECT 'Packets',"
                " MAX(Id) FROM Packets")
            conn.commit()
        out_frames = sum(counts)
        segments = [{"out_path": paths[i], "frames": counts[i],
                     "win_start": bounds[i][0], "win_end": bounds[i][1],
                     "minutes": round((bounds[i][1] - bounds[i][0]) / 60, 2)}
                    for i in range(n_seg)]
        return {"in_frames": total, "out_frames": out_frames, "segments": segments,
                "pan": pan, "seg_minutes": round(seg_seconds / 60, 3),
                "truncated_last": (bounds[-1][1] - bounds[-1][0]) < seg_seconds - 1e-6}
    finally:
        for conn in outs:
            conn.close()
        db.close()


# Packets 列序 (拆分复制用, 保原 Id)
_PKT_COLS = ("Id", "Raw", "Stack", "Channel", "Timestamp", "TimeDelta", "LQI", "RSSI",
             "Comment")


def _copy_aux_tables(db: sqlite3.Connection, out: sqlite3.Connection) -> None:
    """建同 schema + 复制辅助表 (Addresses/Keys/Metadata/Nodes, 原样不解读)."""
    # sqlite_sequence 是 sqlite 内部表, 保留名不能 CREATE, 由 AUTOINCREMENT 自动创建
    for (ddl,) in db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
            " AND name != 'sqlite_sequence'"):
        out.execute(ddl)
    out.commit()
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


def _insert_packets(out: sqlite3.Connection, rows: list[tuple]) -> None:
    """写入选中的 Packets 行 (列序 = _PKT_COLS)"""
    out.executemany(
        "INSERT INTO Packets (Id, Raw, Stack, Channel, Timestamp, TimeDelta,"
        " LQI, RSSI, Comment) VALUES (?,?,?,?,?,?,?,?,?)", rows)


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
