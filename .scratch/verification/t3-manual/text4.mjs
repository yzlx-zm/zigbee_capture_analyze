import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#tl');
await sleep(6500);
const r = await p.ev(`(function(){
  var rows=[...document.querySelectorAll('tbody tr')];
  for(var i=0;i<rows.length;i++){
    if(rows[i].innerText.includes('Basic Read Attributes')){ rows[i].click(); return 'row '+i; }
  }
  return 'NONE';})()`);
console.log('点击:', r);
await sleep(3500);
const det = await p.ev(`(function(){
  var el=document.getElementById('tl-detail');
  var t=el?el.innerText:'';
  return {len:t.length, sample:t.slice(0,600).replace(/\\n+/g,'|')};})()`);
console.log('详情:', JSON.stringify(det, null, 1));
if (det.len > 100) {
  await p.shot(D + 'timeline_detail.jpg');
}
await p.close();
console.log('done');
