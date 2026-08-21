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

### ④ Q&A 对齐后实现窗口 (总控窗口已对齐需求+素材实证+实现要点, 照 ticket 干)

> 2026-08-12 起 (U9 先例): 总控窗口先做"你问我答"需求对齐 + 素材实证 + 实现方案评审,
> 全部结论固化进 ticket (含实现要点/验证标准/风险), 实现窗口只按 ticket 执行。

```text
项目: D:\ai_agent\zigbee_capture_analyze

你是 U9 实现窗口。任务: 节点页精简重构 + 设备信息/控制方式提取。

## 开工前必读 (按序)
1. .scratch/wayfinder/README.md + .scratch/wayfinder/map.md (流程 + 现状)
2. **.scratch/wayfinder/issues/U9-节点页重构与设备信息提取.md** (核心: 需求决策 + 素材实证 + 完整实现要点都已写入, 按它实施, 勿自行改需求)
3. memory/zigbee_l1_scenario_engine.md (场景知识)

## 工作流
1. 读 U9 ticket, 按"实现要点"逐项实施 (解析层 cubx_reader → 契约 tshark 占位 → 聚合 /api/nodes → 前端 nodes.js + app.js 版本参数 → 回归脚本更新)
2. 每完成一层立即验证 (ticket "验证标准" 给了命令和数据对账期望值)
3. 回归按序跑: test_p1_contract → compare_paths → zcl_fcf_regression → tests/test_parser_verify → p2_regression --update → p2_regression
4. CDP 前端验证 (Edge 9222 已有, 更新 u3-nodes/cdp_test.mjs 后跑)
5. 收尾 (铁律 7): ticket 补 Resolution + map.md 加条目 + git commit + push (代理 127.0.0.1:7897)

## 铁律
- 一次会话只解 U9 这一个 ticket; 诚实标注状态 (控制命令统计的真实控制素材等用户提供, 交付时标"待素材")
- 技术断言要有依据 (协议字段级); 遇阻塞/不确定停下来汇报, 不绕行
- 后端: python -m backend --port 8720 (代码改动需重启; 当前已有实例在跑, 可让用户重启或自己管理)
- 素材: C:\Users\Administrator\Desktop\zigbee_capture\设备控制分析-训练素材\ (dimmer 入网包可验证, 控制操作素材等用户另提供)
```

### ⑤ grilling 对齐后实现窗口 (总控窗口 grilling 对齐 + 实测根因, 照 ticket 干)

> 2026-08-13 起 (U11 先例): 总控窗口 grilling 结构化对齐 (一次一问+推荐答案) +
> 后台实测根因 (基准测试+代码级定位), 全部固化进 ticket, 实现窗口照 ticket 执行。

```text
项目: D:\ai_agent\zigbee_capture_analyze

你是 U11 实现窗口。任务: 大 cubx 时间窗拆分导入一体流程 (预扫→选窗→拆小文件→自动导入)。

## 开工前必读 (按序)
1. .scratch/wayfinder/README.md + .scratch/wayfinder/map.md (流程 + 现状)
2. **.scratch/wayfinder/issues/U11-大包时间窗拆分导入.md** (核心: grilling 对齐决策 +
   实测根因 + cubx schema 实证 + 完整实现要点, 按它实施, 勿自行改需求)
3. memory/zigbee_l1_scenario_engine.md (场景知识)

## 工作流
1. 读 U11 ticket, 按"实现要点"逐项实施 (backend/cubx_splitter.py 预扫+拆分 →
   API prescan/split → 前端 import.js 预扫面板+双滑块 → cubx_reader 并行分支
   进度上报修复)
2. 每完成一层立即验证 (ticket "验证标准" 给了数据对账期望值)
3. 回归按序跑: P1 契约 → zcl_fcf → tests/test_parser_verify → p2_regression
   (parse 逻辑未动, 预期不变; 若变先停下汇报)
4. 端到端验证: 85MB 包 选文件→预扫面板→选窗→拆分→自动导入→诊断页可用
   (进度条全程推进不静止 — 并行分支修复后回归确认)
5. 收尾 (铁律 7): ticket 补 Resolution + map.md 加条目 + git commit + push

## 铁律
- 一次会话只解 U11 这一个 ticket; 诚实标注状态 (Ubiqua 打开拆产物由用户验证)
- 技术断言要有依据; 遇阻塞/不确定停下来汇报, 不绕行
- 后端: python -m backend --port 8720 (代码改动需重启)
- 素材: C:\Users\Administrator\Desktop\switch_module\问题整合五-重点\
  (08-13-中继侧抓包.cubx 85MB / 08130929_26.cubx 76MB, 基准: 76MB 全量解析 333.6s)
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

### ③ 总控审查后修复窗口 (总控窗口已实测定位问题, 照清单修)

> 2026-08-12 起 (AI 数据集导出先例): 总控窗口审查新交付 → 实测验证约束 → 发现问题固化修复清单,
> 修复窗口照清单执行 + 提交入库。

```text
项目: D:\ai_agent\zigbee_capture_analyze

