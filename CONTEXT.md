# Zigbee Capture Analyzer — 领域词汇表

> 2026-07-30 创建。来源：/grilling 决策会话。维护规则：术语确定后**立即**写入，绝不批量处理。

---

### Route Record — 上行路由实证

**上下文**：拓扑构建的核心数据源之一。设备向协调器发送单播时被动触发（Many-to-One 场景），途经每个 relay 把自己的短地址写入 NWK 命令帧。协调器收到后获得从设备→协调器的完整多跳路径。

**精确定义**：NWK 命令帧（cmd_id=0x05），包含 relay_count 和 relay_device[] 列表。是**上行方向（upstream）的路由实证**——证明数据包实际经过了这些跳。方向是从 relay[0]（最靠近源设备）→ relay[n]（最靠近协调器）→ 协调器。

**区分于**：
- Route Request：下行探测（协调器→设备），主动发起
- Link Status：1-hop 邻接广播，不是路由路径
- Route Reply：双向确认的路径（既有上行也有下行证据）

**数据手册引用**：Zigbee Specification r22 §3.6.3.6; Silicon Labs UG105.2 "Many-to-One and Source Routing"

---

### Route Request — 下行路由探测

**上下文**：协调器主动向目标设备发起的路径发现。收到 Route Request 的路由器会检查邻居表中发送者的 outgoing cost——若为 0 则**直接丢弃该帧**。这是定位不对称链路阻断的关键机制。

**精确定义**：NWK 命令帧（cmd_id=0x01），由源节点（协调器）发起，带有目标地址和最大跳数（radius）。丢弃事件暴露：单向不可达性（downstream failure）、Outgoing Cost=0 的不对称邻居、路径成本竞争结果、Radius 耗尽边界。

**区分于**：
- Route Record：上行实证（被动），不是探测
- Route Reply：对 Route Request 的响应

**数据手册引用**：Silicon Labs "Table Routing" — 丢弃条件：邻居表中条目的 Outgoing Cost 为 0；"Asymmetric Link Detection"

---

### Route Event — 路由事件

**上下文**：本项目的拓扑数据模型从"静态快照"转向"事件时间线"。Route Event 是所有路由相关协议帧的统一内部表示。

**精确定义**：一个不可变的事件记录，包含 timestamp（发生时间）、event_type（route_record | route_request | network_status）、源/目标短地址、relay 链（仅 Route Record）、可选属性（radius、dropped 标志、status_code）。拓扑图在时刻 T 的状态 = T 之前累积的所有 Route Event 的推导结果。

**区分于**：底层 tshark packet dict（原始解析）— Route Event 是**语义层抽象**，从 tshark 输出提取但独立于具体解析格式。

---

### 事件时间线 — Event Timeline

**上下文**：替代 topology.py 的静态 `build()` 模型。不预先计算拓扑快照，而是存储所有路由事件的时间序列，拓扑按需从事件推导。

**精确定义**：按 timestamp 排序的 `RouteEvent` 列表。支持时间窗口查询（`events_in_range(t0, t1)`）、按事件类型过滤、累积状态推导（任意时刻 T 的拓扑 = 该时刻前所有事件的聚合）。优势：天然支持时间滑块、路由变更检测、方向性区分。

**区分于**：topology.py 的 `build()`——后者一次性计算静态拓扑，不保留事件语义。Event Timeline 保留了原始证据，拓扑是可重复推导的。

---

### 方向语义 — Direction Semantics

**上下文**：Zigbee 路由的连通性是**有方向的**。"设备能上报到协调器"（上行通）≠ "协调器能下发到设备"（下行通）。

**精确定义**：
- `upstream_proven`：Route Record 实证——数据包从这个设备出发到达了协调器
- `downstream_probed`：Route Request 探测——协调器正在尝试建立到达这个设备的路径
- `downstream_failed`：Route Request 被丢弃 或 Network Status 报错——下行不通
- `bidirectional_confirmed`：Route Reply 确认——上下行都通

