# Zigbee 网络分析知识库 — 关键帧诊断手册

> 用于后续网络问题分析脚本/Agent 的知识基础。
> 每帧记录：协议作用 → 关键字段 → 诊断价值 → 正常/异常模式。

---

## 1. Route Request (路由请求)

### 协议作用
AODV 按需路由发现的第一步。当源节点需要向目标节点发送数据但没有有效路由时，
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

---

## 2. Route Reply (路由应答)

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

---

## 3. Route Record (路由记录)

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

---

## 4. Link Status (链路状态)

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

---

## 5. Network Status (网络状态)

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

---

## 6. Leave (离开网络)

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

---

## 7. ZDP Node Descriptor Request/Response

### 协议作用
查询设备的 Zigbee 能力信息：设备类型 (协调器/路由器/终端)、制造商、频段、
缓冲大小、服务器能力等。

### 关键字段 (Response)

| 字段 | 诊断用途 |
|------|---------|
| **Node Type** | 确认设备角色是否匹配预期 |
| **Manufacturer Code** | 识别芯片厂商 (`0x1141`=Silicon Labs) |
| **Frequency Band** | 确认频段支持 (`2.4GHz` 必须为1) |
| **Max Buffer Size** | 设备接收能力 (66=默认, 小值可能导致分片) |
| **Server Mask** | 服务能力 (Trust Center/Primary Binding等) |
| **Complex Info** | MAC能力 (FFD=全功能设备/主电源/空闲接收) |

### 诊断价值
- **Node Type 与预期不符** → 固件配置错误 (如路由器被配置为终端)
- **Max Buffer = 0** → 设备资源耗尽
- **Server Mask 缺少 Trust Center** → 无法作为信任中心

---

## 8. ZDP Mgmt LQI Request/Response

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

---

## 9. Data (应用数据帧)

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
| **同一 Counter 多次出现** | 应用层重传 — 对方未收到 ACK |
| **Data 帧无对应 APS Ack** | 应用层丢包, 需重传 |
| **Cluster 与设备能力不符** | 配置错误或恶意行为 |

---

## 诊断流程速查

### 设备无法通信
1. Link Status → 确认设备在邻居表中, cost 正常
2. Route Request/Reply → 确认路由可建立
3. Data 帧 → 确认应用层数据发送 + APS Ack 返回

### 设备频繁掉线
1. Leave 帧 → 检查 Rejoin 标志 (1=临时, 0=永久)
2. Link Status → 检查邻居 cost 是否波动
3. Network Status → 检查是否有路由失败报告

### 网络整体不稳定
1. Link Status → 扫描所有设备的邻居表, 标记 cost≥5 的链路
2. Route Request → 统计频率, 超过 10次/分 = 异常
3. Network Status → 统计错误类型分布
4. LQI 矩阵 (Mgmt LQI) → 识别弱链路和非对称链路

### 设备加入失败
1. Beacon Request/Response → 确认信道和 PAN ID
2. Association Request/Response → 是否分配短地址
3. Transport Key → TC Link Key 是否正确
4. Device Announce → 确认设备广播入网
5. Node Desc → 确认设备类型和能力
