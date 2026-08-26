// S4: poll 帧修复复验 — 详情无 Encrypted 误导 + 路径列 MAC 地址标注
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#tl';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
await send('Page.enable');await send('Runtime.enable');await send('DOM.enable');
await send('Page.navigate',{url:TARGET});
await new Promise(r=>setTimeout(r,6000));
const pollRow = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length;i++){
    if((rows[i].textContent||'').includes('DataReq'))return {pid:rows[i].dataset.pid, path:rows[i].children[3].textContent};
  }return null;})()`);
check('第 1 页找到 poll 行', !!pollRow, JSON.stringify(pollRow));
if(pollRow){
  check('poll 行路径列 = MAC 地址 (非 —)', pollRow.path.includes('→'), pollRow.path);
  await ev(`tlJumpFrame(${pollRow.pid})`);
  await new Promise(r=>setTimeout(r,2000));
  const detail = await ev(`document.getElementById('tl-detail').textContent`);
  check('poll 详情无 "🔒 Encrypted"', !detail.includes('Encrypted'), detail.includes('Encrypted')?'仍有':'已清除');
  const layers = await ev(`Array.from(document.querySelectorAll('#tl-detail .frame-title')).map(t=>t.textContent).join(', ')`);
  check('poll 详情仅 MAC 层', layers==='MAC', layers);
}
console.log(`\n${results.filter(r=>r.ok).length}/${results.length} 通过`);
ws.close();process.exit(0);
