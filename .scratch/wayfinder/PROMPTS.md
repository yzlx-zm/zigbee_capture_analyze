# Wayfinder 会话提示词集 — 场景工程 & UI 工程

> 2026-08-04 | 用途: 新开 cmd 会话 (claude code) 时的启动提示词模板
> 前置: 项目已配置 wayfinder 协作 (CLAUDE.md 引导 + .scratch/wayfinder/ 地图)

---

## 一、场景工程 (Zigbee 场景检测体系) 提示词

### ① 通用模板(自动读地图,挑下一个可做的)

```text
项目: D:\ai_agent\zigbee_capture_analyze

按 wayfinder 协作流程开工:
1. 读 CLAUDE.md 了解项目协作约定
2. 读 .scratch/wayfinder/README.md 了解会话流程
3. 读 .scratch/wayfinder/map.md 了解进度地图 (Decisions so far / 迷雾)
4. 列出 .scratch/wayfinder/issues/ 下所有 ticket, 挑一个未认领、未被阻塞的
5. 在 ticket 文件顶部加 Assignee 标记认领
6. 向我确认后再开始解决 (一次只做这一个 ticket)
7. 完成后: ticket 写 Resolution → 更新 map.md → git commit + push
```

### ② 指定 ticket 模板(你已决定做什么)

```text
项目: D:\ai_agent\zigbee_capture_analyze

按 wayfinder 协作流程, 认领并解决 ticket:
.scratch/wayfinder/issues/05-L1-4TC拒绝.md

先读 CLAUDE.md + wayfinder README + map.md 了解上下文,
认领后向我确认理解, 再开始。
完成后更新 ticket Resolution + map.md + git 提交推送。
```

### ③ 调研/验证类(不写代码,先对齐)

```text
项目: D:\ai_agent\zigbee_capture_analyze

只做调研和方案对齐, 不写代码:
读 .scratch/wayfinder/map.md 和 issues/01-L2场景拆解.md,
用 grilling 方式和我对齐 L2 场景拆解的需求和判定规则,
产出方案给我确认后再决定是否实现。
```

---

## 二、UI 工程提示词

### ① UI 工程通用模板(读全景,挑一个 UI ticket)

```text
项目: D:\ai_agent\zigbee_capture_analyze

按 wayfinder 协作流程开工, 本次专注 UI 工程模块:
1. 读 CLAUDE.md 了解项目协作约定 (含 wayfinder 流程)
2. 读 .scratch/wayfinder/README.md + map.md (进度地图, 看 UI 工程模块章节)
3. 读 docs/ui_overview.md (UI 工程全景: 8 模块/横切/拆分维度)
4. 列出 .scratch/wayfinder/issues/ 下 U 开头且未认领的 ticket
   (U1 视觉设计系统 / U3 节点页补齐 / U4 页面联动 / U5 时间线优化 / U6 导入页优化 / U7 拓扑页优化)
5. 挑一个未认领、未被阻塞的, 在文件顶部加 Assignee 标记认领
6. 先向我确认理解和范围, 再开始 (一次只做一个)
7. 完成后: ticket 写 Resolution → 更新 map.md → git commit + push
```

### ② 指定 UI ticket 模板

```text
项目: D:\ai_agent\zigbee_capture_analyze

按 wayfinder 协作流程, 认领并解决 UI ticket:
.scratch/wayfinder/issues/U1-视觉设计系统.md

先读 CLAUDE.md + wayfinder README + map.md + docs/ui_overview.md,
认领后向我确认设计方向 (配色/间距/组件类规范), 再实施。
完成后更新 ticket Resolution + map.md + git 提交推送。
```

### ③ UI 验收/审查类(不改代码,先看现状)

```text
项目: D:\ai_agent\zigbee_capture_analyze

只做 UI 审查, 不写代码:
读 docs/ui_overview.md 和前端代码 (frontend/js/*.js, index.html),
逐页面审查: 功能完整性 / 样式一致性 / undefined 或错位问题 / 与后端字段对齐情况,
产出 UI 问题清单给我, 我再决定怎么拆 tickets 处理。
```

---

## 三、解析器工程 (抓包数据处理与 Python 解析层) 提示词

### ① 解析器工程通用模板

```text
项目: D:\ai_agent\zigbee_capture_analyze

按 wayfinder 协作流程开工, 本次专注解析器工程模块:
1. 读 CLAUDE.md + .scratch/wayfinder/README.md + map.md (看解析器工程章节)
2. 读 docs/parser_overview.md (解析器工程全景: 7 模块/已知问题/上下游)
3. 列出 .scratch/wayfinder/issues/ 下 P 开头且未认领的 ticket
   (P1 双路径字段契约对齐 / P2 素材回归测试 / P3 大包性能 / P4 解密覆盖 / P5 字段缺口工单流)
4. 挑一个未认领的, 加 Assignee 认领, 向我确认后开始 (一次一个)
5. 完成后: ticket Resolution → map.md → git commit + push
```

