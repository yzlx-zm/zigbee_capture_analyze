# Zigbee 分析工具 v2 — 设计文档

> 最后更新: 2026-07-20 确认最终范围

---

## 一、核心定位

**不做 Ubiqua 已有的事，只做 Ubiqua 做不好的事。**

| Ubiqua 负责 | 我们负责 |
|---|---|
| 抓包、解密、协议解析、包详情、基础拓扑图 | 拓扑深度分析、链路可靠性评分、节点统计 |

---

## 二、阶段1: CSV 驱动 (当前实现)

### 数据流
```
Ubiqua 打开抓包 → 加 Key 解密 → File → Export → CSV
→ 我们的工具导入 CSV → 拓扑分析 + 节点列表
```

### 输入: Ubiqua CSV
字段: Timestamp, Ch, Packet Type, PAN Src/Dst, MAC Src/Dst, MAC Seq, NWK Src/Dst, NWK Seq, Security, Status

### 核心功能

**1. 拓扑树 + 链路评分**
- BFS 树深度分布（协调器=0层，每层节点数）
- 叶子节点比例
- 邻居对通信成功率（Decrypted vs Encrypted vs Failed）
- Canvas 树形图: 缩放拖拽 + PAN过滤 + 地址高亮
- 节点颜色: 金=协调器 / 蓝=高活跃 / 灰=低活跃

**2. 节点列表**
- 可搜索表格（地址 + 出现次数 + 角色 + PAN）
- 点击节点 → 拓扑图中高亮

### 不包含（阶段2）
- 设备交互时间线
- tshark 全协议字段
- LQI 不对称矩阵
- AI 诊断

---

## 三、阶段2: tshark 升级 (预留)

```
pcap/cubx + key → tshark → JSON (全协议字段)
→ 替换 CSV 数据源
→ 新增: LQI矩阵 + 设备时序泳道 + AI诊断
```

待验证: tshark 解密能力 + Zigbee 字段完整度

---

## 四、前端页面

| 页面 | 内容 |
|---|---|
| 导入 | 拖拽 CSV, 自动解析 |
| 拓扑 | Canvas图 + PAN搜索 + 地址高亮 + 链路统计表 |
| 节点 | 可搜索表格 + 节点详情 |
| AI (预留) | 后续 |

---

## 五、里程碑

| 阶段 | 交付 | 状态 |
|---|---|---|
| M1 CSV解析 | CSV parser + 节点提取 + 统计 | → 开始 |
| M2 拓扑图 | BFS树 + 链路评分 + Canvas图 | |
| M3 节点列表 | 可搜索表格 + 详情联动 | |
| M4 tshark验证 | 解密+字段完整度评估 | 后续 |
| M5 全协议升级 | tshark全字段 + 时序 + LQI矩阵 | 后续 |
