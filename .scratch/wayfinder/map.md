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

- [L3-1 检测闭环](issues/11-L3-1发送命令无APS-Ack.md) — 文档 v1.0 + 检测器 R1-R4 (提交 6c1b517); 素材实证: **中继 838D 下行 ×42 R2 高 + L3-5 交叉 (0x0B×39)**, G32 BE5A 上行 ×45 + 0x0C×216 交叉, 第七次 C1F5 ×32; 配对抽共享模块 aps_pairing.py; 事务级判定 + 重复捕获去重; L3-5/L1-3 回归不变
- [L3-1 判定修正 (08-07)](issues/11-L3-1发送命令无APS-Ack.md) — **"无独立 ack"≠"命令未送达"** (用户指出 + 自审): 部分设备固件 (含中继) 不回独立 ack 帧, 以 ZCL 应用层响应确认 (Silicon Labs 官方 reply attached to ACK, nonstandard extension); 判定改为 **无 ack + 2s 无应用层响应** (反向数据帧: 同 ZCL tsn / 同 cluster / cluster 缺失降级); 三素材计数回填: 中继 838D ×42→**×34**, G32 BE5A ×45→**×36** (EFC2 ×2 保留, 反向帧未解密), 第七次 48→**37 候选 / 设备级仅 C1F5 ×32** (17266/96A8/CE77 全排除); **0x0C 1043→216 错记修正** (台账口径, 无素材支持 1043); L3-5 (0x0B×39/0x0C×216) + L1-3 (B2-LOOP) 回归不变
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
- [L3-5 verdict 语义修正 (08-10)](issues/07-L3-5源路由失效.md) — 诊断页自审: 无 0x0B/0x0C 时原判 HEALTHY(绿) 但结论"无法判定" — 自相矛盾;用户裁定**无证据 = INCONCLUSIVE 琥珀** (撤回负例; 0x0B 缺失 ≠ 无失败, message.h);提交 a5c3e86;回归: 中继 0x0B×39 / G32 0x0C×216 不变
- [L3-9 非对称链路检测闭环](issues/12-L3-9非对称链路.md) — 文档 v1.0 (14 层) + 检测器 R1-R3 + 前端卡 (9 卡);官方依据 MCP (LS 15-16s/out=0=one-way/非对称来源);负例实证: G32 BE5A 对称 ×187/40min 不误报, 三素材 R1 均 0 命中; **自审修正**: 非路由器邻居 out=0 正常态 (0x8C13/0xF95F 误报清除, ls_senders 守卫); 正例待素材; 838D 方向性失败 = R3 行为级候选 (需现场确认); **自审修正 (08-10)**: R3 补实现 (L3-5 交叉) + R1 时间窗 60s + 去重 bug (排序对) + 文档素材统计纠错 (G32 4 台/第七次 15 台); **R2 误报修复 (08-10, test2 pcap)**: 大网络稀疏覆盖 (无 2-3 次交换 out=0 初始态) + stale 重置 (邻居停发 LS) 双重误报根因 — 双向可见守卫 + 全程 out=0; test2 几百条→0
- [解析器字段扩展] — tshark/cubx 对齐补 nwk_cmd_id + Leave 标志 + Remove Device target (0x07) / Update Device status (0x06);tshark.py 此前缺 nwk_cmd_id 提取 (pcap 路径 L1-3 Leave 判定缺口, 已补齐)
- [P6 导入解析校验工具](issues/P6-导入解析校验工具.md) — parser_verify.py: pcap 权威对比 (全量/分层) + cubx 自洽, 分类型失败 (错位锁定/缺key警告); 导入自动跑 + 导入页卡片; 破坏测试 12/12 (抓错能力证明); 健康素材权威匹配 255/255
- [P1 契约修复 + 帧去重](issues/P1-双路径字段契约对齐.md) — 0x28 伪命令清零 (1266→1: 其他 PAN 命令帧解密失败读密文, plain_valid 守卫);nwk_dst 广播保留 (0xFFFC, _addr_nwk 对齐 tshark) + 邻居表 ≥0xFFF0 过滤连带修复;新增 backend/frame_dedup.py 同跳去重 (Unlock 帧 27% 物理重复 + 10% 重传, 全局 8.5%; **不能用 (nwk_src,dst,nwk_seq) 事务键 — 8 位回绕错误合并独立事务, 实锤 (54995,seq=12) 相隔 421s**);**自审修正 (08-06)**: 方向位协议自洽 (锁上行 190 条全 Server→Client, 早期"设备非规范"结论系并发写文件中间态污染, 撤回);回归 15/15 (p1-contract/p1_regression.py)
- [群控压测问题包分析](issues/P1-双路径字段契约对齐.md) — 素材实证: 16 锁 1s 轮询全 SED, 唯一中继 19950;物理去重后 429 次 Unlock 发送事件, 直发锁 100% 帧捕获 + 锁侧 ACK 覆盖 52-87%;中继锁 54995/33440 各 25 发送, 投递帧捕获 16/25 (64% = 抓包器第二跳捕获率), **缺投 18 帧 18/18 有锁侧 ACK (17/18 counter 匹配) → 真实投递 25/25 锁全部收到** → **"中继不转发"是抓包漏投递帧的假象**;锁无 ZCL 上行 (只回 APS ACK) — "子设备不回应"落点在锁协议;抓包器重复 + 漏单跳 → 抓包可信度是后续分析前提;群控包已登记素材台账
- [L2-1 检测闭环](issues/01-L2场景拆解.md) — 文档 v1.0 + 检测器 R1/R2a/R2b/R3;素材实证: **被踢重入循环 (TC→737D rejoin=1 Leave ×336)** = 频繁离线形态之一;健康轮询基线 (poll 间隔 ≤5.5s);R1 (poll>320s)/R2a/R3 待素材
- [中继状态异常分析](issues/09-中继状态异常分析.md) — 中继素材库 (DA13 系列 + G32 + FEED) 专项;模式 1: DA13 网络中继 0x0B 下行 (入网后 2-5s, 与 838D 同构);模式 2: G32 中继 0xBE5A 0x0C 双向失败 (dest 细分) + 0x06; **L3-5-R2 素材验证通过**;模式 4: 08031620 无 NS 但 MTORR 高频 (3.4s/次)
- [L6-S3 检测闭环](issues/10-L6-S3间接事务过期.md) — 文档 v1.0 + 检测器 R1/R2/R3;素材实证: **下行投递失败型** (G32 0xEE48 poll 活跃仍过期 ×38, 0x06 距 poll 2.5s, 与 0x0C 交叉 = L3-5 SED 侧表现);睡眠型待素材
- [P5 ZCL 命令名 FCF 误标修复](issues/P5-字段缺口工单流.md) — get_command_name 增加 frame_type 参数 (0=全局/1=cluster-specific);cubx 传 zcl_fcf&0x03, tshark 解析 zbee_zcl.type (tshark -G fields 确认);Basic 0x0000 全局 Read Attributes 不再被误标 Reset to Factory Defaults (中继素材例证帧实证);回归: 素材 12/12 + unit 8/8 + p1 15/15;test_parser_verify 9/3 为基线既有失败 (stash 对照确认, 非本次引入)
- [P3 大包性能优化](issues/P3-大包性能优化.md) — **bytes 级预筛 + 多进程并行** (组合方案): 预筛 (raw[0]&0x07, scapy 源码级依据: NWK 层只存在于 Data 帧) + ProcessPoolExecutor 2-4 workers (initializer 注入 keys, 失败回退串行, 候选 <8000 走串行); 双向一致性 8/8 素材指纹逐位一致 (p3_consistency.py 入库); 实测提速: 群控 2.72x / test2 2.69x / 29MB 3.09x / 249MB (288 万帧) ~14min→234s (3.6x); p1 15/15, P6 持平; **结论修正 (自审)**: 原 20x 预估错误 — 成本主体是 Data 帧 (1.8ms/帧, 60%), 预筛保留全部 Data 帧, Ack 帧解析本身便宜 (0.04ms); 收益估算以实测为准 (2.7-3.6x)
- [P2 素材回归测试体系](issues/P2-素材回归测试体系.md) — p2_regression.py 入库: 素材快照 (统计层 + 每帧指纹 SHA-256 + 解析器专属 commit, git log 限 3 解析器文件) + 自动回归 (默认快集 4 素材 / --slow 大包 / --update 刷新); 初始快照 4 份 (commit 5c2ae08); **顺带修复 P6 校验器 bug**: parser_verify 权威对比 int(auth_seq,16) 把 tshark 4.6 十进制 seqno 按 16 进制解析 → 基准 3.92% 匹配假象, 修复后 test_parser_verify 9/3→12/12 全过; 回归: p2 4/4 + p1 15/15
- [P4 解密覆盖扩展](issues/P4-解密覆盖扩展.md) — **解密失败原因可观测**: 新字段 sec_key_type (aux bits1-2, 双路径: cubx 手解 / tshark zbee.sec.key_id) + decrypt_note (missing_key/mic_fail/parse_error); parser_verify 健康度按原因分类; VerifyKey key_type=4 selector 0x03 候选补全 (协议级, 待素材); **自审修正**: 中继包安全帧 99.98% 为 key_type=0 (设备唯一 TC link key 加密) — 58.5% 失败 = 缺设备 link key 非 bug; 撤回手写偏移错误统计 + "load hash 实证" 无实证表述; 回归: p2 4/4 (快照 --update) + p1 15/15 + P6 12/12; 素材侧: 提供 838D 等 TC link key → 失败率可降

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
- [U7 拓扑页优化](issues/U7-拓扑页优化.md) — 形状分类 (协调器六边/路由菱形/终端圆/未知三角) + 死控件修复 (taddr 定位 / 静默节点切换) + 播放按钮 + 时间刻度条 + 图实例复用 (时间过滤不再重建, 性能提升); 截图见 .scratch/verification/u7-topo/; **终端设备判定修正 (08-06)**: 素材实证两方向误判 — ①SED 误判 router (Route Request/Record 发送者非 FFD 信号: 群控锁 0x82A0/0xD6D3, G32 0xEE48 实证 SED 也发) ②无信号整网误判终端 (test2 2628 节点); 重构为协议级信号: LS/RREP→router, MAC poll→end_device (修复 poll 帧被 NWK 过滤排除), DA capability 权威声明 (cubx), 无信号→unknown; 验证 34/34 + P1 回归 15/15; ⚠️ 需重导素材生效 (device_type 为导入时快照); **cubx 事件提取缺口修复 (08-06)**: extract_* 只认 tshark raw_layers, cubx 路径 raw_layers={} → RREQ/NS 事件全丢 → 拓扑空 (设备添加失败包实证); 回退 cubx route_req/nwk_status_code/nwk_status_target 字段, 中继包事件 0→140/0→20, 拓扑 nodes=7
- [U3 节点页补齐](issues/U3-节点页补齐.md) — 行内展开详情 (首末时间/帧类型计数/EUI64/LQI-RSSI 统计/邻居表+不对称标记) + 设备类型列 + 🎯 定位按钮; 后端 /api/nodes 加 detail (EUI64/LQI-RSSI 仅 cubx); seen 计数单遍 O(pkts); CDP 17/17; 截图见 .scratch/verification/u3-nodes/; CSV 路径未实测
- [U5 时间线优化](issues/U5-时间线优化.md) — 类型下拉动态化 (/api/packets/types 全量统计) + 事件标记 (⛔Leave 按 rejoin 区分 / 🔄Rejoin / ⚠️NetStatus, 协议依据: NWK 0x04 标志位) + 2 bug 修复 (详情 TypeError: nwk undefined for-in; 联动时间全零: S.topoT0/T1 契约统一 tlToTs 兼容 + isNaN 兜底 + 跳转重置抓包范围) + 跳转节点过滤 (topoAddr→tlNode 同步); 验证: 徽章 DOM/详情/跳转端到端 ✅, 详情崩溃修复待含 MAC 帧素材; 截图见 .scratch/verification/u5-timeline/
- [U8 诊断页优化](issues/U8-诊断页优化.md) — **三批次全部完成 (08-10)**: ①diag.js 嵌套→检测器注册表 (MODULES 数据驱动, 加检测=注册条目+render 函数; 自审修正: Promise.all 统一渲染→渐进渲染+15s 超时兜底, 单模块挂起整页空白实测复现; CDP 对比逐字符一致) ②设备 🔍时间线 跳转 (S.topoAddr 契约, U4 联动落地; 🎯拓扑 用户反馈无意义已移除) + **跨卡片事件链卡** (hitDevices 登记, ≥2 命中触发; CE77: L1-3×L1-4×OFF 案例验证; ⚠️ L6 verdict 为 L6-S3_HIT 非卡片名) ③摘要卡覆盖提示 (无 HIT 时显示 8/55 场景, 防"未发现明显问题"误信); **白话化 (08-10 用户反馈)**: 编号降级 .sc-tag 小角标, 标题/verdict/事件链用白话 (设备找不到网络/密钥分发或验证出问题...), 顺带修 L1-3/L6-S3 vClass 前缀不匹配琥珀 bug

