// 破坏性测试: 人为把某个右侧节点的标签按"旧错误映射"设置 → 断言必须报违规
import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(900); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
const target = await p.ev(`(function(){var c=window.__cy,root=c.getElementById('0').renderedPosition(),pick=null;
  c.nodes().forEach(function(n){var rp=n.renderedPosition();if(Math.abs(rp.x-root.x)/(Math.hypot(rp.x-root.x,rp.y-root.y))>0.9)pick=n.id();});
  var n=c.getElementById(pick); n.style({'text-halign':'left','text-margin-x':6,'text-valign':'center'});
  return pick;})()`);
await sleep(400);
const g = await p.ev(P.geo);
console.log('破坏目标节点:', target);
console.log('破坏后违规数:', g.lblOutBad.length, JSON.stringify(g.lblOutBad));
console.log(g.lblOutBad.length>0 ? '✅ 断言有牙 (抓住人为错误映射)' : '❌ 断言无效 (未抓住!)');
await p.close(); process.exit(g.lblOutBad.length>0?0:1);
