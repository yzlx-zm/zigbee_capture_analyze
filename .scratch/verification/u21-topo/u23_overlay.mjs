// U23: 加载遮罩验证 — 用"同 PAN 但显式传 pan 参数"制造冷算 (~18s), 期间遮罩必须可见+计时
import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(600); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
console.log('初次加载(缓存命中):', JSON.stringify(st));
const vis = async () => p.ev(`(function(){var e=document.getElementById('cy-load');
  return {exists:!!e, hidden:e?e.classList.contains('hidden'):null,
    txt:e?e.textContent.replace(/\s+/g,' ').trim():'', sec:(document.getElementById('cy-load-sec')||{}).textContent};})()`);
console.log('加载后遮罩状态:', JSON.stringify(await vis()));
// 触发冷算: 显式填主 PAN (与默认 pan='' 是不同缓存 key)
const t0=Date.now();
await p.ev(`(function(){var i=document.getElementById('tpan');i.value='2200';
  i.dispatchEvent(new Event('input',{bubbles:true}));
  document.getElementById('tgo').click();return 1;})()`);
await sleep(2500);
const mid = await vis();
console.log('冷算中遮罩 ('+(Date.now()-t0)+'ms):', JSON.stringify(mid));
// 等遮罩隐藏 (冷算完成) 或超时 60s — 不能用"节点数>0"判断 (旧图还在显示)
let hid=false;
for(let i=0;i<40;i++){ await sleep(1500); const v=await vis(); if(v.hidden===true){hid=true;break;} }
st = await p.ev(P.state);
const after = await vis();
console.log('等待遮罩隐藏: ' + (hid?'✅ 已隐藏':'❌ 60s 未见隐藏'));
console.log('冷算完成 ('+(Date.now()-t0)+'ms):', JSON.stringify(after), JSON.stringify(st));
const okVis = mid.exists && mid.hidden===false && /\d+s/.test(mid.sec||'');
const okHide = after.exists && after.hidden===true && st.nodes>0;
console.log(okVis?'✅ 冷算期间遮罩可见 + 计时在走':'❌ 遮罩未显示/无计时');
console.log(okHide?'✅ 完成后遮罩自动隐藏':'❌ 遮罩未隐藏');
console.log('异常: '+p.exceptions.length);
await p.shot('u23_overlay.jpg');
await p.close(); process.exit(okVis&&okHide?0:1);
