"""全局配置"""
import os
import sys

# PyInstaller 打包后资源根目录
if getattr(sys, 'frozen', False):
    RES_ROOT = sys._MEIPASS  # type: ignore[attr-defined]
    APP_DIR = os.path.dirname(sys.executable)
else:
    RES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    APP_DIR = RES_ROOT

FRONTEND_DIR = os.path.join(RES_ROOT, 'frontend')
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')

DEFAULT_PORT = 8720
HOST = '127.0.0.1'

# 包列表单次返回上限
MAX_PAGE_SIZE = 1000
