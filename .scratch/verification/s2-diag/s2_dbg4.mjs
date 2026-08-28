const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const raw=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r;};
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/'});
await new Promise(r=>setTimeout(r,5000));
// 直接测 A.get events
const r1 = await raw(`(async function(){
  try{
    var d = await A.get('/api/topology/events');
    return {ok:true, pans:(d.pans||[]).length, main:d.main_pan, err:null};
  }catch(e){return {ok:false, err:String(e)};}})()`);
console.log("A.get events:", JSON.stringify(r1.result?.result?.value));
// 手动调 R.diag 并捕获异常
const r2 = await raw(`(function(){
  try{ R.diag(); return {ok:true}; }catch(e){ return {ok:false, err:String(e), stack:e.stack}; }})()`);
console.log("R.diag call:", JSON.stringify(r2.result?.result?.value));
await new Promise(r=>setTimeout(r,4000));
console.log("mc len:", await ev(`document.getElementById('mc').innerHTML.length`));
console.log("has diag-pan:", await ev(`!!document.getElementById('diag-pan')`));
console.log("exceptions:", exceptions.length);
exceptions.slice(0,5).forEach(e=>console.log(" !", e.slice(0,200)));
ws.close();process.exit(0);
