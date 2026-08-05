# Wayfinder Map — Zigbee 网络分析平台

> 模式: wayfinder (mattpocock skills) | 本地 markdown tracker | 建立: 2026-08-04
> 使用: 每个 cmd 会话先读本地图 → 认领一个 frontier ticket → 解决 → 更新地图 → 下一个会话

## Destination

Zigbee 网络场景检测体系 (L1-L7 文档→测试→工具闭环) 在拓扑分析工具上完整落地:
每个场景有 ①14 层拆解文档 (官方依据+实测验证) ②检测器规则 (可编程) ③前端诊断展示,
关键网络问题能从抓包直接定位根因 (含真实素材验证)。

## Notes

- 领域: Zigbee 抓包分析 (cubx/pcap), Silicon Labs 生态 + Telink 设备
- 工作流铁律: 文档→测试→工具;判定规则成立即可 (计数允许素材浮动);不妄自揣测,不懂问用户
- 每个会话必读: 本地图 + `memory/zigbee_l1_scenario_engine.md` (用户记忆) + `CONTEXT.md` (领域词汇)
- 关键知识: 素材台账 `.scratch/verification/capture_materials.md`;验证笔记 `.scratch/verification/L1-3_notes.md`
- 素材目录: `C:\Users\Administrator\Desktop\zigbee_capture\` (验证可用-记录 子目录为已验证素材)
- Git: 提交+推送由 Claude 负责 (代理 127.0.0.1:7897 已配)
- 后端: python -m backend --port 8720 (代码改动需重启后端生效)

## Decisions so far

- [L1-1/L1-2 检测闭环](issues/01-...) — 文档 v1.2 + 检测器 + 素材验证;判定规则: 允许单次MISS/1s窗口/AssocResp 200-500ms
- [L1-3 检测闭环](issues/02-...) — 文档 v1.3 + B2-LOOP/B2-LOOP-ROUTE;真实素材根因 = Confirm 经中继转发失败 (Source Route Failure, L3 路由层, 非密钥问题)
- [协议语义破解] — VerifyKey 16B = keyed_hash(TCLK,3);0x0F/0x10 = Zigbee 3.0 标准命令 (Ubiqua Reserved 是库过时);Confirm = [0x10][status=0x00 SUCCESS][key_type][dst]
- [cubx/tshark 命令 ID 提取] — 修复 0x20/0x38 误读根源 (APS 解密分支永不执行 + 缺默认 ZigBeeAlliance09 key)
- [NWK Key 确认] — 故障网络 = c91b384e572a97c8b07a3ae3dbcbdbfd;健康网络 = 0731fe01c8d9fef2a9bd3a3c6b95b80d
- [素材台账] — 验证可用-记录 素材定位;中继入网抓包(1) = L1-3 真实故障素材
- [前端 ES 模块化] — index.html 95 行 + 模块化 JS;L1 检测卡片 (含 L1-3 设备明细)
- [场景体系全景调研](issues/00-场景体系全景调研.md) — taxonomy v1.0 已定义 8 大类 55 场景;验证状态总表见 docs/scenarios/OVERVIEW.md;838D 案例 = L3-5 源路由失效 (场景交叉)
- [L1-4 检测闭环](issues/05-L1-4TC拒绝.md) — 文档 v1.2 (自审修正) + 检测器 R1/R2a/R2b/R3;素材实证: 运营期踢人路径 = **ZDO Mgmt Leave Req (0x0034) 指令可见** (leave_question ×12) + 设备广播 Leave 响应 (rejoin=0);R2b 高置信验证通过, R1/R2a/R3 待素材
- [L3-5 检测闭环](issues/07-L3-5源路由失效.md) — 文档 v1.1 (自审修正) + 检测器 R1 (0x0B 轮次判定) / R2 (0x0C);838D 素材实证: 39 条 0x0B 全 src=1885→838D (7 轮/34s, 检测器实测), **L1-3 交叉双报** (密钥循环 = 本场景表象);路由活动未恢复 (Route Request ×161, MTORR 计数待解析);R2 待素材
- [解析器字段扩展] — tshark/cubx 对齐补 nwk_cmd_id + Leave 标志 + Remove Device target (0x07) / Update Device status (0x06);tshark.py 此前缺 nwk_cmd_id 提取 (pcap 路径 L1-3 Leave 判定缺口, 已补齐)

## 解析器工程模块 (2026-08-05 拆分)

**全景**: `docs/parser_overview.md` — 解析层 7 模块 (5711 行) + 已知问题 + 上下游关系
**Tickets**: P1 双路径字段契约对齐 / P2 素材回归测试体系 / P3 大包性能优化 / P4 解密覆盖扩展 / P5 字段缺口工单流
**定位**: 检测工程与 UI 工程的地基 — 字段缺口走 P5 工单流, 各工程不各自为政改解析器

## UI 工程模块 (2026-08-04 拆分)

**全景**: `docs/ui_overview.md` — 前端 8 模块 (1830 行) + 横切关注点 + 拆分维度
**Tickets**: U1 视觉设计系统 / U2=02 拓扑时间控制 / U3 节点页补齐 / U4 页面联动 / U5 时间线优化 / U6 导入页优化 / U7 拓扑页优化
**已完成切片**: 诊断页 L1-1/2/3/4 卡片统一模板 + 视觉规范初版 (提交 24aa25f)
- [U1 视觉设计系统](issues/U1-视觉设计系统.md) — 设计系统建成: 13 组 token + 状态色体系 + 组件/工具类, CSS 全抽 `frontend/css/app.css` (index.html 内嵌 style 清零), JS inline 样式清零 (仅动态数据色保留); 孤儿类补齐 (.btn-s/.imp-tab/.badge 等); 截图见 .scratch/verification/u1-design-system/; 素材验证通过 (340 包)
- [U6 导入页优化](issues/U6-导入页优化.md) — 三方向落地 (流程反馈/密钥面板/校验报告) + **真实导入进度条**: 6 端点后台任务化 (POST→task_id + /import/progress 轮询), XHR 上传真实进度 (修 0% 静止), pollImport 立即首查+300ms+5min 兜底; **cubx 卡 0 修复 (08-05)**: parse_cubx 加 progress_cb 按包上报 (30MB 实测 0%→10%→90% 平滑推进); **后台任务全局可见 (08-05, grilling)**: 轮询解耦为模块级单例, 顶栏 #sb 三态 (⟳ 进度 / ✅ 完成·点击查看 / ❌ 失败·点击查看, 点击跳回导入页), 非导入页不自动刷新, 切页后进度/完成提示全程可见; 顺带修复 import_pcap 缺 global _verify_report + verify.py 空包除零; CDP 验证 22/22 + 进度轨迹实测 + 12/12 全局可见
- [U7 拓扑页优化](issues/U7-拓扑页优化.md) — 形状分类 (协调器六边/路由菱形/终端圆/未知三角) + 死控件修复 (taddr 定位 / 静默节点切换) + 播放按钮 + 时间刻度条 + 图实例复用 (时间过滤不再重建, 性能提升); 截图见 .scratch/verification/u7-topo/
- [U3 节点页补齐](issues/U3-节点页补齐.md) — 行内展开详情 (首末时间/帧类型计数/EUI64/LQI-RSSI 统计/邻居表+不对称标记) + 设备类型列 + 🎯 定位按钮; 后端 /api/nodes 加 detail (EUI64/LQI-RSSI 仅 cubx); seen 计数单遍 O(pkts); CDP 17/17; 截图见 .scratch/verification/u3-nodes/; CSV 路径未实测
- [U5 时间线优化](issues/U5-时间线优化.md) — 类型下拉动态化 (/api/packets/types 全量统计) + 事件标记 (⛔Leave 按 rejoin 区分 / 🔄Rejoin / ⚠️NetStatus, 协议依据: NWK 0x04 标志位) + 2 bug 修复 (详情 TypeError: nwk undefined for-in; 联动时间全零: S.topoT0/T1 契约统一 tlToTs 兼容 + isNaN 兜底 + 跳转重置抓包范围) + 跳转节点过滤 (topoAddr→tlNode 同步); 验证: 徽章 DOM/详情/跳转端到端 ✅, 详情崩溃修复待含 MAC 帧素材; 截图见 .scratch/verification/u5-timeline/

## Not yet specified

- 55 场景中 50 个未闭环 — 优先级由用户定 (低挂果实: L2-1/L6-S3/L2-6)
- 1885→838D 下行链路断的根因 (非对称: 上行通下行断) — 需现场信息 (L3-5 检测已就绪, 现场复测可验证)
- L1-3 规则 A1/A2/B1 的故障帧形态 — 等用户素材后验证
- L1-4 规则 R1/R2a (0x07 显式拒绝/踢人) 与 R3 (静默拒绝) — 等复现素材 (网关白名单 deny / 删除设备操作)
- L3-5 规则 R2 (0x0C MTORR 上行失败) — 需断链链路上行抓包
- UI 优先级 — 由用户定 (剩 U4 联动; U1/U3/U5/U6/U7 已完成)

## Out of scope

- 设备固件/网关固件实现层修复 (工具只定位, 不修固件)
- 现场网络配置调整
