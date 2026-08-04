# Zigbee Capture Analyzer — AI 协作配置

## 嵌入式协作技能库

本项目内置 [embedded-skills](.claude/skills/) 协作技能库（13 个技能，中文版）。

> **默认使用中文版本**。执行技能时，优先读取中文版指令，以中文回复和产出文档。

### 可用技能

| 技能 | 调用方式 | 用途 |
|------|---------|------|
| `/scan-embedded-project` | 用户 | 深度扫描源码生成知识图谱（适配：构建系统/技术栈/协议栈/API/模块依赖） |
| `/grill-embedded-design` | 用户 | 结构化设计问答 — 每次一个决策维度，带推荐答案 |
| `/grilling` | 两者 | 核心问答引擎 — 一次一问，带推荐 |
| `/domain-modeling` | 模型 | 术语精确定义，写入 CONTEXT.md |
| `/code-review` | 两者 | 双轴审查：代码规范 + 需求匹配 |
| `/to-driver-spec` | 用户 | 对话综合 → 设计规范文档 |
| `/to-dev-tickets` | 用户 | 规范拆分 → 开发工单（含阻塞边） |
| `/handoff` | 用户 | 会话交接文档 |
| `/write-deep-tech-docs` | 用户 | 原理级深度文档 |
| `/research-datasheet` | 两者 | 后台代理查数据手册/参考手册/errata → 带引用 Markdown |
| `/prototype-driver` | 两者 | 一次性原型固件，验证寄存器访问或时序逻辑 |

### 项目自有技能

| 技能 | 文件 | 用途 |
|------|------|------|
| Q&A 需求对齐 | `.claude/skills/qa-align.md` | 结构化提问+预览卡片+安全实验+数据核查 |

### 推荐流程

```
scan-embedded-project → Q&A需求对齐 → grill-embedded-design → to-dev-tickets
         ↓                    ↓
    了解全局架构         逐维度对齐颗粒度
```

## 项目概况

- **类型**: Python 3.13 + FastAPI 后端 + 原生 ES6 HTML 前端
- **用途**: 离线 Zigbee pcap 抓包分析工具
- **关键依赖**: tshark (Wireshark CLI), Cytoscape.js, cryptography
- **数据流**: pcap → tshark 解析 → 内存存储 → API → 单页前端

## 项目文档

- `docs/design_v3.md` — Phase 2 设计
- `docs/network_analysis_kb.md` — 16 种帧诊断知识库 (576 行)
- `docs/diagnosis_playbook.md` — 5 大类 19 子场景诊断手册 (686 行)
- `docs/decryption_setup.md` — 解密流程
- `docs/acceptance_criteria.md` — 验收标准
- `docs/scenarios/OVERVIEW.md` — 55 场景验证状态总表 (wayfinder ticket 00 产出)

## Wayfinder 多会话协作 (2026-08-04 起)

本工程采用 **wayfinder 地图模式** 管理多会话开发进度。**任何新会话开工前必须先读:**

1. `.scratch/wayfinder/README.md` — 会话使用流程 (读图→认领→解决→更新)
2. `.scratch/wayfinder/map.md` — 进度地图 (Decisions so far / 迷雾 / 范围)
3. `memory/zigbee_l1_scenario_engine.md` — 场景检测引擎记忆 (用户记忆目录)

**铁律**: 一次会话只解一个 ticket;不妄自揣测,不懂问用户;判定规则成立即可。
