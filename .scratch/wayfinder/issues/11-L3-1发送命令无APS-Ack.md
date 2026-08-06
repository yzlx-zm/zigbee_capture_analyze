# 11 — L3-1 发送命令无 APS Ack（应用层确认缺失）

**Assignee:** Claude (2026-08-06) — 认领

**What to build:** 场景拆解文档 (ADR-0002 14 层) + 检测器 R1-R4 (无确认/重发高置信/交叉归因/方向) + 前端卡片。
前置已就绪: APS Ack 配对能力 (cc99542 + 60de1ff, counter 精确匹配 + 5s 时间窗)。

**Blocked by:** None (APS 配对已提交)

**Status:** ready-for-agent

**Type:** task | **AFK**

**背景**: 55 场景中 L3-1 ⬜ 未拆解; OVERVIEW 描述 "发送命令无 APS Ack | APS counter/ack 匹配"。
MCP 核对 (2026-08-06): APS 重传 3 次尝试/50ms×hops/1600ms 每次 (EmberZNet 3.1+ 可配);
SED 目标 +7680ms 间接超时; 失败上报 EMBER_DELIVERY_FAILED (0x66); NWK 重试窗口英文版 250ms/中文版 500ms 版本差异;
应用层重传可叠加 (社区案例 23 条 → 重传次数不做硬阈值)。
素材实测无 ack 样本: 第七次 47/103, G32 142/1148 (0000→EE48 Door Lock ×48), 中继 78/290 (0000→838D Door Lock ×34, 与 L3-5 交叉)。

**验证标准**: 中继素材 838D 无 ack ×34 + 0x0B ×39 交叉双报; G32 EE48 无 ack + 0x06 交叉; 第七次 C1F5 无 ack 命中; L3-5/L1-3 回归不变。
