# #2 — derive_topology() + API 端点

**要构建的内容**：在 `RouteEventTimeline` 上实现 `derive_topology(pan, t0, t1)`——从事件流推导拓扑图，输出格式兼容现有 `topology.build()` 返回的 dict（nodes/edges/route_paths/neighbor_tables/etc）。在 `backend/api/topology.py` 新增 `GET /api/topology/events` 端点，接受 `pan`、`time_start`、`time_end` 参数。

**阻塞于**：#1

**需要硬件**：无

**验证方式**：
```bash
curl -s "http://127.0.0.1:8720/api/topology/graph?pan=feed" \
  | python -c "import sys,json; d=json.loads(sys.stdin.read()); print('old nodes:',len(d['nodes']),'edges:',len(d['edges']))"

curl -s "http://127.0.0.1:8720/api/topology/events?pan=feed" \
  | python -c "import sys,json; d=json.loads(sys.stdin.read()); print('new nodes:',len(d['nodes']),'edges:',len(d['edges']))"
# 节点数/边数应与旧端点一致
```

**状态**：ready

- [ ] `derive_topology()` — 事件→拓扑格式兼容
- [ ] 输出包含 nodes/edges/route_paths/neighbor_tables/pan_list/main_pan（与 topology.build() 对齐）
- [ ] `GET /api/topology/events` 端点
- [ ] 对 test2 FEED PAN + leave_question E45A PAN 验证新旧端点一致性
