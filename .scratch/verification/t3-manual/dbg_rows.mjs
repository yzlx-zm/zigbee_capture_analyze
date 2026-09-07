import { openTab, sleep } from './shot_lib.mjs';
let p = await openTab('http://localhost:8720/#tl');
await sleep(6500);
const info = await p.ev(`(function(){
  var tb=document.querySelector('tbody');
  var out=[];
  if(!tb) return 'NO_TB';
  [...tb.querySelectorAll('tr')].slice(0,8).forEach(function(tr,i){
    out.push(i+': '+tr.innerText.replace(/\\n/g,'|').slice(0,150));
  });
  return out;})()`);
console.log(JSON.stringify(info, null, 1));
await p.close();
console.log('ok');
