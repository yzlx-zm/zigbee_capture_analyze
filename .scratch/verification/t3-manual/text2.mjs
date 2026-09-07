// 报文详情面板 + 导入结果卡 + 诊断摘要卡 文案样本
import { openTab, sleep } from './shot_lib.mjs';
let p = await openTab('http://localhost:8720/#tl');
await sleep(6000);
// 找一条 Data 已解密帧行点击
const r = await p.ev(`(function(){
  var rows=[...document.querySelectorAll('tbody tr')];
  for(var i=0;i<rows.length;i++){ var t=rows[i].innerText;
    if(/Data|NWK|APS/.test(t) && !t.includes('—')){ rows[i].click(); return rows[i].innerText.replace(/\\n+/g,'|').slice(0,120);} }
  return 'NONE';})()`);
console.log('点击行:', r);
await sleep(2500);
const det = await p.ev(`(function(){
  // 详情容器: 找含 帧号/分层 的最近展开块
  var cands=[...document.querySelectorAll('tr[class*=open] + tr, .pkt-detail, [class*=detail]')];
  var boxes=cands.filter(x=>x.offsetParent!==null && x.innerText.length>200);
  var t = boxes[0] ? boxes[0].innerText.slice(0,900).replace(/\\n+/g,'|') : 'NO_BOX';
  return t;})()`);
console.log('详情文本:', det.slice(0,700));
await p.close();

p = await openTab('http://localhost:8720/#import');
await sleep(4000);
const sr = await p.ev(`(function(){
  var el=document.getElementById('sout');
  if(!el||el.classList.contains('hidden')) return 'HIDDEN';
  return el.innerText.replace(/\\n+/g,'|').slice(0,700);})()`);
console.log('导入结果卡:', sr.slice(0,600));
await p.close();
