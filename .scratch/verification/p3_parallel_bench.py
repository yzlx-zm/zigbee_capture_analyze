"""P3 并行化可行性基准: Data 帧 (成本主体) 串行 vs 多进程"""
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import cubx_reader


_MATERIAL = r"C:\Users\Administrator\Desktop\zigbee_capture\07251230_26.cubx"
_keys_cache = None


def _load_keys_once():
    global _keys_cache
    if _keys_cache is None:
        db = sqlite3.connect(f"{Path(_MATERIAL).as_uri()}?mode=ro", uri=True)
        _keys_cache = cubx_reader._load_all_keys(db)
        db.close()
    return _keys_cache


def _work_one(args):
    row, = args
    pid, raw, ts, ch, lqi, rssi = row
    nwk_keys, link_keys = _load_keys_once()  # 每进程加载一次 (0.00s)
    cubx_reader._raw_to_dict(bytes(raw), int(pid), float(ts), int(ch), int(lqi), int(rssi),
                             nwk_keys, link_keys)
    return pid


def main():
    db = sqlite3.connect(f"{Path(_MATERIAL).as_uri()}?mode=ro", uri=True)
    rows = db.execute("SELECT Id, Raw, Timestamp, Channel, LQI, RSSI FROM Packets ORDER BY Id").fetchall()
    db.close()
    data_rows = [r for r in rows[:300000] if (bytes(r[1])[0] & 0x07) == 1][:8000]
    print(f"Data 帧样本: {len(data_rows)} 条")

    # 串行
    t0 = time.time()
    for r in data_rows:
        _work_one((r,))
    ser = time.time() - t0
    print(f"串行: {ser:.1f}s ({len(data_rows)/ser:.0f} 包/s)")

    # 多进程
    for workers in (2, 4):
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=workers) as ex:
            list(ex.map(_work_one, [(r,) for r in data_rows]))
        par = time.time() - t0
        print(f"进程 x{workers}: {par:.1f}s ({len(data_rows)/par:.0f} 包/s, 加速 {ser/par:.2f}x)")


if __name__ == "__main__":
    main()
