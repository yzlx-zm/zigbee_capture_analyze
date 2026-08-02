# Zigbee 网络问题分类全景 — Problem Taxonomy

> **版本**: v1.0 | **日期**: 2026-08-01
> **来源**: /grilling 决策会话 + Silicon Labs 官方文档核查（docs.silabs.com / Gecko SDK / Community）
> **用途**: "问题描述 → 自动定位"分析引擎的分类基准。每个场景都有帧级证据链，可被分析脚本自动检测。
> **关联文档**: [diagnosis_playbook.md](diagnosis_playbook.md) — 5 大类 19 场景实战手册（本分类的原有子集）；[network_analysis_kb.md](network_analysis_kb.md) — 帧类型详解

---

## 分类原则

1. **按网络生命周期组织**（形成 → 维持 → 运营 → 维护），另设 SED/MAC/设备硬件三个专项维度
2. **每个场景必须有帧级证据链** — 可从 pcap/cubx 抓包中自动提取的特征（Network Status 错误码、MAC 状态、帧序列模式）
3. **与现有 playbook 兼容** — 原 P1-P5 保留在 playbook 中，本全景是完整超集

## 错误码速查表（帧级黄金标准）

### Network Status 命令错误码（0x00-0x13，来自 stack-info.h）

| 码 | 名称 | 含义 | 场景 |
|----|------|------|------|
| 0x00 | NO_ROUTE_AVAILABLE | 无可用路由 | P3-1 |
| 0x01 | TREE_LINK_FAILURE | 树状链路失败 | P3-1 |
| 0x02 | NON_TREE_LINK_FAILURE | 非树状链路失败 | P3-1 |
| 0x03 | LOW_BATTERY_LEVEL | **低电量导致路由失败** | L3-19 |
| 0x04 | NO_ROUTING_CAPACITY | 路由表满 | P3-4 |
| 0x05 | NO_INDIRECT_CAPACITY | **父节点间接队列满** | L6-S1 |
| 0x06 | INDIRECT_TRANSACTION_EXPIRY | **间接事务超时过期** | L6-S3 |
| 0x07 | TARGET_DEVICE_UNAVAILABLE | **目标设备不可用** | L3-8 |
| 0x08 | TARGET_ADDRESS_UNALLOCATED | **目标地址未分配** | L3-8 |
| 0x09 | PARENT_LINK_FAILURE | **父链路失败** | L2-3 |
| 0x0A | VALIDATE_ROUTE | **路由校验进行中** | L3-6 |
| 0x0B | SOURCE_ROUTE_FAILURE | **源路由失败** | L3-5 |
| 0x0C | MANY_TO_ONE_ROUTE_FAILURE | **Many-to-One 路由失败** | L3-5 |
| 0x0D | ADDRESS_CONFLICT | 短地址冲突 | P5-1 |
| 0x0E | VERIFY_ADDRESSES | **地址验证** | L3-8 |
| 0x0F | PAN_IDENTIFIER_UPDATE | **PAN ID 更新** | L4-3 |
| 0x10 | NETWORK_ADDRESS_UPDATE | **网络地址更新** | L3-8 |
| 0x11 | BAD_FRAME_COUNTER | 帧计数器错误 | P5-2 |
| 0x12 | BAD_KEY_SEQUENCE_NUMBER | 密钥序列号错误 | P5-2 |
| 0x13 | UNKNOWN_COMMAND | **未知命令** | L3-18 |

### MAC 层错误码

| 码 | 名称 | 含义 | 场景 |
|----|------|------|------|
| 0x14 / 0x40 | MAC_NO_ACK | MAC 层无 ACK（直接发送给 SED 常见） | L7-1 / L6 |
| 0x15 | CHANNEL_ACCESS_FAILURE | CCA 持续失败 → 高干扰 | L7-2 / P5-3 |
| 0x41 | MAC_INDIRECT_TIMEOUT | 间接队列超时清空 | L6-S3 |
| 0xA1 | BCAST_LIMIT_EXCEEDED | 8s 内超过 8 个广播（广播限速） | L4-4 |

### ZCL 设备级错误码（补充，区分设备故障 vs 网络故障）

