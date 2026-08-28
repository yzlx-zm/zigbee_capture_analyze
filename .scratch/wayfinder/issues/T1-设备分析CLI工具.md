# T1 — 设备分析 CLI 工具 (节点页设备分析能力独立化, grilling 对齐产出)

**What to build:** 独立 CLI 工具: 输入 cubx (单文件/目录批量) → 输出每包设备画像报告
(厂商ID/型号ID/EUI64/端点/控制命令统计/代表帧解析)。从节点页 U9+U15 能力抽离, 复用最大化。

**Blocked by:** None | **Status:** done

**Assignee:** T1-实现-20260828 | **Type:** task | **独立工具** (非三大工程, 非 S 系列)

**来源**: 2026-08-28 总控窗口 grilling 对齐 + 自审 (工程文件组织 — 用户要求严谨自审)。

## 对齐决策 (用户确认, 不可更改)

| 项 | 结论 |
|----|------|
| 形态 | 方案 A: **CLI 工具** `device-analyze <cubx 或目录>` |
| 输入 | 单文件 + **目录批量** (扫描 *.cubx, 每包一份报告) |
| 输出 | MD (人读: 首行厂商ID/设备ID/EUI64 + 画像表 + 控制命令统计 + 代表帧解析, 复用 U15 格式) + JSON (结构化); 写到**输入同目录** `<名>_device_report.md/.json`, `-o` 可指定 |
| 工程组织 | **方案 D**: 独立目录 + sync_deps.py 构建同步 (见下) |
| 打包 | 本机脚本先用, 好用后再评估 PyInstaller exe |
| 解密边界 | 依赖 cubx 内嵌 key + 本机 zigbee_pc_keys; 无 key 素材标注"未解密 (缺 key)"不报错 |
| 不做 | 诊断/拓扑/报文/Web/时间窗拆分 |

## 工程组织 (方案 D, 自审产物)

```
device-analyzer/               ← 独立目录 (与主工程并列, 如 D:\AI_SKILL\device-analyzer\ 或用户指定)
├─ device_analyze.py           ← CLI 入口 (~200 行新写)
├─ sync_deps.py                ← 构建同步脚本 (~80 行新写)
├─ deps/                       ← 同步产物 (构建时生成, 不手工维护)
│   ├─ cubx_reader.py          # sync from main @ <commit>  (文件头版本戳)
│   ├─ zcl_defs.py / zcl_defs_std.py / tuya_proto.py / key_store.py
│   └─ MANIFEST.json           ← {source_repo, source_commit, sync_date, files:[{name, sha256}]}
└─ 输出: <包名>_device_report.md / .json
```

**关键机制**:
1. 开发期: device_analyze.py 支持 `--src <主工程路径>` 直接 import 主工程 backend (零漂移迭代)
2. 分发期: `python sync_deps.py --src <主工程> --out deps/` 复制依赖模块 + 写 MANIFEST
3. 漂移检测: 每个依赖文件头 `# sync from zigbee_capture_analyze @ <commit>`; 启动时可选
   校验 MANIFEST sha256 (检测文件被手工改过)
4. 无手工复制: 一切走脚本

## 复用清单 (零改动, 原样 import)

- backend/cubx_reader.py — 解析+解密 (依赖 scapy/pycryptodome)
- backend/zcl_defs.py + zcl_defs_std.py — 109 簇/369 命令 (ZAP 自动化产物) + 载荷 schema
- backend/tuya_proto.py — 涂鸦 0xEF00 DP 解析
- backend/key_store.py — 外部 key 读取
- backend/api/topology.py `_node_stats` — 设备聚合 (厂商/型号/端点/簇命令统计) **抽出复用**
- U15 画像导出格式 (MD+JSON 组装逻辑)

## 新写代码

1. **device_analyze.py**: argparse (paths/-o/--src/--json-only) + 目录遍历 (*.cubx) +
   流程编排 (parse_cubx → _node_stats → 画像组装 → MD+JSON 写出) + 进度输出
2. **sync_deps.py**: 从主工程复制 5 个依赖模块 + 写文件头版本戳 + MANIFEST.json

## 验证标准

1. dimmer 素材: 报告含 `_TZE204_dayazmbk` / `TS0601` / 端点 / 0xef00 命令统计 (与 U9/U15 实证一致)
2. 中继入网抓包(1): 多设备报告, 各设备画像完整; 无 key 素材标注不崩
3. 目录批量: 4 个训练素材一次跑完, 每包一份报告
4. JSON 结构化: 与 MD 内容一致; 可被脚本消费 (json.load 通过)
5. sync_deps: 同步后 deps/ 模块 import 正常 + MANIFEST 正确; 启动校验通过
6. 与主工具一致性: 同一素材 CLI 报告 vs 节点页导出内容对账一致

## 风险

- _node_stats 在 topology.py 中 (API 层) — 抽出时保持签名不变, 主工具不回归 (回归: 节点页数据不变)
- scapy 版本兼容 (独立环境可能缺 scapy/pycryptodome) — requirements.txt 记录依赖版本
- 大包解析耗时 (与主工具一致, 无额外优化; 批量时逐包进度输出)
- 报告体积: 多设备多簇帧样本可能大 — MD 样本数控制 (每命令 1-2 帧, U15 先例)

---

## Resolution (2026-08-28, T1-实现-20260828)

