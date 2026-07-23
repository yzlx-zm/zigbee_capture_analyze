# Zigbee 网络问题诊断手册 — 抓包分析实战

> 核心用途：工程师通过抓包定位 Zigbee 网络问题。
> 每类问题按 **现象→证据链→诊断步骤→根因→解决** 结构化。
> 预留 `##extend` 标记，后续 AI Agent 可通过自然语言扩展。
>
> 📚 **关联文档**: [network_analysis_kb.md](network_analysis_kb.md) — 关键帧类型详解，证据链中引用的帧类型定义在 kb 中有完整说明。
>
> **`##extend` 标记规范**: 每个 `##extend: {场景ID}` 为 AI Agent 预留的扩展锚点。Agent 可通过场景 ID
> (如 `P1-1`, `P3-2`, `appendix`) 定位到具体诊断场景，在其后追加新分支或细化步骤，无需修改已有内容。

---

## P1: 控制丢失 & 状态不同步

### P1-1: 发送命令后设备无响应 (无 APS Ack)

**现象:**
- 网关/APP 发送 On/Off/Level 命令，设备不执行
- 发送端未收到应用层确认

**证据链 (抓包中要看的帧):**

| 序号 | 帧类型 | 要看什么 | 正常 | 异常 |
|------|--------|---------|------|------|
| 1 | **Data** (命令帧) | 是否成功发送到 NWK 层 | NWK Src/Dst 正确 | NWK Dst 不匹配或帧丢失 |
| 2 | **APS Ack** (确认帧) | 是否返回应用层确认 | 同 Counter 有配对 Ack | 无 Ack, 或 Ack 延迟 >1s |
| 3 | **Route Request** | 命令发送前是否有路由 | 发送前 1-5 秒有 Route Req/Reply | 大量 Route Req 无 Reply |
| 4 | **Link Status** | 目标设备的邻居链路质量 | in/out cost ≤3 | cost ≥5 或 out=0(断开) |
| 5 | **Network Status** | 路由是否失败 | 无 | 出现 Route Failure (0x00/0x01/0x02) |

**诊断步骤:**
1. 在时间线过滤 `Data` 帧 → 找到命令帧 → 检查 NWK Src/Dst 是否正确
2. 查看命令帧后 0-500ms 内是否有同 Counter 的 `APS Ack` 帧
3. 如无 Ack → 过滤 `Link Status` → 查目标设备的邻居表是否有发送方 + cost 是否正常
4. 如邻居正常 → 过滤 `Route Request` → 查是否有到目标设备的路由发现
5. 如路由正常但仍无 Ack → 查目标设备是否在线 (Link Status 邻居表中是否出现)

**根因定位:**
- 无 APS Ack + Link Status cost=7 → **非对称链路** — 命令能发到设备, 但设备的 Ack 回不来
- 无 APS Ack + 频繁 Route Request → **路由失效** — 路径中的中继节点掉线
- 无 APS Ack + Link Status 无目标设备 → **设备已离线**

**解决方案:**
- 非对称链路: 增加路由器改善反向链路, 或调整目标设备天线位置
- 路由失效: 检查中间路由器是否在线, Link Status 确认路径完整
- 设备离线: 排查设备电源/距离/干扰, 查看 Leave 帧确认是否主动退网

##extend: P1-1

---

### P1-2: 命令已送达但设备未执行 (ZCL 状态码异常)

**现象:**
- APS Ack 正常返回 (表示命令已送达)
- 但设备未执行操作 (灯不亮/窗帘不动)
- ZCL 响应中携带错误状态码

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Data** (命令+响应) | ZCL Command + Status Code |
| 2 | **APS Ack** | 确认命令送达 |
| 3 | **ZCL Default Response** | 错误码 (如 0x80=Malformed, 0x82=Unsupported) |

