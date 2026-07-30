# 6a — Leave + Device Announce 事件提取

**要构建的内容**：`route_events.py` 新增 `extract_leave_events()` 和 `extract_device_announce_events()`。`extract_events()` 包含新类型。

**阻塞于**：无——可立即开始

**需要硬件**：无

**验证方式**：
```bash
python -c "
from backend.route_events import extract_leave_events, extract_device_announce_events
from backend.tshark import parse_packets
pkts = parse_packets(['C:/Users/Administrator/Desktop/leave_question_packet.pcap'])
leaves = extract_leave_events(pkts)
anns = extract_device_announce_events(pkts)
assert len(leaves) == 6
assert len(anns) == 4
assert all(e.rejoin == False and e.request == False for e in leaves)
assert all(e.eui64 is not None for e in anns)
print('PASS')
"
```

**状态**：ready

- [ ] `RouteEvent` 新增字段: `rejoin`, `request`, `remove_children`, `eui64`
- [ ] `extract_leave_events()` — 从 NWK cmd 0x04 提取，含 rejoin/request/children 语义
- [ ] `extract_device_announce_events()` — 从 ZDP 0x0013 提取，含 EUI64
- [ ] `extract_events()` 包含新类型
- [ ] 对 leave_question 验证: 6 Leave + 4 Announce
