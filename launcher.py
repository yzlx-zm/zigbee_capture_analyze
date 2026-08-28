"""PyInstaller 打包入口 (T2, 2026-08-29).

backend/__main__.py 是包内相对导入 (from . import config), 不能直接作为
顶层脚本打包; 此文件作为独立入口, 绝对导入 backend 包 (PyInstaller 静态
分析收集整个 backend 包).

⚠️ 修复 1 (2026-08-29 实测): `from backend import __main__` 在 frozen 下
ImportError (PyInstaller 钩子对 from-pkg-import-sub 支持不完整) —
改用模块路径导入 `import backend.__main__`.

⚠️ 修复 2 (2026-08-29 实测): 大包导入卡 30% — cubx_reader P3 用
ProcessPoolExecutor 解析, frozen 下 spawn 子进程需 freeze_support()
(否则子进程重新执行主程序 → 卡死, 97623 帧拆产物 5 分钟无进展).
"""
import multiprocessing

if __name__ == '__main__':
    multiprocessing.freeze_support()  # frozen 下 multiprocessing 必需 (P3 并行解析)
    import backend.__main__ as _m
    _m.main()
