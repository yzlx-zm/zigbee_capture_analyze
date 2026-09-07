// T3 截图 8: 诊断命中卡区 + 拓扑图例浮层
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#diag');
await sleep(15000);
// 找 L1-3 卡滚动
const card = await p.ev(`(function(){
  var body=document.body.innerText;
  var cards=[...document.querySelectorAll('.l1-card')];
  var idx=-1;
  for(var i=0;i<cards.length;i++){ if(/密钥分发|L1-3|B2-LOOP/.test(cards[i].innerText||'')){idx=i;break;} }
  if(idx>=0){ cards[idx].scrollIntoView({block:'start'}); return cards[idx].innerText.replace(/\\n+/g,'|').slice(0,400); }
  return 'NOTFOUND ' + cards.length;})()`);
console.log('L1-3 卡文本:', card.slice(0,300));
await sleep(1000);
await p.shot(D + 'diag_hitcard.jpg');
await p.close();

p = await openTab('http://localhost:8720/#topo');
await sleep(15000);
const leg = await p.ev(`(function(){
  var b=document.getElementById('tlegend');
  if(!b){return 'NO_BTN';} b.click();
  var el=document.getElementById('legend-pop');
  return el ? (!el.classList.contains('hidden') ? 'visible' : 'still hidden') : 'NO_POP';})()`);
console.log('图例:', leg);
await sleep(600);
await p.shot(D + 'topo_legend.jpg');
// 关浮层 + 单击一个图节点看聚焦/底部面板
await p.ev(`(function(){ var el=document.getElementById('legend-pop'); if(el) el.classList.add('hidden'); return 1;})()`);
const node = await p.ev(`(function(){
  var els=document.querySelectorAll('#cy-graph .cy-node, #cy-graph [class*=node]');
  return els.length;})()`);
console.log('图节点元素:', node);
await p.close();
console.log('s8 done');
