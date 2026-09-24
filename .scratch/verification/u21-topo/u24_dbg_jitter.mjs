import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<90;i++){await sleep(800); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
console.log('加载:', JSON.stringify(st));
await p.ev(`document.getElementById('tagg').click()`); await sleep(2200);
console.log('聚合后:', JSON.stringify(await p.ev(P.state)));
const posA=await p.ev(P.positions);
for (const v of [150,500,850,500]) {
  await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`);
  await sleep(600);
}
const posB=await p.ev(P.positions);
const moved=[];
for(const k in posA){ if(!posB[k]){moved.push(k+' (消失)');continue;}
  const d=Math.hypot(posA[k][0]-posB[k][0],posA[k][1]-posB[k][1]);
  if(d>0.01)moved.push(k+' Δ'+Math.round(d)+'px  '+posA[k]+'→'+posB[k]); }
console.log('位移节点 '+moved.length+' 个:'); moved.slice(0,25).forEach(x=>console.log('  '+x));
const kinds=await p.ev(`(function(){var c=window.__cy,o={};c.nodes().forEach(function(n){var k=n.data('is_badge')?'badge':(n.data('device_type')||'?');o[k]=(o[k]||0)+1;});return o;})()`);
console.log('组成:',JSON.stringify(kinds));
await p.close(); process.exit(0);
