"""Mock Ubiqua Remote Access 服务 (U20-H 验证用).

背景: 用户环境 Ubiqua 常不在运行 (19501 实测不可达, http=000), U19 阶段一的
list_keys 类型验证因此无法在真实 Ubiqua 上完成 → 本 mock 复现 **Ubiqua 公开的
XML 契约** (docs/Ubiqua 命令行接口命令-v5 文档 + ubiqua_api._xml_parse_keys 注释),
用于验证 客户端解析 → 类型分类 → 去重合并 → key_store 落盘 的完整链路。

密钥来源为**真实素材**: 从 cubx 文件 Keys 表读出 (Ubiqua 自身写出的表),
非编造数据。真实 Ubiqua 复验待用户环境 (如实标注)。
"""
from __future__ import annotations

import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST, PORT = "127.0.0.1", 19501
NS = "urn:ubilogix:services"

_keys: list[tuple[str, str]] = []   # [(Type, hex)]
_packet_count = 0
_quiet = False


def load_keys_from_cubx(path: str) -> int:
    """从真实 .cubx 的 Keys 表读取 (Ubiqua 自己的数据模型: [Id, Key, Type])"""
    global _keys
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = db.execute("SELECT Type, Key FROM Keys ORDER BY Id").fetchall()
    db.close()
    _keys = [(str(t), bytes(v).hex().upper()) for t, v in rows if v is not None]
    return len(_keys)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):   # 静音
        if not _quiet:
            pass

    def _send(self, code: int, body: str, ctype: str = "application/xml") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/sniffers"):
            self._send(200, '[{"id":"MOCK-1","name":"Mock Sniffer","isStarted":true,'
                            '"channel":26}]', "application/json")
        elif self.path.startswith("/keys"):
            items = "".join(f'<Key Type="{t}">{h}</Key>' for t, h in _keys)
            self._send(200, f'<?xml version="1.0"?><Keys xmlns="{NS}">{items}</Keys>')
        elif self.path.startswith("/capture"):
            self._send(200, f'<?xml version="1.0"?><Capture xmlns="{NS}">'
                            f'<Packets Count="{_packet_count}"></Packets></Capture>')
        else:
            self._send(404, "not found", "text/plain")

    def do_PUT(self):
        self._send(200, "ok", "text/plain")


def start(keys_cubx: str | None = None) -> HTTPServer:
    if keys_cubx:
        load_keys_from_cubx(keys_cubx)
    srv = HTTPServer((HOST, PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    n = load_keys_from_cubx(sys.argv[1]) if len(sys.argv) > 1 else 0
    print(f"mock Ubiqua on {HOST}:{PORT}, {n} keys, {len(_keys)} total")
    srv = HTTPServer((HOST, PORT), Handler)
    srv.serve_forever()
