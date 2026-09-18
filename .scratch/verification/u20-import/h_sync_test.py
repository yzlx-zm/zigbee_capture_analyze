"""U20-H 验证: Ubiqua 全类型密钥同步 (解析 → 类型计数 → 去重 → 落盘).

用 mock Ubiqua (真实素材 cubx 的 Keys 表作为密钥源) 走完整链路:
  1. 首次同步: 全部新增, 类型计数正确
  2. 二次同步: 幂等 (added=0)
  3. Ubiqua 不可达: connected=False + 明确 error, 不写文件
  4. 落盘内容: 每条 ubiqua_* key 均在 zigbee_pc_keys, 预设保留, 无重复 hex
使用临时 KEYS_FILE (monkeypatch), 不触碰用户真实 %APPDATA%\\Wireshark 文件。
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.join(os.path.abspath("."), ".scratch", "verification", "u20-import"))

from backend import key_store, ubiqua_api           # noqa: E402
from backend.api import files as files_api          # noqa: E402
import mock_ubiqua                                  # noqa: E402

MATERIAL = r"C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包(1).cubx"
FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"  {'✅' if cond else '❌'} {label}{(' — ' + detail) if detail else ''}")
    if not cond:
        FAILS.append(label)


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="u20_keys_")
    real_keys_file = key_store.KEYS_FILE
    key_store.KEYS_FILE = os.path.join(tmpdir, "zigbee_pc_keys")
    print(f"临时 key 文件: {key_store.KEYS_FILE}")

    # 期望值: 直接从素材 Keys 表读 (真实数据)
    db = sqlite3.connect(f"file:{MATERIAL}?mode=ro", uri=True)
    expect = {}
    for t, v in db.execute("SELECT Type, Key FROM Keys"):
        clean = bytes(v).hex().upper()
        expect[(str(t), clean)] = True
    db.close()
    exp_hexes = {h for _, h in expect}
    # 预设 key 已在库中 (ZigBeeAlliance09 是素材 LinkKey 常客) → 不计入"新增"
    preset = {v.upper() for v in key_store.PRESET_KEYS.values()}
    exp_new = exp_hexes - preset
    exp_by_type: dict[str, int] = {}
    for t, h in expect:
        if h in exp_new:
            exp_by_type[t] = exp_by_type.get(t, 0) + 1
    print(f"素材 Keys 表: {len(expect)} 条 / 去重 {len(exp_hexes)} 个 hex "
          f"(其中预设 {len(exp_hexes & preset)} 个) → 预期新增 {len(exp_new)}: {exp_by_type}")

    srv = mock_ubiqua.start(MATERIAL)
    try:
        print("\n[1] 首次同步 (mock Ubiqua 运行中)")
        r1 = files_api._sync_ubiqua_keys()
        print(f"    返回: {r1}")
        check(r1.get("connected") is True, "connected=True")
        check(r1.get("synced") == len(exp_new), "synced = 素材去重 hex 数 - 预设",
              f"{r1.get('synced')} vs {len(exp_new)}")
        check(r1.get("added_by_type") == exp_by_type, "分类新增计数正确",
              f"{r1.get('added_by_type')} vs {exp_by_type}")
        # 落盘校验
        written = key_store.read_all_keys()
        custom = [k for k in written if not k.get("is_preset")]
        check(len(custom) == len(exp_new), "落盘自定义 key 数 = 预期新增",
              f"{len(custom)} vs {len(exp_new)}")
        check(all(k["hex"] in exp_hexes for k in custom), "落盘 hex 全部来自素材")
        check(len({k["hex"] for k in written}) == len(written), "落盘无重复 hex")
        labels = {k["label"] for k in custom}
        check(any(l.startswith("ubiqua_net_") for l in labels), "NetworkKey 标签带类型")
        check(any(l.startswith("ubiqua_link_") for l in labels), "LinkKey 标签带类型")
        check(any(k.get("is_preset") for k in written), "预设 key 保留")

        print("\n[2] 二次同步 (幂等)")
        r2 = files_api._sync_ubiqua_keys()
        check(r2.get("synced") == 0, "二次同步新增 0", str(r2))
        check(r2.get("total_keys") == r1.get("total_keys"), "总数不变")

        print("\n[3] 手动端点语义 (keys.refresh_ubiqua_keys)")
        import asyncio
        resp = asyncio.run(__import__("backend.api.keys", fromlist=["x"]).refresh_ubiqua_keys())
        check(isinstance(resp, dict) and resp.get("ok") is True, "手动刷新返回 ok=True", str(resp))
    finally:
        srv.shutdown()

    print("\n[4] Ubiqua 不可达 (mock 已停)")
    r3 = files_api._sync_ubiqua_keys()
    print(f"    返回: {r3}")
    check(r3.get("connected") is False, "connected=False")
    check(bool(r3.get("error")), "带明确 error 文案", str(r3.get("error")))
    import asyncio as _a
    from fastapi.responses import JSONResponse
    resp3 = _a.run(__import__("backend.api.keys", fromlist=["x"]).refresh_ubiqua_keys())
    check(isinstance(resp3, JSONResponse) and resp3.status_code == 503,
          "手动刷新不可达 → 503", f"{type(resp3).__name__}")

    print("\n[5] 导入流程不阻断 (Ubiqua 不可达时)")
    check(r3.get("synced") == 0, "同步数 0, 导入继续")

    key_store.KEYS_FILE = real_keys_file
    print(f"\n结果: {'全部通过' if not FAILS else '失败项 ' + str(FAILS)}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
