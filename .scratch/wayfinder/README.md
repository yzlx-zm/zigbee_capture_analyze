# Wayfinder 使用说明 (cmd 会话)

> 本目录 = zigbee_capture_analyze 工程的 wayfinder 地图 (拆分大工程, 一次会话一个 ticket)

## 每个 cmd 会话的流程

1. **读地图**: `.scratch/wayfinder/map.md` — 看 Destination / Decisions so far / Not yet specified
2. **选 ticket**: `issues/` 下未被认领的 (无 Assignee 标记)、未被阻塞的 (Blocked by 全完成)
3. **认领**: 在 ticket 文件顶部加 `**Assignee:** <会话标识>` + 日期
4. **解决**: 按 ticket 的 "What to build" 和验收条件执行 (调用的 skill 见 map 的 Notes)
5. **记录**: ticket 文件底部加 "## Resolution" 区段 (答案/结论/产出)
6. **更新地图**: map.md 的 Decisions so far 加一行 (链接 ticket), 迷雾区更新
7. **提交**: git commit + push (代理 127.0.0.1:7897 已配)

## 铁律 (2026-08-04 用户要求强化, 强制执行)

1. **一次会话只解一个 ticket** (research 型可并行)
2. **诚实**: 产出如实标注状态 (已验证/待素材/推断); 不夸大、不把"没解析"当"抓不到"、不把推断当事实; 发现错误必须修正并留记录
3. **严谨**: 技术断言必须有依据 (官方文档/SDK 源码/素材实证/协议级字段), 禁止靠记忆下结论; 帧识别必须协议级 (ADR-0002 v1.1)
4. **不妄加判断**: 不妄自揣测, 不懂问用户 (grilling 默认); 未知的标"未知", 不可判定的标"不可判定"
5. **有问题直接向开发人员汇报**: 遇阻塞/不确定/发现矛盾/外部依赖失败 → 停下来汇报, 不绕行、不自圆其说
6. **判定规则成立即可**: 计数允许素材差异浮动
- 会话前必读: `memory/zigbee_l1_scenario_engine.md` + `CONTEXT.md` + `.scratch/verification/capture_materials.md`
- 素材: `C:\Users\Administrator\Desktop\zigbee_capture\` (验证可用-记录 = 已验证素材)

## Ticket 状态约定

- 未开始: 无 Assignee
- 进行中: 有 Assignee + 日期
- 完成: 有 Resolution 区段 + map.md Decisions so far 已更新 + 已提交