**诊断步骤:**
1. 找到命令帧 → 确认 APS Ack 正常
2. 找到设备返回的 ZCL 响应帧 → 检查 Status Code
3. 常见 ZCL 错误码:
   - `0x80` Malformed Command → 命令格式错误 (固件版本不兼容)
   - `0x81` Unsupported Cluster → 设备不支持该功能
   - `0x82` Unsupported Command → Cluster 支持但该命令不支持
   - `0x8B` Not Authorized → 安全权限不足

**根因:**
- ZCL Status ≠ 0x00 → 应用层拒绝执行
- 非 0x80/0x81/0x82 → 查看具体错误码含义

**解决方案:**
- 检查命令格式是否符合 ZCL 规范
- 确认固件版本支持该 Cluster/Command
- 如果是 Not Authorized, 检查绑定和安全配置

##extend: P1-2

---

### P1-3: 状态上报与实际不符 (Report Attribute 滞后/不一致)

**现象:**
- APP 显示灯亮度 50%, 但实际灯是 100%
- 设备上报的状态与执行结果不一致
- 状态变更后长时间未上报

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Data** (命令帧) | 发送的 Write/Command 的参数值 |
| 2 | **Data** (Report Attribute) | 设备上报的状态值 |
| 3 | **时间戳** | 命令→执行→上报的时间间隔 |

**诊断步骤:**
1. 找到 Write Attribute 或 On/Off 命令帧 → 记录写入值
2. 找到后续 Report Attribute 帧 → 对比上报值是否与写入值一致
3. 计算 Write → Report 的时间间隔 (正常 <1s)
4. 如无 Report → 检查 Configure Reporting 是否已配置

**根因:**
- Report 值与写入值不同 → 设备端执行失败或覆盖写入
- Report 延迟 >10s → 设备速率限制或 Reporting Interval 配置过大
- 无 Report → Reporting 未配置, 或设备不支持自主上报

**解决方案:**
- 配置合理的 Reporting Interval (0-600s)
- 设置 Reportable Change (如亮度变化 >5% 才上报)
- 确认设备支持 Attribute Reporting 功能

##extend: P1-3

---

### P1-4: 绑定/组播命令未到达目标设备

**现象:**
- 通过绑定表或组播发送命令, 部分目标设备未收到
- APS Ack 机制在组播中不适用 (组播不确认, 无法通过 Ack 直接判断丢失)
- 同一组内部分设备执行、部分未执行

**证据链 (抓包中要看的帧):**

| 序号 | 帧类型 | 要看什么 | 正常 | 异常 |
|------|--------|---------|------|------|
| 1 | **Data** (组播/绑定帧) | NWK Dst 是否为组地址 (0xFFxx) 或单播地址 (绑定) | Dst 匹配目标组或绑定地址 | Dst 为广播 (0xFFFF) 但实际应为组地址 |
| 2 | **Multicast Route Request** | 组播路由是否建立 | 有对应的 Multicast Route Reply, Member/Non-Member 模式正确 | 无 Reply, 或 Non-Member 模式但无中继节点 |
| 3 | **Link Status** | 组内所有目标设备的邻居链路 | 组内设备 in/out cost ≤3 | cost ≥5 或设备不在邻居表中 |
| 4 | **ZDO: Match Desc / Bind Req** | 发送前绑定表是否已建立 | 有 Bind Request/Response 且 Status=0x00 | 无绑定记录或绑定失败 |
| 5 | **Group Membership (ZCL)** | 设备是否已加入组 | Add Group Response Status=0x00 | Get Group Membership 返回空或缺少目标组 |

**组播模式说明:**

| 模式 | 工作机制 | 适用场景 | 抓包特征 |
|------|---------|---------|---------|
| **Member Mode** (成员模式) | 设备使用组地址为目标, NWK 层广播到所有组成员 | 小型网络, 设备密集 | NWK Dst = 组地址 (0xFFxx), MAC Dst = 广播 |
| **Non-Member Mode** (非成员模式) | 命令先单播到组播中继 (Multicast Relay), 中继再广播 | 大型网络, 设备分散 | 有 Multicast Route Request/Reply, 中继节点作为代理 |

