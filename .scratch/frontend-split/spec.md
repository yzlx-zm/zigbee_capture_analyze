# 前端模块化拆分 — 设计规范

> 来源：2026-07-31 /grilling 会话。不重新采访用户。

## 概述

- **目标**：将 1724 行单体 `index.html` 拆分为 ES 模块架构，消除全局变量竞态 bug 根源，解锁后续页面独立开发
- **在架构中的位置**：前端渲染层——见 PROJECT-KNOWLEDGE-GRAPH.md §3 数据管道架构，本节覆盖其最右端
- **参考**：CONTEXT.md §前端模块化 + §ES 模块架构

## 核心设计决策

| # | 决策 | 结论 | 来源 |
|---|------|------|------|
| 1 | 拆分策略 | 渐进式——先拆 topo（800行）+ state.js，其余页面后续 | grilling Q1 |
| 2 | 共享模块 | 单文件 state.js 集中管理（方案 A） | grilling Q2 |
| 3 | 模块系统 | ES 模块（`<script type="module">`），零构建工具 | grilling Q3 |
| 4 | 工具函数 | `sr/setProg/doPI/doI` 全进 state.js | grilling Q4 |

## 目标文件结构

```
frontend/
├── index.html          ← 壳 (~60行): #nb 导航 + #mc 容器 + <script type="module">
├── lib/cytoscape.min.js ← 不变 (全局 <script>, 非模块)
├── css/app.css          ← 从 <style> 迁出 (现有文件, 内容待核实)
├── js/
│   ├── state.js         ← 共享模块: S, A, sb, fmtTs, sr, setProg, doPI, doI, tsStart/End
│   ├── app.js           ← 路由引擎: reg(), rt(), 页面注册 (目前为占位, 后续各页面移入)
│   ├── topo.js          ← 拓扑页: reg('topo', ...) 完整回调体
│   ├── import.js        ← 后续 (CSV/pcap 导入页)
│   ├── timeline.js      ← 后续 (时间线页)
│   ├── nodes.js         ← 后续 (节点列表页)
│   └── diag.js          ← 后续 (诊断页)
```

### index.html 壳内容

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Zigbee 分析</title>
  <link rel="stylesheet" href="css/app.css">
  <style>/* 框架级 CSS 保留在此 (nav, card, btn, stats等) */</style>
</head>
<body>
  <nav id="nb">...</nav>           <!-- 保持不变 -->
  <div id="mc"></div>              <!-- 页面渲染目标 -->
  
  <script>/* 极小: S 初始空壳 + verify check + 状态栏 */</script>
  <script src="lib/cytoscape.min.js"></script>  <!-- 全局脚本 -->
  <script type="module" src="js/app.js"></script>
</body>
</html>
```

当前阶段 `app.js` 仅包含 `reg()`、`rt()`、`hashchange` 监听和 `reg('topo', ...)` 调用（委托给 topo.js 的默认导出）。后续各页面模块完成后，`app.js` 变为纯路由调度器。

### state.js export 边界

```js
// state.js — 共享模块 (所有页面 import 此模块)

// ── 全局状态 ──
export const S = {
  pkts:0, nodes:0, topo:null,
  topoPan:null, topoAddr:null, topoT0:null, topoT1:null,
  tlPan:'', tlNode:'', tlType:'', tlHasSearched:false,
  tlTs0H:'', tlTs0M:'', tlTs0S:'', tlTs1H:'', tlTs1M:'', tlTs1S:'',
  impTab:'csv', verifyPassed:null
};

// ── HTTP 工具 ──
export const A = {
  get: u => fetch(u).then(r => r.json()),
  post: (u, b) => fetch(u, {method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(b)}).then(r => r.json())
};

// ── 时间范围 (topo 滑块 + timeline 共用) ──
export let tsStart = 0, tsEnd = 0;

