// 聚焦实测 v4: 聚焦 0x0071 (父切换 0xA868↔0x0000), 拖动对比截图像素差异
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
// 扫描收集所有节点位置
const nodes=new Map();
for(let gy=geo.y+8; gy<geo.y+geo.h-4; gy+=12){
  for(let gx=geo.x+8; gx<geo.x+geo.w-4; gx+=12){
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:gx,y:gy});
    await sleep(15);
    const info = await ev(`(function(){var t=document.getElementById('cy-tt');if(!t||t.style.display!=='block')return null;return t.innerHTML.slice(0,200);})()`);
    if(info && info.includes('状态:')){
      const m=info.match(/0x([0-9A-F]{4})/);
      if(m) nodes.set(m[1], {x:gx,y:gy});
    }
  }
}
console.log('扫描到节点数:', nodes.size);
const target=nodes.values().next().value;
console.log('目标节点:', target?`@(${target.x},${target.y})`:'未扫到');
if(!target){process.exit(0);}
// 点击聚焦 0x0071
await send('Input.dispatchMouseEvent',{type:'mousePressed',x:target.x,y:target.y,button:'left',clickCount:1});
await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:target.x,y:target.y,button:'left',clickCount:1});
await sleep(1500);
const fb = await ev(`document.getElementById('focus-bar').innerHTML.slice(0,60)`);
console.log('聚焦:', fb);
// 拖动游标 (素材 1781813813-4205) — 覆盖 0x0071 父切换区间 (3889-3900)
const shots=[];
for(const v of [0, 150, 250, 350, 450, 550, 700, 900, 1000]){
  await ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(1300);
  const shot = await send('Page.captureScreenshot',{format:'jpeg',quality:50});
  const buf=Buffer.from(shot.result.data,'base64');
  fs.writeFileSync(`.scratch/verification/s3-topo/s3_f71_v${v}.jpg`,buf);
  shots.push({v, size:buf.length});
}
console.log('截图尺寸:', shots.map(s=>`${s.v}:${s.size}`).join(' '));
const sizes=shots.map(s=>s.size);
const max=Math.max(...sizes), min=Math.min(...sizes);
console.log('最大差异:', max-min, 'bytes (', ((max-min)/min*100).toFixed(1), '% )');
ws.close();process.exit(0);
