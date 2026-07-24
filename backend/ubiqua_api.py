"""Ubiqua Protocol Analyzer REST API 客户端

Ubiqua 1.4 build 224, Remote Access Service 端口 19501.
文档: docs/Ubiqua 命令行接口命令-v5-20260723_203404.docx

双路径设计:
  路径A (当前): Ubiqua自动保存pcap → 目录监控 → tshark解析 → 拓扑
  路径B (预留): 直接解析 /capture XML中的 Raw/Decrypted hex → 内部dict
"""
from __future__ import annotations

import json
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

# XML 命名空间
NS = "urn:ubilogix:services"


@dataclass
class UbiquaPacket:
    """/capture 返回的原始包 (XML 解析后)"""
    packet_id: int
    info: str               # 包类型名称, 如 "Link Status", "Data"
    source: str             # "Imported File" / "Live"
    status: str             # "Decrypted" / "Encrypted"
    raw_hex: str            # 原始 hex 字节
    decrypted_hex: str      # 解密后 hex 字节 (未解密则为空)
    # 路径B预留: 直接从 hex 解析协议字段 (NWK src/dst, APS cluster 等)
    # parsed: Optional[dict] = None


@dataclass
class UbiquaStatus:
    connected: bool = False
    host: str = "localhost"
    port: int = 19501
    sniffer_id: str = ""
    sniffer_name: str = ""
    is_started: bool = False
    channel: int = 0
    packet_count: int = 0
    error: str = ""


