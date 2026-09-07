// 报文详情: 点 Data 行 (真实匹配) → 右侧详情加载验证 + 截图
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#tl');
await sleep(6000);
const r = await p.ev(`(function(){
  var rows=[...document.querySelectorAll('tbody tr')];
  for(var i=0;i<rows.length;i++){ var t=rows[i].innerText;
    if(t.includes('Data') && !t.includes('—')){ rows[i].click(); return i + ' :: ' + t.slice(0,140).replace(/\\n/g,'|');} }
  return 'NONE';})()`);
console.log('点击行:', r);
await sleep(3500);
const det = await p.ev(`(function(){
  var el=document.getElementById('tl-detail');
  var t=el?el.innerText:'';
  return {len:t.length, sample:t.slice(0,500).replace(/\\n+/g,'|')};})()`);
console.log('详情:', JSON.stringify(det));
if (det.len > 100) {
  await p.shot(D + 'timeline_detail.jpg');
  // 事务链/字段点选? 截详情滚动底部 (ZCL 段)
  const sc = await p.ev(`(function(){ var el=document.getElementById('tl-detail'); if(el) el.scrollTop=el.scrollHeight; return 1;})()`);
  await sleep(600);
  await p.shot(D + 'timeline_detail2.jpg');
}
await p.close();
console.log('done');