**区分于**：当前的 `route_paths.is_current` / `active` 字段不包含方向语义——它们只标记时间窗口，不区分上下行。

---

### Link Status — 1-hop 邻居表（非路由拓扑）

**上下文**：协议中周期性的单跳广播。每个路由器定期发送自己的完整邻居表（邻居地址 + incoming/outgoing cost）。用于局部链路质量监测和不对称检测。

**精确定义**：NWK 命令帧（cmd_id=0x08）。携带 sender 的所有 1-hop 邻居关系及双向 cost 值。**只描述射频层的直接可达性，不描述多跳路由结构**。一个路由器可能 Link Status 报告 10 个邻居，但其中只有 1 个是它向协调器方向的"父节点"（路由路径上的下一跳）。

**区分于**：Route Record 是路由拓扑（多跳路径），Link Status 是射频邻接（1-hop）。Link Status 为拓扑构建提供邻接矩阵和不对称检测原始数据，但不是拓扑主干。

**数据手册引用**：Silicon Labs "Table Routing"; "Asymmetric Link Detection"

---

### Network Status — 下行路由失败定位

**上下文**：当源路由数据包在某个中间跳无法继续转发时，该跳的路由器向源设备发送 Network Status 命令，报告失败原因。是定位下行路径断裂点的关键信号。

**精确定义**：NWK 命令帧（cmd_id=0x03）。携带 status_code（失败原因码）和 destination_address（失败发生处的目标地址）。典型失败码：0x00=No Route Available、0x01=Tree Link Failure、0x02=Non-Tree Link Failure、0x03=Low Battery Level、0x04=No Routing Capacity、0x05=No Indirect Capacity 等。

**区分于**：Route Request 丢弃——发生在路径发现阶段（探测失败）；Network Status——发生在数据传输阶段（实际的源路由失败）。

**数据手册引用**：Zigbee Specification r22 §3.6.3.3.1

---

## 入网生命周期 (Network Lifecycle)

> 2026-07-30 新增。来源：Phase 6 /grilling 会话。Zigbee 设备从入网到离网的完整生命周期建模。

### Phase 1: Association（MAC 入网）

设备通过 MAC 层 Association 流程加入网络：
- 设备扫描信道找到合适的 PAN + 父节点
- 发送 **Association Request**（MAC 命令，cmd_id=1）：包含 device_type、rx_on_idle、power_source、allocate_address
- 父节点回复 **Association Response**（MAC 命令，cmd_id=2）：分配短地址，或拒绝（status != 0）
- 此时设备拥有 NWK 短地址，但尚无 NWK 加密密钥

**区分于**：Rejoin（使用缓存的网络参数加速入网）、NWK 层的 Transport Key（后续的安全握手）

**数据来源**：802.15.4 MAC 命令帧。当前 pcap 中未观测到（需要抓包在入网时刻）。

### Phase 2: Security Handshake（安全握手）

入网后进行密钥分发和安全建立：
- 协调器发送 **Transport Key**（APS 命令，cmd_id=5）：用 Trust Center Link Key 加密传输 NWK Key
  - key_type=1：Network Key；key_type=4：Trust Center Link Key
  - 包含 key（加密后）、key_seqnum、destination EUI64、source EUI64
- 设备回复 **Verify Key**（APS cmd_id=15）或 **Confirm Key**（APS cmd_id=16）
  - Confirm Key 的 status 字段指示成功/失败
- 密钥建立后，后续通信使用 NWK 层 AES-CCM* 加密

**区分于**：APS 层的加密（用 Link Key，不是 Transport Key 分发的 NWK Key）

**数据来源**：APS 命令帧（zbee_aps.command）。当前 pcap 中未观测到。

### Phase 3: Device Announce（设备通告）

入网或重入网后，设备广播自身身份：
- **Device Announce**（ZDP 0x0013，cluster=0x0013，profile=0x0000）：
  - 目标地址：0xFFFD（广播到所有非休眠设备）
  - Payload：16-bit short address + 64-bit IEEE address + capability byte
