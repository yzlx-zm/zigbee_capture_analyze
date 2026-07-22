# Zigbee Capture Analyzer — 设计文档 v3 (Phase 2: pcap + 协议详情)

## 概述

v3 在 v2 的 CSV 导入 + 拓扑/时间线基础上，新增 **pcap 导入 + tshark 解密 + 单包协议栈分解**。

### 核心设计原则
- **一项功能一次改动** — 每次只改一个功能点，验证后再继续
- **CSV 与 pcap 独立并行** — 两套导入共存，共享下游 API
- **tshark 内置于 PyInstaller exe** — 最终打包时包含 tshark.exe + 依赖 DLL

---

## 1. 数据处理流程

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Sniffer 抓包  │────→│ Ubiqua 导出 pcap  │────→│ 我们的工具导入    │
│ (原始加密)    │     │ (文件不变, 仍加密) │     │                 │
└──────────────┘     └──────────────────┘     └────────┬────────┘
                                                       │
                          ┌────────────────────────────┘
                          │
                   ┌──────▼──────┐
                   │ 写入 NWK Key │ → zigbee_pc_keys 文件
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ tshark -T   │ → 批量 JSON 解析 (5-10s, ~13546帧)
                   │ json 全解析  │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ Python 合并  │ → 多文件按时间戳排序, 统一数据格式
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ 内存存储     │ → _packets dict list (兼容现有 API)
                   │ + 可选导出   │
                   └─────────────┘
```

### 数据格式

tshark JSON 帧 → 内部 dict:

```python
{
    "ts": 1781813813.796795,     # Unix 时间戳
    "ch": 0,
    "pkt_type": "Data",          # MAC 帧类型
    "pan_src": 0xfeed, "pan_dst": 0xfeed,
    "mac_src": 0x0000, "mac_dst": 0x2bd6,
    "mac_seq": 137,
    "nwk_src": 0x0000, "nwk_dst": 0x2bd6,
    "nwk_seq": 194,
    "security": "Encrypted",     # "Encrypted" | "Decrypted"
    "status": "Decrypted",       # 解密状态
    "aps_cluster": 0x0019,       # APS Cluster ID (加密帧为 None)
    "aps_cluster_name": "OTA Upgrade",  # ZCL 名称映射
    "aps_profile": 0x0104,
    "aps_counter": 178,
    "aps_src_ep": 1, "aps_dst_ep": 1,
    "zcl_cmd_id": 0x02,
    "zcl_cmd_name": "Query Next Image Response",
    "zcl_direction": "Server→Client",
    "zcl_seq": 115,
    "sec_level": 5,
    "sec_key_label": "Key2",     # 匹配到的 Key 标签
    "sec_frame_counter": 66794,
    "decrypted": True,           # 是否有 APS/ZCL 数据
    "raw_layers": {...},         # 完整 tshark JSON (用于协议详情)
}
```

---

## 2. 后端 API 设计

### 2.1 已存在 (不变)
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/import/files` | POST | CSV 上传 |
| `/api/import/local` | POST | CSV 本地路径 |
| `/api/import/status` | GET | 当前数据状态 |
| `/api/import/clear` | DELETE | 清除数据 |
| `/api/packets` | GET | 包列表 (分页/过滤) |
| `/api/packets/summary` | GET | 事件摘要 |
| `/api/topology/graph` | GET | 拓扑图 |
| `/api/nodes` | GET | 节点列表 |

### 2.2 新增

| 端点 | 方法 | 说明 | 入参 | 返回值 |
|------|------|------|------|--------|
| `/api/import/pcap` | POST | pcap 文件上传 (多文件) | `files: List[UploadFile]` | `{ok, packets, nodes, file_type, by_type, decrypt_stats}` |
| `/api/import/local-pcap` | POST | pcap 本地路径 | `paths: List[str]` (JSON body) | 同上 |
| `/api/keys` | GET | 获取已配置 Key 列表 | - | `[{hex, label, matched, frame_count}]` |
| `/api/keys` | POST | 添加 Key | `{key: str, label: str}` | `{ok, label}` |
| `/api/keys/{label}` | DELETE | 删除 Key | - | `{ok}` |
| `/api/packets/{pkt_id}` | GET | 单帧协议树 | - | `{packet: {...raw_layers}}` |
| `/api/settings/tshark-path` | GET/PUT | tshark 路径配置 | `{path: str}` | `{path}` |

