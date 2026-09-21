// U21-1: 放射布局基础验证 (当前素材 = 32 中继压测: 33 router + 1 coordinator 星形)
// 断言: 分环正确 / 树边零交叉 / 标签不重叠 / 时刻游标不跳 / 布局三档可切换
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';

const p = await openTab('http://localhost:8720/#topo');
await sleep(9000);

// ── 1. 基本加载 ──
const st = await p.ev(P.state);
check('页面加载 + cy 实例可访问', st && !st.err && st.nodes > 0, JSON.stringify(st));
check('默认布局 = 放射', st && st.layout === '0', 'select=' + (st && st.layout));
const ex0 = p.exceptions.length;
check('初始渲染无异常', ex0 === 0, '异常 ' + ex0 + (ex0 ? ': ' + p.exceptions[0].slice(0, 120) : ''));

// ── 2. 放射几何断言 ──
const geo = await p.ev(`(function(){
  var c=window.__cy, ns=c.nodes().filter(function(n){return !n.data('is_badge');});
  var par={}, byId={};
  ns.forEach(function(n){var d=n.data();byId[d.aid]=d.link_parent;});
  // 深度 = 父链长度 (与实现同源: 数据字段)
  function dep(a,g){var d=0,cur=a,guard=0;while(cur!=null&&guard++<30){var pp=byId[cur];if(pp==null||pp===cur)break;cur=pp;d++;}return d;}
  var rows=[], rings={};
  ns.forEach(function(n){var a=n.data('aid');var p=n.position();
    var R=Math.round(Math.hypot(p.x,p.y)), d=dep(a);
    rows.push({aid:a,dep:d,R:R});
    (rings[d]=rings[d]||[]).push(R);});
  // 环半径一致性: 同深度半径必须相同
  var ringBad=[], ringR={};
  for(var k in rings){var arr=rings[k], mn=Math.min.apply(null,arr), mx=Math.max.apply(null,arr);
    ringR[k]=mn; if(mx-mn>1) ringBad.push(k+':'+mn+'~'+mx);}
  // 环半径递增
  var ds=Object.keys(ringR).map(Number).sort(function(a,b){return a-b;}), incOk=true, prev=-1;
  ds.forEach(function(d){if(ringR[d]<prev)incOk=false;prev=ringR[d];});
  // 树边交叉 (父链路; 共享端点跳过)
  var segs=[];
  ns.forEach(function(n){var lp=n.data('link_parent');if(lp==null)return;
    var pp=c.getElementById(''+lp); if(!pp.nonempty())return;
    segs.push({a:n.position(),b:pp.position(),ids:[n.id(),''+lp]});});
  function ccw(A,B,C){return (C.y-A.y)*(B.x-A.x)>(B.y-A.y)*(C.x-A.x);}
  function inter(A,B,C,D){return (ccw(A,C,D)!==ccw(B,C,D))&&(ccw(A,B,C)!==ccw(A,B,D));}
  var cross=0,cps=[];
  for(var i=0;i<segs.length;i++)for(var j=i+1;j<segs.length;j++){
    var s=segs[i],t=segs[j];
    if(s.ids[0]===t.ids[0]||s.ids[0]===t.ids[1]||s.ids[1]===t.ids[0]||s.ids[1]===t.ids[1])continue;
    if(inter(s.a,s.b,t.a,t.b)){cross++;if(cps.length<4)cps.push(s.ids.join('+')+'×'+t.ids.join('+'));}}
  // 节点圆不重叠
  var ov=0, ovp=[];
  for(var i=0;i<ns.length;i++)for(var j=i+1;j<ns.length;j++){
    var A=ns[i],B=ns[j],pa=A.position(),pb=B.position();
    var dd=Math.hypot(pa.x-pb.x,pa.y-pb.y);
    var rr=(A.width()+B.width())/2;
    if(dd<rr-1){ov++;if(ovp.length<4)ovp.push(A.id()+'-'+B.id()+' d='+Math.round(dd)+'<'+Math.round(rr));}}
  // 标签可见性与重叠 (renderedBoundingBox 含标签)
  var vis=[], hid=0;
  ns.forEach(function(n){var to=n.style('text-opacity');var num=parseFloat(to);
    if(isNaN(num))num=1;
    if(num<0.5){hid++;return;}
    vis.push({id:n.id(),bb:n.renderedBoundingBox(),dt:n.data('device_type'),
      lbl:String(n.data('label')).replace(/\\n/g,'|')});});
  var lbOv=0, lbp=[];
  for(var i=0;i<vis.length;i++)for(var j=i+1;j<vis.length;j++){
    var A=vis[i].bb,B=vis[j].bb;
    var ox=Math.min(A.x2,B.x2)-Math.max(A.x1,B.x1), oy=Math.min(A.y2,B.y2)-Math.max(A.y1,B.y1);
    if(ox>1&&oy>1){lbOv++;if(lbp.length<4)lbp.push(vis[i].id+'/'+vis[i].lbl+' × '+vis[j].id+'/'+vis[j].lbl+' ('+Math.round(ox)+'×'+Math.round(oy)+')');}}
  return {n:ns.length, rings:ringR, ringBad:ringBad, ringInc:incOk, segs:segs.length, cross:cross,
    cps:cps, nodeOv:ov, ovp:ovp, lblVis:vis.length, lblHid:hid, lblOv:lbOv, lbp:lbp,
    sample:rows.slice(0,6)};})()`);
