// app.js — 路由引擎 + 模块引导
// <script type="module" src="js/app.js"> 加载, 其他页面模块后续追加
import { S, A, sb, fmtTs, sr, setProg, doPI, doI } from './state.js';

// ── Re-expose to window for backwards-compat with remaining inline reg() callbacks ──
// (逐步迁移各页面模块后删除)
window.S = S; window.A = A; window.sb = sb; window.fmtTs = fmtTs;
window.sr = sr; window.setProg = setProg; window.doPI = doPI; window.doI = doI;

// ── 路由引擎 ──
window.R = {};
window.reg = function(n, h) { window.R[n] = h; };
window.rt = function() {
  var h = location.hash.slice(1) || 'import';
  document.querySelectorAll('.nt a').forEach(function(t) { t.classList.toggle('on', t.dataset.r === h); });
  if (S.verifyPassed === false) {
    document.querySelectorAll('.nt a[data-r="topo"],.nt a[data-r="tl"],.nt a[data-r="nodes"]').forEach(function(t) { t.style.opacity = '0.4'; t.title = '数据校验未通过'; });
  } else {
    document.querySelectorAll('.nt a').forEach(function(t) { t.style.opacity = ''; t.title = ''; });
  }
  if ((h === 'topo' || h === 'tl' || h === 'nodes') && S.verifyPassed === false) {
    document.getElementById('mc').innerHTML = '<div class="card" style="margin:16px"><h3>🚫 数据校验未通过</h3><p style="color:#dc2626;margin-top:8px">导入数据与 pcap 文件不匹配，拓扑和时间线页已锁定。</p><p style="margin-top:4px">请回到<a href="#import" style="color:#3b82f6">导入页</a>检查校验报告并重新导入。</p></div>';
    return;
  }
  document.getElementById('mc').innerHTML = ''; if (window.R[h]) window.R[h]();
};
window.addEventListener('hashchange', window.rt);

// ── 页面模块导入 (后续工单逐步追加) ──
// import './topo.js';     // #2
// import './import.js';   // 后续
// import './timeline.js'; // 后续
// import './nodes.js';    // 后续
// import './diag.js';     // 后续

// ── 初始路由 ──
window.rt();