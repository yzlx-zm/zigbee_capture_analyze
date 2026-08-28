"""全局配置"""
import os
import sys
import logging
import logging.handlers

# PyInstaller 打包后资源根目录
if getattr(sys, 'frozen', False):
    RES_ROOT = sys._MEIPASS  # type: ignore[attr-defined]
    APP_DIR = os.path.dirname(sys.executable)
else:
    RES_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    APP_DIR = RES_ROOT

FRONTEND_DIR = os.path.join(RES_ROOT, 'frontend')
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')

# ── T2 数据分层 (2026-08-29, 打包分发) ──
# 程序目录 (更新覆盖): exe/_internal/frontend/version.json + zigbee 密钥相关
#   (cubx 内嵌自动; zigbee_pc_keys 在 %APPDATA%\Wireshark\ 系统级照读, 不随工具)
# 用户级数据目录 (更新不碰): %APPDATA%\zigbee-analyzer\ —
#   ai_config.json (AI API key 敏感配置隔离) + logs/ (排障日志)
# 开发模式: APP_DATA_DIR = APP_DIR (原路径, 行为不变)
if getattr(sys, 'frozen', False):
    APP_DATA_DIR = os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'),
                                'zigbee-analyzer')
else:
    APP_DATA_DIR = APP_DIR

AI_CONFIG_PATH = os.path.join(APP_DATA_DIR, 'ai_config.json')
LOG_DIR = os.path.join(APP_DATA_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

# 版本文件 (打包脚本 build.py 写入; 开发模式可能不存在)
VERSION_FILE = os.path.join(APP_DIR, 'version.json')

DEFAULT_PORT = 8720
HOST = '127.0.0.1'

# 包列表单次返回上限
MAX_PAGE_SIZE = 1000


def load_version() -> str | None:
    """version.json → 版本号 (打包产物); 开发模式返回 None (显示 git 无关)."""
    try:
        import json
        with open(VERSION_FILE, encoding='utf-8') as f:
            d = json.load(f)
        return d.get('version')
    except Exception:
        return None


def setup_logging():
    """日志落盘 (T2): logs/app.log 轮转 (2MB×3), 开发/打包模式都启用;
    日志目录不可写时静默跳过, 不阻塞启动."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8')
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(h)
    except Exception:
        pass
