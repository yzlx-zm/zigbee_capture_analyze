// app.js — 路由引擎 + 模块引导
// <script type="module" src="js/app.js"> 加载, 其他页面模块后续追加
import { S, A, sb, fmtTs, sr, setProg, doPI, doI } from './state.js';

// ── Re-expose to window for backwards-compat with remaining inline reg() callbacks ──
// (逐步迁移各页面模块后删除)
window.S = S; window.A = A; window.sb = sb; window.fmtTs = fmtTs;
window.sr = sr; window.setProg = setProg; window.doPI = doPI; window.doI = doI;

// ── 页面模块静态导入 (确保所有 reg() 在 rt() 前完成) ──
import './topo.js';
import './import.js';
import './timeline.js';
import './nodes.js';
import './diag.js?v=20260805';  // 缓存破坏: 浏览器对 ES module 缓存激进, 改版后递增

// ── 初始路由 ──
if (window.rt) window.rt();

// ── 状态栏初始化 (module 内执行, window.A 已暴露) ──
A.get('/api/import/status').then(function(s){if(s.total)sb(s.total+'包 | '+s.nodes+'节点')}).catch(function(){});