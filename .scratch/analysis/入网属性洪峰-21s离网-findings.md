# 入网后属性洪峰 → 密钥请求无应答 → 21s 离网 — 素材实证记录

> 日期: 2026-08-07 | 工具: 工程自带分析工具 (backend 8721, cubx 解析 + L1-L6 检测器 + 帧级明细)
> 状态: ✅ 三个素材均验证核心模式; 细节有修正

## 素材

1. `C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包(1).cubx` (4158 NWK 包)
2. `C:\Users\Administrator\Desktop\zigbee_capture\入网离线分析\sm\第七次设备添加失败.cubx` (588 包)
3. `C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包-DA13-网关修改v3-第一次入网失败-重新入网成功.cubx` (1468 包)

## 核心时序 (TransportKey 为 t0)

| 阶段 | 0x838D (素材1) | 0xCE77 (素材2) | 0x1CC4 (素材3) |
|---|---|---|---|
| TransportKey (网络密钥) | t0 | t0 | t0 |
| Device Announce | +0.01s ×4 | +0.01s ×3 | +0.01s ×3 |
| 网关首条属性命令 | +0.12s (Reset to Factory) | +0.51s | +0.12s |
| 前 3s 下行帧数 | **47** (Write ×12, Reset ×2, ZDP 发现 ×10, Ack ×12) | **45** (Write ×12, Reset ×1, Ack ×14) | **28** (Write ×7, Reset ×2, ZDP 发现 ×8) |
| 首次 RequestKey (link key 0x04) | +2.01s | +1.57s | +2.04s |
| 网关应答 | ✅ +2.05s TransportKey → VerifyKey → VerifyKeyConfirm 完成 | ✅ +2.01s → +2.52s Confirm | ✅ +2.07s → +3.07s Confirm |
| 密钥确认后续轮次 | +3.0/+4.6/+6.6s 多轮 Confirm 均发送 | +2.5s 一轮 | +3.1/+4.8/+6.8/+7.3/+9.2s 多轮 |
| 后续 RequestKey | +9.0/+12.3/+16.5s **全部无应答** | +6.5/+11.5/+16.5s **全部无应答** | +12.2/+16.5s **全部无应答** |
| 离网 | +21.21s Leave(rj=0) | +21.21s Leave(rj=0) | +21.22s Leave(rj=0) |
| Network Status 0x0B | +2.3s 起 39 条 (中继 0x1885) | 0 条 (L3-5 HEALTHY) | +3.0s 起 40 条 (中继 0x87AB) |
| L3-1 无 APS Ack | ×85 | ×39 | ×30 |

## 结论与修正

1. **核心假设成立**: 网关在 TransportKey/DA 后 0.1-0.5s 即开始灌属性/发现命令 (前 3s 28-47 帧), 与密钥更新 (RequestKey→TransportKey→VerifyKey→VerifyKeyConfirm) 重叠。
2. **修正**: 抓包显示网关实际发送了多轮 VerifyKeyConfirm (最终密钥确认包), 并非"完全没发/完全丢失"。但设备仍持续 RequestKey → 说明设备侧**未处理到/未接受**确认包 (抓包可见 ≠ 设备处理), 对应假设中"处理不过来"分支; 也可能是下行确认包在设备队列中丢失。
3. **"网关只回答一次"成立**: 三素材中首个 RequestKey 簇均被应答, 后续全部无应答。
4. **新增强特征 — 21.2s 恒定离网延迟**: 三素材离网均为 t0+21.21s (±0.01s), 疑似设备侧固定入网/密钥超时, 可作检测器核心判定条件。
5. **中继场景叠加源路由失效**: 素材1/3 中 NS 0x0B 从 +2.3-3.0s 开始 (断链前一跳 0x1885/0x87AB), 上行仍通 (RequestKey 可达), 下行部分失败 — 与既有 L3-5 结论一致。
6. **检测器信号**: L3-1 无 APS Ack (30-85 条) + L2-1 Leave + L3-5 交叉, 现有检测器已能部分捕捉; 缺"RequestKey 重复-无应答"和"21.2s 离网"专项规则。

## 建议

立 wayfinder ticket: 新场景 (或 L1-3 子类) "入网后属性洪峰 → 密钥确认未处理 → 21s 超时离网", 检测规则草案:
- R1: TransportKey 后 ≤3s 内下行 ZCL/ZDP 命令 ≥20 帧 (洪峰)
- R2: RequestKey (key_type=0x04) 出现 ≥2 次且其后 2s 无 TransportKey 应答
- R3: t0 → Leave(rj=0) 延迟 ∈ [20.5s, 22s]
- R4: 与 L3-5 交叉归因 (有 0x0B 时优先源路由失效; 无 0x0B 时独立判定)

## 补充核查 (2026-08-07 晚)

