# 场景体系全景调研 — 验证状态总表

> 产出: wayfinder ticket 00 (2026-08-04) | 依据: `docs/network_problems_taxonomy.md` v1.0 (2026-08-01)
> 状态列: ✅=文档+检测器+素材验证闭环 | 📝=有官方依据+拆解文档, 待素材 | ⬜=仅 taxonomy 条目, 未拆解

## 8 大类 55 场景 — 验证状态

### L1 网络形成与入网 (7)

| ID | 场景 | 状态 | 现有检测能力 |
|----|------|------|-------------|
| L1-1 | 信道/网络发现失败 | ✅ 闭环 | MAC BeaconReq/Beacon 提取 (v1.2) |
| L1-2 | Association 失败 | ✅ 闭环 | MAC AssocReq/Resp 提取 (v1.2) |
| L1-3 | 密钥分发失败 | ✅ 闭环 | APS 命令 ID + NWK 错误码 (v1.3, B2-LOOP-ROUTE) |
| L1-4 | TC 拒绝入网 | 📝 检测器就绪 (R2b 高置信验证通过) | Remove Device (0x07) / Mgmt Leave Req (0x0034) / 广播 Leave (rejoin=0) / 静默拒绝 (R1/R2a/R3 待素材) |
| L1-5 | 大网络多跳入网失败 | ⬜ | 需 Update Device + TC 地址解析检测 |
| L1-6 | 并发入网风暴 | ⬜ | 需 Assoc 并发计数 |
| L1-7 | 误入错误 PAN | ⬜ | 需 EPAN ID 对比 |

### L2 设备在线维持 (6)

| ID | 场景 | 状态 | 现有检测能力 |
|----|------|------|-------------|
| L2-1 | 终端设备频繁离线 | ⬜ | DataRequest 轮询 + Leave/Rejoin 检测 |
| L2-2 | 父节点 Child Table 老化 | ⬜ | poll 间隔统计 |
| L2-3 | Orphan/Rejoin 循环 | ⬜ | Rejoin Req 检测 + 0x09 错误码 |
| L2-4 | 路由器掉线→子设备连锁离线 | ⬜ | Leave (RemoveChildren) + Link Status 邻居消失 |
| L2-5 | 设备移动后失联 | ⬜ | MOVE_FAILED 0x0C06 |
| L2-6 | 设备静默失联 | 📝 部分 | Link Status 邻居表条目消失 (已有邻居表解析) |

### L3 运营期核心 (20)

| ID | 场景 | 状态 | 现有检测能力 |
|----|------|------|-------------|
| L3-1 | 发送命令无 APS Ack | ⬜ | APS counter/ack 匹配 |
| L3-2 | 命令送达未执行 | ⬜ | ZCL Default Response |
| L3-3 | 状态上报滞后 | ⬜ | Write→Report 间隔 |
| L3-4 | 绑定/组播未达 | ⬜ | Bind Response / MTORR |
| **L3-5** | **源路由/MTORR 失效** | 📝 **检测器就绪 (R1 素材验证通过)** | **Network Status 0x0B/0x0C 轮次判定 (R1 高置信验证: 838D 39 条 0x0B; R2/0x0C 待素材)** |
| L3-6 | 路由校验失败 | ⬜ | 0x0A + Route Req 频率 |
| L3-7 | 路由路径震荡 | ⬜ | Route Record relay 变化 |
| L3-8 | 目标不可达/地址未分配 | ⬜ | 0x07/0x08/0x0E/0x10 |
| L3-9 | 非对称链路 | ⬜ | Link Status in/out cost (已有解析) |
| L3-10 | 路由表溢出 | ⬜ | 0x04 |
| L3-11 | 应用层重传频繁 | ⬜ | APS counter ≥3 |
| L3-12 | 端到端延迟过大 | ⬜ | TS 差值 |
| L3-13 | 广播中继失败 | ⬜ | 0x0C28/0x0C27 |
| L3-14 | 消息队列满 | ⬜ | 0x0C03 |
| L3-15 | 路由表抖动 | ⬜ | 邻居表频繁增删 |
| L3-16 | TC Link Key 更新失败 | 📝 部分 | 已破解 VerifyKey 语义 (keyed_hash) — 检测器可延伸 |
| L3-17 | TC Swapout | ⬜ | 0x0C10/0x0C11 |
| L3-18 | 未知命令 | ⬜ | 0x13 |
| L3-19 | 低电量路由失败 | ⬜ | 0x03 |
| L3-20 | 密钥不同步/Rotation 失败 | ⬜ | 0x11/0x12 + seq 对比 |

### L4 网络级维护 (5) / L5 应用层 (4) / L6 SED 专项 (5) / L7 MAC (4) / L8 硬件 (3)

全部 ⬜ 未拆解 (taxonomy 条目仅定义 ID + 证据链摘要, 无 14 层拆解文档)

---

## 关键洞察

1. **已验证闭环仅 3/55** (L1-1/2/3) — 但**检测基础设施已覆盖大部分场景的证据提取**:
   MAC 命令帧 (L1 系列) / APS 命令 ID (L1-3, L3-16) / NWK 错误码 (L3 系列) / Link Status 邻居表 (L2-6, L3-9) / Route Record (L3-5/7)
2. **838D 案例揭示场景交叉**: L1-3 (密钥分发失败) 的表象, 根因是 **L3-5 (源路由失效)** —
   检测器已能同时报出 (B2-LOOP-ROUTE 关联 Network Status 0x0B)。**场景间需要交叉引用, 不是孤立判定**
3. **低挂果实** (现有能力可直接检测): L2-1/L2-3/L2-6 (轮询+Leave+邻居表), L3-5 (0x0B), L3-9 (cost 不对称), L3-16 (VerifyKey 语义已破解)
4. **L6 SED 专项** 与 838D 强相关 (SED 轮询 80 次拿不到 Confirm) — 值得优先

## 建议优先级 (参考, 最终由用户定)

1. **L3-5 源路由失效**: 已有真实素材 (838D) + 官方依据, 文档化成本最低
2. **L2-1 终端频繁离线**: 在线维持场景, 检测能力现成
3. **L6-S3 间接事务过期 / L6-S2 轮询超时**: SED 场景, 838D 同源
4. L1-4 TC 拒绝: 与 L1-3 混淆项已部分明确