### 2.3 解密统计 (decrypt_stats)

```json
{
    "total_data_frames": 1902,
    "decrypted": 763,
    "encrypted": 1139,
    "decrypt_rate": 0.40,
    "by_cluster": {"0x0000": 378, "0x0019": 316, "0xFCFA": 69},
    "matched_keys": ["Key2"],
    "unmatched_keys": ["Key0", "Key1", "Key3", ...]
}
```

---

## 3. 前端页面设计

### 3.1 导入页 — 横向 Tab 切换

```
┌──────────────────────────────────────────────┐
│  [📊 CSV 快速预览]  [📡 pcap 深度分析]        │
├──────────────────────────────────────────────┤
│                                              │
│  CSV Tab (现有功能保持不变)                    │
│  - 拖拽 .csv 文件                             │
│  - 或输入本地路径                              │
│  - 导入结果 + 清除按钮                         │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  pcap Tab (新增)                              │
│  ┌─ 上传区 ────────────────────────────────┐  │
│  │  拖拽 .pcap 文件 (支持多选)              │  │
│  │  或输入本地路径 (逗号分隔多个)            │  │
│  │  [🔍 开始导入]  [🗑 清除数据]            │  │
│  └──────────────────────────────────────────┘  │
│  ┌─ 导入结果 ─────────────────────────────┐  │
│  │  📊 13546 包 | 3220 节点 | pcap        │  │
│  │  类型: Link Status×4400, Data×1902 ... │  │
│  └──────────────────────────────────────────┘  │
│  ┌─ 🔑 密钥管理 [展开/折叠] ───────────────┐  │
│  │  预设 Key:                               │  │
│  │  ● ZigBeeAlliance09 [TC Link Key 常驻]   │  │
│  │                                         │  │
│  │  自定义 NWK Key:                         │  │
│  │  ● FF214D7A... [✓ Key2 命中 316帧] [✕] │  │
│  │  ○ FC90D263... [✗ 未命中]        [✕]  │  │
│  │  ○ E265F283... [✗ 未命中]        [✕]  │  │
│  │  ...                                     │  │
│  │  ┌─────────────────────────────────┐    │  │
│  │  │ 粘贴 16 字节 hex Key (支持       │    │  │
│  │  │ FC:90:D2:63 或 FC90D263 等格式) │    │  │
│  │  └─────────────────────────────────┘    │  │
│  │  [标签: Key57___] [+ 添加]              │  │
│  │                                         │  │
│  │  📊 解密: 763/1902 Data 帧 (40%)        │  │
│  │  Cluster: Basic×378 OTA×316 Private×69  │  │
│  └──────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 3.2 时间线页 — 扩展列

pcap 模式下在现有 8 列基础上增加：

| 时间 | 类型 | MAC Src→Dst | NWK Src→Dst | **Cluster** | **ZCL Cmd** | 状态 | 安全 |
|------|------|-------------|-------------|-------------|-------------|------|------|
| 04:16:53 | Data | 0x0000→0x2bd6 | 0x0000→0x2bd6 | **OTA Upgrade** | **Query Next Image** | ✅ | Decrypted |
| 04:16:53 | Cmd | 0xecb1→0xfffc | 0xecb1→0xfffc | - | - | 🔒 | Encrypted |

- ✅ 绿色 = APS/ZCL 已解密
- 🔒 灰色 = 加密 (NWK 命令或未知 Key)

### 3.3 包列表 + 协议详情 (左右分栏)

```
┌── 包列表 (flex:1, 可滚动) ──┬── 协议详情 (width: ~420px) ──────────┐
│ 8-10列表格                    │ ▎ MAC  ────────────────────────── │
│ 点击任意行 → 右侧更新          │ ▎ Frame Type: Data                │
│ 当前选中行高亮 (蓝色背景)      │ ▎ Seq#: 137                       │
│                              │ ▎ Dest PAN: 0xFEED                │
│ 分页控制                     │ ▎ Dest: 0x2BD6  Src: 0x0000       │
│                              │ ▎ FCS: 0xAD7D ✓                  │
│                              │ ▎                                │
│                              │ ▎🌐 NWK ──────────────────────  │
│                              │ ▎ Frame Type: Data (0x0208)      │
│                              │ ▎ Dest: 0x2BD6  Src: 0x0000      │
│                              │ ▎ Radius: 30  Seq#: 194          │
│                              │ ▎ Src IEEE: b4:e3:f9:ff:fe:0a:… │
│                              │ ▎                                │
│                              │ ▎🔒 Security Header ──────────  │
│                              │ ▎ Level: AES-128 + 32-bit MIC    │
│                              │ ▎ Key ID: Network Key            │
│                              │ ▎ Frame Counter: 66794           │
│                              │ ▎ Key Seq#: 0                    │
│                              │ ▎ MIC: ab1b7f39                  │
│                              │ ▎ Matched Key: Key2              │
│                              │ ▎                                │
│                              │ ▎📦 APS ──────────────────────  │
│                              │ ▎ Frame Control: 0x40 (Data)     │
│                              │ ▎ Dest EP: 1  Src EP: 1          │
│                              │ ▎ Cluster: OTA Upgrade (0x0019)   │
│                              │ ▎ Profile: Home Automation (0x0104)│
│                              │ ▎ Counter: 178                    │
│                              │ ▎                                │
│                              │ ▎🎯 ZCL ──────────────────────  │
│                              │ ▎ Frame Type: Cluster-specific    │
│                              │ ▎ Command: Query Next Image (0x02)│
│                              │ ▎ Direction: Server → Client      │
│                              │ ▎ Seq#: 115                       │
│                              │ ▎ Payload:                        │
│                              │ ▎   Status: 0x98                  │
│                              │ ▎   (OTA: No Image Available)     │
│                              │ ▎                                │
│                              │ ┌─ Raw Hex ─── [▶ 展开] ──────┐ │
│                              │ │ 0000  41 88 63 74 02 ff ff   │ │
│                              │ │ 0008  b1 ec 09 12 fc ff b1   │ │
│                              │ │ 0010  ec 1e 05 e2 43 0f 69   │ │
│                              │ │ ...                          │ │
│                              │ │ (选中字段对应字节高亮)          │ │
│                              │ └──────────────────────────────┘ │
└──────────────────────────────┴───────────────────────────────────┘
```

**颜色标识 (左侧色条):**
- 🟡 MAC: 金色
- 🔵 NWK: 蓝色
- 🔴 Security Header: 红色
- 🟢 APS: 绿色
- 🟣 ZCL: 紫色

**加密帧展示:**
```
▎📦 APS ──────────────────────
▎  🔒 Encrypted Payload
▎
▎🎯 ZCL ──────────────────────
▎  🔒 Encrypted (需要正确的 Network Key)
▎  Raw: 3B 5B 0F 4F 2B 6B 0E CC ...
```

### 3.4 密钥管理面板 (Key Store)

```
┌─ 🔑 密钥管理 ────────────────────────────────┐
│                                               │
│  预设密钥 (不可删除):                           │
│  ┌─────────────────────────────────────────┐  │
│  │ ● 5A696742...  ZigBeeAlliance09  [TC LK] │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  自定义 NWK Key:                               │
│  ┌─────────────────────────────────────────┐  │
│  │ ● FF214D7A...  Key2  [✓ 命中 316帧] [✕]│  │
│  │ ○ FC90D263...  Key0  [✗ 未命中]     [✕]│  │
│  │ ○ E265F283...  Key1  [✗ 未命中]     [✕]│  │
│  │ ○ 579B5DFD...  Key3  [✗ 未命中]     [✕]│  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  ┌──────────────────────────────────────┐     │
│  │ 粘贴 Key: FC:90:D2:63:8C:F7:...      │     │
│  └──────────────────────────────────────┘     │
│  [Key57________________] [+ 添加]             │
│                                               │
│  📊 命中统计: 1/5 Key 生效, 763/1902 帧解密   │
│  (可折叠 ↑)                                   │
└───────────────────────────────────────────────┘
```

**状态逻辑:**
- `✓ 命中` = 至少 1 帧用此 Key 成功解密 (MIC 校验通过)
- `✗ 未命中` = 没有任何帧匹配此 Key
- 命中 Key 显示绿色圆点 ●，未命中显示空心圆 ○

---

## 4. 后端模块设计

### 4.1 `tshark.py` — tshark 调用封装

```python
def find_tshark() -> str | None:
    """查找 tshark.exe 路径"""

