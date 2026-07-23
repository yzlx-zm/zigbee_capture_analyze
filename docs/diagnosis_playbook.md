# Zigbee 网络问题诊断手册 — 抓包分析实战

> 核心用途：工程师通过抓包定位 Zigbee 网络问题。
> 每类问题按 **现象→证据链→诊断步骤→根因→解决** 结构化。
> 预留 `##extend` 标记，后续 AI Agent 可通过自然语言扩展。

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
- APS Ack 机制在组播中不适用 (组播不确认)

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Data** (组播帧) | NWK Dst 是否为组地址 (0xFFxx) |
| 2 | **Link Status** | 组内所有设备的邻居链路 |
| 3 | **Route Request** | 组播路由请求 |

**诊断步骤:**
1. 确认组播帧 MAC Dst = 广播 (0xFFFF) 或组地址
2. 检查组内每个设备是否在同一路由域
3. 查看 Link Status 确认设备间直接可达

**根因:**
- 组播帧未被中继 → 超出直接通信范围
- 某些设备不在组内 → 绑定表/组表配置错误

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

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | Timestamp 差值 | 命令帧 TS → 执行完成 TS |
| 2 | **Route Record** | 经过的跳数 |
| 3 | **Route Request** | 路由发现耗时 |

**诊断步骤:**
1. 计算命令帧 → 响应帧的时间戳差值
2. 如果 >500ms: 查看路由路径跳数 (Route Record Relay Count)
3. 如果跳数 >5: 路径过长, 需优化拓扑
4. 如果跳数少但延迟高: 检查中间节点处理延迟 (可能是低功耗设备唤醒)

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

### P5-2: 密钥不同步

**现象:**
- 部分帧无法解密 (NWK Key 不匹配)
- 设备被 TC 拒绝

**证据链:**

| 序号 | 帧类型 | 要看什么 |
|------|--------|---------|
| 1 | **Network Status** | Bad Frame Counter (0x11) |
| 2 | **Security Header** | Key Seq# 是否变化 |
| 3 | **Transport Key** | 是否有 Key Rotation |

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
