# L1-3 素材验证笔记 — 中继入网抓包(1).cubx

> 2026-08-03 | 状态: ✅ 帧级分析完成 (真实故障素材) | 根因归因: ⏳ 待设备固件信息
> 素材: `C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包(1).cubx` (5912 帧, PANID 0x580C)
> 设备构成 (用户确认): **网关(协调器)=自家** / **中继 1885=外购** / **设备 838D=自家** (EUI `a4c1384c5e634768`, Telink OUI)

## 问题描述 (用户观测)

设备 838D 经中继 1885 多跳入网后, **"入网后立即被踢出去了"**。

## 帧级时间线 (838D, t0=抓包起点, 帧号=cubx Packets.Id 可在 Ubiqua 核对)

```
t+ 57.506s  #4973  AssocResp [addr=0x838D status=0x00] (来自 70b3d52b600bdbbe)
t+ 58.016s  #4994  TransportKey key_type=0x01 (TC→838D, 经中继 1885)
t+ 58.027s  #4996  Device Announce ×6 (#4996/5001/5002/5003/5049/5100)
t+ 60.029s  #5155  RequestKey ×4 (#5155/5157/5160/5162, 838D→TC)
t+ 60.068s  #5164  TransportKey key_type=0x04 TCLK (TC→838D)
t+ 61.028s  #5259  VerifyKey ×3 (#5259/5261/5263, 838D→TC)
t+ 61.067s  #5269  Confirm ×2 (#5269/5270, TC→838D)
t+ 62.630s  #5362  VerifyKey ×4 (#5362/5368/5370/5372)   ← Confirm 后仍重发!
t+ 62.684s  #5378  Confirm
t+ 64.630s  #5565  VerifyKey ×2 (#5565/5582)
t+ 64.762s  #5609  Confirm ×5 (#5609-5631)
t+ 67.030s  #5822  RequestKey ×2 (#5822/5826)            ← 回退重新请求
t+ 70.296s  #6010  RequestKey ×3 (#6010/6016/6018)
t+ 74.532s  #6275  RequestKey ×2 (#6275/6283)
t+ 79.228s  #6929  NWK Leave (838D→广播)                  ← 设备主动离网 (~21.7s 后)
```

**关键异常窗口**: t+61.07s 收到 Confirm 后, 设备在 t+62.63s 又发 VerifyKey — **验证未收敛**, 随后多轮重试, 最终主动 Leave。

## 密钥明文对比 (决定性证据, 2026-08-03 二次修正 — 诚实版)

**⚠️ 两次修正说明**:
- 第一次修正: "VerifyKey key≠TCLK" 不是 838D 异常 (所有设备都 ≠)。
- **第二次修正 (重要)**: 
  ① **CE93 与 F67F 是同一台物理设备** (真实 EUI 均为 `a4c1389becfd06ab`) — F67F 入网 → Leave → 以 CE93 短地址再次入网。之前"多设备对比"实际只有 3 台: 838D / 8A41 / 设备A(CE93=F67F)。
  ② **VerifyKey 明文 + 26B 短格式是全网络正常行为** (含健康素材 0x2951) — "838D VerifyKey 明文异常"结论**错误**。
  ③ **TransportKey.dst 与真实 EUI 差 1 字节不导致失败** (CE93/F67F 差 1 字节但验证成功; 838D 完全一致反而失败)。

**全设备对比 (解密后明文, 二次修正)**:

| 设备 | 真实EUI | TK.dst (TC视角) | dst一致? | TCLK | VerifyKey 16B | 结果 |
|------|---------|-----------------|---------|------|---------------|------|
| 838D | a4c1384c5e634768 | a4c1384c5e634768 | ✓ | f362b92a... | bab24513c21a9973746e59f8902e7796 | **未收敛→Leave** |
| 8A41 | a4c13832e19d035d | a4c13832e19d035d | ✓ | 6cd6b978... | (无VerifyKey) | 正常 |
| CE93=F67F | a4c1389becfd06ab | a4c138**b9**ecfd06ab | ✗差1字节 | 538d9eda...(两次相同) | 2441948a... (两次相同) | 正常 |

**结构规律 (全网络一致)**:
- TransportKey(TCLK) = `[05][04][TCLK 16B][dst 8B][src 8B]` 34B — **标准格式**
- VerifyKey = `[0f][04][8B][16B]` 26B 明文 — 前 8B **回显 TK.dst 字段**
- Confirm = `[10][00][04][8B]` 11B 明文 — 同样回显
- VerifyKey 16B: **设备绑定** (同一设备两次入网相同; 838D 不同) — 16B ≠ TCLK (所有设备都 ≠)
- CE93 的 dst 差 1 字节 (9b→b9, 疑似 nibble 交换) — 疑 TC 侧 EUI 记录处理痕迹, 但**不影响验证**