def check_tshark(path: str) -> bool:
    """验证 tshark 是否可用"""

def import_pcaps(file_paths: list[str], tshark_path: str) -> list[dict]:
    """批量导入多个 pcap 文件, 返回合并后的包列表"""

def parse_pcap_to_json(pcap_path: str, tshark_path: str) -> list[dict]:
    """调用 tshark -T json 解析单个 pcap, 返回帧列表"""

def extract_layers(tshark_frame: dict) -> dict:
    """从 tshark JSON 帧中提取各层字段"""
```

### 4.2 `key_store.py` — 密钥文件管理

```python
PRESET_KEYS = {
    "ZigBeeAlliance09": "5A6967426565416C6C69616E63653039",
}

def get_keys_file_path() -> str:
    """返回 zigbee_pc_keys 文件路径"""

def read_keys() -> list[dict]:
    """读取所有 Key: [{hex, label, is_preset}]"""

def add_key(key_hex: str, label: str) -> bool:
    """添加一个 Key 到文件"""

def remove_key(label: str) -> bool:
    """删除一个 Key (预设 Key 不可删除)"""

def write_all_keys(keys: list[dict]) -> None:
    """写入全部 Key 到文件"""

def get_match_stats(packets: list[dict]) -> dict:
    """统计每个 Key 的命中帧数 + 总体解密率"""
