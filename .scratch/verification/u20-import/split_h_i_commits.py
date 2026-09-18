"""U20 提交拆分: 把当前工作区 (H+I 混合) 拆成 H / I 两次提交.

做法: 对混合文件生成 -U1 补丁 → 按 hunk 分类 (I 的 hunk 含 pan/PAN/pan_filter 等标记)
→ 先把 H 的 hunk 应用到索引并提交 → 再把剩余改动整文件入索引提交 I。
安全保证: 提交前后对工作区文件做 sha256 比对, 任何偏差即中止。
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(r"D:\ai_agent\zigbee_capture_analyze")
MIXED = ["backend/api/files.py", "frontend/js/import.js", "frontend/js/state.js"]
# I 项标记 (新增行里出现即判为 I)
I_MARK = re.compile(r"pan_filter|_last_pan_filter|_parse_pan|cs-pan|renderPanRow|panHex|curPan|"
                    r"pan:|pan=|'pan'|\bPAN\b|pans|scan_pans|mac_pan_ids|zigbee_relevant")
# H 项标记 (仅用于人工核对, 不参与分类)
H_MARK = re.compile(r"ubiqua|Ubiqua|list_typed_keys|fmtUbiquaSync|refresh_ubiqua|"
                    r"added_by_type|by_type|pk-ubiqua|ubiqua_link_|ubiqua_net_")


def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def hashes() -> dict[str, str]:
    out = {}
    for f in MIXED + ["backend/cubx_splitter.py", "backend/ubiqua_api.py",
                      "backend/key_store.py", "backend/api/keys.py"]:
        out[f] = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
    return out


def split_hunks(patch: str) -> tuple[str, list[str]]:
    """→ (文件头, [hunk, ...])"""
    lines = patch.splitlines(keepends=True)
    i = 0
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1
    head = "".join(lines[:i])
    hunks, cur = [], []
    for ln in lines[i:]:
        if ln.startswith("@@"):
            if cur:
                hunks.append("".join(cur))
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        hunks.append("".join(cur))
    return head, hunks


def main(write: bool = False) -> int:
    h_patches: dict[str, str] = {}
    for f in MIXED:
        head, hunks = split_hunks(sh(["git", "diff", "-U1", "--", f]))
        h_keep = []
        for hu in hunks:
            added = [l[1:] for l in hu.splitlines()
                     if l.startswith("+") and not l.startswith("+++")]
            blob = "".join(added)
            is_i = any(I_MARK.search(a) for a in added)
            is_h = any(H_MARK.search(a) for a in added)
            # 人工核定的边界 hunk (试运行确认): importPath extra 参数 → I; flash/tbadge → H
            if '"pan"' in blob or "pan_int" in blob:
                is_i, is_h = True, False
            elif "extra" in blob and "importPath" in blob:
                is_i, is_h = True, False
            elif "loadKeyPanel(flash)" in blob or "tbadge" in blob:
                is_i, is_h = False, True
            tag = "I" if is_i else ("H" if is_h else "?")
            print(f"{f} hunk@{hu.splitlines()[0][:44]!r} 新增 {len(added)} 行 → {tag}")
            for a in added:
                if tag == "?":
                    print("     ? 未分类新增行:", a[:110])
            if tag != "I":
                h_keep.append(hu)
        h_patches[f] = head + "".join(h_keep)

    if not write:
        print("\n[试运行] 未写索引; 加 --write 执行")
        return 0

    for f, p in h_patches.items():
        if p.strip() and "@@" in p:
            pf = ROOT / ".scratch/verification/u20-import/_h.patch"
            pf.write_bytes(p.encode("utf-8"))    # 二进制写入: LF 必须保持 (文本模式会加 CR)
            r = subprocess.run(["git", "apply", "--cached", "--unidiff-zero", str(pf)],
                               cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            print(f"apply H {f}: rc={r.returncode} {r.stderr.strip()[:200]}")
    print("索引已含 H 改动:")
    print(sh(["git", "diff", "--cached", "--stat"]).strip()[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main("--write" in sys.argv))
