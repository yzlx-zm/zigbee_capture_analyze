"""T3 使用手册构建脚本 — 模板 + base64 截图 → 单文件 docs/user-manual.html.

用法: python docs/manual/build_manual.py
截图源: .scratch/verification/t3-manual/final/*.jpg (复抓后重跑本脚本即可)
产物: docs/user-manual.html (自包含, 离线可打开)
"""
from __future__ import annotations

import base64
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TPL = os.path.join(ROOT, 'docs', 'manual', 'user-manual.template.html')
SHOTS = os.path.join(ROOT, '.scratch', 'verification', 't3-manual', 'final')
OUT = os.path.join(ROOT, 'docs', 'user-manual.html')

with open(TPL, encoding='utf-8') as f:
    html = f.read()

used, missing = set(), []


def repl(m: re.Match) -> str:
    name = m.group(1)
    used.add(name)
    p = os.path.join(SHOTS, name + '.jpg')
    if not os.path.exists(p):
        missing.append(name)
        return f'[缺图:{name}]'
    with open(p, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'data:image/jpeg;base64,{b64}'


html = re.sub(r'\{IMG:([a-z0-9_]+)\}', repl, html)

if missing:
    print('⚠ 缺图:', ', '.join(missing))
    raise SystemExit(1)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

size = os.path.getsize(OUT)
print(f'OK → {OUT}  ({size/1048576:.2f} MB, {len(used)} 张内嵌截图)')
