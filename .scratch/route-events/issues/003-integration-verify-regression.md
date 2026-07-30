# #3 — 并行管道集成验证 + 回归守卫

**要构建的内容**：纯验证工单。用 test2-export.pcap + leave_question_packet.pcap 做全量端到端验证，确认：#2 的事件管道输出与现有 topology.py 管道输出一致；现有 `/api/topology/graph` API 不受影响；前端拓扑页在两个数据源下渲染正常。

**阻塞于**：#2

**需要硬件**：无

**验证方式**：
```bash
# 1. 回归检查：旧端点不受影响
curl -s "http://127.0.0.1:8720/api/topology/graph?pan=e45a" | python -c "
import sys,json; d=json.loads(sys.stdin.read())
assert len(d['nodes'])==3, f'regression: expected 3 nodes, got {len(d[\"nodes\"])}'
print('PASS regression: existing API unchanged')
"

# 2. 一致性：新旧端点对同一 PAN 输出一致
curl -s "http://127.0.0.1:8720/api/topology/graph?pan=feed" > /tmp/old.json
curl -s "http://127.0.0.1:8720/api/topology/events?pan=feed" > /tmp/new.json
python -c "
import json
old=json.load(open('/tmp/old.json'))
new=json.load(open('/tmp/new.json'))
assert len(old['nodes'])==len(new['nodes']), f'node count mismatch: {len(old[\"nodes\"])} vs {len(new[\"nodes\"])}'
assert len(old['route_paths'])==len(new['route_paths']), f'path count mismatch'
print('PASS consistency: old and new pipelines match')
"
```

**状态**：ready

- [ ] test2 FEED PAN 新旧端点节点数/边数/路径数一致
- [ ] leave_question E45A PAN 结果一致
- [ ] 现有拓扑页正常加载（旧端点无回归）
- [ ] 修复本轮发现的格式对齐差异（如有）
