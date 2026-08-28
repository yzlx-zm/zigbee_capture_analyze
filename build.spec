# -*- mode: python ; coding: utf-8 -*-
"""T2 主工具打包 spec (2026-08-29) — onedir 目录包.

入口 launcher.py (绝对导入 backend 包, 收集全部模块);
datas: frontend 静态文件 → _internal/frontend (config.RES_ROOT = _MEIPASS);
hiddenimports: backend 延迟导入子模块 + scapy 层 (cubx_reader 用 dot15d4);
excludes: 测试/工程内部目录 (缩小体积).

用法: python build.py  (内部调 PyInstaller --noconfirm build.spec)
"""
import os

APP_NAME = 'ZigbeeAnalyzer'
ROOT = SPECPATH  # PyInstaller 注入: spec 文件所在目录 (spec 内无 __file__)

# backend 全部子模块 (含函数内延迟导入, PyInstaller 静态分析一般能跟,
# 显式声明保底) + scapy 802.15.4 层 (cubx_reader 解析用)
hiddenimports = [
    'backend.app', 'backend.config', 'backend.route_events', 'backend.topology',
    'backend.cubx_reader', 'backend.tshark', 'backend.tuya_proto',
    'backend.zcl_defs', 'backend.zcl_defs_std', 'backend.aps_pairing',
    'backend.frame_dedup', 'backend.parser_verify', 'backend.ai_kb',
    'backend.ai_chat', 'backend.ai_scope', 'backend.key_store',
    'backend.ubiqua_parser', 'backend.ubiqua_api', 'backend.cubx_splitter',
    'backend.verify', 'backend.detectors',
    'backend.detectors.l1', 'backend.detectors.l2', 'backend.detectors.l3',
    'backend.detectors.l6',
    'backend.api.router', 'backend.api.files', 'backend.api.topology',
    'backend.api.keys', 'backend.api.ubiqua', 'backend.api.ai',
    'scapy.layers.all', 'scapy.layers.dot15d4',  # dot15d4FCS 层不存在 (scapy 内), 勿加
]

# 排除: 测试/工程内部 (不打包进产物)
excludes = [
    'pytest', 'tests', 'scratch', 'verification', 'exports', 'scripts',
    'analyze_another', 'docs', 'matplotlib', 'pandas', 'numpy',
]

a = Analysis(
    [os.path.join(ROOT, 'launcher.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[(os.path.join(ROOT, 'frontend'), 'frontend')],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # 控制台窗 (关窗=退出, 版本号/日志可见)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
