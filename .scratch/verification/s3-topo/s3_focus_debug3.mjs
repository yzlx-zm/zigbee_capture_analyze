// 聚焦实测 v3: 扫描找【节点】(tooltip 含"状态"), 点击进聚焦, 拖动对比链路边
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
let found=null, nodeInfo='';
outer:
for(let gy=geo.y+10; gy<geo.y+geo.h-5; gy+=14){
  for(let gx=geo.x+10; gx<geo.x+geo.w-5; gx+=14){
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:gx,y:gy});
    await sleep(20);
    const info = await ev(`(function(){var t=document.getElementById('cy-tt');if(!t||t.style.display!=='block')return null;return {txt:t.innerHTML.slice(0,120),disp:t.style.display};})()`);
    if(info && info.txt.includes('状态:')){  // 节点 tooltip 特征
      found={x:gx,y:gy};
      nodeInfo=info.txt;
      break outer;
    }
  }
}
console.log('节点:', found?`@(${found.x},${found.y})`:'未找到', '|', nodeInfo.replace(/<[^>]+>/g,' ').slice(0,80));
if(!found){process.exit(0);}
// 点击进聚焦
await send('Input.dispatchMouseEvent',{type:'mousePressed',x:found.x,y:found.y,button:'left',clickCount:1});
await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:found.x,y:found.y,button:'left',clickCount:1});
await sleep(1500);
const fb = await ev(`(function(){var b=document.getElementById('focus-bar');return b?{disp:b.style.display,html:b.innerHTML.slice(0,90)}:null;})()`);
console.log('聚焦横幅:', JSON.stringify(fb));
// 拖动游标 → 每次截图对比
for(const v of [0, 200, 500, 800, 1000]){
  await ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(1500);
  const shot = await send('Page.captureScreenshot',{format:'jpeg',quality:50});
  fs.writeFileSync(`.scratch/verification/s3-topo/s3_focus_v${v}.jpg`,Buffer.from(shot.result.data,'base64'));
}
console.log('截图完成');
ws.close();process.exit(0);
