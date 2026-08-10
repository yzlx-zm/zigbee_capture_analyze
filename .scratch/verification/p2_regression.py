"""P2 素材回归测试 — 解析器字段快照 + 自动回归 (改解析器必跑).

用法:
  python p2_regression.py             # 解析全部素材, 与快照对比 (快集)
  python p2_regression.py --update    # 生成/更新快照 (首次或解析器有意变更后)
  python p2_regression.py --slow      # 含大包 (29MB, ~30s)
  python p2_regression.py --update --slow

快照: .scratch/verification/p2-snapshots/{name}.json
  - stats: 帧数/pkt_type 分布/关键检测计数 (Leave/NWK 命令/0x0B/APS 命令/节点数)
  - frames_sha256: 每帧指纹 (排除 raw_layers) 聚合 hash — 逐帧差异可检测
  - parser_commit: 生成快照时的解析器版本
"""
import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend import cubx_reader

BASE = r"C:\Users\Administrator\Desktop\zigbee_capture"
SNAP_DIR = Path(__file__).resolve().parent / "p2-snapshots"

# (名称, 路径, slow)
MATERIALS = [
    ("标准入网抓包-2(健康)", f"{BASE}\\验证可用-记录\\1-标准入网抓包-2.cubx", False),
    ("中继入网抓包(1)(故障838D)", f"{BASE}\\中继入网抓包(1).cubx", False),
    ("中继入网抓包-DA13-2", f"{BASE}\\中继入网抓包-DA13-2.cubx", False),
    ("群控压测问题包", f"{BASE}\\验证可用-记录\\2-群控压测问题包.cubx", False),
    ("大包29MB", f"{BASE}\\07251230_26.cubx", True),
]

FINGER_FIELDS = None  # None = 全部字段除 raw_layers


def frame_fingerprint(pkt: dict) -> str:
    d = {k: v for k, v in pkt.items() if k != "raw_layers"}
    return hashlib.sha256(
        json.dumps(d, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def collect_stats(pkts: list[dict]) -> dict:
    nwk_cmd = Counter()
    aps_cmd = Counter()
    status_code = Counter()
    pkt_type = Counter()
    sec = Counter()
    src = set()
    dst = set()
    for p in pkts:
        pkt_type[p.get("pkt_type", "")] += 1
        sec[p.get("security", "")] += 1
        if p.get("nwk_cmd_id") is not None:
            nwk_cmd[p["nwk_cmd_id"]] += 1
        if p.get("aps_cmd_id") is not None:
            aps_cmd[p["aps_cmd_id"]] += 1
        if p.get("nwk_status_code") is not None:
            status_code[p["nwk_status_code"]] += 1
        if p.get("nwk_src") is not None:
            src.add(p["nwk_src"])
        if p.get("nwk_dst") is not None:
            dst.add(p["nwk_dst"])
    return {
        "pkt_type": dict(sorted(pkt_type.items())),
        "security": dict(sorted(sec.items())),
        "nwk_cmd_id": {f"0x{k:02X}": v for k, v in sorted(nwk_cmd.items())},
        "aps_cmd_id": {f"0x{k:02X}": v for k, v in sorted(aps_cmd.items())},
        "nwk_status_code": {f"0x{k:02X}": v for k, v in sorted(status_code.items())},
        "leave_rejoin": sum(1 for p in pkts if p.get("nwk_leave_rejoin")),
        "leave_request": sum(1 for p in pkts if p.get("nwk_leave_request")),
        "zcl_frames": sum(1 for p in pkts if p.get("zcl_cmd_id") is not None),
        "nodes_src": len(src), "nodes_dst": len(dst),
    }


PARSER_FILES = ["backend/cubx_reader.py", "backend/tshark.py", "backend/zcl_defs.py"]


def git_head() -> str:
    """解析器文件最近 commit (UI 等非解析器提交不触发快照失效)"""
    try:
        return subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", *PARSER_FILES],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parents[2]).stdout.strip()
    except Exception:
        return "unknown"


def parse_and_snapshot(path: str) -> dict:
    pkts, _, _ = cubx_reader.parse_cubx(path, include_mac_frames=True)
    frame_hashes = [frame_fingerprint(p) for p in pkts]
    agg = hashlib.sha256("\n".join(frame_hashes).encode("utf-8")).hexdigest()
    return {
        "kept_frames": len(pkts),
        "stats": collect_stats(pkts),
        "frames_sha256": agg,
        "parser_commit": git_head(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--slow", action="store_true")
    args = ap.parse_args()
    SNAP_DIR.mkdir(exist_ok=True)

    ok = fail = 0
    for name, path, is_slow in MATERIALS:
        if is_slow and not args.slow:
            continue
        print(f"\n== {name} ==")
        if not Path(path).is_file():
            print("  ⚠️ 素材缺失, 跳过")
            continue
        snap_path = SNAP_DIR / f"{name}.json"
        cur = parse_and_snapshot(path)
        print(f"  保留帧 {cur['kept_frames']} | 解析器 {cur['parser_commit']}")

        if args.update:
            snap_path.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  ✅ 快照已更新 → {snap_path}")
            ok += 1
            continue

        if not snap_path.is_file():
            print(f"  ❌ 快照不存在 (先跑 --update): {snap_path}")
            fail += 1
            continue
        base = json.loads(snap_path.read_text(encoding="utf-8"))
        diffs = []
        for k in ("kept_frames", "frames_sha256", "parser_commit"):
            if base.get(k) != cur.get(k):
                diffs.append(f"{k}: {base.get(k)} → {cur.get(k)}")
        if base.get("stats") != cur.get("stats"):
            for k in sorted(set(base.get("stats", {})) | set(cur.get("stats", {}))):
                if base.get("stats", {}).get(k) != cur.get("stats", {}).get(k):
                    diffs.append(f"stats[{k}]: {base.get('stats', {}).get(k)} → {cur.get('stats', {}).get(k)}")
        if diffs:
            print("  ❌ 差异:")
            for d in diffs[:8]:
                print(f"    {d}")
            fail += 1
        else:
            print("  ✅ 与快照一致")
            ok += 1

    print(f"\n结果: {ok} 通过 / {fail} 失败")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
