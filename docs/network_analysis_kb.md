# Zigbee 网络分析知识库 — 关键帧诊断手册

> 用于后续网络问题分析脚本/Agent 的知识基础。
> 每帧记录：协议作用 → 关键字段 → 诊断价值 → 正常/异常模式。
> 每个 `##extend` 标记为 AI Agent 预留扩展锚点。
>
> 📚 **关联文档**: [diagnosis_playbook.md](diagnosis_playbook.md) — 基于本知识库的 5 大类 19 个子场景诊断手册。
>
> **`##extend` 标记规范**: 每个 `##extend: {帧类型ID}` 为 AI Agent 预留的扩展锚点。Agent 可通过帧类型 ID
> (如 `route_request`, `link_status`, `data`) 定位到具体帧条目，在其后追加新字段、新异常模式或新诊断关联。

---

## 1. Beacon (信标帧)

### 协议作用
协调器/路由器定期广播 Beacon，宣告网络存在和入网条件。加入中的设备通过
Beacon 了解 PAN ID、协议版本、设备容量、**入网许可状态** 等关键信息。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **Source PAN ID** | 网络 PAN ID | `0xFEED` |
| **Extended PAN ID** | 网络 64-bit 扩展 PAN ID | `b4:e3:f9:ff:fe:0a:17:7a` |
| **Protocol ID** | 协议标识 (Zigbee=0) | `0` |
| **Stack Profile** | 协议栈配置 (0x01=Home, 0x02=Pro) | `0x02` |
| **Protocol Version** | Zigbee 版本 (3=Zigbee 3.0 / Pro 2017) | `3` |
| **Router Capacity** | 是否允许路由器加入 (1=允许) | `1` |
| **End Device Capacity** | 是否允许终端设备加入 (1=允许) | `1` |
| **Device Depth** | 本设备在网络中的深度 (协调器=0) | `0` |
| **Association Permit** | **入网许可** (1=开放入网, 0=关闭) | `1` |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **Beacon Request 发出后无 Beacon 响应** | 信道不匹配或无协调器 | 检查设备与协调器是否在同一信道 |
| **Association Permit = 0** | 协调器关闭了入网许可 | 在协调器侧开启 Permit Join |
| **Router Capacity = 0 且 End Device Capacity = 0** | 网络不允许任何新设备加入 | 检查协调器配置 |
| **Device Depth 接近 Max Depth** | 新设备可能无法通过路由器加入 | 增加路由器密度或减小深度 |

### 正常模式
- 协调器约每 15 秒广播一次 Beacon
- 路由器通常每 15-240 秒广播一次 (取决于 `nwkReportConstantCost` 配置)
- 入网开放期间 Beacon 间隔可能缩短

##extend: beacon

---

## 2. Beacon Request (信标请求)

### 协议作用
加入中的设备在每个信道逐个发送 Beacon Request，请求周围网络回应 Beacon。
用于 Active Scan（主动扫描）阶段。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **MAC Dst** | 广播地址 | `0xFFFF` |
| **MAC Frame Type** | MAC 命令帧 | `3` (MAC Cmd) |
| **Channel** | 当前扫描的信道 | `11` |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **所有信道均无 Beacon Response** | 设备不在任何网络范围内 | 检查距离/天线/射频故障 |
| **某些信道有响应、某些无** | 网络仅在特定信道运行 | 正常 — 只需一个信道有响应 |
| **Beacon Request 持续发送不停止** | 设备陷入扫描循环 | 固件入网逻辑可能死循环 |

##extend: beacon_request

---

## 3. Association Request (关联请求)