- 这是网络学习 "0x1234 = 70:c5:9c:ff:fe:72:a5:cd" 映射的标准方式
- Capability byte 指示：device type（coordinator/router/end_device）、power source、rx_on_idle 等

**数据来源**：ZDP 帧（zbee_aps.zdp）。leave_question 中观测到 4 条（均来自 0xCBEB）。

### Phase 4: Device Discovery（设备发现）

协调器或其他设备主动查询设备信息：
- **IEEE Addr Req/Resp**（ZDP 0x0001 / 0x8001）：通过短地址查 IEEE 地址
- **NWK Addr Req/Resp**（ZDP 0x0000 / 0x8000）：通过 IEEE 地址查短地址
- **Node Desc Req/Resp**（ZDP 0x0002 / 0x8002）：查询设备能力（频段、逻辑类型、制造商码）
- **Active EP Req/Resp**（ZDP 0x0005 / 0x8005）：查询设备有哪些应用端点
- **Simple Desc Req/Resp**（ZDP 0x0004 / 0x8004）：查询某端点的设备 ID、Cluster 列表

**拓扑价值**：这些查询帧在 Leave 前后密集出现（leave_question 有 61 条 IEEE Addr Req），表明协调器在"踢设备"前正在确认设备身份。

### Phase 5: Normal Operation（正常运行）

设备在网内的正常工作状态。包括 Link Status 广播、数据通信、路由维护。
此阶段的事件已在路由拓扑部分覆盖（Route Record、Route Request、Link Status、Network Status）。

### Phase 6: Leave（离网）

设备离开网络的协议行为。**NWK Leave 命令**（cmd_id=0x04）：

| 字段 | 值=0 | 值=1 |
|------|------|------|
| `rejoin` | 永久离开（不复返） | 离开后重新入网 |
| `request` | 命令/指令（发送方命令对方离开） | 申请（发送方自己申请离开） |
| `children` | 不带走子节点 | 连子节点一起移出 |

**含义组合**：
- `rejoin=0, request=0`：**踢设备**——协调器命令某设备永久离开（leave_question 的 6 条全是此模式）
- `rejoin=1, request=1`：**设备申请暂时离网**——设备要走了但会回来
- `rejoin=0, request=1`：**设备主动永久离网**——设备自己决定退出
- `children=1`：路由器离网时带走子节点（树形拓扑重组的证据）

**配套事件**：Mgmt Leave Req/Resp（ZDP 0x0034）——管理层离网请求（与 NWK Leave 互补或独立使用）。

**数据来源**：NWK 命令帧。leave_question 中观测到 6 条（均为 rejoin=0, request=0 = 踢设备模式）。

### Phase 7: Rejoin（重入网）

离开后或断电后重新加入网络：
- **Rejoin Request**（NWK cmd_id=0x06）：使用缓存的 NWK 参数（PAN ID、NWK Key、IEEE 地址）发起重入网
  - 包含 device_type、rx_on_idle、allocate_address
- **Rejoin Response**（NWK cmd_id=0x07）：协调器回复，分配短地址或拒绝
  - 包含 network_address、rejoin_status
- 重入网后通常跟 Device Announce 广播新身份

**区分于**：Association（全新入网，无缓存参数）；Secure Rejoin（使用 NWK Key 加密的 Rejoin）

**数据来源**：NWK 命令帧。当前 pcap 中未观测到。

### 生命周期状态机

```
[未入网] → Association → [已关联,无密钥]
  → Transport Key + Verify/Confirm Key → [已入网,已加密]
  → Device Announce → [身份已通告]
  → Normal Operation（Link Status, Route Record, 数据通信）
  → Leave → [已离网]
  → Rejoin → [已入网,已加密] 或 [入网被拒]
```

### 可用数据对照

| 阶段 | 帧类型 | leave_question | test2 |
|------|--------|---------------|-------|
| Association | MAC Assoc Req/Resp | 0 | 0 |
| Transport Key | APS cmd 5 | 未查 | 未查 |
| Device Announce | ZDP 0x0013 | **4** | 0 |
| IEEE Addr Req | ZDP 0x0001 | **61** | 0 |
| Leave | NWK cmd 0x04 | **6**（踢设备） | 0 |
| Rejoin | NWK cmd 0x06/0x07 | 0 | 0 |
| Mgmt Leave | ZDP 0x0034 | 未查 | 未查 |