你是 AI 数据集导出收尾窗口。任务: 补齐 P1 契约占位 + 提交入库 (总控窗口审查发现, 2026-08-12)。

## 背景
scripts/export_ai_dataset.py (AI 数据集导出, 新功能) 依赖 backend/cubx_reader.py 新增 11 个字段
(frame_len/nwk_fcf/nwk_flags/nwk_dst64/nwk_discover_route/nwk_proto_version/nwk_relay_count/
nwk_relay_index/nwk_relays/aps_fcf/aps_security)。任务说明声称"与 tshark 双路径契约兼容",
但 backend/tshark.py 的 _frame_to_dict 返回 dict 缺这些字段占位 — 总控实测
test_p1_contract.py check 1 挂: cubx 独有 14 字段 = 本次 11 + 既有 3 (route_req/route_reply/zcl_status)。

## 任务
1. tshark.py _frame_to_dict 返回 dict 补 14 个占位字段 (全部 None), 参照既有 zcl_attr_reads 占位先例加 P5 注释:
   - 本次新增 11: frame_len, nwk_fcf, nwk_flags, nwk_dst64, nwk_discover_route,
     nwk_proto_version, nwk_relay_count, nwk_relay_index, nwk_relays, aps_fcf, aps_security
   - 既有 3: route_req, route_reply, zcl_status
   位置: 返回 dict 内按逻辑分组 (frame_len 靠 packet_id; nwk_* 靠 nwk_radius/nwk_security;
   aps_* 靠 aps_counter; route_* 靠 nwk 命令字段; zcl_status 靠 zcl_seq)
2. 验证: 重跑 python .scratch/verification/p1-contract/test_p1_contract.py
   - 期望: check 1 两个子项 PASS (cubx 独有/ pcap 独有 均为空)
   - check 3/4/5 仍失败 = 基线既有 (U9 ticket Resolution 已记录), 对照确认没有新增失败项
   - compare_paths.py 输出对照: 不应出现新的"独有字段"类差异
3. P2 回归: pcap 路径输出加字段 → 跑 python .scratch/verification/p2_regression.py
   看快照是否失效; 失效则 --update 并在结果里记录原因 (预期行为: pcap 快照 hash 变化)
4. 提交入库:
   - 必提交: backend/tshark.py + backend/cubx_reader.py + scripts/export_ai_dataset.py
     + docs/ai_dataset_format.md + 相关回归快照
   - exports/ai/ 样例产物 (约 23K 行数据): 先查 .gitignore 与 git 既有惯例, 不确定问用户
   - commit message 前缀 feat: (含 AI 数据集导出 + 契约补齐说明), git push (代理 127.0.0.1:7897)

## 铁律
- 只做以上范围, 不碰其它文件; 一次会话只解这一件事
- 诚实: 修复后若仍有新增失败, 停下汇报, 不掩盖
- 遇不确定 (exports 是否入库/快照更新口径) 先问用户, 不自行处置
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
| U8 | 诊断页优化 | UI 工程 |
| U9 | 节点页重构与设备信息提取 | UI 工程 (Q&A 对齐产出, 2026-08-12) |
| U10 | AI 数据集导出集成 | UI 工程 (方案待确认, 2026-08-12) |
| U11 | 大包时间窗拆分导入 | UI 工程 (grilling 对齐产出, 2026-08-13) |
| U12 | 诊断页学习机制 | UI 工程 (grilling 对齐产出, 2026-08-13) |
| U13 | 拓扑链路证据重构 | UI 工程 (grilling 对齐产出, 2026-08-21) |

### 认领纪律

- **一次会话只解一个 ticket**(research 型可并行)
- 认领 = 在 ticket 文件顶部加 `**Assignee:** <会话标识> + 日期`
- 完成 = ticket 写 `## Resolution` + map.md Decisions so far 更新 + git 提交推送
- **收尾同步 (2026-08-06 补充, P6 账实不符教训)**: 代码提交后**同一会话内必须**完成 ticket 收尾
  (Assignee/Status/Resolution + map.md 条目 + push), 不得只提交代码留 ticket 空转 —
  总控窗口会定期核对账实, 但收尾是执行会话的责任

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
