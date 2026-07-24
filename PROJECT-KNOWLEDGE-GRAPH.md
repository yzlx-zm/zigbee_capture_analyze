# 项目知识图谱：Zigbee Capture Analyzer

> 由 scan-embedded-project 生成。上次扫描：2026-07-24

## 1. 构建系统

| 属性 | 值 |
|------|-----|
| **类型** | Python setuptools / 无正式构建配置 |
| **入口点** | `backend/__main__.py` → `python -m backend` |
| **Python 版本** | 3.13 |
| **虚拟环境** | `.venv/` (venv) |

### 关键依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `fastapi` | ≥0.110.0 | Web 框架 |
| `uvicorn` | ≥0.29.0 | ASGI 服务器 |
| `cryptography` | ≥42.0.0 | AES-CCM* 解密 |
| `pydantic` | ≥2.0.0 | 数据模型 |
| `python-multipart` | ≥0.0.9 | 文件上传 |

### 打包

| 属性 | 值 |
|------|-----|
| **打包工具** | PyInstaller (计划中) |
| **配置** | PyInstaller hooks: `config.FRONTEND_DIR` 适配 `sys._MEIPASS` |

## 2. 技术栈

| 层 | 技术 | 文件 |
|----|------|------|
| **后端框架** | FastAPI + uvicorn | `backend/app.py`, `backend/__main__.py` |
| **API 路由** | FastAPI APIRouter | `backend/api/router.py` |
| **前端** | 原生 ES6 SPA (无 npm/构建) | `frontend/index.html` (单文件) |
| **图可视化** | Cytoscape.js v3.30.4 (本地 vendored) | `frontend/lib/cytoscape.min.js` |
| **pcap 解析** | tshark (Wireshark CLI) | `backend/tshark.py` |
| **AES-CCM*** | cryptography 库 ECB 原语 | `backend/security.py` (规划中) |
| **前端路由** | Hash-based (`#import`, `#topo`, `#tl`, `#nodes`, `#ai`) | `frontend/index.html` `rt()` |
| **样式** | 内联 `<style>` + 行内 `style=""` (app.css 存在但未被 HTML 引用) | `frontend/css/app.css` |

## 3. 协议栈

### Zigbee 解析层次

| 层 | 解析方式 | 关键字段 |
|----|---------|---------|
| **MAC (802.15.4)** | tshark `wpan` 层 | `wpan.src16`, `wpan.dst16`, `wpan.fcf`, `wpan.fcs_ok` |
| **NWK** | tshark `zbee_nwk` 层 | `zbee_nwk.src`, `zbee_nwk.dst`, `zbee_nwk.radius`, `zbee_nwk.src64` |
| **NWK 命令** | tshark `Command Frame:*` | Link Status, Route Request/Reply/Record, Network Status, Leave |
| **Security** | AES-CCM* (security level 5) | `zbee.sec.counter`, `zbee.sec.key`, `zbee.sec.mic` |
| **APS** | tshark `zbee_aps` 层 | `zbee_aps.cluster`, `zbee_aps.profile`, `zbee_aps.counter` |
| **ZDP** | tshark `zbee_aps.zdp_*` 字段 | Node Desc, Mgmt LQI, Active EP, Device Announce |
| **ZCL** | tshark `zbee_zcl` 层 | `zbee_zcl.cmd.id`, `zbee_zcl.cmd.tsn` |

### tshark 调用方式

```
# 主解析 (JSON 模式)
tshark -r <pcap> -Y "zbee_nwk" -T json

# 补充 relay 列表 (JSON 多实例字段只保留最后一个)
tshark -r <pcap> -Y "zbee_nwk.cmd.id == 0x05" -T fields -e frame.number -e zbee_nwk.cmd.relay_device
```

### 解密

| 属性 | 值 |
|------|-----|
| **密钥类型** | NWK Key (AES-128) |
| **密钥文件** | `%APPDATA%/Wireshark/zigbee_pc_keys` |
| **格式** | `"HEX","Normal","Label"` (每行一个) |
| **TC Link Key** | ZigBeeAlliance09 (`5A:69:67:42:65:65:41:6C:6C:69:61:6E:63:65:30:39`) |
| **解密判断** | APS 层 Counter 字段存在 → 已解密 |

### 输入格式

| 格式 | DLT | 支持状态 |
|------|-----|---------|
| classic pcap | DLT 195 (802.15.4 with FCS) | ✅ 已实现 |
| pcapng | - | ✅ 已实现 |
| Ubiqua .cubx | SQLite | ⏳ 规划中 |

## 4. 模块依赖图

```
backend/
├── __main__.py          ← 入口 (uvicorn + webbrowser)
├── app.py               ← FastAPI create_app() (依赖于 api.router)
├── config.py            ← 全局配置 (端口, 路径, PyInstaller)
├── tshark.py            ← tshark 调用 + JSON 解析 → _frame_to_dict()
│   └── 依赖: zcl_defs.py
├── topology.py           ← 拓扑构建 (Link Status 邻居表 + Route Record 路径 + 不对称检测)
│   └── 被引用: api/topology.py
├── csv_reader.py         ← Ubiqua CSV 解析 (Phase 1)
├── key_store.py          ← zigbee_pc_keys 读写
├── zcl_defs.py           ← ZCL Cluster/Command 名称映射
├── verify.py             ← 数据校验 (6 维度, tshark 为 ground truth)
├── api/
│   ├── router.py         ← 路由聚合 (prefix="/api")
│   ├── files.py          ← 导入 + 包列表 + 包详情 API
│   │   └── 依赖: csv_reader, tshark, key_store, verify
│   ├── topology.py       ← 拓扑图 + 节点列表 API
│   │   └── 依赖: topology.build()
│   └── keys.py           ← 密钥管理 + 重新解密 API
│       └── 依赖: key_store
└── models/               ← (规划中, 当前无文件)

frontend/
├── index.html            ← 单文件 SPA (所有页面 + 路由 + 状态)
├── css/app.css           ← 样式补充
├── lib/
│   └── cytoscape.min.js  ← Cytoscape.js v3.30.4 (373KB)
└── (规划: js/views/, js/components/)
```

