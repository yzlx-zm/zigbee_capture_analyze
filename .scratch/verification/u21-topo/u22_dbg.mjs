import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
const prev=p.ws.onmessage; p.ws.onmessage=(e)=>{const m=JSON.parse(e.data);
  if(m.method==='Runtime.consoleAPICalled'){console.log('CONSOLE:',(m.params.args||[]).map(a=>a.value||a.description||'').join(' ').slice(0,200));}
  prev(e);};
let st=null; for(let i=0;i<80;i++){await sleep(800); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
console.log('加载:', JSON.stringify(st));
await p.ev(`(function(){var s=document.getElementById('tsl');s.value=900;onTimeSlide();return 1;})()`);
await sleep(1200);
const d = await p.ev(`(function(){var c=window.__cy,o=[];
  c.nodes().forEach(function(n){o.push({id:n.id(),aid:n.data('aid'),mv:n.data('mv'),cls:n.classes().join(' ').slice(0,60)});});
  return {nodes:c.nodes().length, sample:o, tinfo:document.getElementById('tinfo').textContent};})()`);
console.log('滑块 900:', JSON.stringify(d, null, 0).slice(0, 700));
await p.close(); process.exit(0);
