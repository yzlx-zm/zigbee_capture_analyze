// app.js — 路由引擎 + 模块引导
// <script type="module" src="js/app.js"> 加载, 其他页面模块后续追加
import { S, A, sb, fmtTs, sr, setProg, doPI, doI } from './state.js';

// ── Re-expose to window for backwards-compat with remaining inline reg() callbacks ──
// (逐步迁移各页面模块后删除)
window.S = S; window.A = A; window.sb = sb; window.fmtTs = fmtTs;
window.sr = sr; window.setProg = setProg; window.doPI = doPI; window.doI = doI;

// ── 页面模块导入 (后续工单逐步追加) ──
// import './topo.js';     // #2

// ── 初始路由 (reg/rt 已在 index.html inline; 此时模块已加载, window.S/A 就绪) ──
// 验证失败检查在 rt 函数内 (index.html), 此处 rt 会触发当前 hash 对应回调
if (window.rt) window.rt();