```

### 4.3 `zcl_defs.py` — ZCL 定义库

```python
ZCL_CLUSTERS = {
    0x0000: "Basic",
    0x0001: "Power Configuration",
    0x0002: "Device Temperature Configuration",
    0x0003: "Identify",
    0x0004: "Groups",
    0x0005: "Scenes",
    0x0006: "On/Off",
    0x0007: "On/Off Switch Configuration",
    0x0008: "Level Control",
    0x0009: "Alarms",
    0x000A: "Time",
    0x000F: "Binary Input (Basic)",
    0x0019: "OTA Upgrade",
    0x0020: "Poll Control",
    0x0101: "Door Lock",
    0x0102: "Window Covering",
    0x0201: "Thermostat",
    0x0202: "Fan Control",
    0x0300: "Color Control",
    0x0400: "Illuminance Measurement",
    0x0402: "Temperature Measurement",
    0x0403: "Pressure Measurement",
    0x0405: "Humidity Measurement",
    0x0406: "Occupancy Sensing",
    0x0500: "IAS Zone",
    0x0501: "IAS ACE",
    0x0502: "IAS WD",
    0x0702: "Smart Energy Metering",
    0x0B05: "Diagnostics",
}

ZCL_COMMANDS = {
    "global": {
        0x00: "Read Attributes",
        0x01: "Read Attributes Response",
        0x02: "Write Attributes",
        0x03: "Write Attributes Undivided",
        0x04: "Write Attributes Response",
        0x05: "Write Attributes No Response",
        0x06: "Configure Reporting",
        0x07: "Configure Reporting Response",
        0x08: "Read Reporting Configuration",
        0x09: "Read Reporting Configuration Response",
        0x0A: "Report Attributes",
        0x0B: "Default Response",
        0x0C: "Discover Attributes",
        0x0D: "Discover Attributes Response",
        0x0E: "Read Attributes Structured",
        0x0F: "Write Attributes Structured",
        0x10: "Write Attributes Structured Response",
    },
    0x0019: {  # OTA Upgrade
        0x00: "Image Notify",
        0x01: "Query Next Image Request",
        0x02: "Query Next Image Response",
        0x03: "Image Block Request",
        0x04: "Image Page Request",
        0x05: "Image Block Response",
        0x06: "Upgrade End Request",
        0x07: "Upgrade End Response",
    },
}

def get_cluster_name(cluster_id: int) -> str:
    """Cluster ID → 名称"""

def get_command_name(cluster_id: int | None, cmd_id: int) -> str:
    """Command ID → 名称 (先查 cluster-specific, 再查 global)"""
