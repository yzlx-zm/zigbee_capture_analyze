import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<90;i++){await sleep(800); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
for (const v of [500, 900, 1000]) {
  await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`);
  await sleep(900);
  const g=await p.ev(P.geo);
  console.log(`滑块 ${v}: 交叉 ${g.cross} | 节点重叠 ${g.nodeOv} | 标签重叠 ${g.lblOv} | 环 ${JSON.stringify(g.rings)}`);
}
await p.close(); process.exit(0);
