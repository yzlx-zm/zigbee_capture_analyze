// S3-C 聚焦增强验证: 进入聚焦 → 时间轴存在 → 拖动指针移动 → ghost 叠加无异常
const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/#topo'});
await sleep(9000);
const geo = await ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();return {x:g.x,y:g.y,w:g.width,h:g.height};})()`);
// 找 0x9F1B (40731, 有父切换)
let target=null;
for(let gy=geo.y+8; gy<geo.y+geo.h-4 && !target; gy+=10){
  for(let gx=geo.x+8; gx<geo.x+geo.w-4; gx+=10){
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:gx,y:gy});
    await sleep(12);
    const info = await ev(`(function(){var t=document.getElementById('cy-tt');if(!t||t.style.display!=='block')return null;return t.innerHTML.slice(0,200);})()`);
    if(info && info.includes('0x9F1B') && info.includes('状态:')){target={x:gx,y:gy};break;}
  }
}
check('找到聚焦目标 0x9F1B', !!target);
if(!target){console.log('总异常:',exceptions.length);process.exit(0);}
// 点击聚焦
await send('Input.dispatchMouseEvent',{type:'mousePressed',x:target.x,y:target.y,button:'left',clickCount:1});
await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:target.x,y:target.y,button:'left',clickCount:1});
await sleep(1800);
const hist = await ev(`(function(){
  var h=document.getElementById('focus-hist');
  return {exists:!!h, segs:h?h.querySelectorAll('.fhist-seg').length:0,
          cursor:!!document.getElementById('fhist-cur'),
          info:document.getElementById('fhist-info')?.textContent.slice(0,60)||''};})()`);
const exA=exceptions.length;
check('聚焦时间轴存在 (段+指针+信息)', hist.exists && hist.segs>0 && hist.cursor && exA===0, JSON.stringify(hist));
// 拖动 → 指针移动 + 无异常
const leftBefore = await ev(`document.getElementById('fhist-cur')?.style.left`);
await ev(`(function(){var sl=document.getElementById('tsl');sl.value=800;onTimeSlide();return 1;})()`);
await sleep(1600);
const leftAfter = await ev(`document.getElementById('fhist-cur')?.style.left`);
const exB=exceptions.length;
check('拖动指针移动', leftBefore!==leftAfter && exB-exA===0, `${leftBefore}→${leftAfter} | 异常:${exB-exA}`);
// 时间轴信息更新 (当前段文字)
const info2 = await ev(`document.getElementById('fhist-info')?.textContent.slice(0,70)||''`);
console.log('  当前段信息:', info2);
// 退出聚焦
await ev(`document.getElementById('focus-exit').click()`);
await sleep(1500);
const exC=exceptions.length;
const exited = await ev(`document.getElementById('focus-bar').style.display`);
check('退出聚焦无异常', exited==='none' && exC-exB===0, `display=${exited} | 异常:${exC-exB}`);
console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
console.log('总异常:', exceptions.length);
exceptions.slice(0,3).forEach(e=>console.log(' !',e.slice(0,100)));
ws.close();process.exit(0);
