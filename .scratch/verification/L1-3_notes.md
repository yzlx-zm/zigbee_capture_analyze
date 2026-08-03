# L1-3 素材验证笔记 — 中继入网抓包(1).cubx

> 2026-08-03 | 状态: ✅ 帧级分析完成 (真实故障素材) | 根因归因: ⏳ 待设备固件信息
> 素材: `C:\Users\Administrator\Desktop\zigbee_capture\中继入网抓包(1).cubx` (5912 帧, PANID 0x580C)
> 设备构成 (用户确认): **网关(协调器)=自家** / **中继 1885=外购** / **设备 838D=自家** (EUI `a4c1384c5e634768`, Telink OUI)

## 问题描述 (用户观测)

设备 838D 经中继 1885 多跳入网后, **"入网后立即被踢出去了"**。

## 帧级时间线 (838D, t0=抓包起点)

```
t+57.5  Assoc成功 (AssocResp 0x838D/0x00, 来自中继 70b3d52b600bdbbe)
t+58.0  0x1885→838D TransKey (0x05, key_type=0x01 NWK)   ← TC 经中继 1885 分发 NWK Key (多跳)
t+58.0  838D announce ×6
t+60.0  838D→0000 ReqKey (0x08, key_type=0x04) ×4        ← 请求 TC Link Key
t+60.1  0000→838D TransKey (0x05, key_type=0x04 TCLK)     ← TCLK 分发 (标准 34B 明文可见)
t+61.0  838D→0000 VerifyKey (0x0F) ×3                     ← 验证 (明文!)
t+61.1  0000→838D Confirm (0x10) ×2                       ← TC 确认
t+62.6  VerifyKey ×4 (Confirm 后仍重发!)                  ← 异常: 验证未收敛
t+64.6  VerifyKey ×2 → Confirm ×5
t+67.0  ReqKey ×2 (重新请求 key)                          ← 异常: 回退重新请求
t+70.3  ReqKey ×3
t+74.5  ReqKey ×2
t+79.2  838D→广播 Leave                                    ← 设备主动离网 (非 TC 踢)
```

## 密钥明文对比 (决定性证据)

| 项 | 值 | 结论 |
|----|----|------|
| TC 分发的 TCLK | `f362b92ae1397acaf78d8949aa6ed446` | 标准 34B TransKey 明文可读 |
| 838D VerifyKey 携带 key | `6847635e4c38c1a4bab24513c21a9973` 或 `bab24513c21a9973746e59f8902e7796` (格式待定) | **≠ TCLK** |
| VerifyKey 加密状态 | **明文** (无 APS security header) | 健康素材 0x2951 的 VerifyKey 是**加密**的 |
| TC Confirm | `10 00 04 [838D-EUI]` 11 字节, 内容恒定 | 非标准 34B 格式 |

对照 (健康素材 1-标准入网抓包-2): VerifyKey 加密 (TCLK 解出), Confirm 标准。

## 帧级结论 (不依赖根因归因)

1. **入网流程前半段正常**: Assoc → NWK Key → announce → ReqKey → TCLK 全部成功
2. **Verify 环节无法收敛**: VerifyKey 携带 key ≠ TC 分发的 TCLK;设备在 Confirm 后仍反复重发 VerifyKey, 后回退 ReqKey 重新请求
3. **~22 秒后设备主动 Leave** (src=838D 广播 Leave, 符合官方 "Key verification failed → emberLeaveNetwork" 帧级表现)
4. **判定**: L1-3 规则 B2 **"验证循环型"变体** — TCLK 出现 + Verify/ReqKey 反复 + 设备 Leave
   (严格 B2 是 Confirm 缺失;本素材 Confirm 出现但验证不收敛 — 规则需扩展)

## 待定 (需设备固件/日志信息)

- 838D 为什么 VerifyKey 明文? (同是自家 Telink 设备, 健康素材 0x2951 是加密的 → 固件版本/配置差异?)
- VerifyKey 携带 key ≠ TCLK 的语义? (设备收到的 TCLK 解密错误? 或 VerifyKey 格式/字段解析不同?)
- 网关 Confirm 11B 短格式的语义? (自家网关实现? 非标准?)
- 设备侧日志: `Key verification failed` / `NO_LINK_KEY_RECEIVED` 确认

## 素材价值

真实故障素材 ✅ | 验证了检测器能识别"验证循环 + 主动 Leave"模式 ✅ | 规则 B2 需扩展循环型变体