### ② 指定解析器 ticket 模板

```text
项目: D:\ai_agent\zigbee_capture_analyze

按 wayfinder 协作流程, 认领并解决解析器 ticket:
.scratch/wayfinder/issues/P2-素材回归测试体系.md

先读 CLAUDE.md + wayfinder README + map.md + docs/parser_overview.md,
认领后向我确认方案, 再实施。完成后更新 ticket + map.md + git 提交推送。
```

---

## 四、使用说明

### Ticket 编号对照

| 编号 | Ticket | 模块 |
|------|--------|------|
| 00 | 场景体系全景调研 | ✅ 已完成 (OVERVIEW.md) |
| 01 | L2 场景拆解 | 场景工程 |
| 02 / U2 | 拓扑时间控制 | UI 工程 (plan 已就绪) |
| 03 | L1-3 故障素材验证 | 场景工程 (等素材) |
| 04 | 1885 链路复测 | 现场 (等复测) |
| 05 | L1-4 TC 拒绝 | 场景工程 (进行中) |
| 06 | UI 对齐优化 | UI 工程 (切片已完成: L1 卡片统一) |
| U1 | 视觉设计系统 | UI 工程 |
| U3 | 节点页补齐 | UI 工程 |
| U4 | 页面联动 | UI 工程 |
| U5 | 时间线优化 | UI 工程 |
| U6 | 导入页优化 | UI 工程 |
| U7 | 拓扑页优化 | UI 工程 |

### 认领纪律

- **一次会话只解一个 ticket**(research 型可并行)
- 认领 = 在 ticket 文件顶部加 `**Assignee:** <会话标识> + 日期`
- 完成 = ticket 写 `## Resolution` + map.md Decisions so far 更新 + git 提交推送

### 共同上下文(每个会话必读)

| 文档 | 用途 |
|------|------|
| `CLAUDE.md` | 协作约定 + wayfinder 引导 |
| `.scratch/wayfinder/README.md` | 会话流程 |
| `.scratch/wayfinder/map.md` | 进度地图 (Decisions/迷雾/范围) |
| `memory/zigbee_l1_scenario_engine.md` | 场景检测引擎记忆 (用户记忆目录) |
| `CONTEXT.md` | 领域词汇表 |
| `docs/scenarios/OVERVIEW.md` | 55 场景验证状态总表 (场景工程) |
| `docs/ui_overview.md` + `docs/ui_pages.md` | UI 工程全景 + 窗口职责 (UI 工程) |

### 素材与工具

- 素材: `C:\Users\Administrator\Desktop\zigbee_capture\`(验证可用-记录 = 已验证素材)
- 台账: `.scratch/verification/capture_materials.md`
- 后端: `python -m backend --port 8720`(改代码需重启)
- Git 代理: 127.0.0.1:7897 已配

---

## 五、总控进度窗口 (多会话统筹) 提示词

### ① 总控窗口模板 (日常进度管理)

```text
项目: D:\ai_agent\zigbee_capture_analyze

你是 wayfinder 协作的【总控/进度控制窗口】, 职责是统筹多会话进度, 不实现具体 ticket:

1. 读 CLAUDE.md + .scratch/wayfinder/README.md + map.md
2. 扫描 .scratch/wayfinder/issues/ 所有 ticket, 生成进度总览:
   - 三大工程 (场景/UI/解析器) 各自 ticket 状态表:
     未认领 / in-progress (Assignee+日期) / blocked / done
3. 冲突检测: 检查各 in-progress ticket 的代码文件是否有重叠
   (git log 最近提交 + ticket 描述的改动范围)
4. 阻塞跟踪: 列出被阻塞 ticket 及解除条件 (等素材/等现场/等前置)
5. 向用户汇报: 当前可并行窗口数建议 / 下一步可认领 ticket 优先级
6. 不做: 不认领 ticket、不写实现代码 — 只做统筹和汇报
```

### ② 总控窗口专用指令 (按需询问)

```text
项目: D:\ai_agent\zigbee_capture_analyze

你是总控窗口。执行:
1. 汇总当前所有 ticket 状态 (含 Assignee), 输出状态表
2. 检查是否有多个 in-progress ticket 修改同一文件 (冲突风险)
3. 给出: 现在开第 N 个新窗口最合适的 ticket 是哪个? 为什么?
4. 若有 blocked ticket, 说明阻塞原因和解除条件
只读分析, 不写代码不改文件。
```

---

## 六、使用说明
