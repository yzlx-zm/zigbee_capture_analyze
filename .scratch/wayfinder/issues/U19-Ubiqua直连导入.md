# U19 — Ubiqua 直连导入 (含可行性实验, 头脑风暴对齐产出)

**What to build:** 导入页新增"从 Ubiqua 直接导入当前抓包" — 免去手工导出 cubx + 找文件 +
拖入三步; 含未连接降级。

**Blocked by:** None (实验阶段需 Ubiqua 在运行) | **Status:** ready-for-agent

**Type:** task | **UI 反馈优化**

**来源**: 2026-09-18 头脑风暴 v3 (用户确认 G/H/I/J 四项; 工单组织 U18→U19(G)→U20(HIJ))。

## 背景与关键事实 (总控已查, 勿重复)

- **`backend/ubiqua_api.py` 是完整的 Ubiqua Remote Access 客户端** (localhost:19501):
  `ping` / `get_status` / `get_packet_count` / `get_packets` / **`save_capture(filepath)`**
  (Ubiqua 直接存为 cubx, 行 216) / `start_sniffer` / `stop_sniffer` / `list_keys` / `add_key`
- **前端完全未使用** (grep frontend/js 零命中); 后端仅 `_sync_ubiqua_keys` (导入时同步 Network Key) 在用
- `backend/api/ubiqua.py` 已有 status/connect/packets/sniffer 端点 (未被前端调用)
- **用户环境: Ubiqua 有时不在运行** → 必须有连接状态显示 + 未连接优雅降级 (不影响现有导入流程)

## 阶段一: 可行性实验 (必须先做, 出结论再定路线)

在真实 Ubiqua 上验证 (需用户配合启动 Ubiqua 并抓到包):

1. `ping` / `get_status` 返回 (sniffer 名/信道/包数)
2. **`save_capture(临时路径.cubx)` 是否可用** + 落盘文件能否被现有 `cubx_reader` 正常解析
   (帧数对账 / 是否含 MAC 帧 / LQI/RSSI / 内嵌 Keys 表)
3. 耗时: 10 万帧级抓包 save_capture 用时; 大包 (数百万帧) 是否可接受
4. `get_packet_count` 与实际包数是否一致 (进度预估用)
5. **顺带验证 `list_keys()` 返回是否带 key 类型** (Network/Link) — 供 U20-H 使用

**产出**: 实验结论 + 推荐路线 (写进本 ticket 记录)。

## 阶段二: 实现 (按实验结论)

### 路线 A (预期推荐): save_capture 导出临时 cubx → 现有解析链
- 工具调 `save_capture(<临时目录>/ubiqua_<时间戳>.cubx)` → 走现有 cubx 导入流程
  (**MAC 帧/LQI/RSSI/key/设备类型全都有**, 零解析风险; 复用大包拆分面板)
- 临时文件: 导入完成后清理 (或纳入现有暂存目录容量控制)

### 路线 B (备选): 直读 /capture XML (Raw/Decrypted hex)
- 少一次落盘, 但需重写解析路径且可能缺 MAC 帧/key — 除非实验证明 A 不可行, 否则不用

### 前端 (导入页)
- 加 `📡 从 Ubiqua 导入` 按钮 + 连接状态指示 (`已连接 · N 包` / `未连接`)
- 未连接/Ubiqua 未运行 → 按钮禁用或点击提示 "Ubiqua 未运行 (需启动 Ubiqua 并抓包)",
  **不影响拖拽/路径导入** (现有流程零改动)
- 未启动抓包 (0 包) → 提示 "Ubiqua 当前无抓包数据"
- 大包 → 接现有拆分面板 (预扫/选窗)
- 连接配置 (主机/端口) — 用户环境可能不同机, 提供可填写入口 (默认 localhost:19501)

## 验证标准

1. **实验结论成文** (阶段一 5 项全部有实测结果, 含文件对账)
2. Ubiqua 运行时: 点按钮 → 导入成功 → 帧数/节点与 Ubiqua 包数对账一致
3. Ubiqua 未运行: 按钮提示友好, 拖拽/路径导入不受影响 (回归)
4. 大包: 接拆分面板正常 (预扫/拆分)
5. 临时 cubx 文件不残留 (导入完成后清理; 或纳入暂存容量控制)
6. 回归: 现有 pcap/cubx 导入流程与 S1 修复项不受影响; 版本号递增

## 风险

- **实验可能失败** (Ubiqua Remote Access 未开启/版本差异) → 阶段一先出结论, 不做无效实现
- 用户环境 Ubiqua 常不在运行 → 功能是"锦上添花", 不能成为导入主路径
- save_capture 大包耗时未知 → 实验量化后再定是否提示/拆分
- 临时文件管理: 与现有 `_CUBX_STAGE_DIR` 暂存机制保持一致 (避免两套临时目录)
