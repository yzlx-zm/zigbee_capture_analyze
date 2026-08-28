const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/'});
await new Promise(r=>setTimeout(r,6000));
console.log("initial hash:", await ev(`location.hash`));
console.log("mc len (import):", await ev(`document.getElementById('mc').innerHTML.length`));
// 手动触发 diag
console.log("R.diag:", await ev(`typeof R.diag`));
await ev(`R.diag()`);
await new Promise(r=>setTimeout(r,3000));
console.log("mc len after R.diag():", await ev(`document.getElementById('mc').innerHTML.length`));
console.log("mc text:", (await ev(`document.getElementById('mc').innerText`)).slice(0,200));
console.log("exceptions:", exceptions.length);
exceptions.slice(0,8).forEach(e=>console.log(" !", e.slice(0,250)));
ws.close();process.exit(0);
