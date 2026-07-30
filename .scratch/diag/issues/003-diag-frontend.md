# 6c — 前端 #diag 页面 + 设备时间线卡片

**要构建的内容**：`frontend/index.html` 新增 `reg('diag', ...)` 页面。导航栏加 `诊断` 入口。卡片渲染：设备身份头 + 时间线事件列表 + 诊断结论。样式：离网红/重入蓝/正常灰/结论琥珀。

**阻塞于**：#6b

**需要硬件**：无

**验证方式**：
- 浏览器访问 `http://127.0.0.1:8720/#diag`
- 导入 leave_question_packet.pcap
- 确认看到 0xCBEB 的设备卡片
- 确认显示两波 Leave + 重入网尝试 + 诊断结论
- 导入 test2-export.pcap → 页面显示"未发现设备离网事件"

**状态**：ready

- [ ] `reg('diag', ...)` 新页面
- [ ] 导航栏添加 `诊断` 入口（`<a href="#diag">🩺 诊断</a>`）
- [ ] `GET /api/diag/offline` 调用 + 卡片渲染
- [ ] 摘要行：X 设备离网 / 被踢 Y / 主动 Z / 重入 W
- [ ] 卡片组件：header（地址+EUI+类型）/ timeline（事件列表+图标）/ conclusion（诊断结论）
- [ ] 样式：.diag-card, .diag-header, .diag-timeline, .diag-event, .diag-conclusion
- [ ] 空状态处理：无离网事件时显示"未发现设备离网事件"
