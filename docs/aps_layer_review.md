# APS 层解析复盘 — Zigbee Application Support Sublayer

> 产出: 2026-08-06 | 用途: APS 层协议知识 + 诊断工具解析现状盘点
> 依据: Silicon Labs 官方文档/SDK 源码 (zigbee_packet_types.h / sl_zigbee_aps_frame_t / test-harness) + 本项目解析器代码
> 状态: 知识已收集; 解析缺口见 §7 (可转入 P5 字段缺口工单流或检测器工单)
> 2026-08-06 合并: 吸收原 docs/aps_interaction_kb.md 增量 (重试时序数值/SED 路径/群控实证/引用清单), 原文档删除

## 1. APS 层职责 (官方依据)

APS 位于 NWK 之上、ZCL/应用之下,负责应用寻址与可靠投递。官方结构 `sl_zigbee_aps_frame_t`
([docs.silabs.com/zigbee/latest/zigbee-stack-api/sl-zigbee-aps-frame-t](https://docs.silabs.com/zigbee/latest/zigbee-stack-api/sl-zigbee-aps-frame-t)):

| 字段 | 含义 |
|------|------|
| profileId | 应用 Profile ID (0x0000=ZDP, 0x0104=HA, 0x0107=SE...) |
| clusterId | 集群 ID |
| sourceEndpoint / destinationEndpoint | 源/目标端点 (EP) |
| options | 选项位 (加密/重传/分段/路由发现等) |
| groupId | 组播组 ID (仅 GCAST) |
| sequence | APS Counter — 帧配对/防重放 |
| radius | 消息半径 (跳数上限) |

关键职责: 端点寻址 (EP)、集群路由、**APS 层密钥管理 (APSME)**、**可靠投递 (APS ACK + 重传)**、
分段/重组 (fragmentation)、组播/广播投递、绑定 (binding)。

## 2. APS 帧格式 (线上, 测试夹具源码实证)

来源: `test-harness-z3-core.c` `layeredHandlingMode` (EmberZNet SDK, APSDE 解析逻辑) +
`interpan.c` (Inter-PAN 变体)。

```
[APS FCF:1][DstEp:1 | GroupId:2(GCAST)][Cluster:2][Profile:2][SrcEp:1][APSCounter:1][ASDU...]
```

- **APS FCF** (1B): bit[1-0] = frame type (00=data / 01=cmd / 10=ack / 11=InterPAN); bit[3-2] = delivery mode
  (00=UCAST / 01=Reserved / 10=BCAST / 11=GCAST); 另有 security/ack-request 位
- delivery mode = GCAST 时, DstEp 位置换成 GroupId (2B LE)
- 地址字段 (16 位短地址/EUI64) 不在 APS 头内 — 取自 NWK 帧头, APS 层只带 EP/Group
- **APS Ack 帧**: type=2, **携带完整 APS 头** (2026-08-06 素材实证, 解密明文 8B:
  `[FCF][dst_ep][cluster:2][profile:2][src_ep][counter]`, 推翻此前 "[FCF][dst:2][counter:1]" 的
  Zigbee 2007 记忆 — G32 1179 条/第七次素材 ack 全部 8B 结构); counter 沿用原帧
  (FCF bit4 ack format=0), 部分设备实现为 2B 短帧 [FCF][counter] (第七次协调器侧, 非标)
- **配对字段**: ack 帧 nwk_dst = 原帧 nwk_src, ack counter = 原帧 counter → 字段级精确配对
  (第七次素材实测 60/62 精确匹配; 已实现于 API 层 + 详情面板展示)

## 3. APS 命令 ID 表 — 官方核对结果 ✅

来源: `zigbee_packet_types.h` ([simplicity_sdk sisdk-2025.6](https://github.com/SiliconLabs/simplicity_sdk/blob/sisdk-2025.6/protocol/zigbee/stack/include/zigbee_packet_types.h)):

| ID | 命令 | 项目代码 (`l1.py`) | 一致 |
|----|------|------|------|
| 0x05 | Transport Key | `APS_CMD_TRANSPORT_KEY = 0x05` | ✅ |
| 0x06 | Update Device | `APS_CMD_UPDATE_DEVICE = 0x06` | ✅ |
| 0x07 | Remove Device | `APS_CMD_REMOVE_DEVICE = 0x07` | ✅ |
| 0x08 | Request Key | `APS_CMD_REQUEST_KEY = 0x08` | ✅ |
| 0x09 | Switch Key | — (未用到) | — |
| 0x0A-0x0D | EA 增强安全挑战 (R21+) | — | — |
| 0x0E | Tunnel Data (Zigbee Direct) | — | — |
| 0x0F | Verify Key | `APS_CMD_VERIFY_KEY = 0x0F` | ✅ |
| 0x10 | Verify Key Confirm | `APS_CMD_VERIFY_KEY_CONFIRM = 0x10` | ✅ |

> ⚠️ 修正记忆误区: 老 Zigbee 2007 表的 0x05=SwitchKey / 0x07=VerifyKey / 0x08=ConfirmKey 已过时;
> EmberZNet (Zigbee 3.0) 体系中 TransportKey=0x05、VerifyKey=0x0F、Confirm=0x10。项目代码从 2026-08-04
> 起就与官方头文件一致 (L1-3.md 有记录), 本次 MCP 复核无出入。

## 4. 密钥管理 (APSME) — key type 体系

**TransportKey 命令里的 StandardKeyType** (zigbee_packet_types.h):

| 值 | 含义 |
|----|------|
| 0x01 | Residential/Standard Network Key (素材实证: 入网 TransportKey) |
| 0x03 | Application Link Key |
| 0x04 | TC Link Key (素材实证: TCLK 更新流程) |
| 0x06 | Invalid Key |
| 0xB0-0xB3 | Zigbee Direct 专用密钥 |

**RequestKey 命令里的 KeyType** (test-harness-z3-aps.c): 0x01=Network Key / 0x02=Application Link Key / 0x04=TCLK
⚠️ 注意: 同一数值在不同命令上下文含义不同 (RequestKey 0x02=App Link, TransportKey 0x03=App Link)。

**辅助安全头 Security Control** (zigbee_packet_types.h): Key Identifier mask = 0x18 →
0x00=Link Key / 0x08=Network Key / 0x10=Key Transport Key / 0x18=Key Load Key。

**完整入网密钥流程** (实测: 中继入网抓包素材, L1-3.md v1.2):
`AssocResp → TransportKey(NWK, 8ms 后) → Device Announce → [TCLK 更新: RequestKey(0x08) → TransportKey(TCLK) → VerifyKey(0x0F, keyed_hash) → VerifyKeyConfirm(0x10)]`
TC 发起 TCLK 更新的前置: Node Descriptor Req 验证对端 R21+ 栈版本 (官方 updateTcLinkKey 文档)。

## 5. 可靠性机制 (诊断相关性)

| 机制 | 协议依据 | 诊断场景关联 |
|------|---------|-------------|
| APS ACK | frame type=2, counter 匹配原帧 | **L3-1 发送命令无 APS Ack** (⬜ 未实现) |
| APS 重传 | `EMBER_APS_OPTION_RETRY`: "Resend the message using the APS retry mechanism" | **L3-11 应用层重传频繁** (⬜) |
| 分段 | `EMBER_APS_OPTION_FRAGMENT` | 大包/满队列相关 |
| 绑定 | binding table: 本地 EP+cluster → 远端设备 | **L3-4 绑定/组播未达** (⬜) |
| 组播 | GCAST delivery mode + groupId | L3-4 (⬜) |
| 间接事务 | NWK 层间接队列 + Network Status 0x06 (非 APS 命令) | L6-S3 (✅ 已实现) |

### 5.1 EmberZNet 完整重试时序 (KBA 实测数值, 诊断时间窗依据)

来源: [Community KBA: EmberZNet 堆栈重试如何工作 (CN)](https://community.silabs.com/s/article/emberznet-cn-x) + [message.h](https://github.com/SiliconLabs/simplicity_sdk/blob/sisdk-2025.6/protocol/zigbee/stack/include/message.h)

| 层 | 行为 | 数值 |
|---|---|---|
| MAC | CSMA/CCA 退避 (0-7/0-15/0-31/0-31/0-31 个 320µs 退避周期) → 传帧 → 等 ACK 最长 54 符号 (864µs); 失败再重试, 共最多 5 次尝试 (4 次重试) | 完全失败 ~37ms |
| NWK | MAC 失败后等 16-48ms 随机退避再发; 单播最长 500ms; 广播 500ms 间隔 ×3 次 (或邻居全回应) | 最长 500ms |
| APS | 失败后等 (100ms×MAX_HOPS)/2 = **50ms×hops** 再重发; 最多 **3 次尝试** (首+2); 单次尝试超时默认 **(50ms×30hops)+100ms = 1600ms** (message.h 宏: `SL_ZIGBEE_APSC_MAX_ACK_WAIT_HOPS_MULTIPLIER_MS 50` + `TERMINAL_SECURITY_MS 100`); EmberZNet 3.1+ 可每节点自定义 (EZSP_CONFIG_APS_ACK_TIMEOUT) | 3 次尝试 |
| SED 特例 | 目标为睡眠终端时每跳**额外加一次间接传输超时** (EMBER_INDIRECT_TRANSMISSION_TIMEOUT); 未设扩展超时标志 → 额外 APS 重试/潜在投递失败 | — |
| 路由修复 | EMBER_APS_OPTION_RETRY + EMBER_APS_OPTION_ENABLE_ROUTE_DISCOVERY 双开 → 投递失败自动修路; 无法投递报 **EMBER_DELIVERY_FAILED (0x66)** | — |

### 5.2 SED 睡眠终端取 APS Ack 的特殊抓包路径

来源: [ETRX357 App Note — Power Consumption §2.6](https://www.silabs.com/documents/public/application-notes/TG-APP-ETRX3Power-201.pdf)

SED 需要 APS ACK 时的完整操作 (三次电流脉冲, 功耗实测):
1. 发送单播消息, 收 MAC ACK
2. **发 Data Request (poll), 从父节点取回 APS Ack, 再回 MAC ACK**
3. (可选) 再次 poll 取更多消息

→ **抓包表现: APS Ack 往往出现在 SED 的 poll (Data Request) 之后, 由父节点下发**, 而非紧跟在数据帧后 (群控锁场景直接相关: 16 锁全部 SED ~1s 轮询)。

## 6. 工具 APS 解析现状 (双路径矩阵)

### 6.1 cubx 路径 (`cubx_reader.py`)

| 字段 | 提取 | 说明 |
|------|------|------|
| aps_cluster / aps_profile | ✅ | 明文可得时; 解密失败置 None 防假字段 (0x20/0x38 误读已修复) |
| aps_cluster_name | ✅ | ZDP 表 (profile 0x0000) / zcl_defs 双表, 对齐 tshark |
| aps_counter / aps_src_ep / aps_dst_ep | ✅ | |
| aps_frametype | ✅ | scapy 拆分字段 (0=data/1=cmd/2=ack) |
| aps_cmd_id | ✅ | 手动字节解析 (仅解密后明文) |
| aps_cmd_key_type | ✅ | 0x05/0x08/0x0F → payload[1]; 0x10 → payload[2] |
| aps_cmd_remove_target | ✅ | 0x07 payload[1:9] EUI64 (L1-4) |
| aps_cmd_update_status | ✅ | 0x06 payload[1] (L1-4) |
| aps_payload_hex | ✅ | 解密明文 hex (ZDP 详情) |
| APS 解密 | ✅ | ZigbeeSecurityHeader 子层判定 + network/link keys |

### 6.2 pcap/tshark 路径 (`tshark.py`)

| 字段 | 提取 | 说明 |
|------|------|------|
| aps_cluster | ✅ | zbee_aps.cluster + zdp_cluster 兼容 |
| aps_profile / counter / src / dst ep | ✅ | (:373-375, zbee_aps.src/dst) |
| aps_cmd_id / key_type / device / update_status | ✅ | zbee_aps.cmd.* (改从 "Command Frame: X" 子 dict 读, P1 缺陷 3 修复) |
| aps_payload_hex | ❌ 占位 None (:434) | P5 待补 (ZDP 详情仅 cubx 可用) |
| pkt_type "APS Ack" | ✅ 输出结构已素材实证 (2026-08-06): 标准素材 7/7 Ack 帧 tshark 输出 zbee_aps.type=0x02 + ack_format + counter, NWK 加密帧 (7/7 nwk_security=True) 解出 APS 层即 decrypted=True; 两路径 counter 值完全一致 (14=14, 195=195); 判定仍为 "Ack" in aps_fcf (:523) key 字符串匹配 → **建议改位级** (zbee_aps.type==2) | ack_format=1 紧凑 ACK 只有 FCF+dst+counter (无 cluster/profile); ack_format=0 时 tshark 输出 zdp_cluster/profile (Ack 帧归 ZDP 命名) → aps_cluster = zcl_cluster or zdp_cluster fallback 对 Ack 帧生效 |

### 6.3 API/前端

- `files.py` fallback: `zbee_aps.*` 键统一对齐前端 (profile/cluster/zdp_cluster/src/dst/counter/cmd_id/key_type/remove_target/update_status)
- 详情面板 (timeline.js): Cluster/Profile/Src EP/Dest EP/Counter + 命令名/Key Type/Remove Target/Update Status (条件显示)
- 类型列: `aps_cluster_name` (ZCL 簇名/命令名)

### 6.4 检测器使用情况

| 检测器 | APS 依赖 | 状态 |
|--------|---------|------|
| L1-3 密钥分发 | aps_cmd_id (0x05/0x08/0x0F/0x10) + key_type (0x01/0x04) | ✅ 素材实证闭环 |
| L1-4 TC 拒绝/踢人 | aps_cmd_remove_target (0x07) + update_status (0x06) | ✅ 检测器就绪 |
| L2-1/L3-5/L6-S3 | 不依赖 APS 命令 (NWK/MAC 层) | ✅ |

### 6.5 群控素材 APS 交互实证 (可靠性维度现有基础)

来源: P1 回归 `.scratch/verification/p1-contract/p1_regression.py` (:41-47) + P1 ticket Resolution (2026-08-06 自审修正)

- **缺投帧锁侧 ACK 佐证 18/18 命中**: 判定 = `pkt_type=='APS Ack'` (cubx aps_frametype==2) + 3s 窗口 + nwk_src 匹配 → "锁均收到, 抓包漏投递帧"结论成立 (中继实际全投递)
- **17/18 counter 匹配 — 实证结论 (2026-08-06 P1 查证)**: 原脚本 `.scratch/analysis_group_control_profile.py` **从未提交过 git** (git log --all 无记录, git ls-files 无匹配), 已删除不可恢复; 但数据路径可重建 — cubx 对 Ack 帧的 aps_counter 从 scapy aps.counter 读 (APS 头 counter 字段, 加密帧解密后读明文), 标准素材实测 cubx Ack 帧 counter=14/195 有值; ⚠️ 注意官方回归口径 (p1_regression.py:36-38) 已弃 counter/事务键 (nwk_seq 8-bit 回绕错误合并相隔 421s 事务), 改用 3s 时间窗; counter 匹配可作为重建方向但需注意此缺陷
- **counter 匹配重建可行性 ✅**: 两路径 APS Ack 字段契约一致 (counter 14=14/195=195, aps_src_ep/aps_dst_ep=0), 可直接用 `pkt_type=='APS Ack'` + `aps_counter` 重建配对
- **数字口径教训**: 首轮 62%/67% (nwk_seq 8 位回绕致事务键失真) → 修正后 64% 实为抓包器第二跳捕获率, 真实投递 25/25; 去重 (frame_dedup.py 同跳 mac 键) 是计数前提
- **已知 counter 不匹配案例** (P1 待办): 33440 seq=77 锁 ACK counter 53 vs 数据帧 31 — 可能锁 ACK 了更早帧, 配对逻辑必须处理此情形
- 配对基线素材: 中继入网抓包(1).cubx 含 221 条 APS Ack

## 7. 缺口清单 (APS 维度)

| # | 缺口 | 影响场景 | 工作量 | 建议路径 |
|---|------|---------|--------|---------|
| A | **APS FCF 未完整提取** (delivery mode/security/ack-req 位) | L3-1 判定需区分"要求了 ack 没收到" vs "没要求"; 含 tshark "Ack" 字符串匹配改位级 + 先实证 tshark 对 type=2 帧输出结构 | 小 | P5 工单 |
| B | **APS Ack 关联匹配** (ack 的 counter ↔ 原帧) | **L3-1 发送命令无 APS Ack** (⬜ 场景, 检测器不存在); 群控已有 18/18 实证基础 (§6.5); **前置已具备 (2026-08-06)**: 两路径 Ack 帧 counter 契约一致, 可直接用 `pkt_type=='APS Ack'` + `aps_counter` 重建配对; 注意 nwk_seq 回绕教训 + 处理"锁 ACK 更早帧"案例 | 中 | 新检测器工单 |
| C | APS 重传轮次判定 (同 counter 多帧) | L3-11 应用层重传频繁 (⬜); 时间窗依据见 §5.1 (APS 3 次/50ms×hops) | 小 | P5 + 检测器 |
| D | groupId / 组播投递解析 | L3-4 绑定/组播未达 (⬜) | 小 | P5 |
| E | aps_payload_hex (pcap 路径) | ZDP 详情双路径一致 (P1 契约遗留) | 中 | P5 (P1 关联) |
| F | APS 帧的 pkt_type 归类细化 | 时间线 APS Ack 无独立类型显示 | 小 | UI 工单 |

**结论**: APS 字段级解析覆盖 ~80%, 密钥流程 (L1-3/L1-4) 已闭环; 空白集中在
**可靠性维度 (ACK 匹配/重传)** — 而这正是"设备收不到下发"类诊断 (L3-1/L3-11) 的协议级判定基础,
建议作为 APS 维度下一个检测器工单的候选 (素材: 中继入网抓包(1).cubx 含 221 条 APS Ack, 可做配对基线)。

## 8. 官方来源清单

- zigbee_packet_types.h (APS 命令 ID / key type / security control): github.com/SiliconLabs/simplicity_sdk sisdk-2025.6
- sl_zigbee_aps_frame_t (APS 帧结构): docs.silabs.com/zigbee/latest/zigbee-stack-api/sl-zigbee-aps-frame-t
- Messaging (APS 选项语义): docs.silabs.com/zigbee/latest/zigbee-concepts-network/messaging
- test-harness-z3-core.c (APSDE 线上帧解析实证): github.com/SiliconLabs/gecko_sdk gsdk_4.5
- test-harness-z3-aps.c (RequestKey key_type / 加密选项): 同上
- interpan.c (Inter-PAN APS 帧): 同上 sisdk-2025.6
- EZSP 参考 (updateTcLinkKey 密钥流程): docs.silabs.com/zigbee/latest/sisdk-ezsp-reference-guide/09-security-frames
- Zigbee Fundamentals — Routing Concepts (三层重试体系/APS ACK 概览): docs.silabs.com/zigbee/latest/zigbee-fundamentals/04-zigbee-routing-concepts
- Zigbee Concepts Network — Table Routing (路由修复/APS 超时): docs.silabs.com/zigbee/latest/zigbee-concepts-network/table-routing
- zigbee_applications — Networking Concepts (单跳 4 步/多跳时序, EMBER_APS_OPTION_RETRY): github.com/SiliconLabsSoftware/zigbee_applications
- KBA: EmberZNet 堆栈重试如何工作 (CN, 完整时序数值): community.silabs.com/s/article/emberznet-cn-x
- message.h (APS ACK 超时宏): github.com/SiliconLabs/simplicity_sdk sisdk-2025.6 stack/include
- ETRX357 App Note — Power Consumption §2.6 (SED poll 取 APS Ack): silabs.com/documents/public/application-notes/TG-APP-ETRX3Power-201.pdf
- Community: Are messages always received in order? (APS 序号/重复帧): community.silabs.com/s/article/are-messages-always-received-in-the-order-they-were-sent-is-it-normal-to-receiv
- Community: duplicate frames (去重可选性, 旧): community.silabs.com/s/question/0D51M00007xeT5jSAE
- KBA: Major R23 Updates (APS Duplicate Rejection R23 起强制): community.silabs.com/s/article/Zigbee-KBA-Discussing-Major-R23-Updates
- Network Analyzer — Viewing Data in Editors (事务定义/endToEndRetries): docs.silabs.com/network-analyzer/latest/network-analyzer-viewing-data-in-editors/
- Network Analyzer — Filtering Captured Data (event.summary == "APS Ack" 过滤): docs.silabs.com/network-analyzer/latest/network-analyzer-filtering-captured-data/
- Community: When the APS command could be used? (广播无 APS ACK): community.silabs.com/s/question/0D58Y0000A8shURSQY
