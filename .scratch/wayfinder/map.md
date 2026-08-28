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
- [L3-13 广播中继失败文档层](issues/17-L3-13广播中继失败.md) — **仅文档 v1.0 (用户裁定)**: MCP 核对 0xC28/0xC27 是栈内部状态不上空口 (抓包不可见, 铁证在网关日志); 代理信号素材语义未明 (广播重发 0.03s ≠ 官方 500ms); 转播缺失受单抓包器盲区约束 (群控教训); 检测器待日志素材/现场确认
- [L3-11 应用层重传频繁检测闭环](issues/16-L3-11应用层重传.md) — 文档 v1.0 + 检测器 R1 + 前端卡 (13 卡); 新 counter 轮次≥3 = 应用层重试 (同 counter=栈重传 L3-1 区分); 自审修正: 周期轮询误报 (0x4FBC/0xF342 Read 有响应) → 长间隔+成功响应排除; test2 0x89F9 ×16 轮/18.1帧每轮实证; **自审重写 (08-13)**: 批量配置误报 (0xCE77 12 轮全不同属性/838D 15 组合) → 属性级 payload 分组 + 帧/轮比守卫 (18.1 重传 vs 1.36 轮询分界); 修正后 8 台命中全帧级核实
- [L3-3 状态上报滞后检测闭环](issues/15-L3-3状态上报滞后.md) — 文档 v1.0 + 检测器 R1/R2 + 前端卡 (12 卡); 官方依据 ZCL 上报机制; 自审修正: 同 cluster 匹配误报 (0xCE93 Basic 稀疏属性) → 设备级沉默 + Write 被拒排除 (0x86); 四素材负例 HEALTHY; 正例待素材; pcap zcl_status 待 P5
- [L3-2 命令送达未执行检测闭环](issues/14-L3-2命令送达未执行.md) — 文档 v1.0 + 检测器 R1/R2 + 解析器 zcl_status (cubx); 官方依据 EmberAfStatus 枚举; 素材: 第七次 0x86×16 (0xFFDE 厂商属性被拒) / 中继 0x86×52+0xC3×6; 自审修正: Default Rsp 偏移 (command_id 误判) + cluster-specific frame type 守卫 (OTA 0x10 误报); 修正后全标准码; pcap 路径待 P5
- [L2-6 静默失联检测闭环](issues/13-L2-6静默失联.md) — 文档 v1.0 + 检测器 R1 (规律 poll 停止) / R2 (LS 邻居消失+全局沉默守卫); 官方依据: Poll Timeout / 邻居 aging / "失联无官方通知需自建检测"; 负例: test2 稀疏覆盖误报清除 (表替换/移动); 候选: 中继 838D/737D/D259/8A41 (需现场确认); 正例待素材; 事件链联动 (737D: 频繁离线×静默失联×离网)
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
- [U9 节点页重构与设备信息提取](issues/U9-节点页重构与设备信息提取.md) — 精简 6 列 (地址|设备类型|厂商名|型号|出现次数|操作) + 设备身份提取 (Basic Read Attr Rsp: cubx 新字段 zcl_attr_reads + _parse_read_attr_records, ZCL spec 2.4.2.2.1) + 控制命令统计 (cluster+cmd+dir+频率, 展开小节); dimmer 实证: `_TZE204_dayazmbk`/`TS0601` (ticket TS6001 笔误修正), 0xef00 cmd11×22 与实证一致; **实现要点偏移修正 (zcl_off+3→+2)** + **U9 统计块按帧去重** (4-aid 循环重复计数); 242 GP EP 归协调器; pcap 路径占位 (P5 记录); 回归: zcl_fcf 12/12 + P6 12/12 + p2 4/4 (快照刷新) + **CDP 23/23**; test_p1_contract 5 失败 = 基线既有; 控制命令真实素材待用户 (入网包无控制帧)
- [U11 大包时间窗拆分导入](issues/U11-大包时间窗拆分导入.md) — 大包卡死一体流程: prescan (秒级, 60 桶直方图) → 选窗 → 物理拆小 cubx (同 schema + 保 Id + sqlite_sequence, Ubiqua 兼容) → 自动导入; API /cubx/prescan + /cubx/split (后台任务复用互斥); 前端 >30MB 弹预扫面板 (双滑块) 小文件直接导入; **并行进度修复 (附带必修)**: _parse_rows_parallel 分块 submit + as_completed 块级上报, 解析 [0,90%] 组装 [90,100%] 衔接 (卡死根因 cubx_reader:916 无回调); 实证: 76MB 预扫 3.2s/85MB 3.6s, 1 分钟窗拆分 2.7s 对账一致, 85MB 端到端 5 分钟窗 → 1156 帧/15 节点诊断可用; 回归: P1 基线 4 / zcl_fcf 12/12 / P6 12/12 / p2 4/4; Ubiqua 打开拆产物用户验证
- [U5 时间线优化](issues/U5-时间线优化.md) — 类型下拉动态化 (/api/packets/types 全量统计) + 事件标记 (⛔Leave 按 rejoin 区分 / 🔄Rejoin / ⚠️NetStatus, 协议依据: NWK 0x04 标志位) + 2 bug 修复 (详情 TypeError: nwk undefined for-in; 联动时间全零: S.topoT0/T1 契约统一 tlToTs 兼容 + isNaN 兜底 + 跳转重置抓包范围) + 跳转节点过滤 (topoAddr→tlNode 同步); 验证: 徽章 DOM/详情/跳转端到端 ✅, 详情崩溃修复待含 MAC 帧素材; 截图见 .scratch/verification/u5-timeline/
- [U8 诊断页优化](issues/U8-诊断页优化.md) — **三批次全部完成 (08-10)**: ①diag.js 嵌套→检测器注册表 (MODULES 数据驱动, 加检测=注册条目+render 函数; 自审修正: Promise.all 统一渲染→渐进渲染+15s 超时兜底, 单模块挂起整页空白实测复现; CDP 对比逐字符一致) ②设备 🔍时间线 跳转 (S.topoAddr 契约, U4 联动落地; 🎯拓扑 用户反馈无意义已移除) + **跨卡片事件链卡** (hitDevices 登记, ≥2 命中触发; CE77: L1-3×L1-4×OFF 案例验证; ⚠️ L6 verdict 为 L6-S3_HIT 非卡片名) ③摘要卡覆盖提示 (无 HIT 时显示 8/55 场景, 防"未发现明显问题"误信); **白话化 (08-10 用户反馈)**: 编号降级 .sc-tag 小角标, 标题/verdict/事件链用白话 (设备找不到网络/密钥分发或验证出问题...), 顺带修 L1-3/L6-S3 vClass 前缀不匹配琥珀 bug

