// app.js — 路由引擎 + 模块引导
// <script type="module" src="js/app.js"> 加载, 其他页面模块后续追加
// ⚠️ 2026-08-25 修复: state.js 不得带版本号 — 曾 ?v=20260813k 导致浏览器把
// './state.js?v=...' 与 './state.js' 当两个模块 → 双 S 实例 (window.S 与页面模块
// S 不同步, topoT0/topoAddr 等跨模块状态全部失效 — 滑块/聚焦状态不同步根源)
import { S, A, sb, fmtTs, sr, setProg, doPI } from './state.js';

// ── Re-expose to window for backwards-compat with remaining inline reg() callbacks ──
// (逐步迁移各页面模块后删除)
window.S = S; window.A = A; window.sb = sb; window.fmtTs = fmtTs;
window.sr = sr; window.setProg = setProg; window.doPI = doPI;

// ── 页面模块静态导入 (确保所有 reg() 在 rt() 前完成) ──
import './topo.js?v=20260828o';  // S3: 底部面板增强 (路径行点击聚焦/链路历史指针/邻居不对称+色带), 改版递增
import './import.js?v=20260827a';  // S1: CSV 导入删除 (只留抓包), 改版递增
import './timeline.js?v=20260827e';  // S4: Security 层修复 + 详情帧号, 改版递增
import './nodes.js?v=20260824a';  // 缓存破坏: 时区修复 + U9 重构, 改版递增
import './diag.js?v=20260825a';  // 缓存破坏: 报文改名 (设备跳转), 改版递增
import './ai.js?v=20260827a';  // U17: resize 手柄移到头部加减号中间, 改版递增

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