| 码 | 含义 |
|----|------|
| 0x80-0x8D | 命令格式/集群/属性错误（P1-2 已覆盖） |
| 0xC0 | **Hardware Failure — 设备硬件故障** |
| 0xC1 | **Software Failure — 设备软件故障** |
| 0xC2 | **Calibration Error — 校准错误** |

---

## 完整场景清单（8 大类 ~55 场景）

### L1 网络形成与入网（7）

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L1-1 | 信道/网络发现失败（无 Beacon） | Beacon Request 无 Beacon 响应；0xAB NO_BEACONS |
| L1-2 | Association 失败 | Assoc Req 无 Resp；0x9B JOIN_FAILED |
| L1-3 | 密钥分发失败 | Assoc 成功但无 Transport Key；0x0C1B NO_NETWORK_KEY_RECEIVED |
| L1-4 | TC 拒绝入网 | Device Announce → 立即 Leave (Rejoin=0)；Remove Device |
| L1-5 | 大网络多跳入网失败（TC 地址解析失败） | Update Device 来自 >1 跳设备，TC 无 EUI64 地址解析 → APS 解密失败 |
| L1-6 | 并发入网风暴 | 多设备同时 Association Request 全部失败 |
| L1-7 | 误入错误 PAN | 加入的 EPAN ID ≠ 目标网络 |

### L2 设备在线维持（6）

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L2-1 | 终端设备频繁离线 | Data Request 轮询停止；Leave Rejoin=1 循环 |
| L2-2 | 父节点 Child Table 老化 | 子设备静默消失（无 Leave）；子设备 poll 未达 5min 超时 |
| L2-3 | Orphan/Rejoin 循环 | Orphan Notification 频繁；Rejoin Req 无响应；0x09 PARENT_LINK_FAILURE |
| L2-4 | 路由器掉线 → 子设备连锁离线 | 路由器 Leave (RemoveChildren=1)；Link Status 邻居表消失 |
| L2-5 | 设备移动后失联 | MOVE_FAILED (0x0C06)；Mobile Device 无父节点 |
| L2-6 | 设备静默失联（无 Leave 帧） | Link Status 邻居表条目消失，无任何离开通知 |

### L3 运营期核心（20）

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L3-1 | 发送命令无 APS Ack | Data 无同 Counter Ack；无 Ack 或 >1s |
| L3-2 | 命令送达未执行（ZCL 状态异常） | ZCL Default Response 0x80-0x8D |
| L3-3 | 状态上报滞后/不一致 | Write → Report 间隔 >10s 或无 Report |
| L3-4 | 绑定/组播命令未达 | 无 Bind Response；组播无 Multicast Route Reply |
| L3-5 | **源路由 / MTORR 失效** | Route Record 缺失；0x0B/0x0C SOURCE_ROUTE/MANY_TO_ONE_FAILURE |
| L3-6 | **路由校验失败** | 0x0A VALIDATE_ROUTE；频繁 Route Req |
| L3-7 | 路由路径震荡 | Route Record Relay List 频繁变化 |
| L3-8 | **目标不可达/地址未分配/地址验证** | 0x07/0x08/0x0E/0x10 |
| L3-9 | 非对称链路 | Link Status in/out cost 严重不对称 |
| L3-10 | 路由表溢出 | 0x04 NO_ROUTING_CAPACITY |
| L3-11 | 应用层重传频繁 | 同 APS Counter ≥3 次 |
| L3-12 | 端到端延迟过大 | TS 差值分级（见 playbook P1-6） |
| L3-13 | **广播中继失败** | 0x0C28 BROADCAST_RELAY_FAILED；0x0C27 SLEEPY_CHILDREN_TIMEOUT |
| L3-14 | **消息队列满/洪泛** | 0x0C03 MAX_MESSAGE_LIMIT_REACHED；in-flight 超限 |
| L3-15 | **路由表抖动 thrashing** | 邻居表频繁增删（dense network） |
| L3-16 | **TC Link Key 更新失败** | Request Key → Verify Key 超时；Update TC Link Key Error 0x04 |
| L3-17 | **信任中心更换（TC Swapout）** | 0x0C10/0x0C11 TRUST_CENTER_SWAP |
| L3-18 | **未知命令** | 0x13 UNKNOWN_COMMAND |
| L3-19 | **低电量路由失败** | 0x03 LOW_BATTERY_LEVEL |
| L3-20 | 密钥不同步 / Key Rotation 失败 / Counter 异常 | 0x11/0x12；Security Header Seq# 不一致（P5-2） |