**诊断步骤:**
1. 在时间线过滤 `Data` 帧 → 找到组播/绑定命令 → 确认 NWK Dst 格式
2. 如果是组播 → 检查是否有 `Multicast Route Request` 及对应 Reply → 确认组播模式
3. 如果是绑定 → 过滤 `Bind Request/Response` (ZDO) → 确认绑定表条目状态
4. 过滤 `Link Status` → 检查组内每个目标设备的邻居表中是否包含发送方, cost 是否正常
5. 过滤 `Get Group Membership` / `Add Group Response` → 确认目标设备的组表中是否存在目标组 ID

**根因定位:**
- 无 Multicast Route Reply + Non-Member 模式 → **组播中继不可用** — 无设备作为组播中继或中继路由失败
- 有 Multicast Route Reply 但部分设备没收到 → **中继覆盖不足** — 部分设备在中继广播范围外
- 绑定模式无 Bind Response → **绑定表未建立** — 发送端绑定配置失败或目标设备不支持绑定
- 组内设备 Link Status 中无发送方 → **设备不在同一路由域** — 组播帧无法到达
- 设备 Group Table 中无目标组 → **设备未加入组** — Add Group 未执行或组 ID 被清除

**解决方案:**
- 组播中继不可用: 在组内指定一台稳定路由器作为 Multicast Relay, 确保其在所有组成员的 1-hop 范围内
- 中继覆盖不足: 增加组播中继数量, 或改用 Member Mode (仅适用于小规模网络)
- 绑定表未建立: 重新执行绑定流程 → 检查 ZDO Bind Response 的 Status
- 设备未入组: 重新发送 Add Group 命令 → 确认 Group Membership Response 包含目标组
- 混合使用绑定和组播时: 确认发送端侧的逻辑正确切换 (绑定的设备用单播, 组播的设备用组地址)

##extend: P1-4

---

### P1-5: 应用层重传频繁 (同 Counter 多次出现)

**现象:**
- 同一 APS Counter 的命令帧出现多次
- 设备收到重复命令 (可能导致重复执行)

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Data** (重复帧) | 同一 APS Counter 出现次数 |
| 2 | **APS Ack** | 是否缺失 |

**诊断步骤:**
1. 在时间线按 Counter 排序 → 查同一 Counter 出现次数
2. 如果 Counter 出现 ≥3 次 → APS Ack 未正常返回 → 回退到 P1-1 排查
3. 如果 Ack 正常但仍有重复 → 发送端重传逻辑异常 (应用层 bug)

**根因:**
- APS Ack 超时 → 发送端重传 → 链路质量问题
- 发送端 APS 重传间隔设置过短

##extend: P1-5

---

### P1-6: 端到端延迟过大 (>500ms)

**现象:**
- 命令发送到设备执行间隔过长 (>500ms)
- 用户体验差 (按键后灯有明显延迟)

**延迟分级标准:**

| 级别 | 延迟范围 | 含义 | 对策 |
|------|---------|------|------|
| 🟢 正常 | `< 100ms` | 单跳或多跳快速路由 | 无需处理 |
| 🟡 偏慢 | `100 ~ 500ms` | 稍慢, 用户几乎无感 | 可优化拓扑 |
| 🟠 慢 | `500ms ~ 1.6s` | 用户明显感到延迟 | 需排查 (见诊断步骤) |
| 🔴 异常 | `1.6s ~ 10s` | 超过 APS 重传超时 (~1.6s), 可能存在路由发现阻塞 | **必须排查** |
| ⚫ 严重 | `> 10s` | 超过 `nwkRouteDiscoveryTime` (NWK 路由发现超时, 默认 10s) | 路由已失效, 通信实际上已中断 |