**数据手册引用**：Zigbee Specification r22 §3.6.1.8 (Leave), §3.6.1.6 (Rejoin), §2.4.3 (Device Announce);
Silicon Labs UG105.2 "Device Association"

---

## 诊断分析 (Diagnostics)

> 2026-07-30 新增。来源：Phase 6 /grilling 会话。独立于拓扑分析，聚焦网络问题的证据收集和诊断推断。

### 设备离线分析 (Device Offline Diagnosis)

针对设备离开网络的行为进行证据收集和诊断推断。核心数据源：Leave 命令、Device Announce、IEEE Addr Req、Network Status。

### Leave Burst（离网波次）

同一设备在短时间内（默认 5 秒窗口）发送的连续 Leave 命令集合。一次"离网波次"代表一次独立的离网行为。leave_question 中 0xCBEB 有两次波次：9.2s-10.2s（3 帧）和 23.3s-24.3s（3 帧），间隔 14 秒。

**区分于**：单条 Leave 帧（可能因重传产生多条，属于同一波次）。

### Leave Type（离网类型）

基于 NWK Leave 命令的 `rejoin` 和 `request` 标志推断的离网原因：

| 类型 | rejoin | request | 含义 |
|------|--------|---------|------|
| `kicked`（被踢） | 0 | 0 | 协调器/父节点命令设备离开，且不复返 |
| `voluntary_permanent`（主动永久） | 0 | 1 | 设备自己申请永久离开 |
| `voluntary_rejoin`（主动暂离） | 1 | 1 | 设备申请暂时离网（会回来） |
| `kicked_rejoin`（被踢但重入） | 1 | 0 | 被命令离开但允许重入 |

leave_question 中 0xCBEB 的 6 条 Leave 全部为 `kicked` 类型。
**帧方向实证（2026-08-04, tshark 复核, 详见 docs/scenarios/L1-4.md 示例 B）**：6 条均为**设备广播**
（src=0xCBEB → dst=0xFFFD）——是设备侧 Leave Announcement（设备执行 Leave 时广播，Silabs KB）。
**TC 的踢人指令 = ZDO Mgmt Leave Req（ZDP cluster 0x0034）×12，第二波踢人前完全可见**
（t=1785138818.0-19.4，TC 单播 0000→0xCBEB）；第一波（t=1785138804.4）无指令帧可见。"协调器命令
0xCBEB 离开" 是早期推断，帧方向不支持（指令在 ZDO 层而非 NWK 单播 Leave）。运营期踢人三路径:
APS Remove Device (0x07) / ZDO Mgmt Leave Req (0x0034) / NWK Leave（L1-4 检测器 R2a/R2b/R2c）。

**区分于**：Mgmt Leave（ZDP 0x0034，管理层离网请求，使用不同的协议机制）。

### Rejoin Inference（重入网推断）

Leave 事件后出现 Device Announce 帧，推断设备尝试了重入网。推断依据：
- Device Announce 通常只在入网/重入网后发送
- Leave 后 30 秒内出现 Device Announce → 标记为"检测到重入网尝试"
- Leave 后无 Device Announce → 标记为"未检测到重入网"（设备彻底离开）

leave_question 中 0xCBEB 在第一波 Leave（9.2s-10.2s）后 5 秒出现了 4 条 Device Announce（15.4s-15.9s），推断为尝试重入网。第二波 Leave（23.3s-24.3s）后无 Device Announce，推断为彻底离开。

**区分于**：此推断不是协议层面的确认（需要看到 Rejoin Request/Response 才能确认），而是基于可观测证据的合理推测。

### Device Timeline Card（设备时间线卡片）

诊断面板的核心 UI 组件。每张卡片展示一个离网设备的完整证据链：

