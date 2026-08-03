# 项目知识图谱：Zigbee Capture Analyzer

> 由 scan-embedded-project 生成。上次扫描：2026-07-31

## 1. 构建系统 & 运行时

| 属性 | 值 |
|------|-----|
| **类型** | Python CLI (无 setup.py/pyproject.toml) |
| **入口** | `python -m backend [--port PORT] [--no-browser]` |
| **Python** | 3.13 (系统安装, `C:\Python313\`) |
| **虚拟环境** | 无 (直接使用系统 Python) |
| **打包** | PyInstaller 预留 (`config.py` 已适配 `sys._MEIPASS`) |
| **默认端口** | 8720 (auto-port 模式默认 0) |
| **主机** | 127.0.0.1 |

### 关键依赖

| 包 | 用途 |
|----|------|
| `fastapi` + `uvicorn` | Web 框架 + ASGI 服务器 |
| `scapy` (2.7.0) | .cubx 802.15.4/NWK/APS/ZCL 帧解析 |
| `pycryptodome` | AES-CCM 解密 (cubx 自解析路径) |
| `tshark` (Wireshark 4.6.2) | pcap 路径解析引擎 (外部 CLI, `D:\work_tool\Wireshark\`) |
| `cryptography` | (已安装, 当前未使用——预留 AES-CCM* 自实现) |
| `pydantic` ≥2.0.0 | API 数据模型 |

## 2. 技术栈

| 层 | 技术 | 文件 |
|----|------|------|
| **Web 框架** | FastAPI + uvicorn | `backend/app.py`, `backend/__main__.py` |
| **API 路由** | APIRouter (prefix=/api) | `backend/api/router.py` |
| **前端** | 原生 ES6 SPA (无 npm/框架), 单文件 1724 行 | `frontend/index.html` |
| **图可视化** | Cytoscape.js v3.30.4 (本地 vendored) | `frontend/lib/cytoscape.min.js` |
| **pcap 解析** | tshark CLI `-T json` + `-T fields` 双通道 | `backend/tshark.py` |
| **cubx 解析** | scapy Dot15d4FCS + pycryptodome AES-CCM | `backend/cubx_reader.py` |
| **前端路由** | Hash-based (`#import`, `#topo`, `#tl`, `#nodes`, `#diag`) | `index.html` `rt()` |

## 3. 数据管道架构

```
输入源:
  pcap/pcapng ─→ tshark.py ─→ list[dict]
  .cubx       ─→ cubx_reader.py ─→ list[dict]
  Ubiqua API  ─→ ubiqua_api.py ─→ (REST 客户端, 路径B预留)

处理层:
  list[dict] ─→ route_events.py (extract_events → RouteEventTimeline)
              ├─ derive_topology() → dict (兼容 topology.build)
              └─ aggregate_offline_diagnosis() → dict

  list[dict] ─→ topology.py (build: 旧管道, 仅 /topology/graph 在用)

  list[dict] ─→ key_store.py (get_match_stats: 解密命中统计)
  list[dict] ─→ verify.py      (pcap 完整性校验, 内部调用 tshark)

前端:
  topology/events → Cytoscape 图 + 路径面板
  diag/offline    → 诊断卡片 (#diag 页)
  packets         → 时间线 (分页+过滤)
  nodes           → 节点列表
```

### 两套拓扑管道

| 维度 | topology.py (旧) | route_events.py (新) |
|------|-----------------|---------------------|
| 端点 | `/topology/graph` | `/topology/events` |
| 节点来源 | traffic + Link Status + PAN 过滤 | Route Record/Request/Status 事件参与者 |
| 方向语义 | ❌ 无 | ✅ upstream_proven / downstream_probed / downstream_failed |
| 邻居表 | ✅ `_build_neighbor_tables` | ✅ 复用 topology 函数 |
| 前端使用 | ❌ 已切到 events | ✅ 当前在用 |
| 状态 | ⚠️ 待淘汰 | ✅ 主力 |

## 4. 模块依赖图

```
backend/
├── __main__.py          ← 入口 (uvicorn + webbrowser)
├── app.py               ← FastAPI create_app()
├── config.py            ← 全局配置 (端口, 路径)
│
├── tshark.py (343行)    ← pcap→list[dict] (tshark JSON + fields 双通道)
│   └── 依赖: zcl_defs.py
│   └── FCS workaround: -o wpan.802154_fcs_ok:FALSE
│
├── cubx_reader.py (475行) ← .cubx→list[dict] (scapy + pycryptodome)
│   └── 依赖: scapy, pycryptodome, key_store
│   └── 移植: akubela _capture_probe.py 解密原语
│
├── route_events.py (743行) ← 事件时间线 (Phase 1-5)
│   ├── RouteEvent dataclass + RouteEventTimeline
│   ├── extract_* (6种事件提取器)
│   ├── derive_topology() + aggregate_offline_diagnosis()
│   └── 依赖: topology._build_neighbor_tables, key_store
│
├── topology.py (353行)   ← 旧拓扑管道
│   ├── _build_neighbor_tables, _build_route_paths, _detect_asymmetric
│   └── build() (主入口, filter_pan/time_start/time_end)
│
├── csv_reader.py         ← Ubiqua CSV 解析 (Phase 1)
├── key_store.py          ← zigbee_pc_keys 读写 (去重合并)
├── zcl_defs.py           ← ZCL Cluster/Command 名称映射
├── verify.py             ← pcap 完整性校验 (6 维度, 9 处内部 tshark 调用)
├── ubiqua_api.py (431行) ← Ubiqua REST 客户端 (localhost:19501)
├── ubiqua_parser.py      ← 路径B stub (UbiquaPacket→dict, 未实现)
│
└── api/
    ├── router.py         ← 路由聚合 (prefix="/api")
    ├── files.py (541行)  ← 导入 + 包列表 + 包详情 (含 cubx 导入, 持久化摘要)
    ├── topology.py (122行) ← /topology/* + /diag/offline + /nodes
    ├── keys.py           ← 密钥管理
    └── ubiqua.py         ← Ubiqua 集成 API

前端:
frontend/
├── index.html (1724行)   ← 单文件 SPA (5 页面 + 状态 + 渲染 + CSS)
└── lib/cytoscape.min.js  ← Cytoscape.js v3.30.4
```

### 依赖方向

```
api/router.py → files.py, topology.py, keys.py, ubiqua.py
files.py → csv_reader, tshark, cubx_reader, key_store, verify
topology.py (api) → topology.build(), route_events.derive_topology()
route_events.py → topology._build_neighbor_tables, key_store
keys.py → key_store
tshark.py → zcl_defs
cubx_reader.py → key_store
app.py → api/router + StaticFiles(frontend)
```

## 5. API 表面

### 导入 (files.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/import/files` | POST | CSV 文件上传 |
| `/api/import/local` | POST | CSV 本地路径 |
| `/api/import/pcap` | POST | pcap/pcapng 上传 (tshark) |
| `/api/import/local-pcap` | POST | pcap 本地路径 |
| `/api/import/cubx` | POST | .cubx 上传 (scapy 自解析) |
| `/api/import/local-cubx` | POST | .cubx 本地路径 |
| `/api/import/clear` | DELETE | 清除所有数据 |
| `/api/import/status` | GET | 总包数/节点数/类型/时间范围 |
| `/api/import/verify` | GET | 校验报告 |
| `/api/import/last` | GET | 最近导入摘要 (含文件名, 切页恢复) |

### 拓扑 & 诊断 (topology.py)

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/topology/graph` | GET | pan, time_start, time_end | 旧管道拓扑 |
| `/api/topology/events` | GET | pan, time_start, time_end | 事件管道拓扑 (含 route_probes/failures, LS 邻居表) |
| `/api/diag/offline` | GET | pan, time_start, time_end | 设备离线诊断 (Leave burst + rejoin 推断) |
| `/api/nodes` | GET | search, pan | 节点列表 |

### 数据 (files.py)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/packets` | GET | 分页包列表 (addr/pan/time/type 过滤) |
| `/api/packets/summary` | GET | 设备行为摘要 / PAN 统计 |
| `/api/packets/{pkt_id}` | GET | 单帧完整协议树 |

### 密钥 & Ubiqua

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/keys` | GET/POST/DELETE | 密钥管理 |
| `/api/keys/reprocess` | POST | 重新解密统计 |
| `/api/ubiqua/*` | (7 个端点) | Ubiqua 连接/抓包/过滤器/密钥 |

## 6. Zigbee 协议分析覆盖

### 协议层解析

| 层 | pcap 路径 (tshark) | cubx 路径 (scapy) | 状态 |
|----|-------------------|-------------------|------|
| MAC (802.15.4) | `wpan.*` | Dot15d4FCS | ✅ 双路径完整 |
| NWK | `zbee_nwk.*` | ZigbeeNWK | ✅ 双路径完整 |
| NWK Security | `zbee.sec.*` | ZigbeeSecurityHeader + AES-CCM | ✅ 解密双路径 |
| NWK Commands | `Command Frame:*` | ZigbeeNWKCommandPayload + 手动解析 | ⚠️ cubx 有 3 次 scapy 字段修正 |
| APS | `zbee_aps.*` | ZigbeeAppDataPayload | ✅ 双路径 |
| ZCL/ZDP | `zbee_zcl.*`, `zbee_aps.zdp_*` | 部分覆盖 | ⚠️ ZCL payload 未深度解析 |

### 事件类型覆盖 (route_events.py)

| 事件类型 | 提取 | 数据源 | 前端展示 |
|---------|------|--------|---------|
| Route Record (上行路径) | ✅ | tshark + cubx | ✅ 拓扑面板 + 路由面板 |
| Route Request (下行探测) | ✅ | tshark + cubx | ✅ 路由面板 |
| Network Status (下行失败) | ✅ | tshark + cubx | ✅ 路由面板 |
| Link Status (邻接) | ✅ | tshark + cubx | ✅ 拓扑邻居表 + 不对称链路 |
| Leave (离网) | ✅ | tshark + cubx | ✅ 诊断面板 |
| Device Announce (身份通告) | ✅ | tshark + cubx | ❌ 仅用于 EUI64/rejoin 推断 |
| IEEE Addr Req (设备发现) | ✅ | tshark + cubx | ❌ 仅用于离网前置事件 |
| Transport Key (安全) | ❌ | — | ❌ |
| Rejoin Request/Response | ❌ | — | ❌ |
| MAC Association | ❌ | — | ❌ |
| ZCL Basic 字符串 | ❌ | — | ❌ |

## 7. 前端架构

### 页面路由 (hash-based)

| Hash | 页面 | 核心功能 |
|------|------|---------|
| `#import` | 导入页 | CSV/pcap/cubx 拖放+路径导入, 密钥管理, 校验报告, 结果持 |
| `#topo` | 拓扑页 | Cytoscape 力导/列图, 路由路径面板, 邻居面板, 不对称链路, 时间滑块 |
| `#tl` | 时间线 | 包列表(分页+过滤), 协议详情面板 |
| `#nodes` | 节点 | 节点搜索+列表 |
| `#diag` | 诊断 | 设备离线分析卡片 (Leave burst + rejoin 推断) |

### 全局状态 S

```javascript
S = {
    pkts, nodes,           // 统计
    topo, topoPan, topoAddr, topoT0, topoT1,  // 拓扑状态
    tlPan, tlNode, tlType, tlTs0H/M/S, tlTs1H/M/S,  // 时间线过滤
    impTab, verifyPassed,    // 导入状态
}
```

### 页面间联动

- 拓扑→时间线: `S.topoAddr` (节点 tap) / `S.topoPan` (PAN→TL 按钮)
- 时间线→拓扑: `S.topoAddr` (双向), 回拓扑时 `highlightNode()`
- 拓扑→诊断: 无直接联动 (独立页面)

## 8. 数据模型

### 内部包 dict (tshark._frame_to_dict / cubx_reader._raw_to_dict)

```python
{
    "ts": float, "ch": int, "lqi": int, "rssi": int,
    "pkt_type": str,        # "Data" / "Link Status" / "Route Record" / "Leave" / 等
    "pan_src/dst": int|None,
    "mac_src/dst": int|None, "mac_seq": int|None,
    "nwk_src/dst": int|None, "nwk_seq": int|None, "nwk_radius": int|None,
    "security": str,         # "Decrypted" / "Encrypted"
    "decrypted": bool,
    "aps_cluster/profile": int|None, "aps_counter": int|None,
    "link_status_neighbors": list[dict]|None,  # [{addr, in_cost, out_cost}]
    "route_record_relays": dict|None,          # {count, relays: [addr,...]}
    "raw_layers": dict,      # tshark JSON 原始层 (cubx 路径为空)
}
```

### RouteEvent (route_events.py)

```python
@dataclass
class RouteEvent:
    timestamp: float; event_type: str  # route_record/request/status/leave/announce/ieee_addr_req
    src: int; dst: int; relays: list[int]
    rejoin: bool; request: bool; remove_children: bool;  # Leave 专属
    radius: int|None; dropped: bool; dropped_at_hop: int|None  # Request 专属
    status_code: int|None; eui64: int|None
    pan: int|None; packet_id: int
```

### 全局内存状态

```python
_packets: list[dict]      # files.py — 全部已导入包
_nodes: dict[int, dict]   # files.py — 全部节点
_file_type: str           # "csv" | "pcap" | "cubx"
_last_import_summary: dict # files.py — 最近导入摘要 (前端切页恢复)
_events_timeline: RouteEventTimeline  # api/topology.py — 事件时间线缓存
```

## 9. 已有文档

| 文件 | 内容 |
|------|------|
| `CLAUDE.md` | AI 协作配置, 嵌入式技能库引用 |
| `CONTEXT.md` | 领域词汇表 (路由术语 + 诊断术语 + .cubx 格式) |
| `README.md` | 项目说明 |
| `docs/decryption_setup.md` | 解密流程 + FCS 第0步排查 (10.8KB) |
| `docs/design_v2.md` / `design_v3.md` | Phase 1/2 设计 (2KB + 22.4KB) |
| `docs/network_analysis_kb.md` | 16 种帧诊断知识库 (22.5KB) |
| `docs/diagnosis_playbook.md` | 5 大类 19 子场景诊断手册 (27.3KB) |
| `docs/acceptance_criteria.md` | 验收标准 (2.3KB) |
| `.scratch/route-events/` | 事件管道: spec.md + 3 工单 |
| `.scratch/diag/` | 诊断面板: spec.md + 3 工单 |
| `.scratch/cubx-reader/` | cubx 解析器: spec.md + 3 工单 |
| `analyze_another/` | akubela-zigbee-analyser 参考技能 (不入库) |

## 10. 技术债清单

| # | 严重性 | 问题 | 影响 |
|---|--------|------|------|
| 1 | 🔴 | `frontend/index.html` 1724 行单体 | 所有页面+状态+渲染混在一起；竞态/覆盖类 bug 频发 (import 持久化 7+ commit)；新增功能困难 |
| 2 | 🔴 | 双拓扑管道并行 | `topology.py` 和 `route_events.py` 同时运行；两套 event 提取（旧管道 tshark JSON、新管道自提取） |
| 3 | 🟡 | `verify.py` 重复 tshark 调用逻辑 | 9 处 tshark 命令构造；加 `-o` 参数必须改两处 |
| 4 | 🟡 | cubx_reader scapy 字段依赖脆弱 | 已 3 次字段名修正；scapy 版本升级可能引入新不一致 |
| 5 | 🟡 | 无测试框架 | 全部验证靠手动导入 pcap |
| 6 | 🟡 | `api/topology.py` 端点混放 | topology/graph + events + diag/offline + nodes 在一个文件 |
| 7 | 🟡 | cubx 和 pcap 输出不完全对齐 | Data/NWK Cmd 分类偏差 (cubx 比 pcap 多 1011 帧)；device_type 推断可能受影响 |
| 8 | 🟢 | `route_events.py` 函数边界模糊 | derive + aggregate + extract 混在一个文件 743 行 |
| 9 | 🟢 | 前端静态文件无版本号/无缓存控制 | 每次改前端用户需要 Ctrl+F5 |
| 10 | 🟢 | 内存存储无持久化 | 后端重启后数据丢失 (设计决定, 非 bug) |
| 11 | 🟢 | 诊断面板仅 Leave 分析 | 缺 Rejoin/TransportKey/Association 事件关联 |
| 12 | 🟢 | cubx Route Record relay 覆盖率 | 40/207 (key 局限在捕获文件内) |