### 1. ConfirmKey 状态字节 = 0x00 SUCCESS (crypto 完全健康)

从 aps_payload_hex 直接解析 (cubx_reader):
- VerifyKeyConfirm payload = `10 00 04 <dst_eui64 LE 8B>` — 状态恒为 0x00, key type 0x04, dst EUI64 与设备一致
- TransportKey (type=4) 携带的是每个设备独立的 TC Link Key; VerifyKey 载荷 (keyed hash) 每次重试完全相同
- → 排除: 密钥不一致 / TC 拒绝 / 校验失败。设备反复 VerifyKey/RequestKey 是因为**没收到或没处理** ConfirmKey

### 2. "Reset to Factory Defaults" 是解析器误标, 实际是 Read Attributes (读版本号)

`aps_payload_hex = 10 4b 00 04 00 00 00 01 00 05 00 07 00 fe ff`
- fcf=0x10 (profile-wide, disable default response) → cmd 0x00 = **Read Attributes**, 非 cluster-specific 的 Reset to Factory Defaults
- 读取 Basic 簇属性: 0x0000 ZCLVersion / 0x0001 AppVersion / 0x0005 Model / 0x0007 PowerSource / 0xFFFE
- 网关入网后立即读"版本号" — 与素材名"版本号未上报/网关没收到"直接对应
- ⚠️ 工具 bug: cubx 路径 zcl_cmd_name 未按 FCF 帧类型区分, 把所有 cluster=0x0000+cmd=0x00 标成 Reset to Factory Defaults (P5 字段缺口)

### 3. 离网是设备自决, 非网关踢

- 838D/CE77/1CC4 离网前窗口无 Remove Device (0x07) / Mgmt Leave Req (0x0034)
- 设备广播 Leave(rj=0, req=0) — 自身超时后离开; 工具 diag "被踢" 分类不准确
- 21.2s 恒定 → 设备侧固定入网/密钥超时 (疑似 Telink SDK join/link-key timeout, 待源码确认)

### 4. 中继场景: 入网设备无 Route Record → 下行源路由缺失

- 838D/1CC4 入网后无任何 Route Record (全网 RR 列表无该短地址)
- 网关下行单播源路由不可用 → 0x0B 风暴 (断链前一跳 0x1885/0x87AB)
- CE77 无 0x0B 也以同样方式失败 → 路由失效是放大器, 非根因

### 5. 修正后的根因候选排序

1. 设备 APS/安全状态机未处理到 ConfirmKey (洪峰占用队列/处理) — 主因候选
2. 网关"只答一次" TC 策略 (防 RequestKey 洪泛, 合理但加剧) — 次因
3. 设备固件安全子层对 ConfirmKey 处理缺陷 (Telink 栈, 待源码/日志) — 待查
4. 中继下行源路由缺失 (仅中继场景) — 放大器

### 区分实验建议

- A: 网关延迟 5s 再读属性 → 是否仍 21s 离网
- B: 网关持续应答 RequestKey → 是否不再离网
- C: 设备侧串口日志看 ConfirmKey 是否到达、安全状态机去向
- D: 对照健康素材 (标准入网 2): 健康网络网关是否也立即读属性

## 健康素材对照 (2026-08-07, 实验 D 完成)

素材: `验证可用-记录\1-标准入网抓包-2.cubx` (0x2951 入网, 340 包)

| 维度 | 健康 (0x2951) | 故障 (838D/CE77/1CC4) |
|---|---|---|
| 密钥流程 | RequestKey×1 → TransportKey×1 → VerifyKey×1 → Confirm×1 (一次闭环, 36ms) | 多轮 VerifyKey/Confirm + 后续 RequestKey 无应答 |
| 网关读属性/洪峰 | 仅 +0.1s 一条 Match Desc Req; **无 Write/Read 洪峰** | DA 后 0.1-0.5s 起 28-47 帧/3s |
| 设备上报 | +1.7s 设备主动 Report Attributes ×12 | 设备忙于应答网关命令 |
| 离网 | 无 (0 Leave) | +21.2s 自决 Leave |

结论: 健康与故障的**唯一显著差异 = 网关是否在密钥握手期间灌属性洪峰**。

## Telink 栈侧机制 (用户工程文档, 待固件日志确认)