```
┌ 0xCBEB  70:c5:9c:ff:fe:72:a5:cd  路由器 ────────┐
│                                                  │
│  ▸ 活跃通信 (Link Status, Route Record, Data)     │
│  ▸ Network Status ×3 出现                         │
│  ✕ 第一波 Leave ×3 (9.2s-10.2s) [被踢]           │
│  📢 Device Announce ×4 (15.4s-15.9s) ← 重入网尝试  │
│  ✕ 第二波 Leave ×3 (23.3s-24.3s) [被踢, 彻底离开] │
│                                                  │
│  诊断: 被踢出网络, 有重入网尝试, 最终彻底离网       │
└──────────────────────────────────────────────────┘
```

**设计决策**（来自 grilling Q4-5）：后端预聚合 → 前端渲染；按设备分卡片；新页面 `#diag`。

### Diagnostic Panel（诊断面板）

前端新页面 `#diag`（hash 路由），与 `#import`、`#topo`、`#tl`、`#nodes` 同级。设计为可扩展的诊断平台：
- 第一个诊断场景："设备离线分析"（当前实现）
- 后续扩展："路由异常分析"、"入网失败分析" 等
- 每个诊断场景是一个独立区域，互不干扰

**区分于**：拓扑页（展示网络结构）和时间线页（展示原始帧）——诊断面板展示的是**推断结论 + 证据链**。

---

## .cubx 格式与自解析 (Cubx Native Parser)

> 2026-07-30 新增。来源：Phase 7 /grilling 会话。替代 pcap+tshark 管线，实现 key 内嵌、信号数据完整、解析自控。

### .cubx 文件格式

Ubiqua Protocol Analyzer 的原生抓包格式。本质是 **SQLite 数据库**，表结构：

| 表 | 关键列 | 说明 |
|----|--------|------|
| `Packets` | Id, Raw, Timestamp, Channel, LQI, RSSI | 802.15.4 原始帧（含 FCS）+ 信号数据 |
| `Keys` | Id, Type, Key | 内嵌密钥（NetworkKey / LinkKey），**解决 pcap 导出丢 key 的根源问题** |
| `Addresses` | — | 长短地址映射表 |
| `Nodes` | — | 节点信息 |

**区分于**：pcap 导出（key 丢失 + FCS 可能为 0xffff + 无 Channel/LQI/RSSI）。

### cubx_reader.py（计划）

新建模块 `backend/cubx_reader.py`，职责：
1. 读取 .cubx SQLite → 提取 Keys（写入 zigbee_pc_keys）+ 提取 Raw 帧
2. 用 scapy `Dot15d4FCS` 解析 802.15.4 帧结构
3. 用 pycryptodome AES-CCM 解密 NWK/APS（参考 akubela `_capture_probe.py`）
4. 输出 `list[dict]`，格式兼容 `tshark._frame_to_dict`，事件管道无感切换

**设计决策**：
- 架构：独立模块 `cubx_reader.py`，与 `tshark.py` 平行的输入源
- MVP 字段范围：pkt_type, ts, ch, nwk_src/dst, mac_src/dst, pan_src/dst, aps_cluster, decrypted, link_status_neighbors, route_record_relays, LQI, RSSI
- 解密算法：AES-CCM*（ENC-MIC-32），参考 akubela 的 `decrypt_nwk` / `decrypt_aps` / `zigbee_hash` / `security_candidates`
- 依赖：scapy + pycryptodome（已安装）

**数据来源**：akubela-zigbee-analyser `_capture_probe.py`（参考实现）。

---

## 前端模块化 (Frontend Modularization)

> 2026-07-31 新增。来源：/grilling 技术债治理会话。将 1724 行单体 index.html 拆分为独立模块。

### 全局共享模块（state.js）

所有页面脚本共享的基础设施文件。**只放变量声明和工具函数**，不放任何页面业务逻辑。