## Not yet specified

- 55 场景中 49 个未闭环 — 优先级由用户定 (低挂果实: L6-S3/L2-6/L2-3)
- 1885→838D 下行链路断的根因 (非对称: 上行通下行断) — 需现场信息 (L3-5 检测已就绪, 现场复测可验证)
- L1-3 规则 A1/A2/B1 的故障帧形态 — 等用户素材后验证
- L1-4 规则 R1/R2a (0x07 显式拒绝/踢人) 与 R3 (静默拒绝) — 等复现素材 (网关白名单 deny / 删除设备操作)
- L3-5 规则 R2 (0x0C MTORR 上行失败) — 需断链链路上行抓包
- L2-1 规则 R1 (poll >320s 超时) / R2a (自发循环) / R3 (poll 无 ACK) — 需终端频繁离线场景抓包 (≥320s 覆盖 + poll 链路)
- UI 优先级 — 由用户定 (剩 U4 联动; U1/U3/U5/U6/U7 已完成)
- 群控压测"概率控制失败"根因 — 素材内不可判定 (锁均收到命令): 需网关日志 (锁执行后不上报?) / 网关是否收到锁 ACK 上行 / 现场复测;另: 0x61/0x20 命令语义待用户确认 (P5)
- 抓包可信度 — 群控包重复 37% + 投递帧漏抓: 需确认抓包器部署 (多接收器? 位置?), 影响一切计数类检测结论

## Out of scope

- 设备固件/网关固件实现层修复 (工具只定位, 不修固件)
- 现场网络配置调整
