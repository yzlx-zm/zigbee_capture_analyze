import fs from 'fs';
// S3 聚焦模式自查: 截图 → 点击节点 → 拖动游标 → 对比
const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/#topo'});
await sleep(9000);
// 截图1: 全貌
await send('Page.captureScreenshot',{format:'png'}).then(r=>{
  fs.writeFileSync('.scratch/verification/s3-topo/s3_focus_1_full.png', Buffer.from(r.result.data,'base64'));
});
console.log('截图1 done (全貌)');
// 图容器位置
const geo = await ev(`(function(){
  var g=document.getElementById('cy-graph').getBoundingClientRect();
  return {x:g.x,y:g.y,w:g.width,h:g.height};})()`);
console.log('cy-graph:', JSON.stringify(geo));
// 尝试点击 canvas 中心区域 (布局中心附近是协调器/主链)
await send('Input.dispatchMouseEvent',{type:'mousePressed',x:geo.x+geo.w/2,y:geo.y+geo.h/2,button:'left',clickCount:1});
await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:geo.x+geo.w/2,y:geo.y+geo.h/2,button:'left',clickCount:1});
await sleep(1500);
const focusBar = await ev(`(function(){
  var b=document.getElementById('focus-bar');
  return b?{display:b.style.display, html:b.innerHTML.slice(0,100)}:null;})()`);
console.log('聚焦横幅:', JSON.stringify(focusBar));
ws.close();process.exit(0);