**内容边界**：
- `window.S`：全局状态对象（pkts, nodes, topo, topoPan, topoAddr, topoT0/T1, impTab, verifyPassed 等）
- `window.A`：HTTP 工具（get/post）
- `window.sb()`：状态栏更新函数
- `window.setProg()` / `window.sr()` / `window.doPI()` / `window.doI()`：导入页工具函数
- `window.fmtTs()`：时间戳格式化（topo+timeline 共用）
- `window.PATH_COLORS`：路径颜色常量
- `window.tsStart` / `window.tsEnd`：抓包时间范围（topo+timeline 共用）

**区分于**：页面模块（topo.js 等）——state.js 是可被所有页面引用的**被动数据**，页面模块是**主动逻辑**。

### 页面模块（Page Module）

每个 hash 路由对应一个独立 JS 文件。文件内只包含该页面的 reg() 回调和内部渲染/事件逻辑。

**加载顺序**：state.js 必须第一个加载（提供所有共享变量），页面模块按需加载（无先后依赖）。

**区分于**：state.js 是水平共享层，页面模块是垂直切分。

### index.html 壳

拆分后的 HTML 文件仅保留：
- `<nav>` 导航栏（页面间切换，不随 hash 变化重建）
- `<div id="mc">` 主内容容器（页面模块渲染目标）
- `<link rel="stylesheet">` 引用外部 CSS
- 共享脚本和页面脚本的 `<script>` 标签（按 state.js → 页面模块顺序）
- 顶层的 `rt()` 路由调度和 `reg()` 注册函数（极简，~10 行）

**区分于**：拆分前的 1724 行单体 index.html——壳是加载器，单体是全集。

### 设计决策

| # | 决策 | 结论 | 来源 |
|---|------|------|------|
| 1 | 拆分策略 | 渐进式——先拆 topo（800行）+ state.js，再拆其余页面 | grilling Q1 |
| 2 | 共享模块方案 | 单文件 state.js 集中管理（方案 A） | grilling Q2 |
| 3 | 模块系统 | **ES 模块**（`<script type="module">`）——零构建工具，浏览器原生 `import/export` | grilling Q3 |
| 4 | 工具函数归属 | `sr/setProg/doPI` 全进 state.js，避免碎片化 | grilling Q4 |

### ES 模块架构

**区分于**：之前的加载顺序契约（`<script>` 标签 + 全局变量依赖）——ES 模块用**编译器强制隔离**替代开发者纪律。未导入的变量在模块内不可见。

### ES Modules

浏览器原生模块系统（Chrome 61+, 2017）。`<script type="module">` 加载的 JS 文件可使用 `import/export` 语法，模块内变量默认私有，只导出明确声明的符号。

**上下文**：本项目无构建工具（无 npm/webpack），但需要跨文件变量隔离——原生 ES 模块是唯一零依赖方案。

**区分于**：CommonJS（Node.js `require`/`module.exports`）——浏览器不支持；AMD（`define`）——已废弃。Vite/webpack 的模块系统是构建时转换的，ES 模块是运行时原生支持的。

### Module Export Boundary（模块导出边界）

`state.js` 的 `export` 声明列表，定义了所有页面模块**能访问什么**。未在 `export` 中的变量，其他模块不可见。

当前边界：
```js
// state.js — 导出的符号 (白名单)
export const S = {...};          // 全局状态
export const A = {get, post};    // HTTP 工具
export let tsStart, tsEnd;       // 抓包时间范围 (topo+tl共用)
export function sb(m) {...}      // 状态栏
export function fmtTs(ts) {...}  // 时间戳格式化
export function sr(d, fname) {...} // 导入结果渲染
export function setProg(msg) {...} // 进度提示
export function doPI(files) {...}  // pcap/cubx 上传
export function doI(file) {...}    // CSV 上传
```

**区分于**：`window.*` 全局变量——导出边界是白名单（显式声明），window 是黑名单（所有变量可用，靠约定隔离）。

### Import-based Coupling（导入耦合）

每个页面模块通过 `import { ... } from './state.js'` 声明自己的依赖。依赖关系是可静态分析的——搜索 `import.*from` 即可列出所有模块的依赖图。

