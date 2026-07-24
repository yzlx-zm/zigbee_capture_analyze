"""Ubiqua 包解析器 — 路径B: 直接从 Raw/Decrypted hex 解析协议字段

当前状态: 预留接口, 未实现完整协议解析。
路径A (tshark) 已验证可用, 路径B 在以下场景启用:
  - tshark 不可用时 (打包分发场景)
  - 需要 Ubiqua 独有的元数据字段 (RSSI/LQI/Timestamp 等)
  - 性能优化 (跳过 tshark 子进程调用)

Ubiqua 的 /capture API 返回每个包的 Raw 和 Decrypted hex 字节。
Decrypted 字段是 NWK 层解密后的完整 802.15.4 帧。
可以从中解析: MAC 头 → NWK 头 → APS 头 → ZCL/ZDP payload。

解析规范参考:
  - IEEE 802.15.4-2006 (MAC)
  - Zigbee Specification r22 (NWK/APS/ZCL)
  - docs/network_analysis_kb.md (帧字段参考)
"""
from __future__ import annotations

from typing import Optional
from .ubiqua_api import UbiquaPacket


class UbiquaPacketParser:
    """Ubiqua Raw/Decrypted hex → 内部 dict (路径B)"""

    def parse(self, pkt: UbiquaPacket) -> Optional[dict]:
        """
        解析单个 Ubiqua 包为内部 dict 格式 (兼容 tshark _frame_to_dict 输出)。

        当前: 返回 None (未实现), 调用方应 fallback 到 tshark 路径。
        后续: 实现 MAC/NWK/APS/ZCL 逐层解析。

        优先级: Decrypted hex (已解密) > Raw hex (可能加密)
        """
        hex_data = pkt.decrypted_hex or pkt.raw_hex
        if not hex_data:
            return None

        # TODO: 逐层解析 802.15.4 帧
        # 1. MAC header (FCF → 帧类型/寻址模式/安全)
        # 2. NWK header (FCF → 帧类型/安全/源路由)
        # 3. NWK payload → APS or NWK Command
        # 4. APS payload → ZCL or ZDP

        return None

    def parse_batch(self, pkts: list[UbiquaPacket]) -> list[dict]:
        """批量解析, 跳过无法解析的包"""
        results = []
        for pkt in pkts:
            parsed = self.parse(pkt)
            if parsed is not None:
                results.append(parsed)
        return results