> 基准: `nwkRouteDiscoveryTime` (默认 10000ms, NWK 层路由发现超时) 为协议层面异常判定标准。
> 超过此阈值意味着路由发现已经超时, 设备在等待路由重建而非正常通信延迟。

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | Timestamp 差值 | 命令帧 TS → 执行完成 TS (精确到 ms) |
| 2 | **Route Record** | 经过的跳数 + Relay List 路径 |
| 3 | **Route Request** | 路由发现耗时 (首 Req → 对应 Reply 的间隔) |
| 4 | **NWK FCF** | 是否包含 Discover Route 标志 (路由发现中) |
| 5 | **Link Status** | 路径上各跳的 in/out cost |

**诊断步骤:**
1. 计算命令帧 → 响应帧的时间戳差值, 按分级标准判定严重程度
2. 如果延迟在 500ms~1.6s: 查看 Route Record 的 Relay Count → 跳数>5 则路径过长需优化拓扑
3. 如果延迟在 1.6s~10s: 检查是否有并发 Route Request → 发送时路由表缺失, 路由发现拖慢了首帧
4. 如果延迟 >10s: 检查 NWK FCF Discover Route 标志 → 路由已超时 → 回退到 P3-1 (路由黑洞)
5. 如果跳数少但延迟高: 检查 Link Status → 中间节点是否为低功耗设备 (Sleepy End Device 唤醒延迟)
6. 如果路径中某跳 cost ≥5: 该链路为瓶颈 → 非对称或干扰 → 参考 P3-3

##extend: P1-6

---

## P2: 设备掉线 & 入网失败

### P2-1: 终端设备频繁离线

**现象:**
- 终端设备 (ZED) 反复从网络中消失
- 需手动重置才能恢复

**证据链:**

| 序号 | 帧类型 | 要看什么 | 正常 | 异常 |
|------|--------|---------|------|------|
| 1 | **Leave** | Rejoin 标志 | - | Rejoin=0 (永久离开) |
| 2 | **Link Status** | 设备在邻居表中消失的时间 | 持续出现 | 突然消失 |
| 3 | **Data Request** | ZED 轮询父节点的频率 | 每 1-10s | 突然停止 |
| 4 | **Orphan Notification** | ZED 失联后请求恢复 | 偶尔出现 | 频繁出现 |

**诊断步骤:**
1. 在时间线过滤 `Leave` → 查找设备发出的 Leave 帧
2. 如果 Rejoin=1 → 设备临时离开 (信号/电源原因), 会自动重连
3. 如果 Rejoin=0 → 设备被永久踢出, 需手动重新入网
4. 如果无 Leave 帧 → 设备静默离线 (电池耗尽/硬件故障)

**根因:**
- Leave + Rejoin=1: 信号边缘区域, 设备反复掉线重连
- Leave + Rejoin=0: 安全策略拒绝 (TC Link Key 失败)
- 无 Leave 静默离线: 电池耗尽或硬件故障

**解决方案:**
- 信号边缘: 增加路由器, 缩短 ZED-父节点距离
- TC 拒绝: 检查 Trust Center 安全策略, 清空设备重新入网
- 电池问题: 检查 Report Interval 是否过于频繁

##extend: P2-1

---

### P2-2: 设备无法加入网络

**现象:**
- 新设备或重置后的设备无法加入
- 入网流程中断在某个步骤

**入网流程 (完整 10 步):**
```
1. Beacon Request → 2. Beacon → 3. Association Request → 4. Association Response
→ 5. Data Request → 6. Transport Key → 7. Device Announce → 8. Active EP Req/Resp
→ 9. Simple Desc Req/Resp → 10. Basic Read Attributes
```

**证据链 (哪步断了):**