**工具位置**: `D:\ai_agent\zigbee_device_analyze\` (用户指定, 非 ticket 示例 D:\AI_SKILL\device-analyzer\)

### ⚠️ 需求确认变更 (开工前用户指示)

1. **原工程零改动 (用户强调)**: 曾按 ticket "共享位置" 选项创建 backend/node_stats.py 并改
   api/topology.py import, 用户打断明确要求不动原工程 → **已完整回滚** (node_stats.py 删除 +
   topology.py 4 处编辑还原, git diff 核实仅剩会话前既有 S3 改动)。最终方案 = ticket 方案 D
   **工具内复制**: sync_deps.py 从主工程按函数边界抽取到 deps/, 原工程零改动。
2. 样本帧分层解析复用: 用户选定 "抽取到 deps/detail_shared.py" 方案。

### 交付内容 (2 新写文件 + 3 抽取产物 + 同步机制)

| 文件 | 内容 |
|---|---|
| `device_analyze.py` (~300 行) | CLI 入口: argparse (paths/-o/--src/--json-only) + 目录遍历 (*.cubx) + 流程编排 (parse_cubx → _extract_nodes_from_packets → _node_stats → 画像组装 → MD+JSON 写出) + 进度输出 (逐包/解析百分比); deps 模式启动时 MANIFEST sha256 漂移检测 |
| `sync_deps.py` (~240 行) | 方案 D 同步脚本: 整文件复制 6 模块 (cubx_reader/zcl_defs/zcl_defs_std/tuya_proto/key_store/topology) + ast 函数级抽取 3 共享模块 + 文件头版本戳 `# sync from ... @ <commit>` + MANIFEST.json (source_commit/sha256) + --check 漂移校验 + 依赖检查 (函数体内调用未抽取的同文件顶层函数 → WARN) |
| `deps/` (sync 产物) | 6 复制模块 + detail_shared.py (_detail_dict+_fallback_layers+_fallback_nwk_cmd_tree+_fallback_zdp_tree, import 重写) + node_stats_shared.py (_node_stats+_build_phase3_supplements+LS 缓存) + nodes_shared.py (_extract_nodes_from_packets) + MANIFEST.json |
| `requirements.txt` | scapy>=2.5.0 / pycryptodome>=3.20.0 (主工程同款, 本机实测 2.7.0/3.23.0) |
| `README.md` | 用法/输出/工程组织/一致性说明 |

**画像组装 (CLI 新写 ~120 行, 格式复用 U15)**: JSON profile 与主工具 /nodes/{aid}/export
逐字段一致 (aid/pan/device_type/eui64/manufacturer_name/model_id/seen/first_ts/last_ts/
endpoints/clusters[每命令最早+最近 2 帧 _detail_dict 完整解析]); MD = 首行厂商ID/设备ID/
EUI64 + 画像表 + 端点 + 控制命令统计 + 每命令最近 1 帧样本 (仅 APS 层+ZCL 载荷解析,
U15 用户反馈精简口径)。报告 = 每包一份 `<名>_device_report.md/.json`, 设备排序 = 有厂商/
型号置顶 (U9 用户要求) + 地址序。

### 实现要点记录

- **dev 模式 --src 直连主工程** (零漂移迭代), 分发模式 deps/ — 两模式输出**逐字段完全一致**
  (实测 0 差异, 含 samples 完整分层解析)
- **涂鸦注册坑 (U15 依赖)**: PAYLOAD_PARSERS 注册发生在主工程 files.py 顶部
  `_tuya_proto.register(zcl_defs.PAYLOAD_PARSERS)`, deps 模式无 files.py → 0xEF00 静默走
  字节偏移兜底 (deps 输出 0xEF00 parser=fallback vs src parser=涂鸦) — device_analyze.py
  _load_api 两分支显式注册修复
- 解密边界: 无 key 帧标注 "未解密 (缺 key)" 不报错, 报告 source 摘要含 decrypt_summary
  (P4 语义: 有 nwk_security 且 decrypted=False)

### 验证结果 (6 项全过)

1. **dimmer 素材**: 报告含 `_TZE204_dayazmbk` / `TS0601` / 端点 [0x01×78, 0x00×16, 0xFF×2] /
   0xEF00 cmd 0x0B×22 (Default Response, U15 修正口径) + cmd 0x02×20 + Basic cmd0×8/cmd1×7 —
   **与 U9/U15 素材实证逐项一致** ✓
2. **中继入网抓包(1)**: 8435 帧 122 设备, 3 台命名 (0x838D=smart lock/AKLOCK-C6 与 U14 实证一致,
   0xCE93/0xF67F=_TZ3210_rsl0rprr/TS0503B); 缺 key 帧标注不崩 ✓
3. **目录批量**: 训练素材 5 个 (31321×2/32200/32533/33340) 一次跑完, 每包一份报告 ✓
4. **JSON 可消费**: json.load 通过; deps vs src 模式输出逐字段 0 差异 ✓
5. **sync_deps**: 9 文件 + MANIFEST 正确 (commit ca1fae9), --check 校验通过 ✓
6. **与主工具一致性**: 同素材 CLI 报告 vs 主工具 /nodes/0xCE5B/export (同路径内部函数调用)
   **逐字段 0 差异** (含 samples 完整分层解析) ✓

### 诚实标注

- 主工具对账用内部函数模拟导入 (parse_cubx + files._packets/_nodes 赋值 + asyncio.run
  node_export), 未走 HTTP 服务 — 与真实端点同代码路径, 差异风险可忽略
- CLI 工具目录尚未 git init/远端 — 仅本地文件, 待用户确认版本管理方式
- 报告 MD 样本帧含未解密帧时载荷区显示兜底 (与主工具行为一致)
