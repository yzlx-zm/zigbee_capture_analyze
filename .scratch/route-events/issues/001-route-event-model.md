# #1 — RouteEvent 核心数据模型 + Route Record 提取

**要构建的内容**：新建 `backend/route_events.py`，定义 `RouteEvent` dataclass 和 `RouteEventTimeline` 存储/查询类。实现 `extract_route_record_events()`——从 tshark 已解析的 `route_record_relays` 字段提取 Route Record 事件，写入时间线。

**阻塞于**：无——可立即开始

**需要硬件**：无

**验证方式**：
```bash
python -c "
from backend.route_events import extract_route_record_events, RouteEventTimeline
from backend.tshark import parse_packets
pkts = parse_packets(['C:/Users/Administrator/Desktop/test2-export.pcap'])
events = extract_route_record_events(pkts)
tl = RouteEventTimeline()
tl.add(events)
assert len(events) == 109, f'Expected 109 Route Record events, got {len(events)}'
# verify relay lists are non-empty
for e in events:
    assert len(e.relays) >= 2, f'Event {e.packet_id} has empty relay list'
    assert e.event_type == 'route_record'
print(f'PASS: {len(events)} Route Record events extracted')
"
```

**状态**：ready

- [ ] `RouteEvent` dataclass（含 relay 链完整性校验）
- [ ] `RouteEventTimeline`（排序存储 + `query(t0, t1, types)`）
- [ ] `extract_route_record_events()`（从 packet dict 提取）
- [ ] 对 test2-export.pcap 运行，assert 109 条 Route Record 事件