| 断在哪步 | 要看的帧 | 根因 |
|----------|---------|------|
| 无 Beacon Response | Beacon Request 无回复 | 信道不匹配 或 协调器未开启入网许可 |
| Beacon Permit=0 | Beacon 帧的 Association Permit 标志 | 协调器关闭了入网 |
| 无 Association Response | Assoc Req 发送后无回应 | PAN ID 不匹配 或 设备不在协调器范围内 |
| 无 Transport Key | Assoc Resp 后无 Key | TC Link Key 配置错误 |
| 无 Device Announce | Device Announce 未广播 | 设备未收到短地址 或 NWK 层异常 |
| TC Link Key 交换失败 | Device Announce → Leave | TC 拒绝了设备的 Link Key (Zigbee 3.0) |

**诊断步骤:**
1. 过滤 `Beacon Request` 和 `Beacon` → 确认信道和 PAN ID 匹配
2. 过滤 `Association Request/Response` → 确认设备被分配了短地址
3. 过滤 `Transport Key` → 确认 NWK Key 已分发
4. 过滤 `Device Announce` → 确认设备广播入网成功

##extend: P2-2

---

### P2-3: 设备被 Trust Center 拒绝 (Zigbee 3.0)

**现象:**
- Device Announce 之后立即收到 Leave (Rejoin=0)
- 设备进入无限重试循环

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Transport Key** | TC Link Key 交换 |
| 2 | **Device Announce** | 设备宣布入网 |
| 3 | **Leave** (紧随其后) | Rejoin=0, 被踢出 |

**根因:**
- 设备携带的 TC Link Key 与协调器不匹配
- 固件升级后 TC Link Key 被重置
- 协调器侧 `zgPreConfigKeys = TRUE` 导致 Link Key 无法协商

**解决方案:**
- 清空设备端 NV/Flash 重新入网
- 协调器侧设置 `zgPreConfigKeys = FALSE`

##extend: P2-3

---

### P2-4: 路由器掉线导致子设备连锁离线

**现象:**
- 一个路由器离线 → 其下所有子设备同时掉线
- 子设备无法自动切换到其他父节点

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Leave** (路由器) | Remove Children=1 |
| 2 | **Link Status** | 路由器从所有邻居表中消失 |
| 3 | **Orphan Notification** | 子设备寻找新父节点 |

**诊断步骤:**
1. 找到路由器的 Leave 帧 → 确认 Remove Children 标志
2. 查看子设备的 Orphan Notification → 确认是否成功找到新父节点
3. 如果子设备未恢复 → 检查范围内是否有其他可用路由器

**根因:**
- 路由器单点故障 → 子设备无冗余父节点
- 子设备未启动 Orphan 恢复机制

**解决方案:**
- 增加冗余路由器覆盖
- 确保子设备固件支持 Orphan Notification 恢复

##extend: P2-4

---

## P3: 路由异常

### P3-1: 路由黑洞 (Route Request 无 Reply)

**现象:**
- 设备持续发送 Route Request 但无 Route Reply
- 数据无法到达目标设备

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Route Request** | Target Dest / Route ID / 频率 |
| 2 | **Route Reply** | 是否有匹配的 Reply |
| 3 | **Link Status** | 目标设备 + 中间设备邻居表 |
| 4 | **Network Status** | 路由失败错误码 |

**诊断步骤:**
1. 过滤 Route Request → 记录未收到 Reply 的 Route ID
2. 检查 Target Dest 设备是否在线 (Link Status 中是否出现)
3. 检查路径中每跳的 Link Status: 是否有 cost=0 (断开) 的邻居
4. 查看 Network Status 的错误码

**根因:**
- 目标设备离线
- 路径中某跳链路断开 (in/out cost = 0)
- 中间设备路由表满, 无法转发
- 设备间距离过远 (Radius 不足)

##extend: P3-1

---

### P3-2: 路由路径震荡 (频繁切换路径)

**现象:**
- Route Record 路径频繁变化
- 同一 Route ID 对应不同 Relay List

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Route Record** | Relay List 是否变化 |
| 2 | **Route Request** | 频率是否异常 (>5次/秒) |
| 3 | **Link Status** | 邻居 cost 是否波动 |

