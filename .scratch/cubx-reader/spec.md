# cubx_reader.py — 设计规范

> 来源：2026-07-30 /grilling 会话。参考：akubela `_capture_probe.py`。

## 概述

- **模块名称**：`backend/cubx_reader.py`
- **目标**：Ubiqua .cubx 文件直读，输出兼容 tshark._frame_to_dict 的 dict 格式
- **在架构中的位置**：与 `tshark.py` 平行的输入源；输出后进入同一事件管道
- **依赖**：scapy（Dot15d4FCS, ZigbeeNWK, ZigbeeSecurityHeader）, pycryptodome（AES-CCM）

## 核心设计决策

| # | 决策 | 结论 | 来源 |
|---|------|------|------|
| 1 | 集成路径 | scapy 自解析（最完整，保留 LQI/RSSI/Channel） | grilling Q1 |
| 2 | 架构 | 独立模块 cubx_reader.py | grilling Q2 |
| 3 | MVP 字段范围 | 核心字段（拓扑+诊断可用），LQI/RSSI 首版带上 | grilling Q3 |

## 数据流

```
.cubx ─→ SQLite read
         ├─ Keys → key_store.merge_from_ubiqua() → zigbee_pc_keys
         └─ Packets → scapy Dot15d4FCS → decrypt → parse → list[dict]
                                                              │
                           (与 tshark._frame_to_dict 格式兼容)  │
                                                              ▼
                                              events pipeline (无感切换)
```

## 公开接口

```python
def parse_cubx(path: str) -> tuple[list[dict], int, int]:
    """解析 .cubx 文件 → (包列表, key新增数, key总数).
    key 自动同步到 zigbee_pc_keys.
    """
```

## 内部模块

### 1. cubx_key_loader

```python
def _load_cubx_keys(db: sqlite3.Connection) -> tuple[list[KeyRecord], list[KeyRecord]]:
    """读取 Keys 表 → (network_keys, link_keys). 格式: KeyRecord(label, value: bytes)."""
```

### 2. cubx_decrypt（参考 akubela）

```python
def _zigbee_hash(value: bytes) -> bytes:
    """AES-MMO hash (Zigbee spec B.1.3/B.6)."""

def _decrypt_nwk(nwk_frame, network_keys) -> tuple[bytes, str]:
    """NWK ENC-MIC-32 解密. 返回 (明文, key_label)."""

def _decrypt_aps(aps_frame, network_keys, link_keys) -> tuple[bytes, str]:
    """APS ENC-MIC-32 解密, 含 transport key 派生."""
```

### 3. cubx_frame_parser

```python
def _raw_to_dict(raw_bytes, packet_id, timestamp, channel, lqi, rssi,
                 network_keys, link_keys) -> dict:
    """单帧解析: 802.15.4→NWK→APS→ZCL/ZDP, 输出兼容 tshark dict."""
```

输出字段（MVP）：
- `ts`(float), `ch`(int), `lqi`(int), `rssi`(int)
- `pkt_type`(str): Beacon / Data / Acknowledgement / MAC Cmd / NWK Cmd / Route Record / Route Request / Link Status / Leave / Network Status / ZDP: * / APS Ack / ...
- `mac_src`, `mac_dst`, `pan_src`, `pan_dst`
- `nwk_src`, `nwk_dst`, `nwk_radius`, `nwk_seq`, `nwk_src64`
- `aps_cluster`, `aps_counter`, `aps_src_ep`, `aps_dst_ep`
- `decrypted`(bool), `security`(str)
- `link_status_neighbors`: [{addr, in_cost, out_cost}] or None
- `route_record_relays`: {count, relays: [addr, ...]} or None
- `raw_layers`: {} (MVP 置空, 后续补 scapy layer 序列化)

### 4. pkt_type 判别

根据 MAC FCF frame_type + NWK command + APS/ZDP cluster 推断，与 tshark._pkt_type 逻辑对齐。

## 验证策略

| 层级 | 方法 |
|------|------|
| 单元 | `parse_cubx(test2.cubx)` → assert len==9341, 和 tshark(test2.pcap) 对比 pkt_type 分布 |
| 集成 | 导入后拓扑页/诊断页正常渲染, 数据与 pcap 导入一致 |
| 回归 | pcap 导入路径不受影响 |

## 不包含的范围

- APS Tunnel 解密（akubela 有，MVP 不实现，后续工单）
- ZCL payload 深度解析（Basic cluster 字符串提取等）
- Addresses/Nodes 表读取
- raw_layers 兼容输出

## 关键文件

| 文件 | 角色 |
|------|------|
| `backend/cubx_reader.py` | 新模块：SQLite→scapy→decrypt→dict |
| `backend/api/files.py` | 新增 `.cubx` 导入路径 |
| `CONTEXT.md` | cubx 术语（已更新） |
| `.scratch/cubx-reader/spec.md` | 本文件 |