- [U15 节点控制协议解析 + 画像导出](issues/U15-节点控制协议解析与导出.md) — **载荷字段级解析闭环**: zcl_defs CMD_PAYLOAD_SCHEMAS (On/Off/Level/Color/Door Lock/Window Covering/Groups/Scenes/Identify 标准簇 + 全局命令属性记录) + tuya_proto.py (0xEF00 DP) + 字节偏移兜底链 (PAYLOAD_PARSERS 注册表扩展); packet_detail 加 zcl_payload_parsed; 节点页 📄示例弹层 + ⬇️导出 (JSON+MD 含代表帧解析); **素材实证推翻 ticket 假设**: dimmer 0x0B×22 实为 Default Response (非涂鸦控制命令), DP 结构 [seq:2 BE]+[dp][type][len:2 BE][value], value 4B BE, 无 ms code; **0x42=短字符串 1B 前缀** (Read Attr Rsp 实证); 回归 P1 15/15 + zcl_fcf 12/12 + p2 4/4 + P6 12/12; CDP 3 项全过 (截图 .scratch/verification/u15-control-parse/); 涂鸦 0x0B 控制帧/控制操作抓包待用户

- [U14 拓扑节点显示增强](issues/U14-拓扑节点显示增强.md) — 分步 5 步全落地 (后端字段 ff4aebe /
  label 双行 3922e21 / 状态样式 53e0bd8 / tooltip 9302b98 / 时间窗联动): graph+events 节点加
  model_id/manufacturer_name/eui64/behavior/poll_interval/tx/rx (rejoin 方向语义 + 协调器豁免 +
  poll 仅发送方); label 第二行型号; rejoining 橙虚线/sleeping 灰/sleeping 未实证/offline 暗红边框;
  tooltip 全字段 (838D 实测: 厂商 smart lock/型号 AKLOCK-C6/poll 0.2s/帧量 254/180);
  滑块联动窗内重算 (CDP 请求参数验证); 回归 zcl_fcf 12/12 + p2 4/4 (--update);
  与 U13 协调: 仅动节点呈现段, 边/链路未触碰; sleeping 素材缺口待用户

