# Zigbee Capture Analyzer — AI 协作配置

## 嵌入式协作技能库

本项目加载 [embedded-skills](D:/AI_SKILL/embedded-skills/CLAUDE.md) 中的协作技能。

> **默认使用中文版本**（`skills/zh/` 目录）。执行技能时，优先读取中文版指令，以中文回复和产出文档。

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
