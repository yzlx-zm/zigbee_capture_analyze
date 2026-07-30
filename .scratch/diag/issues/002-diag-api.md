# 6b — 诊断聚合逻辑 + /api/diag/offline

**要构建的内容**：`route_events.py` 新增 `aggregate_offline_diagnosis()`—— Leave burst 检测 + rejoin 推断 + 诊断结论生成。`api/topology.py`（或新建 `api/diag.py`）新增 `GET /api/diag/offline` 端点。

**阻塞于**：#6a

**需要硬件**：无

**验证方式**：
```bash
curl -s "http://127.0.0.1:8720/api/diag/offline" | python -c "
import sys, json
d = json.loads(sys.stdin.read())
assert len(d['devices']) == 1
dev = d['devices'][0]
assert dev['aid'] == 0xCBEB
assert len(dev['leave_bursts']) == 2
assert dev['diagnosis']['leave_type'] == 'kicked'
assert dev['diagnosis']['has_rejoin_attempt'] == True
print('PASS')
"
```

**状态**：ready

- [ ] `aggregate_offline_diagnosis(timeline, pan, t0, t1)` — burst 检测 + rejoin 推断
- [ ] Burst detection: 5 秒窗口合并同设备 Leave 帧
- [ ] Rejoin inference: Leave 后 30 秒内 Device Announce → rejoin_attempt
- [ ] 诊断结论生成: leave_type + has_rejoin + final_status + summary
- [ ] `GET /api/diag/offline` 端点
- [ ] 对 leave_question 验证: 1 设备, 2 bursts, kicked, has_rejoin