**诊断步骤:**
1. 过滤 Route Record → 按时间排序 → 查看 Relay List 是否频繁变化
2. 对比多次 Route Record 的路径 — 如果每次不同 → 路由震荡
3. 检查变化路径上设备的 Link Status → cost 波动 → 信号不稳定

**根因:**
- 某条链路质量波动 → 设备反复切换路由
- 环境干扰 → 2.4GHz 信道拥挤

##extend: P3-2

---

### P3-3: 非对称链路 (A→B OK, B→A 不通)

**现象:**
- 一端能发数据, 另一端发不了
- Link Status 显示 in/out cost 严重不对称

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Link Status** (设备A) | 邻居B的 in/out cost |
| 2 | **Link Status** (设备B) | 邻居A的 in/out cost |
| 3 | **Data** | 单向有 APS Ack, 反向无 Ack |

**诊断步骤:**
1. 收集设备A和设备B的 Link Status (需两者都在抓包范围内)
2. 对比: A→B 的 out cost vs B→A 的 in cost → 如果都正常 → 不是非对称
3. 如果 A.out=1, B.in=7 → A→B好, B→A差 → 非对称
4. 常见原因: A 发射功率高 (+18dBm), B 发射功率低 (+3dBm)

**解决方案:**
- 调整发射功率使两端均衡
- 在 A 和 B 之间增加中继路由器
- 避免使用非对称链路作为路由路径 (Zigbee 路由协议会自动避开)

##extend: P3-3

---

### P3-4: 路由表溢出

**现象:**
- 路由器无法建立新路由条目
- 旧路由被过早淘汰

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Network Status** | No Routing Capacity (0x04) |
| 2 | **Route Request** | 频率异常高 (路由条目被淘汰后重新请求) |
| 3 | **Node Desc** | Max Buffer 很小 |

**诊断步骤:**
1. 过滤 Network Status → 查看是否有 `No Routing Capacity` 错误
2. 过滤 Route Request → 如果某设备频繁为不同目标发送 Route Req → 路由表满
3. 检查设备 Node Desc 的 Max Buffer (路由表大小通常与此相关)

**解决方案:**
- 减少网络中活跃路由数量 (避免过多并发通信)
- 增加路由器数量分担路由负载
- 调整设备路由表大小 (固件参数)

##extend: P3-4

---

## P4: OTA 升级失败

### P4-1: 升级过程中断 (Image Block 传输失败)

**现象:**
- OTA 升级到某 % 后停止
- 设备回退到旧固件

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Data** (OTA Image Block) | Block Request/Response 连续性 |
| 2 | **APS Ack** | 每个 Block 是否确认 |
| 3 | **Route Request** | 升级期间路由是否稳定 |

**诊断步骤:**
1. 过滤 `OTA Upgrade` Cluster → 查看 Image Block Req/Resp 序列
2. 检查有无 Block Request 未收到 Response → 传输中断点
3. 中断点附近查看 Route Request → 是否路由失效导致中断

**根因:**
- 路由中断 → Block 传输失败 → 重试超限 → 升级失败
- 设备内存不足 → 无法接收下一个 Block

##extend: P4-1

---

### P4-2: 镜像请求失败 (Query Next Image 返回 No Image)

**现象:**
- 设备请求 OTA 镜像, 服务器返回 `No Image Available`

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Data** (OTA Query Next Image Req) | 请求的 Manufacturer Code + Image Type |
| 2 | **Data** (OTA Query Next Image Resp) | Status: No Image Available |

**根因:**
- Manufacturer Code 不匹配
- Image Type 不匹配
- 服务器尚未准备好镜像

##extend: P4-2

---

## P5: 其他

### P5-1: 短地址冲突