- [U13 拓扑链路证据重构](issues/U13-拓扑链路证据重构.md) — 分步 4 步全落地: 链路证据协议化
  (poll 父/AssocResp 父/RR 下一跳/下行 source-route 反转, 芯科规范) + 父链路边渲染 +
  🕐链路历史时间轴 (RR 路径切换/poll 父变更分段, CE93 直连↔5FDD 实证) + 去播放;
  **过程中 6 项修复**: Cytoscape data.parent 复合节点冲突 (网关框子设备) / RR 中继漏判
  (906C) / 直连 RR 三重拦截丢弃 (1F4A 等 5 设备消失) / 多 PAN 混杂 (过滤顺序+列表全量) /
  DA capability 优先级 (中继间接传输 poll 误判) / PAN 列表恢复切换; 回归 zcl_fcf 12/12 +
  p2 4/4; A657 unknown 素材证据不足诚实标注
- [U16 报文页看包体验优化](issues/U16-时间线看包体验优化.md) — 7 项全落地 (提交 1048e70):
  字段点选 (PAN/地址) / 未解密默认隐藏+开关 / 摘要列 / 路径列 (完整路径+展开) /
  APS Ctr 列 / 层级着色 / 事务链 (同 tsn 响应+跳转; ⚠️ 首版误配收紧: 仅 ZCL 帧+仅 tsn);
  用户驱动附加: **页面改名 时间线→报文** / **全量化** (用户裁定 A: _packets=全量帧
  4158→8435, 未解密语义=仅 NWK 安全未解密, 明文 MAC 帧不隐藏) / **MAC Ack 支持**
  (用户裁定 B, cubx+tshark 双路径 ft=2, 8626=8435+104 reserved+87 无信息帧;
  MCP 依据: 官方 Network Analyzer 展示 Ack) / 自动加载全量 / DataReq 命名 scapy 源码级
  修正 (4=DataReq) / 🔒 仅限 NWK 安全; 上行路径=下行 source-route 反转 (RR 证据实证
  不足: 31 帧仅 3 帧 relays 非空); 回归 P1 15/15 + P2 4/4 + CDP 9 脚本 74/74
- [U17 AI 侧边栏助手 (阶段一)](issues/U17-AI侧边栏助手.md) — ①知识检索先行闭环
  (提交 d7d7c89): **MCP 端点实测非匿名** (OAuth 保护, public OAuth; Python mcp 库未装无需 —
  httpx 直调 streamable-HTTP + SSE 解析); token 自动发现链 (ai_config.json → Claude Code
  凭证, 用户已授权 kapa.ai); **意图分流统一对话入口** (非双 Tab): 纯知识 → 检索结果
  (8 条+官方链接); 含范围/包 → analyze 引导 (阶段二); 侧边栏 (右下角浮标, 任何页面) +
  单例+localStorage 多会话持久化 (刷新恢复) + 导入新包上下文提示 + 设置区 (key 仅存本地,
  不入 git/分发包); 修复 2 bug (load() 未调用 → 刷新不恢复; ai-system/ai-error class 选择器
  不匹配); CDP 14/14; ⚠️ 并发冲突 (并行会话 15c1709 卷入 app.css/恢复 AI 导航, 用户裁定
  本会话继续, 已合并); **阶段二 (08-26) 代码完成**: 检索质量优化 (标题精简/HTML
  清洗/Thread 排除/去重) + 范围解析 (时间窗/相对时间/短地址/PAN, 失败引导/追问继承)
  + 范围摘要 (统计+事件+检测精简) + LLM 兼容层 (Anthropic/OpenAI/DeepSeek 流式,
  key 本地配置) + 范围确认卡/SSE 流式/帧引用跳时间线 (tlJumpFrame); 验证: 范围
  解析/继承/no_key 兜底/检索清洗全通过; **真 LLM 流式待 key 实测 (诚实标注)**
