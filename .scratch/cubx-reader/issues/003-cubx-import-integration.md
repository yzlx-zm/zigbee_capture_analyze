# 7c — .cubx 导入集成 + 端到端验证

**要构建的内容**：`api/files.py` 新增 `.cubx` 导入端点。支持文件上传和本地路径两种方式。导入时自动同步 .cubx 内嵌 key → zigbee_pc_keys。前端上传支持 `.cubx` 扩展名。

**阻塞于**：#7b

**需要硬件**：无

**验证方式**：
```bash
# 1. API 导入
curl -X POST http://127.0.0.1:8720/api/import/local-cubx \
  -F "path=C:/Users/Administrator/Desktop/test2-ubiqua-export.cubx"

# 2. 拓扑对比 (cubx导入 vs pcap导入)
# 导入 cubx → 拓扑页 → 节点数/路径数应该和 pcap 一致
# 导入 leave_question 的 cubx → 诊断页 → 同样的离网检测

# 3. 回归: pcap 导入不受影响
```

**状态**：ready

- [ ] `POST /api/import/cubx` — 文件上传 .cubx
- [ ] `POST /api/import/local-cubx` — 本地路径 .cubx
- [ ] 导入流程: cubx_reader.parse_cubx() → 替换 _packets/_nodes → 触发事件重建
- [ ] 前端 `accept=".pcap,.pcapng,.cubx"` 支持选择 .cubx
- [ ] test2.cubx 导入 → 拓扑页/诊断页与 pcap 一致
- [ ] leave_question *.cubx 导入 → 同样可用