### 协议作用
设备扫描到 Beacon 并选定 PAN 后，向协调器/路由器发送 Association Request 请求加入。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **Capability Information** | 设备能力 (FFD/RFD, 主电源/电池, 空闲接收等) | `0x8E` (FFD+主电源+空闲接收) |
| **Alternate PAN Coordinator** | 是否可成为 PAN 协调器 | `0` |
| **Device Type** | FFD (全功能) 或 RFD (精简功能) | FFD=Router, RFD=End Device |
| **Power Source** | 主电源 (1) 或 电池 (0) | `1` |
| **Receiver On When Idle** | 空闲时是否保持接收 (Router=Yes, Sleepy End Device=No) | `1` |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **Association Request 发送后无 Response** | 协调器未收到请求或拒绝响应 | P2-2: 检查距离/PAN ID/干扰 → [diagnosis_playbook.md](diagnosis_playbook.md#p2-2-设备无法加入网络) |
| **Capability 与预期不符** | 固件角色配置错误 | 检查 `zgDeviceLogicalType` 或对应宏 |
| **Receiver On When Idle = 0 但预期为 Router** | ZED 伪装成 ZR 加入 → 会被分配短地址但路由功能异常 | 检查固件设备类型定义 |
| **多次 Assoc Req 无响应** | 协调器端入网许可超时或已关闭 | 重新打开 Permit Join |

##extend: association_request

---

## 4. Association Response (关联响应)

### 协议作用
协调器/路由器对 Association Request 的应答。分配短地址或拒绝加入。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **Short Address** | 分配给设备的 16-bit 短地址 | `0x2BD6` |
| **Association Status** | 加入结果 | `0x00`=成功 |

### Association Status 含义

| Status | 含义 | 解决方向 |
|--------|------|---------|
| `0x00` | 成功 | ✅ 设备获得短地址 |
| `0x01` | PAN 容量已满 | 协调器已达到最大子设备数 |
| `0x02` | PAN 访问拒绝 | 安全策略拒绝 (如 MAC 地址黑名单) |

### 诊断价值
- **Status ≠ 0x00** → 协调器主动拒绝 → 检查容量/安全策略
- **无 Response** → 返回检查 Association Request 是否被正确接收 (MAC Ack 是否存在)
- **Short Address = 0xFFFE** → 特殊情况, 可能表示分配失败但仍允许加入

##extend: association_response

---

## 5. Transport Key (密钥传输)

### 协议作用
Zigbee 3.0 入网安全流程的核心步骤。Trust Center (通常为协调器) 将 NWK Key
用预配置的 TC Link Key 加密后发送给新加入设备。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **Key Type** | 密钥类型 | `0x01`=Network Key, `0x02`=TC Link Key, `0x03`=TC Master Key |
| **Key** | 密钥数据 (AES-128 加密) | 16 字节 |
| **Destination IEEE** | 目标设备 64-bit IEEE 地址 | `b4:e3:f9:ff:fe:0a:17:7a` |
| **Source IEEE** | Trust Center IEEE 地址 | 协调器 IEEE |
| **Key Seq Number** | 密钥序列号 | `0` (初始) |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **Association Response 后无 Transport Key** | TC Link Key 配置错误, TC 拒绝发送密钥 | P2-3: 检查 `zgPreConfigKeys` / TC Link Key |
| **Transport Key 发出后设备立即 Leave** | 设备用错误的 TC Link Key 解密失败 → 被踢出 | P2-3: 清空设备 NV 重新入网 |
| **Key Seq Number 非 0** | 网络已进行过 Key Rotation | 新加入设备应获取最新 Key |
| **Key Type = 0x02 (TC Link Key)** | 协调器正在分发 Link Key 而非 NWK Key | 正常: Zigbee 3.0 先发 TC Link Key 再发 NWK Key |

##extend: transport_key

---

## 6. Device Announce (设备通告)

### 协议作用
设备收到 NWK Key 后, 广播 Device Announce 向全网宣告自己的 IEEE 地址和
短地址映射。协调器收到后更新地址映射表。其他设备也会缓存此映射。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **IEEE Address** | 设备 64-bit IEEE/MAC 地址 | `b4:e3:f9:ff:fe:0a:17:7a` |
| **Short Address (NWK Addr)** | 刚分配的 16-bit 短地址 | `0x2BD6` |
| **MAC Capability** | 设备能力标志 (同 Association Request) | `0x8E` |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **Transport Key 后无 Device Announce** | 设备 NWK 层异常, 未完成入网最后一步 | 设备可能仍在入网流程中, 检查后续帧 |
| **Device Announce 立即跟 Leave** | TC 拒绝设备 — 安全验证失败 (Zigbee 3.0) | P2-3: TC Link Key 不匹配 |
| **两个不同 IEEE 使用相同短地址** | 短地址冲突 | P5-1: 检查地址分配策略 |
| **Device Announce 反复出现 (同一 IEEE)** | 设备反复掉线重连 | P2-1: 检查信号/Link Status |

##extend: device_announce

---

## 7. MAC Acknowledgement (MAC 层确认)

### 协议作用
802.15.4 MAC 层的逐跳确认机制。接收方在收到非广播帧后约 192μs
(aTurnaroundTime) 内由射频硬件自动发送 MAC Ack。**这是物理层可靠性基础。**

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **MAC Sequence Number** | 与所确认帧的 MAC Seq# **完全相同** | `137` |
| **MAC Frame Type** | 固定为 `2` (Acknowledgement) | `2` |
| **FCS (Frame Check Sequence)** | CRC 校验 (2 字节) | `0xAD7D` |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **Data 帧发送后无 MAC Ack** | 物理层丢包 — 目标不在射频范围内/干扰/冲突 | P5-3: 检查信道干扰 |
| **MAC Ack 延迟异常 (>1ms)** | 中继转发或设备处理延迟 | 检查中间节点负载 |
| **MAC Ack 存在但 FCS 错误** | 物理层噪声导致 Ack 帧损坏 | 检查天线/射频环境 |
| **同一 MAC Seq 重传 ≥3 次** | 链路质量极差 | 检查 LQI / Link Status cost |

### 与其他 Ack 的关系

```
发送方 → [Data] → 接收方 → [MAC Ack] (逐跳, 硬件自动, ~192μs)
                              → [APS Ack] (端到端, 应用层, 0~数百ms)
```
- MAC Ack 成功 ≠ 应用层送达 (可能 NWK 层转发失败或应用层丢弃)
- MAC Ack 失败 = 物理层不可达 (信号/干扰/设备关机)
- MAC Ack 每跳独立, 路径上的每个路由器都要发送/接收 MAC Ack

##extend: mac_ack

---

## 8. Route Request (路由请求)

### 协议作用
AODV 按需路由发现的第一步。当源节点需要向目标节点发送数据但没有有效路由时,
广播 Route Request 寻找路径。类似 IP 网络的 ARP 请求。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **Originator** (NWK Src) | 发起路由请求的设备地址 | `0x07B8` |
| **Target Dest** | 路由目标地址 | `0x0000` = 协调器 |
| **Path Cost** | 累积路径开销 (每跳+链路cost) | `3` |
| **Route ID** | 本次路由发现的唯一标识 | `35` |
| **Radius** | 最大跳数限制 | `30` |
| **Options** | Many-to-One / Multicast / DestExt / OrigExt | `OrigExt` |

### 广播行为
- MAC Dst = `0xFFFF` (广播到所有设备)
- NWK Dst = `0xFFFC` (广播到所有路由器和协调器)
- 每台中间路由器收到后: 更新Path Cost → 重建Route Request → 转发
- 如果某设备已有到目标的路由, 可代答 Route Reply

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **Route Request 频繁出现** | 路由不稳定, 路由表频繁失效 | 检查链路质量(Link Status cost), 是否存在非对称链路 |
| **同一 Route ID 大量重复** | 路由发现无响应, 网络中存在盲区 | 检查 Target Dest 是否在线, 中间节点是否全部可达 |
| **Path Cost 异常高** (>10) | 路径过长或链路质量差 | 检查中间跳的 Link Status in/out cost |
| **Target Dest = 0x0000** | 设备试图找到达协调器的路由 | 正常行为, 除非数量异常 |
| **Target Dest = 0xFFFC** | 异常! 广播地址不应作为路由目标 | 固件 bug 或网络配置错误 |
| **Radius = 0 的 Route Request** | 路由发现被限制, 无法跨跳 | 配置问题, 可能 nwkMaxDepth 设置过小 |

### 正常模式
- 设备上电后首次发送数据时出现 1-3 个 Route Request
- Many-to-One 模式下协调器定期广播 Route Request (所有设备建立到协调器的路由)
- 路由表条目过期后重新发现 (~30秒)

##extend: route_request

---

## 9. Route Reply (路由应答)

### 协议作用
AODV 路由发现的第二步。目标节点收到 Route Request 后, 沿反向路径单播 Route Reply
回到 Originator。路径上的中间节点建立路由表条目。

### 关键字段

| 字段 | 含义 |
|------|------|
| **Originator** | 原始请求方 (Route Request 的 NWK Src) |
| **Responder** | 路由应答方 (Route Request 的 Target Dest) |
| **Path Cost** | 累积路径开销 |
| **Route ID** | 与对应 Route Request 一致 |
| **Options** | OrigExt / RespExt |

### 诊断价值

| 异常 | 含义 |
|------|------|
| **Route Request 无对应 Reply** | 目标不可达或路径中断 |
| **Reply 的 Path Cost 高于 Request** | 不对称链路, 反向路径质量差 |
| **Reply 延迟 > 1 秒** | 路径多跳或中间节点处理慢 |

##extend: route_reply

---

## 10. Route Record (路由记录)

### 协议作用
源节点发送数据时, 在 NWK 头附加完整的路由路径 (Relay List)。
接收方知道数据经过的每一跳, 可用于 Many-to-One 路由的逆向路径记录。

### 关键字段

| 字段 | 含义 |
|------|------|
| **Relay Count** | 路径中的中继节点数 |
| **Relay List** | 每跳的 16-bit 短地址列表 |

### 诊断价值
- Relay Count = 0 → 直连通信 (单跳)
- 对比 Route Record 路径与实际数据流 → 验证路由表正确性
- 多次 Route Record 路径变化 → 网络拓扑波动

##extend: route_record

---

## 11. Link Status (链路状态)

### 协议作用
每台路由器/协调器定期 (15秒) 广播 1-hop Link Status 消息。包含所有邻居的
incoming/outgoing cost。用于邻居表维护和非对称链路检测。

### 关键字段

| 字段 | 含义 | 正常值 |
|------|------|--------|
| **Neighbor Address** | 邻居短地址 | - |
| **Incoming Cost** (1-7) | 本机收到邻居信号的质量 | 1-3 |
| **Outgoing Cost** (1-7) | 邻居收到本机信号的质量 | 1-3 |
| **Cost = 0** | 链路断开或从未评估 | 首次连接时临时出现 |

### Cost 含义
| Cost | 质量 | 建议 |
|------|------|------|
| 1 | 极佳 | 首选路径 |
| 2-3 | 良好 | 可用 |
| 4-5 | 较差 | 备用路径 |
| 6-7 | 差 | 需排查 |
| 0 | 断开 | 邻居不可达 |

### 诊断价值 — 非对称链路

```
设备A的Link Status: Neighbor B  in:1 out:7
设备B的Link Status: Neighbor A  in:7 out:1
```
→ A 的发信号强 (+18dBm), B 的发信号弱 (+3dBm)。A → B 可靠, B → A 不可靠。
路由应避免使用此链路。

### 诊断价值 — 网络稳定性

| 异常 | 含义 |
|------|------|
| **邻居数量频繁变化** | 设备移动或信号不稳定 |
| **所有邻居 out cost = 0** | 设备射频故障, 能收不能发 |
| **邻居表为空** | 设备隔离, 无直接通信 |
| **某邻居 cost 突然从 1→7** | 障碍物/干扰出现 |

##extend: link_status

---

## 12. Network Status (网络状态)

### 协议作用
当路由失败时, 中间节点向源节点发送 Network Status 报告错误原因。

### 状态码速查

| 代码 | 含义 | 常见原因 |
|------|------|---------|
| `0x00` | No Route Available | 目标设备离线或路由表缺失 |
| `0x01` | Tree Link Failure | 树状路由链路断开 |
| `0x02` | Non-Tree Link Failure | Mesh路由链路断开 |
| `0x03` | Low Battery | 终端设备电量不足 |
| `0x04` | No Routing Capacity | 路由表已满 |
| `0x07` | Target Unavailable | 目标设备无响应 |
| `0x0b` | Source Route Failure | 源路由路径中某跳不可达 |
| `0x0c` | Many-to-One Route Failure | Many-to-One 路由失败 |
| `0x0d` | Address Conflict | 短地址冲突 |
| `0x11` | Bad Frame Counter | 帧计数器异常 (安全攻击/密钥不同步) |

##extend: network_status

---

## 13. Leave (离开网络)

### 协议作用
设备主动或被动离开 Zigbee 网络。

### 关键字段

| 字段 | 含义 | 值 |
|------|------|-----|
| **Rejoin** | 是否允许重新加入 | 1=是, 0=否(永久离开) |
| **Remove Children** | 是否同时移除子设备 | 1=是, 0=否 |
| **Leave Address** | 离开的设备地址 | - |

### 诊断价值

| 场景 | 含义 |
|------|------|
| Rejoin=0 | 设备被永久踢出 (安全策略/TC拒绝), 需手动重新入网 |
| Rejoin=1 | 设备临时离开 (信号丢失/重启), 将自动尝试重新入网 |
| Remove Children=1 | 路由器离开, 其子设备也被移除 → 可能导致大量设备同时掉线 |
| 频繁 Leave/Rejoin | 设备在边缘信号区域反复掉线重连 |

##extend: leave

---

## 14. APS Acknowledgement (应用层确认)

### 协议作用
APS (Application Support Sublayer) 端到端确认机制。**与 MAC Ack 的关键区别：**
MAC Ack 是逐跳硬件确认 (~192μs)，APS Ack 由最终目标设备的应用层发送，
确认应用层数据已被正确接收。

### 关键字段

| 字段 | 含义 | 示例值 |
|------|------|--------|
| **APS Counter** | **必须等于所确认 Data 帧的 APS Counter** | `178` |
| **APS Frame Type** | APS Ack = `0x02` | `0x02` |
| **Dest Endpoint** | 目标端点 (通常与原始 Data 帧 Src EP 相同) | `1` |
| **Src Endpoint** | 源端点 | `1` |

### 诊断价值

| 异常现象 | 诊断含义 | 排查方向 |
|----------|---------|---------|
| **MAC Ack 存在但无 APS Ack** | 设备物理可达但应用层无响应 | P1-1: 检查 ZCL 层/路由非对称/设备忙 |
| **APS Ack 延迟 > 500ms** | 路由路径长或中间节点拥塞 | P1-6: 检查 Route Record 跳数 |
| **同一 APS Counter 多个 Data 帧** | 发送端未收到 APS Ack → 应用层重传 | P1-5: 检查链路/路由 |
| **APS Ack 的 Counter 不匹配任何 Data 帧** | 可能是延迟到达的陈旧 Ack | 正常可忽略 |

### APS Ack vs MAC Ack

| 维度 | MAC Ack | APS Ack |
|------|---------|---------|
| 层 | MAC (硬件) | APS (软件/应用层) |
| 范围 | 逐跳 (每对邻居之间) | 端到端 (源→最终目标) |
| 延迟 | ~192μs | 数ms ~ 数百ms |
| 失败含义 | 物理层/链路层不可达 | 应用层未处理或路由失败 |
| 广播帧 | 不发 (MAC Dst=0xFFFF) | 不发 (NWK Dst 广播) |

##extend: aps_ack

---

## 15. ZDP Node Descriptor Request/Response

### 协议作用
查询设备的 Zigbee 能力信息：设备类型 (协调器/路由器/终端)、制造商、频段、
缓冲大小、服务器能力等。

### 关键字段 (Response)

| 字段 | 诊断用途 |
|------|---------|
| **Node Type** | 确认设备角色是否匹配预期 |
| **Manufacturer Code** | 识别芯片厂商 (`0x1141`=Silicon Labs) |
| **Frequency Band** | 确认频段支持 (`2.4GHz` 必须为1) |
| **Max Buffer Size** | Node Descriptor 中的最大缓冲区大小 (1字节字段, 典型值66, 与 `maxIncomingTransferSize` 不同) |
| **Server Mask** | 服务能力 (Trust Center/Primary Binding等) |
| **Complex Info** | MAC能力 (FFD=全功能设备/主电源/空闲接收) |

### 诊断价值
- **Node Type 与预期不符** → 固件配置错误 (如路由器被配置为终端)
- **Max Buffer Size = 0** → 设备 Node Descriptor 缓冲区耗尽 (maxBufferSize=0, 非 maxIncomingTransferSize)
- **Server Mask 缺少 Trust Center** → 无法作为信任中心

##extend: zdp_node_desc

---

## 16. ZDP Mgmt LQI Request/Response

### 协议作用
查询设备的邻居表 (含 LQI 值)。可递归查询所有路由器, 构建全网络 LQI 矩阵。

### 关键字段 (Response)

| 字段 | 含义 |
|------|------|
| **Neighbor List** | 邻居设备列表 |
| **Neighbor Address** | 邻居短地址 |
| **Neighbor LQI** | 链路质量 (0-255, 值越大越好) |
| **Device Type** | 邻居类型 (Coord/Router/EndDev) |
| **Relationship** | 关系 (Parent/Child/Sibling/None) |

### 诊断价值
- **LQI < 50** → 链路质量极差, 丢包率 > 50%
- **LQI 100-200** → 可用, 有偶发丢包
- **LQI > 200** → 极佳链路
- **LQI 非对称** (A→B LQI=200, B→A LQI=40) → 确认非对称链路
- **邻居表缺少某设备** → 不在直接通信范围内

##extend: zdp_mgmt_lqi

---

## 17. Data (应用数据帧)

### 协议作用
承载 ZCL (Zigbee Cluster Library) 应用层数据。

### 关键字段

| 字段 | 含义 |
|------|------|
| **APS Cluster** | 应用功能分类 (0x0006=On/Off, 0x0019=OTA, 0x0000=Basic) |
| **APS Profile** | 应用规范 (0x0104=Home Automation, 0x0000=ZDP) |
| **ZCL Command** | 具体操作 (Read/Write/Report/Config) |
| **APS Counter** | 应用层序列号 (用于确认/重传配对) |
| **NWK Security** | 是否加密 |

### 诊断价值

| 异常 | 含义 |
|------|------|
| **APS Counter 跳跃** | 丢帧 — 链路或路由问题 |
| **同一 Counter 多次出现** | 应用层重传 — 对方未收到 Ack |
| **Data 帧无对应 APS Ack** | 应用层丢包, 需重传 |
| **Cluster 与设备能力不符** | 配置错误或恶意行为 |

##extend: data

---

## 诊断流程速查

> 以下为快速索引。每个场景的完整诊断流程（现象→证据链→诊断步骤→根因→解决）参见 [diagnosis_playbook.md](diagnosis_playbook.md)。

### 设备无法通信
→ 对应 [P1-1](diagnosis_playbook.md#p1-1-发送命令后设备无响应-无-aps-ack)
1. Link Status → 确认设备在邻居表中, cost 正常
2. Route Request/Reply → 确认路由可建立
3. Data 帧 → 确认应用层数据发送 + APS Ack 返回

### 设备频繁掉线
→ 对应 [P2-1](diagnosis_playbook.md#p2-1-终端设备频繁离线)
1. Leave 帧 → 检查 Rejoin 标志 (1=临时, 0=永久)
2. Link Status → 检查邻居 cost 是否波动
3. Network Status → 检查是否有路由失败报告

### 网络整体不稳定
→ 对应 [P3系列](diagnosis_playbook.md#p3-路由异常) + [P5-3](diagnosis_playbook.md#p5-3-信道干扰)
1. Link Status → 扫描所有设备的邻居表, 标记 cost≥5 的链路
2. Route Request → 统计频率, 超过 10次/分 = 异常
3. Network Status → 统计错误类型分布
4. LQI 矩阵 (Mgmt LQI) → 识别弱链路和非对称链路

### 设备加入失败
→ 对应 [P2-2](diagnosis_playbook.md#p2-2-设备无法加入网络) + [P2-3](diagnosis_playbook.md#p2-3-设备被-trust-center-拒绝-zigbee-30)
1. Beacon Request/Response → 确认信道和 PAN ID
2. Association Request/Response → 是否分配短地址
3. Transport Key → TC Link Key 是否正确
4. Device Announce → 确认设备广播入网
5. Node Desc → 确认设备类型和能力

### 密钥/安全异常
→ 对应 [P5-2](diagnosis_playbook.md#p5-2-密钥不同步--安全层异常)
1. Security Header → 检查 Key Seq# + Frame Counter
2. Network Status → 统计 Bad Frame Counter (0x11) 频率
3. Transport Key → 检查 Key Rotation 时序

---

> 文档版本: v2.0 | 16 帧类型 + `##extend` AI 扩展锚点
> 关联: [diagnosis_playbook.md](diagnosis_playbook.md) — 对应诊断场景