**区分于**：拆分前的隐式耦合（index.html 全局作用域里所有变量相互可见，无法静态分析谁用了谁）。

**数据手册引用**：MDN: `import` / `export` / `<script type="module">`
### 问题包 — Problem Package

**上下文**：工具核心工作流的输入单元。用户"导入问题包 → 描述问题 → 快速定位分析 → 人工复核"（2026-08-01 grilling 对齐的核心诉求）。

**精确定义**：一个抓包文件（.cubx/.pcap/.pcapng/.csv）+ 一段自然语言问题描述。抓包提供帧级证据，描述提供诊断方向。两者绑定后进入分析引擎。

**区分于**：单纯的文件导入（现有 import 功能，无问题描述语义）；完整测试报告包（多文件+日志+配置，后续 M 阶段可能支持）。

### 问题分类基准 — Problem Taxonomy

**上下文**：分析引擎的分类基准，ADR-0001 固化。定义"Zigbee 网络问题有哪些"，是"问题描述 → 自动定位"的映射目标。

**精确定义**：8 大类 ~55 场景（L1 形成/L2 维持/L3 运营/L4 维护/L5 应用/L6 SED/L7 MAC/L8 硬件），每个场景有帧级证据链（Network Status 错误码 0x00-0x13、MAC 状态码、ZCL 状态码、帧序列模式）。详见 `docs/network_problems_taxonomy.md`。

**区分于**：diagnosis_playbook.md（19 场景人工诊断手册，按现象组织，是 taxonomy 的已覆盖子集）；network_analysis_kb.md（17 种帧类型详解，证据链引用源）。

**约束**：场景 ID 一经引用不可重编号；框架只允许增量扩展，不允许结构性调整（ADR-0001）。

### 帧级证据链 — Frame-Level Evidence Chain

**上下文**：分析引擎自动检测的判定依据。每个 taxonomy 场景都必须能映射到抓包中可自动提取的信号。

**精确定义**：可从 pcap/cubx 自动提取的帧特征组合——Network Status 命令错误码（如 0x05 NO_INDIRECT_CAPACITY）、MAC 层状态（0x41 INDIRECT_TIMEOUT）、ZCL 状态（0xC0 Hardware Failure）、帧序列模式（Transport Key 无 Verify Key）、时间间隔（poll 间隔 >7.68s）。

**区分于**：人工诊断步骤（playbook 中的"看什么"→ 人眼观察）；分析结论（证据链的推导结果，供人工复核）。

### 睡眠设备假阳性在线 — SED Zombie State

**上下文**：L6-S4 场景。SED 特有故障——设备 poll 无响应但栈状态仍报 JOINED，不触发 rejoin，设备"僵尸化"（Community 案例）。

**精确定义**：睡眠终端设备与父节点实际断联（MAC Data Request 无确认），但设备侧网络状态未切换为无父节点，导致不触发 rejoin、设备不可达但网关仍认为在线。抓包特征：Data Request 发出后无 MAC ACK/无数据返回，但无 Leave/Orphan 帧。

**区分于**：正常离线（有 Leave 帧或 Orphan Notification）；Child Table 老化（父节点侧主动移除）。

---

### 场景拆解模板 — Scenario Breakdown Template

**上下文**：ADR-0002 固化。55 个 taxonomy 场景逐个拆解时的标准文档格式，保证格式统一、可被分析引擎直接翻译。

**精确定义**：14 层结构 — 0 抓包可行性（数据现实层）/ 1 场景识别 / 2 正常基线 / 3 异常表现 / 4 判定条件（可编程规则）/ 5 直接证据 / 6 根因链路 / 7 混淆项 / 8 自动检测盲区 / 9 置信度分级 / 10 人工复核清单 / 11 上下游关联 / 12 判定示例。

**区分于**：playbook 的诊断步骤（人眼观察流程）；taxonomy 场景清单（只有 ID 和证据链摘要，无拆解）。

**约束**：第 0 层是前提（抓包条件不满足 → 不可判定）；第 9 层约束所有输出（结论必须带置信度）；模板只允许增量扩展（ADR-0002）。

