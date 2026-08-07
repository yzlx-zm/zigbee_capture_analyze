# 11 — L3-1 发送命令无 APS Ack（应用层确认缺失）

**Assignee:** Claude (2026-08-06) — 认领

**What to build:** 场景拆解文档 (ADR-0002 14 层) + 检测器 R1-R4 (无确认/重发高置信/交叉归因/方向) + 前端卡片。
前置已就绪: APS Ack 配对能力 (cc99542 + 60de1ff, counter 精确匹配 + 5s 时间窗)。

**Blocked by:** None (APS 配对已提交)

**Status:** ✅ 完成 (2026-08-06, 提交 6c1b517)

**Type:** task | **AFK**

**背景**: 55 场景中 L3-1 ⬜ 未拆解; OVERVIEW 描述 "发送命令无 APS Ack | APS counter/ack 匹配"。
MCP 核对 (2026-08-06): APS 重传 3 次尝试/50ms×hops/1600ms 每次 (EmberZNet 3.1+ 可配);
SED 目标 +7680ms 间接超时; 失败上报 EMBER_DELIVERY_FAILED (0x66); NWK 重试窗口英文版 250ms/中文版 500ms 版本差异;
应用层重传可叠加 (社区案例 23 条 → 重传次数不做硬阈值)。
素材实测无 ack 样本: 第七次 47/103, G32 142/1148 (0000→EE48 Door Lock ×48), 中继 78/290 (0000→838D Door Lock ×34, 与 L3-5 交叉)。

**验证标准**: 中继素材 838D 无 ack ×34 + 0x0B ×39 交叉双报; G32 EE48 无 ack + 0x06 交叉; 第七次 C1F5 无 ack 命中; L3-5/L1-3 回归不变。

## Resolution (2026-08-06, 提交 6c1b517)

**完成**: 文档 v1.0 (14 层) + 检测器 R1-R4 + 前端卡片 + OVERVIEW 状态更新。

**素材实证**:
- 中继入网: **838D 下行 ×42 R2 高置信 + L3-5 交叉 (0x0B ×39)** — 核心交叉验证
- G32: **BE5A 上行 ×45 R2 高 + 0x0C ×1043 交叉** (0x0C 加入交叉信号后); EFC2 下行 ×2 + 0x06 交叉
- 第七次: C1F5 下行 ×32 R2 高 (去重复捕获后重发 9); CE77 上行 ×2 R1 中
- L3-5 (0x0B×39)/L1-3 (B2-LOOP) 回归不变

**实现要点**:
- 配对逻辑抽共享模块 backend/aps_pairing.py (详情端点 + 检测器共用)
- 事务级无 ack 判定 (重传帧同 counter 算一事务, 修正初版按帧误判)
- 重复捕获去重 (同 counter+mac_seq) — C1F5 32 帧实为 9 个唯一帧
- 重传次数不做硬阈值 (应用层可叠加, 社区案例 23 条) — 只做严重度
- 交叉信号含 0x0B+0x0C (L3-5) / 0x06 (L6-S3) / Leave (离线)

**待办**: pcap 路径 ack_req 提取 (P5) → L3-1 pcap 支持; 判定参数真实样本校准 (第 14 层)。

## Resolution 追加 (2026-08-07, L3-1 判定修正窗口)

**用户报告**: 诊断页 L3-1 判定结果/计数不对 — 帧 224 (0→17266 Basic Write Attributes, ack_req=1) 被判"无 APS Ack", 但设备 19ms 后回 Write Attributes Response (同 tsn=33) — 命令送达+处理。

**根因 (判定口径错误)**: "无独立 ack 帧" ≠ "命令未送达"。素材实证: 部分设备固件 (含中继 17266/96A8 等) 收到 ack_req=1 命令后**不回独立 ack 帧, 以 ZCL 应用层响应确认** — Silicon Labs 官方 sl_zigbee_send_reply: "The reply will be included with the ACK that the stack automatically sends back" / "Replies are a nonstandard extension to Zigbee"。同素材设备行为不一致 (CE77 收 17 回 17 独立 ack), 不按设备类型硬编码。ack 配对本身无系统性 bug (62 ack 中 59 配对, 3 个无候选原帧 = 漏抓/非标)。

**修复 (提交 8xxxxxx)**: l3.py detect_l3_1 — no_ack 候选增加应用层响应排除 (2s 窗口反向数据帧: ① 同 ZCL tsn 铁证 ② 同 cluster ③ cluster 缺失降级); 新增 `app_ack_absent_total` 字段 (无 ack 但有响应, 非故障); 文档 L3-1.md v1.1。

**回归 (全通过)**: L3-5 中继 0x0B×39 不变 / G32 0x0C×216 不变 (台账口径; map 的 1043 为错记, 无素材支持, 已修正); L1-3 B2-LOOP (838D) 不变; 前端字段兼容 (无改动)。

**素材基线回填 (检测器实测)**: 中继 838D 下行 ×42→×34 (-8 响应确认); G32 BE5A 上行 ×45→×36 (-9); 第七次 48→37 候选, 设备级仅 C1F5 ×32 (17266/96A8/CE77 全排除)。

**待素材/边界 (诚实标注)**: G32 EFC2 ×2 保留 — 反向帧未解密无法字段级关联 (保守不排除); SED 响应可能 >2s (poll 周期), 2s 窗口边界情况保留计数。
