# 2 — topo.js 拓扑模块提取

**要构建的内容**：从 index.html 提取 reg('topo') 回调体（~800行）到 `js/topo.js`。所有 topo 专有变量（cy/topoData/hlNode/tCenter/PATH_COLORS 等）改为模块内 `let/const`，不 export。topo.js 从 state.js import 所需符号（S/A/sb/fmtTs/tsStart/tsEnd）。

**阻塞于**：#1

**验证方式**：拓扑页全部功能正常——
- Cytoscape 图渲染（列图/力导切换）
- 路由路径面板（上行/探测/失败三区）
- 邻居面板 (neighbor_tables)
- 不对称链路面板
- 时间滑块 + 步进按钮 + 窗口大小
- 节点点击跳时间线
- 双击高亮/淡出
- PAN 列表切换
- 侧边栏统计

**状态**：ready

- [ ] `js/topo.js` — reg('topo') 回调 + 所有 topo 函数/变量
- [ ] topo 专有变量全部模块内 `let/const`（不污染全局）
- [ ] import { S, A, sb, fmtTs, tsStart, tsEnd } from './state.js'
- [ ] index.html 中删除原 reg('topo') 回调体
