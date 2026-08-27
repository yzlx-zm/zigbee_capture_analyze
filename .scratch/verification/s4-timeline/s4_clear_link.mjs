// S4: 清除数据 → 报文页过滤重置联动验证
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
// 1. 设过滤条件
await ev(`(function(){
  document.getElementById('tl-pan').value='0x580C';
  document.getElementById('tl-node').value='0x737D';
  document.getElementById('tshow').click();})()`);
await sleep(2500);
const filteredStat = await ev(`document.getElementById('tl-stat').textContent`);
check('过滤生效', filteredStat.includes('PAN=') && filteredStat.includes('节点='), filteredStat);
// 2. 切导入页 → 清除数据
await ev(`location.hash='import'`);
await sleep(1500);
await ev(`document.getElementById('clr').click()`);
await sleep(400);
await ev(`document.getElementById('clr').click()`);
await sleep(2000);
const sbAfter = await ev(`document.getElementById('sb').textContent`);
check('清除完成', sbAfter==='就绪', sbAfter);
// 3. 切回报文页 → 过滤已重置
await ev(`location.hash='tl'`);
await sleep(6000);
const filters = await ev(`(function(){
  return {pan:document.getElementById('tl-pan').value,
          node:document.getElementById('tl-node').value,
          type:document.getElementById('tl-type').value,
          h0:document.getElementById('tl-h0').value,
          stat:document.getElementById('tl-stat').textContent};})()`);
check('PAN 框已清空', filters.pan==='', JSON.stringify(filters));
check('节点框已清空', filters.node==='');
check('类型下拉已重置', filters.type==='');
check('时间下拉已重置', filters.h0==='');
check('自动加载全部 (无旧条件)', filters.stat.includes('共 '), filters.stat);
console.log(`\n${results.filter(r=>r.ok).length}/${results.length} 通过`);
ws.close();process.exit(0);
