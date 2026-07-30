# 路由事件时间线 — 设计规范

> 来源：2026-07-30 /grilling 决策会话。不重新采访用户。

## 概述

- **模块名称**：`backend/route_events.py`
- **目标**：将 Zigbee 抓包中的路由相关协议帧提取为统一的事件时间线，从事件流推导拓扑，替代静态 snapshots
- **在架构中的位置**：并行于 `backend/topology.py`，共享 `backend/tshark.py` 输出；成熟后替代 topology.py
- **参考**：CONTEXT.md 领域词汇表；akubela-zigbee-analyser `_capture_probe.py` Event model

## 核心设计决策

| # | 决策 | 结论 | 来源 |
|---|------|------|------|
| 1 | 拓扑主干不是 LS 邻接，是 Route Record+Request 的多跳路由 | 方向分离的事件模型 | grilling Q1 |
| 2 | 数据模型 = 事件时间线，非静态快照 | topology=累积事件推导 | grilling Q2 |
| 3 | 事件框架先行，Route Record 验证，后续填充其他事件 | 渐进式 | grilling Q3 |
| 4 | 并行管道，不破坏现有 topology.py | 共存→替代 | grilling Q4 |

## 数据模型

### RouteEvent

```python
@dataclass
class RouteEvent:
    timestamp: float           # Unix 时间戳
    event_type: str            # "route_record" | "route_request" | "network_status"
    src: int                   # 源 NWK 短地址
    dst: int                   # 目标 NWK 短地址
    # Route Record 专属
    relays: list[int]          # 中继路径 (设备→协调器方向)
    # Route Request 专属
    radius: int | None         # 最大跳数
    dropped: bool              # 是否被中途丢弃
    dropped_at_hop: int | None # 在第几跳被丢弃 (src 到该 hop)
    # Network Status 专属
    status_code: int | None    # 失败原因码
    # 公共
    packet_id: int             # 帧号, 用于交叉引用
    pan: int | None            # PAN ID
```

### RouteEventTimeline

```python
class RouteEventTimeline:
    events: list[RouteEvent]   # 按 timestamp 排序
    def add(events: list[RouteEvent]) -> None
    def query(t0: float|None, t1: float|None, event_types: list[str]|None) -> list[RouteEvent]
    def derive_topology(pan: int|None, t0: float|None, t1: float|None) -> dict
```

`derive_topology()` 输出格式**兼容现有 `topology.build()` 返回 dict**，前端 `renderGraph()` 无需改动即可消费。

## 事件提取

### Phase 1：Route Record（实现）

从 `tshark._frame_to_dict()` 的 `route_record_relays` 字段提取：

```python
def extract_route_record_events(packets: list[dict]) -> list[RouteEvent]:
    for p in packets:
        if p.get("pkt_type") != "Route Record": continue
        yield RouteEvent(
            timestamp=p["ts"],
            event_type="route_record",
            src=p["nwk_src"],
            dst=p["nwk_dst"],
            relays=p["route_record_relays"]["relays"],  # 已由 -T fields 补充完整
            pan=p["pan_src"] or p["pan_dst"],
            packet_id=...   # from raw_layers or frame data
        )
```

数据来源已验证可用（tshark.py 已提取完整 relay_device 列表）。

### Phase 2-3：Route Request / Network Status（后续）

预留扩展点。`extract_events()` 按 event_type 分发到各自的 extractor，返回合并的 `list[RouteEvent]`。

## API 设计

| 端点 | 方法 | 参数 | 返回 |
|------|------|------|------|
| `/api/topology/events` | GET | `pan?`, `time_start?`, `time_end?` | 事件推导的拓扑（格式兼容 topology/graph） |

- 内部：`extract_events(packets)` → `RouteEventTimeline` → `derive_topology(pan, t0, t1)`
- 与现有 `/api/topology/graph` 共存，前端可逐步切换
- 事件时间线首次构建后缓存在内存（packets 不变时事件不变）

## 测试策略

| 层级 | 验证方式 |
|------|---------|
| 单元 | `extract_route_record_events()` 输入已知 packet dict → 验证输出的 RouteEvent 字段 |
| 集成 | 用 `test2-export.pcap` 全量运行，对比 `derive_topology()` 与现有 `topology.build()` 的节点数/边数一致性 |
| 回归 | 确保现有 topology/graph API 不受影响（并行管道） |

## 不包含的范围

- Route Request / Network Status 事件提取（Phase 2+3 后续工单）
- 前端改动（事件输出格式兼容现有 renderGraph）
- topology.py 删除（待新管道稳定后单独决策）
- .cubx 直读（正交，Path B 预留）

## 关键文件

| 文件 | 角色 |
|------|------|
| `backend/route_events.py` | 新模块：dataclass + Timeline + extract + derive |
| `backend/api/topology.py` | 新增 `/topology/events` 端点 |
| `backend/topology.py` | 不动，并行运行 |
| `CONTEXT.md` | 领域词汇表（已更新） |
| `.scratch/route-events/spec.md` | 本文件 |
