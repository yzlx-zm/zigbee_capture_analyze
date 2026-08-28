"""入口: python -m backend [--port PORT] [--no-browser]

T2 (2026-08-29, 打包分发):
- 单实例锁 (temp 目录 PID 锁 + 存活检测, 防双击双开)
- 版本号显示 (version.json, 打包产物; 控制台标题 + 打印)
- 日志落盘 (config.setup_logging → %APPDATA%\\zigbee-analyzer\\logs\\app.log)
- uvicorn 直接传 app 对象 (frozen 下字符串 import 不可靠, PyInstaller 收集 backend 包)
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import tempfile
import threading
import time
import webbrowser

from . import config


def free_port(default: int = 8720) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


_LOCK_FILE = os.path.join(tempfile.gettempdir(), 'zigbee-analyzer.lock')
_mutex_handle = None  # 保持引用: Windows 内核互斥句柄进程生命周期内不释放


def _pid_alive(pid: int) -> bool:
    """PID 存活检测 (POSIX 锁文件路径用).

    ⚠️ 修复 (2026-08-29 打包实测): Windows 下 os.kill(pid, 0) 对 sig=0 抛
    OSError (非 ProcessLookupError) 被 catch 吞掉 → 单实例失效 (第二实例
    覆盖锁文件双开, 实锤 PID 46444)。Windows 用 OpenProcess 查询句柄."""
    if os.name == 'nt':
        try:
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def acquire_single_instance() -> bool:
    """单实例互斥: 已存在实例 → 返回 False (提示退出).

    Windows: 内核命名互斥 (CreateMutex, 进程退出自动释放, 无残留文件);
    POSIX: 锁文件 + PID 存活检测 (残留锁自动接管)."""
    global _mutex_handle
    if os.name == 'nt':
        try:
            import ctypes
            _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False,
                                                                'Local\\ZigbeeAnalyzerInstance')
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                print('工具已在运行, 请关闭已打开的窗口 (控制台窗) 后重试.')
                return False
            return True
        except Exception:
            return True  # 互斥创建失败 (罕见) → 不阻塞启动
    # POSIX 锁文件路径
    if os.path.exists(_LOCK_FILE):
        try:
            with open(_LOCK_FILE, encoding='utf-8') as f:
                pid = int(f.read().strip())
            if _pid_alive(pid):
                print(f'工具已在运行 (PID {pid}), 请关闭已打开的窗口后重试.')
                return False
        except (ValueError, OSError):
            pass  # 残留锁文件 (进程已退出), 接管
    try:
        with open(_LOCK_FILE, 'w', encoding='utf-8') as f:
            f.write(str(os.getpid()))
    except OSError:
        pass  # temp 不可写 (罕见) → 不阻塞启动
    return True


def _console_title(version: str | None):
    """Windows 控制台标题 (版本号可见); 非 Windows/非打包模式忽略."""
    try:
        import ctypes
        ver = f' v{version}' if version else ''
        ctypes.windll.kernel32.SetConsoleTitleW(f'Zigbee Capture Analyzer{ver} — 关闭此窗口即退出')
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='Zigbee Capture Analyzer')
    parser.add_argument('--port', type=int, default=0, help='端口 (0=自动)')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    args = parser.parse_args()

    if not acquire_single_instance():
        sys.exit(1)

    config.setup_logging()

    version = config.load_version()
    _console_title(version)

    port = args.port or free_port()
    host = '127.0.0.1'
    url = f'http://{host}:{port}'

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    import uvicorn
    # T2: 直接传 app 对象 (frozen 下字符串 import 需 backend 包可发现, 传对象最稳)
    from .app import create_app
    ver_txt = f' v{version}' if version else ''
    print(f'Zigbee Capture Analyzer{ver_txt} 启动: {url}')
    print('关闭此窗口即退出工具.')
    uvicorn.run(create_app(), host=host, port=port,
                log_level='warning')


if __name__ == '__main__':
    main()
