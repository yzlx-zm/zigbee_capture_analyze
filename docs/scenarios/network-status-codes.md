# Network Status 命令错误码全表 (0x00-0x13)

> 建立: 2026-08-05 | 依据: stack-info.h 官方枚举 + message.h 语义 + Zigbee 规范
> ⚠️ 诚实标注: ✅=官方文档展开确认; 📝=枚举名确认但详细语义待 Zigbee 规范核实; ❓=有疑问待确认
> Network Status 帧结构: [src=生成者][dst=通知对象][code(1)][dest_addr(2)] — **dst 与 dest 组合决定语义**

## 路由错误类 (0x00-0x0F, ROUTE_ERROR_*)

| 码 | 名称 | 官方语义 | 方向 | 典型场景 | 检测建议 | 状态 |
|----|------|---------|------|---------|---------|------|
| 0x00 | NO_ROUTE_AVAILABLE | 无可用路由 (路由表无条目) | 双向 | 路由表缺失/未建立; 可作为断链通知码 (可配置) | 持续出现 → 路由建立问题 | 📝 |
| 0x01 | TREE_LINK_FAILURE | 树链路失败 (Zigbee 2006 树路由) | 下行 | Zigbee PRO 基本不用 (非树路由为主) | 罕见, 出现即异常 | 📝 |
| 0x02 | NON_TREE_LINK_FAILURE | 非树链路失败 (表路由) | 双向 | 路由表条目指向的链路断; 可作为断链通知码 (可配置) | 与 0x00 同族 | 📝 |
| 0x03 | LOW_BATTERY_LEVEL | 低电量 (路由节点电量低无法转发?) | — | 电池供电路由/终端 | 结合设备类型判断 | 📝 |
| 0x04 | NO_ROUTING_CAPACITY | 无路由容量 (路由表满) | — | 大网络路由表溢出 | 网络规模问题 | 📝 |
| 0x05 | NO_INDIRECT_CAPACITY | 无间接容量 (间接队列满) | 下行 | 父节点间接队列满, 无法缓存 SED 消息 | **SED 场景 (L6-S3 相关)** | 📝 |
| 0x06 | INDIRECT_TRANSACTION_EXPIRY | 间接事务过期: "message sent to the target end device could not be delivered by the parent because the indirect transaction timer expired" | 下行 | **父节点缓存消息过期** (SED 未及时 poll 取走); 收到后栈会为目标设置 extended timeout | **SED 场景核心 (G32 ×38 实证)** | ✅ |
| 0x07 | TARGET_DEVICE_UNAVAILABLE | 目标设备不可用 | 下行 | 目标已离网/不可达 | L3-8 相关 | 📝 |
| 0x08 | TARGET_ADDRESS_UNALLOCATED | 目标地址未分配 | 下行 | 目标短地址未分配 (设备离开后地址失效) | 与 0x07 区分 | 📝 |
| 0x09 | PARENT_LINK_FAILURE | 父链路失败 | 上行 | 设备到父节点链路断 | L2 系列相关 | 📝 |
| 0x0A | VALIDATE_ROUTE | 校验路由 (路由发现流程) | — | 路由校验阶段 | 与 L3-6 相关 | ❓ |
| 0x0B | SOURCE_ROUTE_FAILURE | "source-routed unicast **sent from this node** failed en route"; 仅 concentrator 模式; 断链前一跳生成沿 MTORR 回传 | **下行** | concentrator 源路由下发失败 (DA13 系列/838D 实证) | **L3-5-R1** | ✅ |
| 0x0C | MANY_TO_ONE_ROUTE_FAILURE | "unicast **sent to the local device** along MTORR failed"; 仅 concentrator 模式; 断链前一跳经随机邻居转发 | **上行为主** (dest 决定) | 设备 MTORR 上报失败 (G32 实证, dest 细分方向) | **L3-5-R2** | ✅ |
| 0x0D | ADDRESS_CONFLICT | 地址冲突 (两设备同短地址) | — | 重入网/地址复用冲突 | 网络地址管理问题 | 📝 |
| 0x0E | VERIFY_ADDRESSES | 验证地址 (冲突检测流程) | — | 地址冲突检测的确认流程 | 与 0x0D 同流程 | ❓ |
| 0x0F | PAN_IDENTIFIER_UPDATE | PAN ID 更新 (PAN 冲突解决) | — | 协调器 PAN ID 冲突更换 | 罕见 | 📝 |

## 网络状态通知类 (0x10-0x13, ZIGBEE_NETWORK_STATUS_*)

> ⚠️ **不是路由错误**! 通过 network status handler 而非 route error handler 处理

| 码 | 名称 | 语义 | 场景 | 状态 |
|----|------|------|------|------|
| 0x10 | NETWORK_ADDRESS_UPDATE | 网络地址更新通知 | 设备短地址变更 | 📝 |
| 0x11 | BAD_FRAME_COUNTER | 帧计数器错误 (重放/计数器失步) | 密钥/计数器问题 (L3-20 相关) | 📝 |
| 0x12 | BAD_KEY_SEQUENCE_NUMBER | 密钥序列号错误 (密钥轮换不同步) | **L3-20 密钥 Rotation 失败** | 📝 |
| 0x13 | UNKNOWN_COMMAND | 未知命令 (收到不认识的 NWK 命令) | 协议版本/实现不兼容 | 📝 |

## 关键官方细节 (MCP 确认)

1. **断链通知码可配置且仅两个**: `emberSetBrokenRouteErrorCode` 只允许 0x00 或 0x02 —
   路由器通知发起方断链时用这两个之一 → 0x01/0x0B/0x0C 等由栈内部生成
2. **0x06 附带行为**: 收到后栈为目标设备在地址表设置 extended timeout
3. **3 连发 = 预期**: APS retry 每次失败生成一条 route error → 单轮 3 条是正常
4. **不保证送达**: route error 可能丢失, 0x0B/0x0C 缺失 ≠ 无失败

## 检测器现状与缺口

| 码 | 检测器覆盖 | 状态 |
|----|-----------|------|
| 0x0B/0x0C | L3-5 R1/R2 (轮次判定) | ✅ 闭环 |
| 0x06 | 无专门规则 (G32 素材实证出现) | 📝 观察项 → L6-S3 候选 |
| 0x00-0x05/0x07-0x0A/0x0D-0x0F | 无 | 📝 需全码统计输出 |
| 0x10-0x13 | 无 | 📝 需全码统计输出 (非路由错误, 分类标注) |

**增强计划**: 检测器输出全码统计 (network_status_codes: {code: count}), 诊断页显示分布,
异常码 (≥阈值) 单独提示; 专门规则按素材出现顺序补。

## 素材已观测到的码

- 0x0B: 838D + DA13 系列 (7 包实证)
- 0x0C: G32 ×216 + FEED ×16
- 0x06: G32 ×38
- 其他 17 码: **现有素材 0 条** — 后续素材出现时按本表对照分析

## 待核实疑问 (审慎声明)

1. ❓ 0x0A VALIDATE_ROUTE 的精确触发条件 (路由校验流程何时发)
2. ❓ 0x0E VERIFY_ADDRESSES 与 0x0D 的流程关系
3. ❓ 0x10-0x13 的帧格式是否与路由错误相同 (dst 字段语义)
4. ❓ 0x03 LOW_BATTERY 的生成者与条件 (规范原文)
5. ❓ 0x05 NO_INDIRECT_CAPACITY 与 0x06 的触发顺序 (间接队列满 vs 过期)
