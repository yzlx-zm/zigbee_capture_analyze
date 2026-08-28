"""T2 主工具打包脚本 (2026-08-29).

用法:
    python build.py                 # 版本自动 (git describe + 日期)
    python build.py --version 1.0.0 # 指定版本

流程: 清理 dist → PyInstaller (build.spec, onedir) → 写 version.json →
    打 zip (ZigbeeAnalyzer-版本.zip) → 输出体积/文件清单.
产物: dist/ZigbeeAnalyzer/ (目录包) + dist/ZigbeeAnalyzer-<版本>.zip.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = 'ZigbeeAnalyzer'
DIST_DIR = os.path.join(ROOT, 'dist')
BUILD_DIR = os.path.join(ROOT, 'build')
VERSION_JSON = os.path.join(DIST_DIR, APP_NAME, 'version.json')


def auto_version() -> str:
    """自动版本: git describe (最近 tag + 提交数 + 短哈希) → 空格 + 日期."""
    try:
        v = subprocess.run(['git', 'describe', '--tags', '--always', '--dirty'],
                           capture_output=True, text=True, cwd=ROOT).stdout.strip()
    except Exception:
        v = 'dev'
    d = date.today().strftime('%Y%m%d')
    return f'{v} ({d})'


def clean() -> None:
    for d in (DIST_DIR, BUILD_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f'清理 {d}')


def pyinstaller_build() -> None:
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
           os.path.join(ROOT, 'build.spec')]
    print('== PyInstaller:', ' '.join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def write_version(version: str) -> None:
    data = {
        'version': version,
        'date': date.today().isoformat(),
        'note': 'Zigbee Capture Analyzer 主工具 (双击启动, 关控制台退出)',
    }
    with open(VERSION_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'version.json → {VERSION_JSON}')


def make_zip(version: str) -> str:
    pkg = os.path.join(DIST_DIR, APP_NAME)
    zip_name = f'{APP_NAME}-{version.split()[0]}.zip'
    zip_path = os.path.join(DIST_DIR, zip_name)
    if os.path.exists(zip_path):
        os.unlink(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pkg):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, DIST_DIR)
                zf.write(full, rel)
    print(f'zip → {zip_path}')
    return zip_path


def summary() -> None:
    pkg = os.path.join(DIST_DIR, APP_NAME)
    total = 0
    n_files = 0
    for root, _, files in os.walk(pkg):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
            n_files += 1
    size_mb = total / 1024 / 1024
    zips = [f for f in os.listdir(DIST_DIR) if f.endswith('.zip')]
    zip_mb = os.path.getsize(os.path.join(DIST_DIR, zips[-1])) / 1024 / 1024 if zips else 0
    print('=' * 56)
    print(f'目录包体积: {size_mb:.1f} MB ({n_files} 文件)')
    print(f'zip 体积:   {zip_mb:.1f} MB')
    print(f'产物: dist/{APP_NAME}/ + dist/{zips[-1] if zips else "?"}')


def main() -> None:
    ap = argparse.ArgumentParser(description='Zigbee Analyzer 打包分发')
    ap.add_argument('--version', default=None, help='版本号 (默认 git describe + 日期)')
    ap.add_argument('--no-clean', action='store_true', help='不清理 dist/build (增量)')
    args = ap.parse_args()

    version = args.version or auto_version()
    print(f'版本: {version}')

    if not args.no_clean:
        clean()
    pyinstaller_build()
    write_version(version)
    make_zip(version)
    summary()


if __name__ == '__main__':
    main()