### 依赖方向

```
api/router.py → files.py, topology.py, keys.py
files.py → csv_reader, tshark, key_store, verify
topology.py → topology.build()
keys.py → key_store
tshark.py → zcl_defs
app.py → api/router
__main__.py → app (factory)
```

## 5. API 表面

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/api/import/files` | POST | 多文件上传 (.csv) | 包数/节点数/类型分布 |
| `/api/import/local` | POST | path (CSV) | 同上 |
| `/api/import/pcap` | POST | 多文件上传 (pcap/pcapng) | 包数/节点数/类型/解密/校验 |
| `/api/import/local-pcap` | POST | paths (逗号分隔) | 同上 |
| `/api/import/clear` | DELETE | - | ok |
| `/api/import/status` | GET | - | 总包数/节点数/类型/时间范围/校验 |
| `/api/import/verify` | GET | - | 校验报告 |
| `/api/packets` | GET | addr/pan/time_start/time_end/pkt_type/limit/offset | 分页包列表+总数 |
| `/api/packets/summary` | GET | addr/pan/time_start/time_end | 设备行为摘要或PAN统计 |
| `/api/packets/{pkt_id}` | GET | - | 单帧完整协议树 (raw_layers) |
| `/api/topology/graph` | GET | pan | 拓扑图数据 (节点/边/邻居表/路径/不对称) |
| `/api/nodes` | GET | search/pan | 节点列表 |
| `/api/keys` | GET | - | 所有密钥 |
| `/api/keys` | POST | {key, label} | 添加密钥 |
| `/api/keys/{label}` | DELETE | - | 删除密钥 |
| `/api/keys/reprocess` | POST | - | 重新解密 (用新密钥) |

## 6. 数据模型

### 内部包 dict (_frame_to_dict 输出)

```python
{
    "ts": float, "ch": int,
    "pkt_type": str,           # "Link Status" / "Route Record" / "Data" / "ZDP: Node Desc Resp" 等
    "pan_src/pan_dst": int|None,
    "mac_src/mac_dst": int|None,
    "nwk_src/nwk_dst": int|None, "nwk_seq": int|None,
    "security": str,           # "Decrypted" / "Encrypted"
    "status": str,
    "aps_cluster": int|None, "aps_cluster_name": str,
    "aps_profile": int|None,
    "zcl_cmd_id": int|None, "zcl_cmd_name": str|None,
    "decrypted": bool,
    "link_status_neighbors": list[dict]|None,  # [{addr, in_cost, out_cost}]
    "route_record_relays": dict|None,          # {count, relays: [addr, ...]}
    "raw_layers": dict,        # 完整 tshark JSON 层树
}
```

### 节点 dict

```python
{
    "aid": int, "seen": int, "pan": int|None,
    "is_coord": bool, "type_list": list[str],
    "device_type": "coordinator"|"router"|"end_device"|"unknown",
}
```

### 全局状态 (内存存储)

```python
_packets: list[dict]    # 全部包
_nodes: dict[int, dict] # 全部节点
_file_type: str         # "csv"|"pcap"
_verify_report: dict    # 校验报告
_pcap_paths: list[str]  # 最后一次导入的 pcap 路径
```

## 7. 前端架构

### 页面路由 (hash-based)

| Hash | 页面 | 功能 |
|------|------|------|
| `#import` | 导入页 | CSV/pcap 上传、密钥管理、校验报告 |
| `#topo` | 拓扑页 | Cytoscape 力导向图 + 路由路径链 + 邻居面板 + 层级树 |
| `#tl` | 时间线 | 包列表(分页) + 协议详情面板 |
| `#nodes` | 节点 | 节点搜索 + 列表 |
| `#ai` | AI | 预留 |

### 全局状态对象 `S`

```javascript
S = {
    pkts, nodes,           // 统计
    topo, topoPan, topoAddr,  // 拓扑
    tlPan, tlNode, tlType, tlHasSearched,  // 时间线过滤
    tlTs0H/M/S, tlTs1H/M/S,  // 时间线时间范围
    impTab, verifyPassed,    // 导入
}
```

### 跨页面联动

- 拓扑 → 时间线: `S.topoPan` / `S.topoAddr` → `location.hash='tl'`
- 时间线 → 拓扑: `S.topoAddr` (双向), 回拓扑时 `highlightNode()`

## 8. 已有文档

| 文件 | 内容 | 行数 |
|------|------|------|
| `CLAUDE.md` | AI 协作配置 (本文件) | ~30 |
| `.claude/skills/qa-align.md` | Q&A 需求对齐 Skill | 148 |
| `docs/design_v2.md` | Phase 1 设计 | - |
| `docs/design_v3.md` | Phase 2 设计 | - |
| `docs/network_analysis_kb.md` | 16 种帧诊断知识库 | 576 |
| `docs/diagnosis_playbook.md` | 5 大类 19 子场景诊断手册 | 686 |
| `docs/decryption_setup.md` | 解密流程文档 | - |
| `docs/acceptance_criteria.md` | 验收标准 | - |
| `docs/weekly-reports/` | 周报 | - |
| `README.md` | 项目说明 | - |
