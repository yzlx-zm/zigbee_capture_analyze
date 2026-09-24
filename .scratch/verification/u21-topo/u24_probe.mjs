// 间距诊断: fit 缩放 / 屏幕上节点与字号实际大小 / 环半径与留白
import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(700); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
const g = await p.ev(`(function(){
  var c=window.__cy, gb=document.getElementById('cy-graph').getBoundingClientRect();
  var zoom=c.zoom(), bb=c.nodes().boundingBox();
  var rows=[], rings={};
  c.nodes().forEach(function(n){
    if(n.data('is_badge'))return;
    var pos=n.position(), R=Math.sqrt(pos.x*pos.x+pos.y*pos.y);
    var d=n.data('aid'), dt=n.data('device_type');
    var dep=null;   // 深度 (由 link_parent 链推)
    (rings[Math.round(R)]=rings[Math.round(R)]||[]).push('');
    rows.push({aid:'0x'+Number(d).toString(16).toUpperCase(),R:Math.round(R),dt:dt,
      rw:Math.round(n.renderedWidth()), rh:Math.round(n.renderedHeight()),
      fs:n.style('font-size'), lbl:String(n.data('label')).split(String.fromCharCode(10)).length});
  });
  return {zoom:Math.round(zoom*1000)/1000, container:[Math.round(gb.width),Math.round(gb.height)],
    bbox:[Math.round(bb.w),Math.round(bb.h)],
    rings:Object.keys(rings).sort(function(a,b){return a-b}).map(function(k){return k+'('+rings[k].length+')'}),
    rows:rows, dense40:c.nodes().length>40};})()`);
console.log('容器:',JSON.stringify(g.container),' bbox:',JSON.stringify(g.bbox),' fit zoom:',g.zoom);
console.log('环半径(节点数):', g.rings.join('  '));
console.log('屏幕上尺寸: 节点宽 x zoom =', g.rows[0]?Math.round(g.rows[0].rw)+'px':'', ' 字号', g.rows[0]?g.rows[0].fs:'', '→ 屏幕上', g.rows[0]?Math.round(parseFloat(g.rows[0].fs)*g.zoom)+'px':'');
console.log('每节点:', JSON.stringify(g.rows.slice(0,8)));
await p.shot('u24_spacing_before.jpg');
await p.close(); process.exit(0);