**现象:**
- 两个设备使用相同的 16-bit 短地址
- 通信混乱, 数据发到错误设备

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Network Status** | Address Conflict (0x0d) |
| 2 | **Device Announce** | 新设备宣布的短地址是否与已有设备冲突 |
| 3 | **IEEE Address** | 用 IEEE 长地址区分冲突设备 |

##extend: P5-1

---

### P5-2: 密钥不同步 / 安全层异常

**三层密钥架构速查 (Zigbee 3.0):**

| 密钥层 | 名称 | 作用 | 分发方式 | 生命周期 |
|--------|------|------|---------|---------|
| **NWK Key** | Network Key | 保护所有 NWK 层 payload (APS+ZCL 数据) | Transport Key (TC → 设备) | Key Rotation 时更新, 全网统一 |
| **TC Link Key** | Trust Center Link Key | 保护入网时 NWK Key 分发, 建立安全信任 | 预配置 (Pre-configured) 或 默认 (ZigBeeAlliance09) | 设备入网后可能被 APS Link Key 替换 |
| **APS Link Key** | Application Link Key | 保护两个设备间的 APS 层应用数据 (端到端) | TC 分发 (Request Key) 或 预配置 | 设备间绑定/配对时建立 |

**现象:**
- 部分帧无法解密 (NWK Key 不匹配)
- 设备被 TC 拒绝
- 已入网设备突然通信中断 (Key Rotation 后)
- Network Status 报告 `Bad Frame Counter (0x11)` 或 `Bad Key Sequence Number (0x12)`

**证据链:**

| 序号 | 帧类型 | 要看什么 | 正常 | 异常 |
|------|--------|---------|------|------|
| 1 | **Security Header** (每帧) | Key Seq# + Frame Counter | Seq# 全网一致, Counter 单调递增 | Seq# 不一致, Counter 回跳或重复 |
| 2 | **Network Status** | Bad Frame Counter (0x11) / Bad Key Seq# (0x12) | 无此类错误 | 频繁出现 → 安全不同步 |
| 3 | **Transport Key** | NWK Key 分发 / Key Rotation | Key Seq# 递增, 全网广播 | Key 分发后仍有老 Key 的帧 |
| 4 | **Leave** (紧随 Device Announce 之后) | TC 拒绝 (Rejoin=0) | - | Device Announce → 立即 Leave → TC Link Key 不匹配 |
| 5 | **Data** (加密帧) | APS 层是否能解密 | 用网络当前 NWK Key 可解 | 用老 Key 加密的帧持续出现 (设备仍用旧 Key) |