- [S1 导入页稳定化](issues/S1-导入页稳定化.md) — 打包前稳定化第一站完成: **P1×2 清零**
  (子包下载 400 — 命名正则与 MMDD_HHMM 实际命名不匹配 / 精确时间输入分钟 vs 秒级边界被拒)
  + **P2 修 12 项** (P6 卡 fresh 缺失 / 密钥面板一次点击无效 / 空文件友好错误 / 拆分进度
  接线+顶栏残留 / 窗口闭区间丢末帧 / key 转义 / 路径穿越 / 端口硬编码 / 大包 5min 超时误报 /
  面板窗口保持 / **解密统计口径 109% 荒谬值** — total 改安全帧 41.7%);
  复验: CDP 群控真实整包 108324 帧 30→90% 进度 + 重启按钮 4/4 + 回归 zcl_fcf 12/12 +
  p1 15/15 + parser_verify 12/12 + p2 4/4 (快照刷新); 素材教训: **85MB 中继包物理帧 179 万**
  (U11 的 333s 基准是 76MB 网关包); 提交 da005f7/2e9c100/901f11a/1efbf52;
  **用户抽验 4/4 通过 (08-26)**: 大包拆分流程 / 重启按钮 / 小包导入 /
  **Ubiqua 拆产物复验 — U11 遗留项闭环**; **自审 (08-26 用户要求)**: 核实导航
  锁定真实存在 / 密钥"失败"实为测试数据 17 组 hex 非法 / 补 pollImport 30 分钟
  长兜底 / 补测 4 缺口 13/13 / **CSV 导入删除 (用户需求, 只留抓包)** —
  删 /import/files + /import/local + csv_reader.py + 前端 CSV tab (cbb6806)
- [S4 报文页稳定化](issues/S4-报文页稳定化.md) — 打包前稳定化 (用户指定跳过
  S2/S3 先做 S4): **P1×2 清零** (①事务链构建 O(n²) — 群控 10.8 万帧点详情卡死
  数分钟 → 索引化 (src,dst,tsn) 分组, 108324 帧详情 0.2s, 语义逐位一致
  ②cubx 详情 Security 层整层缺失 — fallback 顶层 vs timeline 查 nwk 内 → 双查)
  + P2×1 (详情标题帧号 vs 表格帧号不一致); 复验: CDP s4_verify 7/8 (路径列
  单独实测正常 '0xED6F→0x5694→0x0000') + 回归 3 套 + 群控详情 0.2s;
  **U16 遗留 2 部分闭环**: pcap MAC Ack 419 帧识别 ✓, pending=1 位待素材
  (诚实标注); 提交 e127191; 遗留优化项 (上行反转假设/RR 证据/pending=1) 待用户
  列出清单后处理; **用户抽验待确认**; **用户逐层核对补修 (08-26, cf562ba)**:
  poll/Ack 逐层对照 Ubiqua 发现 2 个 P1 — ①FCF 截断 (0x0003 vs 真实 0x8863,
  高位 security/ackreq/寻址模式全丢 → 存完整 mac_fcf) ②GP 帧命令误标
  ("Write Attributes" 实为 GP Proxy Commissioning Mode, 官方 SDK command-id.h
  依据 → zcl_defs 补 GP 表 + 前端 frame_type 守卫不猜) — 帧96 标题
  "ZCL GP Proxy Commissioning Mode" ✓, poll FCF 0x8863 ✓, 回归 3 套全过