### 置信度分级 — Confidence Level

**上下文**：分析引擎每个结论的强制标签（ADR-0002 第 9 层）。防止"抓包里没看到"被误判为"网络上没发生"。

**精确定义**：四级 — **高**（Network Status/MAC 错误码直接出现）、**中**（帧序列模式匹配）、**低**（由缺失帧推断）、**不可判定**（抓包条件不满足，如单 sniffer 覆盖不到远跳节点）。

**区分于**：证据强度（某条证据本身多硬）vs 置信度（综合全部证据后结论多可信）。

### 抓包盲区 — Capture Blind Zone

**上下文**：单点 sniffer 的先天限制（芯科官方确认），每个场景必须声明。三类盲区决定结论可信度。

**精确定义**：① **抓包未覆盖** — sniffer 射频范围外节点的帧完全缺失；② **设备未听到** — sniffer 抓到了但目标设备可能没收到（反之亦然）；③ **sniffer 听不到** — 仅发送方知晓的失败（未送达的传输、内部重传计数）在抓包里无痕迹。

**区分于**：帧丢失（抓包工具自身丢帧）；时间窗口不足（抓得太短，如 Link Status 16s 周期只抓 10s）。

---

## L1/L2 场景验证 (L1/L2 Scenario Verification)

> 2026-08-01 新增。来源：MCP 二次复核（silicon-labs-docs + gecko_sdk 源码）。L1-1/L1-2 拆解文档的协议级判定规则已获官方确认。

### 协议级判定规则（已官方确认）— 权威依据

| 断言 | 官方依据 | 状态 |
|------|---------|------|
| AssocReq=0x01, AssocResp=0x02, BeaconReq=0x07 | gecko_sdk `mac-command.h`; Zephyr `ieee802154_frame.h` | ✅ |
| Association 8 步流程 | UG235.02 §4.3 | ✅ |
| status: 0x00 成功/0x01 容量满/0x02 拒绝/0x80+ 保留 | Zephyr `ieee802154_association_status_field` | ✅ |
| 0xFFFE=未分配(成功) vs 0xFFFF=拒绝 | UG235.02: "not assigned → 0xfffe" | ✅ |
| Beacon Request 单跳广播、跨 PAN 边界 | docs.silabs.com "Network Activities" | ✅ |
| Steering 12 步 + 默认掩码 BIT32(11)\|BIT32(14) | network-steering.c 源码 `#define` | ✅ |
| NO_BEACONS(0xAB) / JOIN_FAILED(0x9B) 语义 | network-steering-v2.c `cleanupAndStop` / `tryNextMethod` | ✅ |

### 实测类断言（待抓包验证）— 无官方文档可核

- Beacon 响应延迟基线 3-48ms（L1-1 第 12 层）
- AssocResp 延迟基线 ~205ms（L1-2 第 12 层）
- request→响应命中率 32/32（L1-1 第 12 层）

### 验证标准（用户决策）

**判定规则成立即可**——匹配方法/阈值/status 语义正确即通过；具体计数允许素材差异浮动。

### 验证流程

1. 用户提供标准入网抓包（健康）+ 错误复现抓包
2. 检测模块原型 `backend/detectors/l1.py`（吃扩展后的包 dict）输出指标
3. 对比文档断言 → 一致/差异/存疑
4. 差异逐条问裁决 → 修正文档/模块

### 关键数据缺口

现有 `parse_cubx` 过滤 `if nwk_src or nwk_dst` → **MAC 命令帧（Beacon Request/Assoc Req/Resp）被全部丢弃**。检测模块原型必须先扩展 `cubx_reader` 提取 MAC 命令层（cmd_id + 长地址）。

### TC Key 验证失败 → Leave（L1-3 铁证级依据）

network-steering-v2.c `finishSteeringEventHandler`：**"Key verification failed. Leaving network" → `emberLeaveNetwork()`**。TC 发 Transport Key 后设备 Verify Key 失败会直接 Leave——L1-3（密钥分发失败）拆解时的协议级确认。
