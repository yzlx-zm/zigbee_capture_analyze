// S4: ✕ 统一清除所有过滤验证
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#tl';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable');await send('Runtime.enable');await send('DOM.enable');
await send('Page.navigate',{url:TARGET});
await sleep(6000);
// 设多个过滤
await ev(`(function(){
  document.getElementById('tl-pan').value='0x1EF9';
  document.getElementById('tl-node').value='0x0000';
  document.getElementById('tl-h0').value='17';
  document.getElementById('tl-m0').value='09';
  document.getElementById('tl-s0').value='00';
  document.getElementById('tshow').click();})()`);
await sleep(2000);
const before = await ev(`(function(){return {
  pan:document.getElementById('tl-pan').value, node:document.getElementById('tl-node').value,
  h0:document.getElementById('tl-h0').value, stat:document.getElementById('tl-stat').textContent};})()`);
check('过滤生效', before.pan!=='' && before.h0!=='', JSON.stringify(before));
// 点 ✕
await ev(`document.getElementById('tl-tclear').click()`);
await sleep(2500);
const after = await ev(`(function(){return {
  pan:document.getElementById('tl-pan').value, node:document.getElementById('tl-node').value,
  type:document.getElementById('tl-type').value, h0:document.getElementById('tl-h0').value,
  hide:document.getElementById('tl-hide-undec').checked,
  stat:document.getElementById('tl-stat').textContent};})()`);
check('✕ 清除 PAN', after.pan==='', JSON.stringify(after));
check('✕ 清除节点', after.node==='');
check('✕ 清除类型', after.type==='');
check('✕ 清除时间', after.h0==='');
check('✕ 清除未解密开关', after.hide===false);
check('✕ 后自动重查 (全量)', after.stat.includes('共 '), after.stat);
console.log(`\n${results.filter(r=>r.ok).length}/${results.length} 通过`);
ws.close();process.exit(0);
