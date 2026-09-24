// U22: 节点时刻态证据标记验证 (素材: 中继入网 = 有 leave/announce)
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(800); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
console.log('加载:', JSON.stringify(st));
// 取后端事件 (供测试算期望)
const api = await p.ev(`fetch('/api/topology/events').then(r=>r.json()).then(d=>({t0:null,t1:null,
  ev:(function(){var o={};d.nodes.forEach(function(n){o[n.aid]={ev:n.node_events||[],gaps:n.ev_gaps||[]};});return o;})()}))`);
const edges = await p.ev(`(function(){var c=window.__cy,d=c.edges(),o=[];
  c.edges().forEach(function(e){if(e.data('edge_type')==='parent')o.push([e.data('source'),e.data('target')]);});
  return o.length;})()`);
const st1 = await p.ev(`(function(){var c=window.__cy,o={};
  c.nodes().forEach(function(n){if(n.data('is_badge'))return;o[n.data('aid')]={mv:n.data('mv'),
    cls:n.classes().join(' '),lbl:String(n.data('label')).split(String.fromCharCode(10)).join('|')};});
  return o;})()`);
const at0 = Object.entries(st1).map(([a,v])=>'0x'+(+a).toString(16).toUpperCase()+':'+v.mv).join(' ');
console.log('初始游标状态:', at0);
// 找一个"已离网"事件 (leave rejoin=0) 并把游标拖到事件后
let target=null;
for (const [aid,v] of Object.entries(api.ev)) {
  const lv=(v.ev||[]).filter(e=>e.type==='leave'&&!e.rejoin);
  if(lv.length && +aid!==0) { target={aid:+aid, ts:lv[lv.length-1].ts}; break; }
}
if(!target){ console.log('⚠️ 本素材无 leave(rejoin=0) → 跳过离网断言'); }
else{
  const sl = await p.ev(`(function(){
    var st=window.S; /* 用滑块反推: 二分找到时间 >= ${target.ts} */
    var el=document.getElementById('tsl');
    // tsStart/tsEnd 不可见 → 用页面已有的 sliderToTs? 不可见; 改为直接用 window.onTimeSlide + 扫值
    return 1;})()`);
  // 扫滑块值, 找第一个使该节点 mv==='left' 的位置
  let found=null;
  for (const v of [0,100,200,300,400,500,600,700,800,900,1000]) {
    await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`);
    await sleep(500);
    const mv = await p.ev(`(function(){var n=window.__cy.getElementById('${target.aid}');
      return n.nonempty()?{mv:n.data('mv'),cls:n.classes().join(' '),lbl:n.data('label')}:null;})()`);
    if (mv && mv.mv==='left') { found={v, mv}; break; }
  }
  console.log('目标 0x'+(target.aid).toString(16).toUpperCase()+' (leave@'+target.ts+') →', JSON.stringify(found));
  check('离网节点在事件后标记为 left (⛻)', !!(found&&found.mv&&found.mv.mv==='left'), JSON.stringify(found));
  check('离网节点带 offline 样式类', !!(found&&/offline/.test(found.mv.cls||'')), found?found.mv.cls:'');
  check('标签含 ⛻ 图标', !!(found&&/⛻/.test(String(found.mv.lbl||''))), found?String(found.mv.lbl):'');
}
// 找一段"无证据区间"内 → nogap
let g2=null;
for (const [aid,v] of Object.entries(api.ev)) {
  if (+aid===0) continue;
  // 跳过"有离网事件"的节点 (事件优先级高于缺口 — 那种应显示 ⛻ 而非 ⏳)
  if ((v.ev||[]).some(e=>e.type==='leave'&&!e.rejoin)) continue;
  const gs=(v.gaps||[]).filter(g=>g.t1-g.t0>=120);
  if (gs.length) { g2={aid:+aid, t0:gs[0].t0, t1:gs[0].t1}; break; }
}
if(g2){
  let found=null;
  for (const v of [0,100,200,300,400,500,600,700,800,900,1000]) {
    await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`);
    await sleep(400);
    const mv=await p.ev(`(function(){var n=window.__cy.getElementById('${g2.aid}');return n.nonempty()?n.data('mv'):null;})()`);
    if(mv==='nogap'){found={v,mv};break;}
  }
  console.log('无证据区间节点 0x'+(g2.aid).toString(16).toUpperCase()+' →', JSON.stringify(found));
  check('落入证据缺口 → nogap (⏳)', !!(found&&found.mv==='nogap'), JSON.stringify(found));
}
const ex=p.exceptions.length; check('无 JS 异常', ex===0, String(ex));
await p.shot('u22_moment_state.jpg');
const ok=summary(); await p.close(); process.exit(ok?0:1);
