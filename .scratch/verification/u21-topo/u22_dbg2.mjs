import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(800); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
for (const v of [0,20,40,60]) {
  await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`);
  await sleep(600);
  const d = await p.ev(`(function(){var c=window.__cy,o={};
    c.nodes().forEach(function(n){o['0x'+Number(n.data('aid')).toString(16).toUpperCase()]=n.data('mv');});return o;})()`);
  const t = await p.ev(`(document.getElementById('ttime-label')||{}).textContent`);
  console.log('v='+v+' T='+t, JSON.stringify(d));
}
await p.close(); process.exit(0);
