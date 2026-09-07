// 报文右侧详情面板验证 + 重截 (确保详情真实加载)
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#tl');
await sleep(6000);
const r = await p.ev(`(function(){
  var rows=[...document.querySelectorAll('tbody tr')];
  for(var i=0;i<rows.length;i++){ var t=rows[i].innerText;
    if(/\\|Data\\||NWK Cmd/.test(t)){ rows[i].click(); return rows[i].innerText.replace(/\\n+/g,'|').slice(0,140);} }
  return 'NONE';})()`);
console.log('点击行:', r);
await sleep(3000);
const det = await p.ev(`(function(){
  var el=document.getElementById('tl-detail');
  if(!el) return 'NO_PANEL';
  var t=el.innerText;
  return {len: t.length, sample: t.slice(0,400).replace(/\\n+/g,'|')};})()`);
console.log('详情面板:', JSON.stringify(det, null, 1));
await p.shot(D + 'timeline_detail.jpg');
await p.close();
console.log('done');