来源: `D:\work\SwitchModule-telink\zigbee开发积累\` + Claude memory

- RX 链路: `RX → tl_zbTaskProcedure → zcl_cmdHandler → 回调 → 主循环`; 若主循环/回调被阻塞或任务调度不及时, 协议栈无法处理入站帧
- 用户手册原文: "设备入网后离网 | 保活失败 | 检查主循环 tl_zbTaskProcedure() 是否被调用"
- BDB 入网状态含 TCLK_FAILURE (TC key 失败); 本素材 ConfirmKey=SUCCESS → 不是 key 不匹配, 而是设备没收到/没处理
- 已知 SDK 侧缺陷 (group0-buffer-leak-debug.md): tl_zbTaskProcedure 内部 G0 缓冲只 alloc 不 free — 洪峰下缓冲耗尽可致丢帧 (对中继固件为推断)
- 设备 EUI a4c138... = Telink OUI; 协调器 EUI ef3f4afeff7ee0e8 同为 Telink — Telink↔Telink 网络

## 修正后的根因模型 (证据分级)

1. **触发 (实证)**: 网关在 Device Announce 后 0.1-0.5s 开始读版本+写配置+ZDP 发现洪峰 (28-47 帧/3s), 与 TC Link Key 更新握手重叠
2. **直接机制 (强推断)**: 设备 Telink 栈应用处理/任务队列被洪峰占用 → ConfirmKey 处理被推迟/丢弃 → BDB 安全握手未闭环 → 5s 重试 VerifyKey/RequestKey
3. **加剧 (实证)**: 网关仅应答首个 RequestKey 簇, 后续全部忽略 (TC 防重/策略)
4. **中继放大器 (实证)**: 入网设备无 Route Record → 下行源路由缺失 → 0x0B 风暴
5. **超时 (实证, 常量待 SDK 确认)**: 21.2s 固定离网延迟 (t0+21.21s ±0.01s, 三个素材一致)
6. **已排除**: 密钥不匹配 / TC 拒绝 (ConfirmKey status=0x00); 网关踢人 (无 0x07/0x0034)

## 待办

- [ ] 实验 C: 设备侧日志 (bdbcommissioningCb 状态 / ConfirmKey 是否收到 / tl_zbTaskProcedure 调度)
- [ ] 实验 A: 网关延迟 5s 读属性
- [ ] SDK 源码找 21.2s / 5s 重试常量 (当前 X: 路径不存在, 需用户提供 SDK 位置)
- [ ] 工具 bug: FCF 误标 (提示词已交付 Claude Code)

## 泛洪测试对照 (2026-08-11, 用户 zigbee_router_test 目录)

### 测试结果

- 泛洪测试一/二 + buffer-40: 洪峰中入网 5-8 次, **全部未离网** (`Last Leave: 0`, `APS Unauthorized Key: 0`, `Packet Buffer Allocate Failures: 0`)
- 复现的是: `MANY_TO_ONE_ROUTE_FAILURE (0xAA)` / `DELIVERY_FAILED(0x66)` / MAC retry 30 / NWK retry overflow 8 → 对应抓包的 0x0B/0x0C 路由错误分支
- 基准线 cubx (直连, 6 次密钥交换): 全部闭环, 无 21.2s 离网; 其 Leave 为测试流程主动 (间隔 38-83s)

### 对照量化 (入网后前 3s 网关→设备的定向下行帧)

| 场景 | 结果 | 前3s下行 | 内容特征 |
|---|---|---|---|
| 健康 0x2951 | 成功 | 8 | APS Cmd×3 + Match Desc×1 + Ack×3 |
| 基准线 0x250E (6次) | 成功 | 3~11 | APS Cmd + Match Desc + Ack, **无 Write 洪峰** |
| CE77 (素材2) | 失败 21.2s | **45** | **Write×12** + 读版本 + ZDP 发现×4 + Ack×14 |
| 838D (素材1) | 失败 21.2s | **47** | **Write×12** + 读版本×2 + ZDP 发现 + Ack×12 |
| 1CC4 (素材3) | 失败 21.2s | **28** | **Write×7** + 读版本×2 + ZDP 发现×8 |

### 关键推论

1. **CE77 直连协调器入网 (wpan 0000→CE77, 无中继, NS=0) 也 21.2s 离网** → 中继/0x0B 不是必要条件
2. **泛洪测试未复现离网** 的原因不是"洪峰不够", 而是洪峰形态不对:
   网络级泛洪(路由错误/DELIVERY_FAILED) ≠ 网关 add 流程的**定向单播配置洪峰**
   (Write Attributes ×7-12 + 读版本 + ZDP 发现, 全部定向发给入网设备, 要求 APS Ack/ZCL 响应)
3. 判别量: 成功 ≤11 帧/3s; 失败 ≥28 帧/3s 且含 Write Attributes ×7+
4. 泛洪测试日志还证明: 该固件在路由错误风暴下不丢包缓冲 (Buffer Failures=0)、不报 Unauthorized Key

### 修正后的复现配方 (待验证)

- 拓扑: **直连即可** (CE77 已证明不需要中继)
- 触发: 设备入网 DA 后 0.1~0.5s, 网关对**该设备**发送 ≥28 帧/3s 定向单播:
  Write Attributes ×12 + Basic 读版本 (0x0000/0x0001/0x0005/0x0007/0xFFFE) + ZDP Match/ActiveEP/SimpleDesc
- 预期: RequestKey (+1.5~2s) → 网关答一次 → 5s×3 重试 → +21.2s Leave(rj=0)
- 观察: 必须同时 RF 抓包 + 设备串口 (bdbcommissioningCb / Last Leave / Unauthorized Key)
- 对照: 同一 add 流程去掉 Write×12 洪峰 → 应成功闭环 (基准线 3~11 帧已证明)

## SDK 源码实证 (2026-08-07, Telink SDK V3.7.2.0)

路径: `X:\allen\work\code_sdb1\SwitchModule-telink\tls8258\telink_zigbee_sdk-V3.7.2.0\tl_zigbee_sdk\zigbee\bdb\`

### 1. 5s 等待 = BDBC_TC_LINK_KEY_EXCHANGE_TIMEOUT (bdb.h:45)

> `#define BDBC_TC_LINK_KEY_EXCHANGE_TIMEOUT (5) // the maximum time in seconds a joining node will wait for a response when sending an APS request key to the Trust Center`

