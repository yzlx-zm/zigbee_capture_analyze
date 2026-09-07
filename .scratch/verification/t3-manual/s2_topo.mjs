// T3 截图 2: 拓扑页 — 全貌 + 图例 + 时刻游标
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#topo');
await sleep(14000); // graph + events 加载
const info = await p.ev(`(function(){
  var nodes = document.querySelectorAll('canvas, svg').length;
  var legend = document.querySelector('.cy-legend, #topo-legend')?.innerText || '';
  var body = document.body.innerText.replace(/\s+/g,' ');
  var hasSlider = !!document.querySelector('input[type=range], #tl-slider, .tl-slider');
  return {canvas: nodes, legend: legend.slice(0,120), hasSlider, head: body.slice(0,150), ex:0};})()`);
console.log('拓扑结构:', JSON.stringify(info, null, 1));
await p.shot(D + 'topo_overview.jpg');
// 图例区
const leg = await p.ev(`(function(){
  var els=document.querySelectorAll('*'); var out=[];
  for(var i=0;i<els.length;i++){var t=els[i]; if(/形状|终端|协调器|路由器|图例|链路|邻居/.test(t.className||'')) out.push((t.className||'').toString().slice(0,80));}
  return out.slice(0,12);})()`);
console.log('图例候选 class:', JSON.stringify(leg));
await p.close();
console.log('s2 done');
