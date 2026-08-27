// S4: 路径列直连显示验证 (NWK 帧无中继 → Src→Dst)
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
// 跳转 Door Lock 帧 (id=3059) 看路径列
await ev(`tlJumpFrame(3059)`);
await new Promise(r=>setTimeout(r,2000));
const rowPath = await ev(`(function(){var r=document.querySelector('#tltb tr.hl');return r?r.children[3].textContent:'';})()`);
check('Door Lock 帧路径列 = Src→Dst', /^0x[0-9A-F]{4}→0x[0-9A-F]{4}$/.test(rowPath), rowPath);
// 随机统计: 有 NWK 的帧路径列不再 "—" (全量第 1 页检查)
const dashCount = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  var dash=0, nwk=0;
  for(var i=0;i<rows.length;i++){
    var path=rows[i].children[3].textContent;
    if(path==='—')dash++;
    if(rows[i].children[4].textContent!=='-')nwk++;
  }
  return {dash:dash, nwk:nwk, total:rows.length};})()`);
check('路径列无 "—" 的 NWK 帧存在', dashCount.dash < dashCount.total, JSON.stringify(dashCount));
console.log(`\n${results.filter(r=>r.ok).length}/${results.length} 通过`);
ws.close();process.exit(0);