### 2. 重试上限 3 次 (bdb.h:44 + bdb.c:973)

- `BDBC_REC_SAME_NETWROK_RETRY_ATTEMPTS 3`
- `bdb_retrieveTcLinkKeyStart`: `g_bdbAttrs.tcLinkKeyExchangeAttemptsMax = 3;` (APSRK 方法)

### 3. 重试与离网状态机 (bdb.c:921-946)

```c
bdb_retrieveTcLinkKeyTimeout:
  if (attempts++ < max) {
      zb_zdoNodeDescReq(0x0000, ...);   // 重试: 先发 ZDO Node Desc Req
      return 0;                          // 再等 5s
  } else {
      /* leave the network */
      req.rejoin = 0;                    // ← 与抓包 Leave(rj=0) 完全一致
      req.removeChildren = 0;
      zb_nlmeLeaveReq(&req);
      return 3 * 1000;                   // 离网后再等 3s
  }
```

### 4. 完整设备侧流程 (bdb.c:961-983)

1. 入网后 `bdb_retrieveTcLinkKeyStart` → 发 ZDO Node Desc Req 给 0x0000
2. `bdb_nodeDescRespHandler` (bdb.c:896-910): Node Desc Resp 的 stackRev ≥ 21 →
   发 APS RequestKey (keyType=TCLK) 给 0x0000; 启动 5s 定时器
3. 若交换未完成 → 每 5s 重试 (Node Desc Req → RequestKey), 上限 3 次
4. 耗尽 → `nlme_leave_req(rejoin=0)` → 设备广播 Leave 并离网

### 5. 完成条件 (关键)

- `bdb_retrieveTcLinkKeyDone(SUCCESS)` 会 `bdb_retrieveTcLinkKeyTimerStop()`
- 源码中只有 Node Desc Resp 非 r21 路径直接调 SUCCESS; 正常 r21 路径的成功
  必须由 APS/安全层在处理完密钥交换 (含 ConfirmKey) 后触发
- 失败路径: `aps_authenticated=0; BDB_STATUS_SET(TCLK_EX_FAILURE); nodeIsOnANetwork=0`

### 6. 抓包 ↔ 源码对账 (wire evidence)

| 观察 (838D/CE77/1CC4) | SDK 源码 |
|---|---|
| RequestKey 每 ~5s 重试 (+6.5/+11.5/+16.5) | BDBC_TC_LINK_KEY_EXCHANGE_TIMEOUT = 5s |
| 重试前先发 ZDP Node Desc Req (1CC4: +12.21s NodeDesc → +12.22s RequestKey) | bdb_retrieveTcLinkKeyTimeout 先发 Node Desc Req |
| 重试 3 轮后离网 | attemptsMax = 3 |
| Leave(rj=0) 广播 | nlme_leave_req req.rejoin = 0 |
| 离网 ≈ 首请求 +15~18s (总 ~21.2s) | 3×5s + 3s + 首请求偏移 |

### 7. 因果链修正后的证据分级

- ✅ **源码实证**: 设备在 TC Link Key 交换未完成时, 5s×3 重试后主动离网 (rejoin=0)
- ✅ **源码+抓包实证**: 网关 ConfirmKey 状态=SUCCESS 且多次发送, 但设备从未完成交换
- ⚠️ **仍待证明**: 设备为何未完成 (未处理 ConfirmKey?) — 需要设备侧日志
  (bdbcommissioningCb 若回调 TCLK_EX_FAILURE 即一锤定音)
- ⚠️ **仍待证明**: 洪峰是否为未处理的原因 — 实验 A (网关延迟读属性) / 设备日志