```

---

## 5. 实现步骤

按顺序逐项实现，每项完成后验证：

### Step 1: 后端基础设施
- [ ] `key_store.py` — zigbee_pc_keys 读写 + 预设 Key
- [ ] `zcl_defs.py` — Cluster/Command 名称映射
- [ ] `tshark.py` — tshark 查找 + 单文件 JSON 解析
- [ ] 测试: 用 test2-ubiqua-export.pcap + Key2 验证 tshark 解析输出

### Step 2: pcap 导入 API
- [ ] `POST /api/import/pcap` — 多文件上传 + tshark 解析 + 内存存储
- [ ] `POST /api/import/local-pcap` — 本地路径导入
- [ ] 数据格式适配: tshark JSON → 内部 dict (兼容现有 _packets)
- [ ] 测试: curl 导入 → 验证 topology/timeline API 正常工作

### Step 3: Key 管理 API
- [ ] `GET /api/keys` — 读取已配置 Key + 命中统计
- [ ] `POST /api/keys` — 添加 Key
- [ ] `DELETE /api/keys/{label}` — 删除 Key
- [ ] 测试: curl 添加 Key → 验证 zigbee_pc_keys 文件更新

### Step 4: 单帧协议树 API
- [ ] `GET /api/packets/{id}` — 返回 raw_layers 完整 JSON
- [ ] 测试: curl 获取帧 302 → 验证四层字段完整

### Step 5: 导入页改造
- [ ] 横向 Tab (CSV / pcap)
- [ ] pcap Tab 上传区 (拖拽 + 路径)
- [ ] 导入结果展示 (含解密统计)
- [ ] 测试: 浏览器上传 pcap → 看结果

### Step 6: Key 管理面板
- [ ] 可折叠面板 UI
- [ ] 预设 Key + 自定义 Key 列表
- [ ] 添加/删除交互
- [ ] 命中状态标签 (✓/✗)
- [ ] 测试: 添加 Key → 刷新看命中状态

### Step 7: 协议详情面板 (左右分栏)
- [ ] 时间线页改布局: 左侧包列表 + 右侧详情
- [ ] 详情面板: 五层连续列表 (MAC/NWK/Security/APS/ZCL) + 左侧色条
- [ ] 加密帧展示 🔒
- [ ] 包列表增加 Cluster/ZCL Cmd/解密状态 列
- [ ] 点击帧 → 详情更新 + 当前行高亮
- [ ] 测试: 点解密帧 → 看 OTA Upgrade 详情; 点加密帧 → 看 🔒 标记

### Step 8: Raw Hex 面板
- [ ] 详情面板底部折叠区
- [ ] offset + hex bytes + ASCII 三列
- [ ] 选中字段高亮 (后续迭代)
- [ ] 测试: 展开 Raw Hex → 看完整帧 hex

---

## 6. PyInstaller 打包

```python
# zigbee_analyzer.spec 关键配置
a = Analysis(
    ...
    datas=[
        ('frontend/', 'frontend/'),          # 前端 HTML/CSS/JS
        ('D:/work_tool/Wireshark/tshark.exe', '.'),  # tshark 可执行文件
        # tshark 依赖的 DLL 需手动收集
    ],
)
```

打包后由 `__main__.py` 中的代码在运行时动态定位 tshark (检查 `sys._MEIPASS` 或 `sys.executable` 同级目录)。

---

## 7. 依赖

| 组件 | 用途 | 打包 |
|------|------|------|
| tshark.exe 4.6.2 | Zigbee 协议解析 + 解密 | 内置到 exe |
| cryptography | (备用: AES-CCM* 验证) | requirements.txt |
| fastapi + uvicorn | Web 后端 | 已有 |
| zigbee_pc_keys | Key 配置文件 | 运行时写入 %APPDATA% |

---

## 8. 测试验证标准

每个 Step 的验收条件:
1. **API 正确性**: curl 测试端点返回正确数据
2. **解密验证**: 帧 302 显示 OTA Upgrade Cluster + Query Next Image 命令
3. **UI 交互**: 浏览器操作无卡顿、无 JS 错误
4. **向后兼容**: CSV 导入和现有页面不受影响