**诊断步骤:**
1. 过滤 `Transport Key` → 检查是否有 Key Rotation 事件 (Key Seq# 从 0→1→2...)
2. 过滤 `Network Status` → 统计 `Bad Frame Counter (0x11)` 的次数和源设备
3. 如果有 Key Rotation → 查看 Rotation 前后各设备的帧: 是否所有设备同步切换到新 Key
4. 如果某设备持续用老 Key → 该设备未收到 Transport Key (路由黑洞/离线期间 Key Rotation)
5. 过滤 `Leave` → 检查 Device Announce 后立即 Leave 的设备 (TC Link Key 不匹配)
6. 检查 Security Header 的 Key Seq# → 同一网络中不同设备是否使用相同的 Key Seq#

**Frame Counter 异常场景:**

| 场景 | 特征 | 根因 | 解决 |
|------|------|------|------|
| **Counter 回跳** | 同一设备 Frame Counter 从大值 (如 50000) 跳到小值 (如 10) | 设备 NV/Flash 清空或复位, Counter 归零 | 设备重新入网获取新 Key |
| **Counter 重复** | 两个设备使用相同的 Frame Counter 序列 | 设备克隆或固件 bug | 检查固件 Counter 存储逻辑 |
| **Counter 溢出** | Counter 接近 0xFFFFFFFF (32-bit 上限) | 设备长期运行, 未触发 Key Rotation | 主动触发 Key Rotation 重置 Counter |
| **Bad Counter 增多** | 多个邻居报告同一设备的 Bad Frame Counter | 该设备安全状态异常 (被攻击/固件错误) | 检查设备, 必要时清空 NV 重新入网 |

**Key Rotation 时序分析:**

```
正常 Key Rotation 流程:
1. TC 生成新 NWK Key → broadcast Transport Key (Key Seq# N+1)
2. 全网路由器接收新 Key → 更新本地 NWK Key 表
3. TC 开始用新 Key 加密 → 旧 Key Seq# N 的帧逐渐消失
4. 全部设备切换到新 Key → 完成

异常场景:
- 设备离线期间发生 Key Rotation → 设备回来后用老 Key 发帧 → 被丢弃
- Key Rotation 过快 (间隔<1min) → 部分设备跟不上 → Security Header Seq# 不一致
- Transport Key 广播未被中继 → 远跳设备收不到新 Key → 出现两种 Key Seq# 并存
```

**根因定位:**
- Device Announce 后立即 Leave (Rejoin=0) → **TC Link Key 不匹配** — 参考 P2-3
- Key Rotation 后部分设备通信中断 → **Key 同步失败** — 设备未收到或未处理 Transport Key
- 频繁 Bad Frame Counter → **Counter 不同步** — 设备 NV 异常或 Frame Counter 归零
- 同一网络出现两种 Key Seq# → **Key Rotation 不完整** — 存在网络盲区或广播未覆盖到

**解决方案:**
- TC Link Key 不匹配: 清空设备 NV → 协调器侧确认 `zgPreConfigKeys = FALSE` → 重新入网
- Key Rotation 同步失败: 增加 Key Rotation 前的广播确认; 对未同步设备单独发送 Transport Key (单播)
- Frame Counter 异常: 检查设备 NV 存储可靠性; 触发 Key Rotation 重置全局 Counter
- 混合 Key Seq#: 手动触发全网 Key Rotation 强制统一; 排查 Transport Key 广播未到达的设备

##extend: P5-2

---

### P5-3: 信道干扰

**现象:**
- 所有设备通信不稳定
- LQI 普遍偏低

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Link Status** | 全局 cost 是否普遍偏高 |
| 2 | **Mgmt LQI** | 全网络 LQI 矩阵 |
| 3 | **MAC ACK** | MAC 层重传频率 |

**诊断:**
- 大量 MAC 重传 → 物理层干扰
- 所有链路 LQI < 100 → 信道拥塞 (WiFi/蓝牙同频干扰)
- 切换到不同信道 (Ch.11/15/20/25)

##extend: P5-3

---

## 附录 A: 诊断流程速查

### A1: 设备不通 → 分三层排查
```
应用层: Data帧有APS Ack? → Yes→ ZCL Status正常? → Yes→ 设备执行?
                                   → No→ P1-1(链路/路由)
                        → No→ P1-1(设备离线)
网络层: Route Request/Reply正常? → Yes→ 查Route Record路径
                                  → No→ P3-1(路由黑洞)
MAC层:  Link Status邻居表有目标? → Yes→ cost正常?
                                  → No→ P2-1(设备掉线)
```

### A2: 抓包证据收集模板
```
问题描述: [设备地址] [操作] [预期结果] [实际结果] [发生时间]
抓包时间范围: [开始 ~ 结束]
关键帧清单:
  □ Link Status (源+目的+路径上所有路由器的邻居表)
  □ Route Request/Reply/Record (路由状态)
  □ Data (命令+响应, 含ZCL Status)
  □ APS Ack (确认率)
  □ Leave (设备离线原因)
  □ Network Status (路由错误)
  □ Node Desc (设备能力)
```

##extend: appendix

---

> 文档版本: v1.0 | 覆盖: P1-P5 共 5 大类 19 个子场景
> 每个 `##extend` 标记为 AI Agent 预留扩展点
