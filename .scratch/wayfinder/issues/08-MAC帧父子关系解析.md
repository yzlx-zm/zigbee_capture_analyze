# 08 — MAC 命令帧解析补齐 → 拓扑父子关系重建

**What to build:** cubx 解析器补 MAC 命令帧地址字段 + Beacon 归类; 基于 Assoc/轮询帧重建拓扑父子关系 (替代当前 traffic 启发式)。

**Blocked by:** None

**Status:** ready-for-agent

**背景 (2026-08-05 实验证据, 素材: 中继入网抓包(1).cubx, 5912 帧)**:
- 素材含完整入网证据: AssocReq 3 + AssocResp 14 + DataRequest(轮询) 154 + BeaconReq 32 + Beacon 1454
- `cubx_reader.py:373` 已提取 `mac_cmd_id` (1=AssocReq/2=AssocResp/4=DataReq/7=BeaconReq, 与 335 行注释一致)
- ❌ MAC 命令帧 `mac_src`/`mac_dst`/`mac_seq` 全为 None — 无法得知谁请求谁响应
- ⚠️ 1454 Beacon 帧 pkt_type='Unknown' (mac_frame_type=0 已识别未归类)
- ⚠️ cmd 0x09 ×83 帧语义未确认 (待查证, 不妄断)
- ⚠️ 本实验仅验证 cubx 路径; pcap/tshark 路径未验证

**What to do:**
- [ ] cubx_reader: MAC 命令帧头地址提取 (短/长地址, mac_src/mac_dst/mac_seq)
- [ ] Beacon 归类: mac_frame_type=0 → pkt_type='Beacon'
- [ ] 素材验证: AssocReq 源 ↔ AssocResp 源 ↔ 轮询目标 三点交叉恢复父子关系
- [ ] 协议语义: 0x09 命令查证 (Zigbee spec / MCP)
- [ ] pcap/tshark 路径 MAC 帧验证
- [ ] topology.build §4 父子启发式替换为协议证据 (设计决策)

**验证标准:** 在"中继入网抓包(1)"素材上, 恢复的父子关系与 traffic 启发式结果对比; 入网设备能找到其父节点 (AssocResp 源 = 轮询目标)

**Type:** task | **AFK**

**来源**: U7 会话的拓扑数据来源复盘 (2026-08-05, 见 U7-拓扑页优化.md Resolution)
