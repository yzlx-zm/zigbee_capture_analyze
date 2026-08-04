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

## Not yet specified

- 55 场景中 52 个未闭环 — 优先级由用户定 (低挂果实: L3-5/L2-1/L6-S3/L1-4)
- 1885→838D 下行链路断的根因 (非对称: 上行通下行断) — 需现场信息
- 前端剩余需求清单 — 待评估 (除拓扑时间控制外, 02 待用户确认)
- L1-3 规则 A1/A2/B1 的故障帧形态 — 等用户素材后验证

## Out of scope

- 设备固件/网关固件实现层修复 (工具只定位, 不修固件)
- 现场网络配置调整
