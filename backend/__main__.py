"""入口: python -m backend [--port PORT] [--no-browser]"""
from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser


def free_port(default: int = 8720) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description='Zigbee Capture Analyzer')
    parser.add_argument('--port', type=int, default=0, help='端口 (0=自动)')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    args = parser.parse_args()

    port = args.port or free_port()
    host = '127.0.0.1'
    url = f'http://{host}:{port}'

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    import uvicorn
    print(f'Zigbee Capture Analyzer 启动: {url}')
    uvicorn.run('backend.app:create_app', host=host, port=port,
                factory=True, log_level='warning')


if __name__ == '__main__':
    main()
