// app.js — 路由引擎 + 模块引导
// <script type="module" src="js/app.js"> 加载, 其他页面模块后续追加
import { S, A, sb, fmtTs, sr, setProg, doPI, doI } from './state.js?v=20260813k';  // 缓存破坏: 大包阈值 1MB

// ── Re-expose to window for backwards-compat with remaining inline reg() callbacks ──
// (逐步迁移各页面模块后删除)
window.S = S; window.A = A; window.sb = sb; window.fmtTs = fmtTs;
window.sr = sr; window.setProg = setProg; window.doPI = doPI; window.doI = doI;

// ── 页面模块静态导入 (确保所有 reg() 在 rt() 前完成) ──
import './topo.js?v=20260825i';  // 缓存破坏: 时区修复 (UTC→本地), 改版递增
import './import.js?v=20260813k';  // 缓存破坏: 大包阈值 30MB→1MB, 改版递增
import './timeline.js?v=20260824a';  // 缓存破坏: 详情 ZCL 属性展示, 改版递增
import './nodes.js?v=20260824a';  // 缓存破坏: 时区修复 + U9 重构, 改版递增
import './diag.js?v=20260812c';  // 缓存破坏: 浏览器对 ES module 缓存激进, 改版后递增

// ── 初始路由 ──
if (window.rt) window.rt();

// ── 状态栏初始化 (module 内执行, window.A 已暴露) ──
A.get('/api/import/status').then(function(s){if(s.total)sb(s.total+'包 | '+s.nodes+'节点')}).catch(function(){});

// ── 后端重启按钮 (U11 用户需求: 导入卡死时的网页可触重启) ──
var _sbRestart=document.getElementById('sb-restart');
if(_sbRestart){
  _sbRestart.addEventListener('click',function(){
    if(!confirm('重启后端? 约 3 秒后可用, 当前导入进度将丢失'))return;
    fetch('/api/system/restart',{method:'POST'}).then(function(r){return r.json();}).then(function(d){
      if(d&&d.ok){
        sb('⟳ 后端重启中...');
        var n=0;
        var t=setInterval(function(){
          n++;
          if(n>30){clearInterval(t);sb('❌ 重启超时, 请手动重启');return;}
          fetch('/api/import/status').then(function(){clearInterval(t);location.reload();})
            .catch(function(){sb('⟳ 重启中 ('+n*2+'s)...');});
        },2000);
      }else{
        sb('❌ '+(d&&d.error||'重启失败'));
      }
    }).catch(function(e){sb('❌ 网络错误: '+e.message);});
  });
}