// 聚焦模式实测: 网格扫描 tooltip 找节点 → 点击进聚焦 → 拖动游标 → 对比链路
import fs from 'fs';
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
const geo = await ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();return {x:g.x,y:g.y,w:g.width,h:g.height};})()`);
console.log('图容器:', JSON.stringify(geo));
// 网格扫描找节点 (tooltip 出现)
let found=null;
outer:
for(let gy=geo.y+15; gy<geo.y+geo.h-10; gy+=22){
  for(let gx=geo.x+15; gx<geo.x+geo.w-10; gx+=22){
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:gx,y:gy});
    await sleep(25);
    const tt = await ev(`(function(){var t=document.getElementById('cy-tt');return t&&t.style.display==='block';})()`);
    if(tt){
      found={x:gx,y:gy};
      const txt = await ev(`document.getElementById('cy-tt').innerHTML.slice(0,80)`);
      console.log('找到节点 @', gx, gy, 'tooltip:', txt);
      break outer;
    }
  }
}
if(!found){console.log('未找到节点 (图可能空或渲染问题)');process.exit(0);}
// 点击进聚焦
await send('Input.dispatchMouseEvent',{type:'mousePressed',x:found.x,y:found.y,button:'left',clickCount:1});
await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:found.x,y:found.y,button:'left',clickCount:1});
await sleep(1500);
const fb = await ev(`(function(){var b=document.getElementById('focus-bar');return b?{disp:b.style.display,html:b.innerHTML.slice(0,80)}:null;})()`);
console.log('聚焦横幅:', JSON.stringify(fb));
// 截图 (聚焦后)
await send('Page.captureScreenshot',{format:'jpeg',quality:60}).then(r=>{fs.writeFileSync('.scratch/verification/s3-topo/s3_focus_2_focus.jpg',Buffer.from(r.result.data,'base64'));});
// 拖动游标: 0 → 500 → 1000
for(const v of [0, 300, 700, 1000]){
  await ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(1200);
  const ttl = await ev(`document.getElementById('ttime-label').textContent`);
  console.log(`拖动到 ${v}: 时刻 ${ttl}`);
}
await send('Page.captureScreenshot',{format:'jpeg',quality:60}).then(r=>{fs.writeFileSync('.scratch/verification/s3-topo/s3_focus_3_slid.jpg',Buffer.from(r.result.data,'base64'));});
console.log('done');
ws.close();process.exit(0);