console.log('  几何:', JSON.stringify(geo, null, 1).slice(0, 1400));
check('同跳数节点同半径 (分环正确)', geo.ringBad.length === 0, '异常环: ' + JSON.stringify(geo.ringBad));
check('环半径随跳数递增', geo.ringInc, '环半径 ' + JSON.stringify(geo.rings));
check('父链路树边零交叉 (子树扇区生效)', geo.cross === 0, '交叉 ' + geo.cross + ' ' + JSON.stringify(geo.cps));
check('节点圆无重叠', geo.nodeOv === 0, geo.nodeOv + ' 对 ' + JSON.stringify(geo.ovp));
check('标签不重叠 (bbox 同帧)', geo.lblOv === 0, geo.lblOv + ' 对 ' + JSON.stringify(geo.lbp));

await p.shot('u21_radial_star.jpg');

// ── 3. 时刻游标稳定性 (位置不得重算) ──
const posA = await p.ev(P.positions);
for (const v of [80, 300, 700, 950, 500]) {
  await p.ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(450);
}
const posB = await p.ev(P.positions);
let moved = 0, maxd = 0;
for (const k in posA) { const a = posA[k], b = posB[k]; if (!b) { moved++; continue; }
  const d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (d > 0.01) { moved++; maxd = Math.max(maxd, d); } }
check('拖动时刻游标位置零变化', moved === 0, '位移节点 ' + moved + ' 最大 ' + Math.round(maxd) + 'px');
const exT = p.exceptions.length;
check('时刻游标拖动无异常', exT === ex0, '新增 ' + (exT - ex0));

// 游标时刻的边仍在 (时刻链路可读)
const edgeAt = await p.ev(`(function(){var c=window.__cy;return {route:c.edges('[edge_type="route"]').length,parent:c.edges('[edge_type="parent"]').length};})()`);
console.log('  该时刻边:', JSON.stringify(edgeAt));

// ── 4. 布局三档切换 ──
await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='1';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
await sleep(2500);
const col = await p.ev(P.state);
const colPos = await p.ev(P.positions);
check('切列式: 节点数保持', col.nodes === st.nodes, JSON.stringify(col));
check('切列式: 位置与放射不同', JSON.stringify(colPos) !== JSON.stringify(posA));
await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='2';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
await sleep(3500);
const fr = await p.ev(P.state);
check('切自由: 节点数保持 + 无异常', fr.nodes === st.nodes && p.exceptions.length === exT, JSON.stringify(fr));
await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='0';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
await sleep(2500);
const posC = await p.ev(P.positions);
let diff = 0;
for (const k in posA) { const a = posA[k], b = posC[k]; if (!b) { diff++; continue; } if (Math.hypot(a[0] - b[0], a[1] - b[1]) > 0.01) diff++; }
check('切回放射: 位置与初始一致 (确定性)', diff === 0, '差异节点 ' + diff);

// ── 5. 交互回归 (图例/统计卡/邻居面板/路径面板) ──
const ui = await p.ev(`(function(){
  var lg=document.getElementById('legend-pop');
  document.getElementById('tlegend').click();
  var openLg=!lg.classList.contains('hidden');
  var legendTxt=lg.textContent;
  return {openLg:openLg, hasBadge:legendTxt.indexOf('终端聚合')>=0, hasRadial:legendTxt.indexOf('放射')>=0,
    stat:(document.getElementById('tstat')||{}).textContent.slice(0,60),
    rows:(document.querySelectorAll('#bp-routes .rp-row, #bp-routes tr').length)};})()`);
check('图例含聚合/放射说明', ui.openLg && ui.hasBadge && ui.hasRadial, JSON.stringify(ui));
check('统计卡非空', /节点|PAN/.test(ui.stat || ''), ui.stat);

await p.shot('u21_radial_after_switch.jpg');
console.log('\n异常总数: ' + p.exceptions.length);
p.exceptions.slice(0, 5).forEach(e => console.log(' !', String(e).slice(0, 160)));
const ok = summary();
await p.close();
process.exit(ok ? 0 : 1);
