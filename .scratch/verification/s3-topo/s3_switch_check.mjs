// 切换点标记验证: 聚焦 0x9F1B (父切换 0x0000↔0xE2A8) → 切换点竖线
const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/#topo'});
await sleep(9000);
// 搜索聚焦 9F1B
await ev(`(function(){var s=document.getElementById('tsearch');s.value='9F1B';s.dispatchEvent(new Event('input'));var it=document.querySelector('#tsearch-list .tsearch-item');if(it)it.click();return 1;})()`);
await sleep(1500);
const sw = await ev(`(function(){
  var switches=document.querySelectorAll('.fhist-switch');
  var titles=Array.from(switches).map(function(x){return x.title;});
  return {count:switches.length, titles:titles.slice(0,4),
          legend:document.querySelector('.fhist-legend')?.textContent||''};})()`);
const ex=exceptions.length;
console.log('切换点:', JSON.stringify(sw,null,1));
console.log('异常:', ex);
const ok = sw.count>0 && sw.titles.some(t=>t.includes('链路变更')||t.includes('切换')) && ex===0;
console.log(ok?'✅ 切换点标记工作':'❌ 失败');
ws.close();process.exit(ok?0:1);
