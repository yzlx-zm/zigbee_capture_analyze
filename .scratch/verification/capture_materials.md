# 抓包素材台账 (Capture Materials Registry)

> 2026-08-03 建立 | 用途: L1/L2 场景检测的文档→测试→工具闭环素材库
> 素材主目录: `C:\Users\Administrator\Desktop\zigbee_capture\`

## 验证可用素材 (素材主目录 `验证可用-记录\` 子目录)

| 文件 | 大小 | 内容 | 验证状态 |
|------|------|------|----------|
| `验证可用-记录\1-标准入网抓包-2.cubx` | 90KB | 标准入网 (0x2951, 887包/37.6s/信道15) | ✅ L1-1/L1-2 v1.2 验证通过; L1-3 健康基线 (密钥流程 5 帧完整) |
| `验证可用-记录\1-标准入网抓包-2.pcap` | 40KB | 同素材 pcap 版 | ✅ L1-1/L1-2 pcap 路径验证; L1-3 tshark 权威解析确认 |

## 入网相关素材 (主目录)

| 文件 | 大小 | 内容 | 验证状态 |
|------|------|------|----------|
| `中继入网抓包(1).cubx` | 667KB | **入网后立即被踢** (用户观测) | ✅ L1-3 B2-LOOP-ROUTE (838D); **附加发现 2026-08-04: TC 同时踢 0x8A41/0xF67F (Mgmt Leave Req ×3 各, L1-4-R2b)** — 同素材多设备踢人活动 |
| `1-标准入网抓包.cubx` | 40KB | 标准入网第一版 | ❌ L1-1 拒绝 (无 BeaconReq); 有 Assoc+密钥流程可做命令 ID 解析验证 |
| `入网后又离网问题分析示例包.cubx` | 159KB | 入网后离网 | ⏳ 待分析 |
| `圆合中继C6添加和控制.cubx` | 610KB | 中继 C6 添加和控制 | ⏳ 待分析 |
| `07240934_26.cubx` 等 4 个大包 | 26-260MB | 批量抓包 | ⏳ 未分析 |

## 离网/Leave 素材 (主目录)

| 文件 | 大小 | 内容 | 验证状态 |
|------|------|------|----------|
| `leave_question_packet.pcap` | 90KB | Leave 问题包 (0xCBEB 路由器被踢: TC 发 Mgmt Leave Req ×12 → 广播 Leave ×6 rejoin=0) | ✅ **L1-4-R2b 高置信验证通过** (2026-08-04, tshark 复核: ZDO 踢人指令 0x0034 ×12 可见 + 广播 Leave ×6; 无 0x07) |
| `test3_cpature_leave.pcap` | 696KB | test3 leave 捕获 | ⏳ 早期问题素材 |
| `test2-ubiqua-export.cubx` | 1.3MB | test2 导出 (大量琥珀色终端节点问题) | ⏳ 早期问题素材 |
| `test2-ubiqua-export.pcap` / `test2-export.pcap` / `test3-ubiqua-export.pcap` | ~1MB | test2/test3 pcap 版 | ⏳ 早期问题素材 |

## 使用约定

- **判定规则成立即可**: 具体计数允许素材差异浮动 (用户决策, 2026-08-01)
- **cubx 优先**: 含 MAC 帧 (L1 检测完整); pcap 路径依赖 tshark `-o wpan.802154_fcs_ok:FALSE`
- Git Bash 中文路径会坏 → 用 glob/数字匹配绕开
