# 诊断面板 — 设计规范

> 来源：2026-07-30 /grilling 会话。不重新采访用户。

## 概述

- **模块名称**：诊断面板（Diagnostic Panel）
- **目标**：提供协议数据驱动的网络问题诊断，首场景为"设备离线分析"
- **在架构中的位置**：独立于拓扑分析（`route_events.py`），复用事件提取基础设施
- **参考**：CONTEXT.md §诊断分析；akubela-zigbee-analyser Report findings

## 核心设计决策

| # | 决策 | 结论 | 来源 |
|---|------|------|------|
| 1 | 放置位置 | 新页面 `#diag`，独立于 topo/timeline | grilling Q1 |
| 2 | 展示模型 | 按设备的 timeline 卡片 | grilling Q2 |
| 3 | 首场景 | Leave 离网分析（Announce/Addr Req 后续） | grilling Q3 |
| 4 | 数据聚合 | 后端预聚合诊断数据，前端只渲染 | 实现决策（用户委托） |
| 5 | 扩展性 | 每个诊断场景独立区域，互不干扰 | grilling 隐含 |

## 数据模型

### 后端：Leave 事件提取

`route_events.py` 新增：
- `EVENT_LEAVE`, `EVENT_DEVICE_ANNOUNCE` 事件类型常量
- `RouteEvent` 新增字段：`rejoin: bool`, `request: bool`, `remove_children: bool`, `eui64: int | None`
- `extract_leave_events(packets) -> list[RouteEvent]`
- `extract_device_announce_events(packets) -> list[RouteEvent]`
- `extract_events()` 输出包含新类型

### API：诊断端点

```
GET /api/diag/offline?pan=&time_start=&time_end=
```

**请求**：PAN 和时间窗口过滤（可选）

**响应**：
```json
{
  "devices": [{
    "aid": 52171,
    "label": "0xCBEB",
    "eui64": "70c59cfffe72a5cd",
    "device_type": "router",
    "leave_bursts": [{
      "first_ts": 1785138794.0,
      "last_ts": 1785138794.0,
      "count": 3,
      "rejoin": 0,
      "request": 0,
      "children": 0,
      "type": "kicked",
      "burst_index": 1
    }],
    "rejoin_attempts": [{
      "after_burst": 1,
      "announce_count": 4,
      "first_ts": 1785138799.0,
      "last_ts": 1785138799.0,
      "delay_seconds": 5.2
    }],
    "pre_events": {
      "network_status_count": 3,
      "first_ts": 1785138793.0
    },
    "diagnosis": {
      "leave_type": "kicked",
      "has_rejoin_attempt": true,
      "final_status": "departed_permanently",
      "burst_count": 2,
      "summary": "被踢出网络, 有重入网尝试(5.2s后), 最终在14.1s后再次被踢并彻底离开"
    }
  }],
  "summary": {
    "total_devices_left": 1,
    "kicked": 1,
    "voluntary": 0,
    "with_rejoin": 1
  }
}
```

### 后端：诊断聚合逻辑

`route_events.py` 新增 `aggregate_offline_diagnosis()`：
1. 从事件时间线提取所有 Leave + Device Announce 事件
2. 按设备分组
3. Leave burst 检测（5 秒窗口）
4. Leave 后 30 秒内 Device Announce → rejoin_attempt
5. 诊断推断：leave_type + has_rejoin + final_status + summary

## 前端设计

### 路由

- Hash `#diag`，导航栏添加入口 `诊断`
- 页面结构（index.html `reg('diag', ...)`）：
  - 顶部：总览摘要（X 台设备离网，被踢 Y 台，主动 Z 台，重入网 W 台）
  - 主体：按设备的 timeline 卡片堆叠

### 卡片组件（纯 HTML/CSS/JS，无框架）

每张卡片 = 设备身份区 + 时间线区 + 诊断结论区：

```html
<div class="diag-card">
  <div class="diag-header">0xCBEB  70:c5:9c:ff:fe:72:a5:cd  <badge>路由器</badge></div>
  <div class="diag-timeline">
    <!-- 每行一个事件, 用 icon 区分类型 -->
    <div class="diag-event">▸ 正常通信 (Link Status, Route Record, Data)</div>
    <div class="diag-event warn">⚠ Network Status ×3</div>
    <div class="diag-event leave">✕ 第一波 Leave ×3  [被踢]</div>
    <div class="diag-event announce">📢 Device Announce ×4  ← 重入网尝试</div>
    <div class="diag-event leave">✕ 第二波 Leave ×3  [被踢, 彻底离开]</div>
  </div>
  <div class="diag-conclusion">诊断: 被踢出网络, 有重入网尝试, 最终彻底离网</div>
</div>
```

### 样式要点

- 离网事件：红色系（#ef4444）
- 重入网尝试：蓝色系（#3b82f6）
- 正常通信/背景事件：灰色系（#94a3b8）
- 诊断结论：琥珀色背景卡片（#fffbeb）

## 实施范围

| 工单 | 内容 | 阻塞 |
|------|------|------|
| Phase 6a | Leave + Device Announce 事件提取 | 无 |
| Phase 6b | 诊断聚合逻辑 + /api/diag/offline | Phase 6a |
| Phase 6c | 前端 #diag 页面 + 卡片渲染 | Phase 6b |

## 关键文件

| 文件 | 角色 |
|------|------|
| `backend/route_events.py` | 新增 Leave/Announce 提取 + 诊断聚合 |
| `backend/api/topology.py` | 新增 `/diag/offline` 端点（或新建 `api/diag.py`） |
| `frontend/index.html` | `reg('diag', ...)` 页面 + 导航 + 卡片样式 |
| `CONTEXT.md` | 诊断术语（已更新） |
| `.scratch/diag/spec.md` | 本文件 |