// ── 工具函数 ──
export function sb(m) { ... }          // 状态栏
export function fmtTs(ts) { ... }      // 时间戳→HH:MM:SS
export function sr(d, fname) { ... }   // 导入结果渲染
export function setProg(msg) { ... }   // 进度提示
export function doPI(files) { ... }    // pcap/cubx 上传
export function doI(file) { ... }      // CSV 上传
```

### topo.js 导入契约

```js
// topo.js — 拓扑页面模块
import { S, A, sb, fmtTs, tsStart, tsEnd, sr, setProg } from './state.js';

// topo 专属变量 (模块内私有, 不可被其他文件 import)
let cy = null, topoData = null, hlNode = null;
let tCenter = null, tSliderTO = null, curLayout = 0;
const PATH_COLORS = [...];

// topo 专属函数 (模块内私有)
function renderGraph(d) { ... }
function renderRoutePaths(d) { ... }
function renderSidebar(d) { ... }
function highlightNode(aid) { ... }
function runLayout() { ... }
function applyTimeFilter() { ... }
// ...

// 注册到路由
reg('topo', function() { ... });
```

关键约束：`cy`、`topoData`、`PATH_COLORS`、`renderGraph` 等 topo 专有符号**不出现在 `export` 中**——其他模块无法访问。只有通过 `state.js` 的 `import` 和路由跳转（`location.hash`）才能跨页面通信。

## 迁移步骤

### Step 1: 创建 state.js

从 index.html 提取所有共享变量和函数到 state.js，加 `export` 声明。在 index.html 通过 `<script type="module" src="js/app.js">` 间接加载（app.js `import` state.js）。

**验证**：在浏览器控制台输入 `import('./js/state.js').then(m=>console.log(Object.keys(m)))` ——应列出 9 个导出符号。

### Step 2: 创建 topo.js

从 index.html 提取 `reg('topo', ...)` 回调体（~800行）到 topo.js。topo 内 `cy` 等变量去全局化（`let cy=null` 代替隐式全局）。

**验证**：导入 pcap → 切到拓扑页 → 节点/边/路径正常渲染，时间滑块/布局切换/节点高亮/双击淡出全部正常。

### Step 3: 从 index.html 删除已迁移代码

删除 `<style>` 中迁到 app.css 的部分、删除 topo 的 `reg` 回调体、删除已迁到 state.js 的变量声明。保留导航栏、验证检查、`reg`/`rt`/路由引擎。

**验证**：全部 5 个页面（导入/拓扑/时间线/节点/诊断）正常。回归：导入+切页不丢、拓扑节点跳时间线、时间过滤、PAN 切换。

### Step 4: 清理

删除 index.html 中已无用的全局变量声明（原 `var S=...`、`var A=...`）。

## 验证策略

| 层级 | 方法 |
|------|------|
| 模块加载 | 浏览器 Network 面板：确认 state.js、app.js、topo.js 按序加载，无 404 |
| 功能回归 | 手动走 5 页面全部交互路径（导入→拓扑→时间线→节点→诊断） |
| 隔离验证 | 控制台 `import('./js/topo.js')` 查看导出——应为空对象（topo.js 不导出任何符号） |
| 缓存防护 | 开发期间 Disable cache (DevTools > Network > Disable cache)，发版前加版本查询参数 |

## 不包含的范围

- import.js / timeline.js / nodes.js / diag.js 的拆分（后续独立工单）
- app.css 内容核实和合并（独立工单——需对比 app.css 和 `<style>` 块内容）
- 前端自动化测试框架搭建
- 构建工具引入（已决策不使用）

## 关键文件

| 文件 | 角色 |
|------|------|
| `frontend/js/state.js` | 新：共享模块（9 个导出符号） |
| `frontend/js/app.js` | 新：路由引擎（`reg/rt/hashchange`） |
| `frontend/js/topo.js` | 新：拓扑页面模块（~800行，无默认导出） |
| `frontend/index.html` | 改：壳（1724→~120行） |
| `frontend/css/app.css` | 查：内容核实后迁移 `<style>` 中的页面通用样式 |
| `CONTEXT.md` | 已更新：ES 模块架构术语 |
| `.scratch/frontend-split/spec.md` | 本文件 |
