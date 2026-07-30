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
