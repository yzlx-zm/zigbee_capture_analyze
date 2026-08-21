# U10 — AI 数据集导出集成到 Web 工具 (方案待确认)

**What to build:** 把已入库的 AI 数据集导出能力 (scripts/export_ai_dataset.py, 提交 e738ae6)
从 CLI 集成到 Web 工具: 导入页一键导出 + 后台任务进度 + 完成提示。

**Blocked by:** None — 但需用户确认方案后再开工

**Status:** ⏸ 待用户确认 (2026-08-12 总控窗口出方案)

**Type:** task | **AFK**

## 背景

- scripts/export_ai_dataset.py (1211 行) 已入库: cubx → AI 可读数据集
  (packets.jsonl/csv + events + interactions + timeline.md + digest.md, 密钥脱敏 + PAN 隔离)
- 纯函数结构 (csv_record/build_graph/write_timeline/…), backend 可直接 import
- 导出是耗时操作 (26MB 大包几十秒) — U6 已建后台任务全局三态基建 (顶栏 ⟳/✅/❌), 直接复用
- 总控审查已通过 (密钥脱敏/载荷清除/.keys 清理/PAN 隔离实测验证), P1 契约已补齐 (e738ae6)

## 实现方案 (总控设计, 已做可行性分析)

### 1. 脚本重构 (scripts/export_ai_dataset.py)
- main() 的 CLI 解析与核心逻辑拆开: 抽 `export_dataset(packets, out_dir, target_pan, progress_cb=None) -> dict`
- 参数从"文件路径"改为"packets 列表" (工具导入后内存/磁盘里就有, 不重新 parse, 更快)
- CLI main() 保持可用: parse_cubx 后调 export_dataset (行为不变)

### 2. 后端 API (backend/api/)
- `POST /api/export/ai` — 对当前导入素材发起导出 → 返回 task_id (后台任务)
- `GET /api/export/progress/{task_id}` — 进度轮询 (复用 U6 import progress 模式)
- 后台任务注册进 U6 的全局任务单例 (顶栏三态可见)
- 大包进度上报: export_dataset 加 progress_cb (参考 parse_cubx 先例)

### 3. 前端 (frontend/js/import.js + app.js)
- 导入页素材已导入时显示"导出 AI 数据集"按钮 (未导入置灰)
- 顶栏三态显示导出进度 (⟳ 进度 / ✅ 完成·点击查看 / ❌ 失败)
- 完成提示: 输出目录路径 + 文件清单 + 打开目录 (参考 U6 完成提示样式)

### 4. 数据流
```
导入页当前素材 (get_packets()) → POST /api/export/ai → 后台任务
  → export_dataset(packets, exports/ai/<名>_ai/, 自动 target_pan)
  → 完成 → 顶栏 ✅ → 点击查看路径
```

## 边界与决策

- **只导出当前导入的素材** (单素材, 不做批量)
- **cubx 最全**: pcap/CSV 路径也可导 (packets dict 通用), 但部分字段 None — 界面标注"cubx 导入字段最全"
- **密钥安全**: 复用 _redact() + .keys 清理, 不新增密钥处理逻辑
- **同名重复导出**: 固定目录名覆盖 (与 CLI 一致), 不做时间戳版本
- **不做**: 导出内容在线预览 / 多素材批量 / 目标 PAN 手动选择 (自动选解密帧最多 PAN, 与 CLI 默认一致; 如需手动选 PAN 可后续迭代)

## 验证标准

1. 导入 中继入网抓包(1).cubx → 点导出 → 顶栏三态推进 → 完成提示
2. 产物与 CLI 运行结果一致 (文件集 + packets_target.csv 行数 2174)
3. 密钥脱敏抽查: 产物无 sec_key / TransportKey 载荷 (复用总控审查方法)
4. 大包验证: 07240934_26.cubx (26MB) 导出进度推进不卡死 (progress_cb 生效)
5. 回归: 现有导入流程/CDP 不受影响; CLI 直接跑 export_ai_dataset.py 行为不变

## 风险

- export_dataset 重构时勿破坏 CLI 行为 (main() 回归跑一遍样例)
- 后台任务与 U6 单例的键冲突 (import vs export 任务 ID 命名空间)
- 大包导出内存: packets 已在内存, export 只做遍历+写文件, 内存增量小
