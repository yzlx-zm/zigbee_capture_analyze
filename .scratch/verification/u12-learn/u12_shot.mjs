// 截图: 场景学习视图 (总览 + L3-5 案例)
const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/#diag'});
await sleep(14000);
await ev(`(function(){var t=document.querySelector('.sc-view-tab[data-v="learn"]');if(t)t.click();return 1;})()`);
await sleep(4000);
const shot=await send('Page.captureScreenshot',{format:'png'});
const fs=await import('fs');
fs.writeFileSync('.scratch/verification/u12-learn/u12_learn_overview.png',Buffer.from(shot.result.data,'base64'));
// L3-5 场景 tab
await ev(`(function(){var ts=document.querySelectorAll('#diag-learn .sc-tab');for(var i=0;i<ts.length;i++){if(ts[i].textContent.includes('L3-5')){ts[i].click();return 1;}}return 0;})()`);
await sleep(1000);
const shot2=await send('Page.captureScreenshot',{format:'png'});
fs.writeFileSync('.scratch/verification/u12-learn/u12_learn_l35.png',Buffer.from(shot2.result.data,'base64'));
console.log('shots saved');
await fetch(`${CDP}/json/close/${t.id}`);