class UbiquaClient:
    """Ubiqua REST API 封装"""

    def __init__(self, host: str = "localhost", port: int = 19501):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._timeout = 10

    # ── 内部 ──

    def _get(self, path: str) -> tuple[int, str]:
        """GET 请求 → (status_code, body)"""
        try:
            req = urllib.request.Request(f"{self.base_url}{path}")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return 0, str(e)

    def _put(self, path: str, body: str = "") -> tuple[int, str]:
        """PUT 请求 → (status_code, body)"""
        try:
            data = body.encode("utf-8") if body else b""
            req = urllib.request.Request(
                f"{self.base_url}{path}", data=data, method="PUT",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return 0, str(e)

    def _post(self, path: str, body: str = "") -> tuple[int, str]:
        """POST 请求 → (status_code, body)"""
        try:
            data = body.encode("utf-8") if body else b""
            req = urllib.request.Request(
                f"{self.base_url}{path}", data=data, method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return 0, str(e)

    # ── 连接探测 ──

    def ping(self) -> bool:
        """快速探测 Ubiqua 是否可达"""
        code, _ = self._get("/sniffers")
        return code == 200

    # ── 包数据 ──

    # ── XML 解析辅助 ──

    @staticmethod
    def _xml_packet_count(xml_str: str) -> int:
        """从 /capture XML 提取总包数"""
        try:
            root = ET.fromstring(xml_str)
            packets = root.find(f"{{{NS}}}Packets")
            if packets is not None:
                return int(packets.get("Count", 0))
        except ET.ParseError:
            pass
        return -1

    @staticmethod
    def _xml_parse_packets(xml_str: str) -> list[UbiquaPacket]:
        """从 /capture XML 提取包列表 (路径B数据源)"""
        result = []
        try:
            root = ET.fromstring(xml_str)
            packets = root.find(f"{{{NS}}}Packets")
            if packets is not None:
                for pkt_el in packets.findall(f"{{{NS}}}Packet"):
                    pkt_id = int(pkt_el.get("Id", 0))
                    info = ""
                    source = ""
                    status = ""
                    raw_hex = ""
                    decrypted_hex = ""
                    for child in pkt_el:
                        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                        text = child.text or ""
                        if tag == "Info":
                            info = text
                        elif tag == "Source":
                            source = text
                        elif tag == "Status":
                            status = text
                        elif tag == "Raw":
                            raw_hex = text
                        elif tag == "Decrypted":
                            decrypted_hex = text
                    result.append(UbiquaPacket(
                        packet_id=pkt_id, info=info, source=source,
                        status=status, raw_hex=raw_hex, decrypted_hex=decrypted_hex
                    ))
        except ET.ParseError:
            pass
        return result

    # ── 包数据 ──

    def get_packet_count(self) -> int:
        """GET /capture?offset=0&limit=0 → 总包数"""
        code, body = self._get("/capture?offset=0&limit=0")
        if code == 200:
            count = self._xml_packet_count(body)
            if count >= 0:
                return count
        return -1

    def get_packets_raw(self, offset: int = 0, limit: int = 100) -> Optional[list[UbiquaPacket]]:
        """GET /capture?offset=N&limit=M → 原始包对象列表 (路径B)
        直接返回 Ubiqua 的 Raw/Decrypted hex, 不做协议解析。
        """
        code, body = self._get(f"/capture?offset={offset}&limit={limit}")
        if code == 200:
            pkts = self._xml_parse_packets(body)
            if pkts:
                return pkts
        return None

    def get_packets(self, offset: int = 0, limit: int = 100) -> Optional[list[dict]]:
        """GET /capture?offset=N&limit=M → 原始包列表 (兼容旧接口)"""
        code, body = self._get(f"/capture?offset={offset}&limit={limit}")
        if code == 200:
            # 尝试 JSON (历史兼容), 失败则 XML
            try:
                data = json.loads(body)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    for key in ("packets", "frames", "data", "items"):
                        if key in data and isinstance(data[key], list):
                            return data[key]
                    return [data]
            except json.JSONDecodeError:
                pass
            # XML 格式 → 转为 dict
            pkts = self._xml_parse_packets(body)
            if pkts:
                return [{
                    "id": p.packet_id, "info": p.info,
                    "source": p.source, "status": p.status,
                    "raw_hex": p.raw_hex, "decrypted_hex": p.decrypted_hex,
                } for p in pkts]
        return None

    def save_capture(self, filepath: str) -> bool:
        """PUT /capture action=save → 保存为 cubx"""
        body = urllib.parse.urlencode({"action": "save", "filename": filepath})
        code, _ = self._put("/capture", body)
        return code == 200

    def export_csv(self, filepath: str) -> bool:
        """PUT /capture action=export → 导出 CSV"""
        body = urllib.parse.urlencode({"action": "export", "filename": filepath})
        code, _ = self._put("/capture", body)
        return code == 200

    def clear_capture(self) -> bool:
        """PUT /capture action=clear → 清空 Traffic View"""
        code, _ = self._put("/capture", "action=clear")
        return code in (200, 202)

    def load_capture(self, filepath: str) -> bool:
        """PUT /capture action=load → 加载 cubx 文件"""
        body = urllib.parse.urlencode({"action": "load", "filename": filepath})
        code, _ = self._put("/capture", body)
        return code == 200

    # ── 抓包控制 ──

    def list_sniffers(self) -> Optional[list[dict]]:
        """GET /sniffers → sniffer 列表"""
        code, body = self._get("/sniffers")
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None

    def get_sniffer(self, sniffer_id: str) -> Optional[dict]:
        """GET /sniffers/{id} → 指定 sniffer 详情"""
        code, body = self._get(f"/sniffers/{sniffer_id}")
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None

    def start_sniffer(self, sniffer_id: str, channel: int = 26) -> bool:
        """PUT /sniffers/{id} action=start&channel=N"""
        body = urllib.parse.urlencode({"action": "start", "channel": str(channel)})
        code, _ = self._put(f"/sniffers/{sniffer_id}", body)
        return code == 200

    def stop_sniffer(self, sniffer_id: str) -> bool:
        """PUT /sniffers/{id} action=stop"""
        code, _ = self._put(f"/sniffers/{sniffer_id}", "action=stop")
        return code == 200

    # ── 过滤器 ──

    def list_filters(self) -> Optional[list[dict]]:
        """GET /filters → 过滤器列表"""
        code, body = self._get("/filters")
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None

    def get_filter(self, filter_id: int) -> Optional[dict]:
        """GET /filters/{id} → 过滤器详情"""
        code, body = self._get(f"/filters/{filter_id}")
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None

    def enable_filter(self, filter_name: str) -> bool:
        """PUT /filters action=enable&filter=NAME"""
        body = urllib.parse.urlencode({"action": "enable", "filter": filter_name})
        code, _ = self._put("/filters", body)
        return code == 200

    def disable_filter(self, filter_name: str) -> bool:
        """PUT /filters action=disable&filter=NAME"""
        body = urllib.parse.urlencode({"action": "disable", "filter": filter_name})
        code, _ = self._put("/filters", body)
        return code == 200

    # ── 密钥 ──

    def list_keys(self) -> Optional[list[dict]]:
        """GET /keys → 密钥列表 (含真实 key 值, 注意安全)"""
        code, body = self._get("/keys")
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None

    def add_key(self, key_hex: str, key_type: str = "NetworkKey") -> bool:
        """POST /keys → 新增密钥"""
        body = urllib.parse.urlencode({"type": key_type, "key": key_hex})
        code, _ = self._post("/keys", body)
        return code == 200

    # ── 地址映射 ──

    def get_addresses(self) -> Optional[dict]:
        """GET /addresses → 地址映射表 (~3.8MB)"""
        code, body = self._get("/addresses")
        if code == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return None

    def add_address_mapping(self, long_addr: str, short_addr: str) -> bool:
        """POST /addresses → 新增长短地址映射"""
        body = urllib.parse.urlencode({"longAddress": long_addr, "shortAddress": short_addr})
        code, _ = self._post("/addresses", body)
        return code == 200

    # ── 综合状态 ──

    def get_status(self) -> UbiquaStatus:
        """综合状态查询 → UbiquaStatus"""
        status = UbiquaStatus(host=self.host, port=self.port)

        sniffers = self.list_sniffers()
        if sniffers is None:
            status.error = "无法连接 Ubiqua"
            return status

        status.connected = True

        # 解析 sniffer 列表 (格式待实测确认)
        if isinstance(sniffers, list) and len(sniffers) > 0:
            s0 = sniffers[0]
            if isinstance(s0, dict):
                status.sniffer_id = s0.get("id", s0.get("Id", s0.get("snifferId", "")))
                status.sniffer_name = s0.get("name", s0.get("Name", ""))
                status.is_started = s0.get("isStarted", s0.get("IsStarted", False))
                status.channel = s0.get("channel", s0.get("Channel", 0))
        elif isinstance(sniffers, dict):
            # 可能是单个 sniffer 对象
            status.sniffer_id = sniffers.get("id", sniffers.get("Id", ""))
            status.is_started = sniffers.get("isStarted", sniffers.get("IsStarted", False))
            status.channel = sniffers.get("channel", sniffers.get("Channel", 0))

        status.packet_count = self.get_packet_count()
        return status


# ── 全局客户端实例 ──

_client: Optional[UbiquaClient] = None


def get_client(host: str = "localhost", port: int = 19501) -> UbiquaClient:
    global _client
    if _client is None or _client.host != host or _client.port != port:
        _client = UbiquaClient(host, port)
    return _client
