const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://127.0.0.1:50246/'});
await new Promise(r=>setTimeout(r,6000));
console.log("location:", await ev(`location.href`));
console.log("A 可用:", await ev(`typeof window.A`));
const f = await ev(`(async function(){
  try{var r=await window.A.get('/api/version');return JSON.stringify(r);}
  catch(e){return 'ERR:'+e.message;}})()`);
console.log("A.get version:", f);
const f2 = await ev(`(async function(){
  try{var r=await fetch('/api/version');var d=await r.json();return 'fetch OK: '+JSON.stringify(d);}
  catch(e){return 'ERR:'+e;}})()`);
console.log("fetch version:", f2);
console.log("exceptions:", exceptions.length);
exceptions.slice(0,3).forEach(e=>console.log(" !",e.slice(0,200)));
ws.close();process.exit(0);