**帧级确定的事实 (仅此而已)**:
1. 838D 前半段入网正常 (Assoc→NWK Key→announce→ReqKey→TCLK)
2. 838D 在 TC 回 Confirm 后**仍重发 VerifyKey/ReqKey ×7** (t+62.6 ~ t+74.5)
3. 838D 最终**主动 Leave** (t+79.2, #6929)
4. **"谁不认谁" (TC 不认 838D 的 16B, 还是 838D 不认 TC 的 Confirm) 帧级无法确定** — 不妄自揣测

## 🔑 协议语义破解 (2026-08-03 决定性成果)

**VerifyKey 16B = keyed_hash(TCLK, selector=3)** — 三台设备全部验证匹配:

| 设备 | TC 发的 TCLK | keyed_hash(TCLK,3) 计算 | 实际 16B | 一致 |
|------|-------------|------------------------|---------|------|
| 838D | f362b92ae1397acaf78d8949aa6ed446 | bab24513c21a9973746e59f8902e7796 | 同左 | ✓ |
| 设备A | 538d9eda29348a518bcecfaab3aee18c | 2441948a885eef532b044128c0b16538 | 同左 | ✓ |
| 健康0x2951 | fc4c5083e43dd60ba4f3dd7e5bb651bf | cc2cc74d5508c7164cf76af12f78c1df | 同左 | ✓ |

**完整命令格式 (该网络, 明文)**:
- TransportKey(TCLK): `[05][04][TCLK 16B][dst 8B][src 8B]` 34B — 标准
- VerifyKey: `[0f][04][dst 回显 8B][keyed_hash(TCLK,3) 16B]` 26B 明文
- Confirm: `[10][00][04][dst 8B]` 11B 明文 (内容恒定, 所有设备一致)

**NWK Key (用户提供并确认)**: 故障网络 = `c91b384e572a97c8b07a3ae3dbcbdbfd` (从 k1 明文解出, 完全一致)。
健康网络 = `0731fe01c8d9fef2a9bd3a3c6b95b80d`。每网络一把, 与 16B 无关。

## 🔴 根因确认 (2026-08-03 用户人工复核 + 芯科官方文档)

**真正根因 = Confirm 经中继 1885 转发失败 (Source Route Failure), 属 L3 路由/链路层 — 不是密钥协议问题!**

用户 Ubiqua 复核发现: 5259 (VerifyKey) 中继正常转发, 5269/5270 (网关 Confirm) 中继 1885 接收成功,
但转发给 838D 时失败 — **帧 5272: Network Status [0x03] code=[0x0B] Source Route Failure target=0x838D**!

**素材全貌 (脚本验证)**:
- **39 个 Network Status 全部 1885→0000, target 全部 0x838D**
- **每轮 Confirm 后都有 route error**: #5269→3个 (#5272/5274/5276), #5378→7个, #5609-5631→6个 — 没有一轮成功送达
- 838D 是 **SED** (80 次 Data Request 轮询), 轮询拿不到 Confirm
- 非对称: 上行 (838D→1885→网关 VerifyKey) 通, 下行 (网关→1885→838D Confirm) 断

**官方依据 (芯科 message.h / stack-info.h)**:
- 0x0B = SL_ZIGBEE_ROUTE_ERROR_SOURCE_ROUTE_FAILURE
- concentrator (网关) 用 MTO 收 + 源路由发; broken link 前一节点 (1885) 生成 route error 沿 MTO 回报
- "three route error messages in succession" = APS retry 3 次的官方预期 (#5272/5274/5276 精确匹配)

**完整根因链**:
```
838D 入网 → TCLK 分发成功 → VerifyKey 内容正确 (keyed_hash(TCLK,3))
→ 网关回 Confirm SUCCESS ×8
→ 1885 转发 Confirm 给 838D 全部失败 (Source Route Failure ×39) ← 根因!
→ 838D 收不到确认 → 重发 VerifyKey ×3 轮 (同样失败)
→ 838D 改发 RequestKey ×7 → 网关安全策略拒绝
→ 838D 放弃 → Leave (#6929)
```

**检测器修正**: B2-LOOP 判定新增 Network Status (0x0B) 检查 — 伴随路由错误 → 根因标注 L3
(不是密钥内容问题)。cubx_reader 新增 nwk_status_code/nwk_status_target 解析。

## 帧级结论 (最终修正版)

1. 838D VerifyKey 内容 100% 正确 (keyed_hash 匹配)
2. 网关 Confirm 8 次全部 SUCCESS
3. **Confirm 全部在 1885→838D 转发环节丢失 (Source Route Failure)**
4. 838D 因此重发 → 被拒 → Leave

## 待定 (次要点)

- 1885→838D 链路为何断? (中继 child 表 / 非对称链路 / 射频) — 需现场/设备侧确认
- F67F (设备A第一次入网) t+38.2 Leave 的原因 (与 838D 不同场景, 待查)

## 素材价值

真实故障素材 ✅ | 验证了检测器能识别"验证循环 + 主动 Leave"模式 ✅ | 规则 B2 需扩展循环型变体