- [T1 设备分析 CLI 工具](issues/T1-设备分析CLI工具.md) — **独立工具完成 (08-28)**, 目录
  `D:\ai_agent\zigbee_device_analyze\` (用户指定): device_analyze.py (argparse/目录批量/进度/
  --src/--json-only) + sync_deps.py (方案 D: 整文件复制 6 模块 + ast 函数级抽取 3 共享模块
  detail_shared/node_stats_shared/nodes_shared + 版本戳 + MANIFEST sha256 漂移检测);
  **原工程零改动** (用户强调, 曾试共享位置方案已完整回滚); 复用 = parse_cubx/_node_stats/
  _extract_nodes_from_packets/_detail_dict + U15 画像格式; 坑: 涂鸦 PAYLOAD_PARSERS 注册在
  files.py 顶部 → deps 模式需显式注册 (否则 0xEF00 静默走 fallback); 验证 6/6: dimmer 对账
  (U9/U15 实证逐项一致) + 中继 122 设备 (838D=AKLOCK-C6) + 批量 5 素材 + deps/src 逐字段 0 差异
  + MANIFEST 校验 + 与主工具 /nodes/export 逐字段 0 差异; CLI 目录 git 管理待用户确认
- [S3 拓扑页稳定化](issues/S3-拓扑页稳定化.md) — 打包前稳定化第 3 站 (用户指定
  下一站): **P1×5 清零** (①runLayout 固定列 nd ReferenceError — 布局二次切换
  崩溃, CDP 异常实测 ②link-history 端点缺 return — 恒 null → 前端 TypeError
  "加载失败"; 补契约 {aid,segments} 非裸数组 ③histAid=null → aid=null 422
  假象 "0 段链路证据" ④route 边 (U13 时刻游标) tooltip "#NaN 第NaN跳" ⑤路径行
  hover 高亮按 path_idx 匹配永不命中 — 改路径链匹配) + **P2×6** (死代码 8 函数
  清理 twin-size 已删 / trst 清 S.topoT0/T1 / 小网络按钮文本与实际布局不一致 /
  _all_link_segments PAN 过滤 (多 PAN 证据串网) / events 整体缓存 (O(full)×4,
  键=包数/PAN/t0/t1, 同窗 0.26→0.20s) / runLayout 缩放失效行删除);
  素材实证: 中继包 838D 链路历史 2 段 (poll 父 0x1885 + RR 路径) 与 U13 一致,
  U14 行为状态复现 (rejoining/offline/poll 0.245s); 提交 cc88866;
  回归 zcl_fcf 12/12 + p1 15/15 + p2 4/4 + parser_verify passed; CDP 12/12 (0 异常)
  **第二轮 绘制原理重构** (13d8b27): 四来源证据 (poll/assoc/rr/源路由下行) +
  30s 证据窗+顺延 + 节点在线协议判定 + 邻居边移除 + 全貌/时刻双模式
  **第三轮 用户驱动四方向** (7c3be22~e40ccf1, 30+ 提交): ①节点判定三连修
  (异 PAN 混入 78→10 / 协调器根 / 幽灵 478→117 / 成员 117→92 / 孤立节点回退)
  ②聚焦链路变化 (renderGraph 崩溃根因 + ghost 叠加 + 时间轴+切换点 + 指针
  坐标系统一) ③底部面板 (行点击聚焦/滑块指针/邻居不对称+色带) ④图区呈现
  (残影边实线化 — 静默≠离线 / 状态图标 / 填充色 / 图例补全 / 路径色板)
  ⑤交互体验 (单击高亮/双击聚焦 / 工具栏收纳 / 刻度条指针 / tgo 动态化);
  **版本号教训**: app.js topo.js import sed 多次失败卡旧版 → 必须 Edit 精确改,
  三处同步 (css?v/app.js?v/topo.js?v)

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
