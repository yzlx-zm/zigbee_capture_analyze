// U21 诊断: 导出当前素材的实际布局几何 (环半径/角度/相邻角距) + 截图
import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st = null;
for (let i = 0; i < 120; i++) { await sleep(800); st = await p.ev(P.state); if (st && st.nodes > 0) break; }
const g = await p.ev(`(function(){
  var c=window.__cy, out=[];
  c.nodes().forEach(function(n){
    var d=n.data(); if(d.is_badge){out.push({id:n.id(),badge:d.count});return;}
    var pos=n.position(), R=Math.hypot(pos.x,pos.y);
    out.push({aid:'0x'+d.aid.toString(16).toUpperCase().padStart(4,'0'),dt:d.device_type,
      R:Math.round(R),deg:Math.round(((Math.atan2(pos.y,pos.x)*180/Math.PI)+360)%360),parent:d.link_parent});
  });
  // 各环相邻角距
  var rings={};
  out.forEach(function(o){ if(o.R==null)return; (rings[o.R]=rings[o.R]||[]).push(o); });
  var gaps={};
  for(var R in rings){ var arr=rings[R].sort(function(a,b){return a.deg-b.deg});
    gaps[R]=arr.map(function(o,i){var nx=arr[(i+1)%arr.length];var g=((i+1<arr.length)?(nx.deg-o.deg):(arr[0].deg+360-o.deg));return Math.round(g);});}
  return {nodes:out, gaps:gaps, bb:c.nodes().boundingBox()};})()`);
console.log(JSON.stringify(g, null, 0).slice(0, 2500));
await p.shot('u21_now_look.jpg');
await p.close(); process.exit(0);