### L4 网络级维护（5）

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L4-1 | 信道切换未跟随 | Network Update (ch 变更) 后设备失联重扫 |
| L4-2 | 信道干扰（WiFi/BLE 同频） | 全局 LQI 低；MAC 重传多（P5-3） |
| L4-3 | **PAN ID 变更/冲突** | 0x0F PAN_IDENTIFIER_UPDATE；0x0C16 PAN_ID_CHANGED；duplicate PAN ID |
| L4-4 | **广播风暴/限速** | 0xA1 广播限速；全网广播洪泛 |
| L4-5 | 网络规模超限 | dense network 邻居表抖动、路由表满 |

### L5 应用/功能层（4）

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L5-1 | OTA 升级中断 | Image Block Req 无 Resp |
| L5-2 | OTA 镜像请求失败 | Query Next Image → No Image |
| L5-3 | **Touchlink 加入失败** | Touchlink 流程中断（ZLL joining failed） |
| L5-4 | **ZCL 命令超时** | 命令后无 Default Response 超时 |

### L6 睡眠设备 SED 专项（5）⭐ 本会话新维度

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L6-S1 | **间接队列满（父节点）** | 0x05 NO_INDIRECT_CAPACITY |
| L6-S2 | **轮询间隔 > 7.68s 丢消息** | EMBER_INDIRECT_TRANSMISSION_TIMEOUT=7.68s；Data Request 间隔超时 |
| L6-S3 | **间接事务过期** | 0x06 INDIRECT_TRANSACTION_EXPIRY；0x41 MAC_INDIRECT_TIMEOUT |
| L6-S4 | **SED 假阳性在线（僵尸化）** | poll 无响应但栈状态 JOINED，不触发 rejoin |
| L6-S5 | **Poll Control 集群故障** | Check-in 无响应；Fast Poll 未触发 |

### L7 MAC/物理层（4）⭐ 本会话新维度

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L7-1 | MAC 无 ACK（直接发送 SED） | 0x14/0x40 MAC_NO_ACK |
| L7-2 | CCA 信道接入失败 | 0x15 CHANNEL_ACCESS_FAILURE |
| L7-3 | MAC 层重传风暴 | MAC ACK 重传频率异常高 |
| L7-4 | 帧校验失败（FCS） | FCS 错误帧比例高（干扰/硬件） |

### L8 设备硬件/固件（3）⭐ 本会话新维度

| ID | 场景 | 帧级证据链 |
|----|------|-----------|
| L8-1 | 设备硬件故障 | ZCL 0xC0 Hardware Failure |
| L8-2 | 设备软件故障 | ZCL 0xC1 Software Failure |
| L8-3 | **堆栈/硬件不匹配** | 0x0C15 STACK_AND_HARDWARE_MISMATCH |

---

## 与现有 playbook 的对应关系

| Taxonomy | Playbook |
|----------|----------|
| L1-1 ~ L1-4 | P2-2（入网 10 步断点定位） |
| L1-4 | P2-3（TC 拒绝） |
| L2-1, L2-4 | P2-1, P2-4 |
| L3-1 ~ L3-4 | P1-1 ~ P1-4 |
| L3-7, L3-9, L3-10 | P3-2, P3-3, P3-4 |
| L3-11, L3-12 | P1-5, P1-6 |
| L3-20 | P5-2 |
| L4-2 | P5-3 |
| L3-8(部分) | P5-1（短地址冲突） |
| L5-1, L5-2 | P4-1, P4-2 |

**新增（无对应 playbook 场景）**: L1-5, L1-6, L1-7, L2-2, L2-3, L2-5, L2-6, L3-5, L3-6, L3-8, L3-13, L3-14, L3-15, L3-16, L3-17, L3-18, L3-19, L4-1, L4-3, L4-4, L4-5, L5-3, L5-4, L6 全部, L7 全部, L8 全部

## 下一步（分析引擎设计基准）

1. 每个场景 → 可自动检测的帧特征规则（Network Status 码 / 帧序列模式 / 时间间隔）
2. "问题描述"自然语言 → 场景分类映射（关键词 + 症状特征）
3. 检测结果 → 关联 playbook 诊断步骤（人工复核依据）
