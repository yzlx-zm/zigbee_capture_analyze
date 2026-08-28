// S3 交互体验验证: 单击高亮/双击聚焦/工具栏精简/tgo动态/刻度条指针
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

// 1. 工具栏精简
const toolbar = await ev(`(function(){
  return {hasTshow:!!document.getElementById('tshow-all'),
          hasThl:!!document.getElementById('thl-clear'),
          hasViews:!!document.getElementById('tviews'),
          tgoText:document.getElementById('tgo')?.textContent};})()`);
check('冗余控件已删 (静默/清高亮)', toolbar.hasTshow===false && toolbar.hasThl===false, '');
check('视图收纳按钮存在', toolbar.hasViews===true, '');
check('tgo 初始文案 全量', toolbar.tgoText==='🔍 全量', toolbar.tgoText);

// 2. tgo 动态化
const dyn = await ev(`(function(){
  document.getElementById('taddr').value='838D';
  document.getElementById('taddr').dispatchEvent(new Event('input'));
  var t1=document.getElementById('tgo').textContent;
  document.getElementById('taddr').value='';
  document.getElementById('tpan').value='580C';
  document.getElementById('tpan').dispatchEvent(new Event('input'));
  var t2=document.getElementById('tgo').textContent;
  return {addr:t1, pan:t2};})()`);
check('tgo 动态 (定位/筛PAN)', dyn.addr==='🔍 定位' && dyn.pan==='🔍 筛PAN', JSON.stringify(dyn));

// 3. 视图组展开
await ev(`document.getElementById('tviews').click()`);
await sleep(300);
const vg = await ev(`document.getElementById('tview-group').style.display`);
check('视图组展开', vg==='inline-flex', vg);

// 4. 刻度条指针
const cur0 = await ev(`document.getElementById('ts-cursor')?.style.left`);
await ev(`(function(){var sl=document.getElementById('tsl');sl.value=800;onTimeSlide();return 1;})()`);
await sleep(800);
const cur1 = await ev(`document.getElementById('ts-cursor')?.style.left`);
check('刻度条指针跟随', cur0!==cur1 && cur1!=='', `${cur0}→${cur1}`);

// 5. 单击/双击行为 (无异常即可, canvas 事件)
const geo = await ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();return {x:g.x,y:g.y,w:g.width,h:g.height};})()`);
// 找节点 (tooltip 扫描)
let target=null;
for(let gy=geo.y+10; gy<geo.y+geo.h-5 && !target; gy+=14){
  for(let gx=geo.x+10; gx<geo.x+geo.w-5; gx+=14){
    await send('Input.dispatchMouseEvent',{type:'mouseMoved',x:gx,y:gy});
    await sleep(15);
    const info = await ev(`(function(){var t=document.getElementById('cy-tt');if(!t||t.style.display!=='block')return null;return t.innerHTML.slice(0,100);})()`);
    if(info && info.includes('状态:')){target={x:gx,y:gy};break;}
  }
}
check('找到节点', !!target);
if(target){
  // 单击 → 高亮 (不聚焦)
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:target.x,y:target.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:target.x,y:target.y,button:'left',clickCount:1});
  await sleep(800);
  const afterSingle = await ev(`document.getElementById('focus-bar').style.display`);
  const exA=exceptions.length;
  check('单击不高亮进聚焦 (聚焦横幅不显示)', afterSingle==='none' && exA===0, `focus-bar=${afterSingle} | 异常:${exA}`);
  // 双击 → 聚焦 (标准双击: 两次完整点击序列)
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:target.x,y:target.y,button:'left',clickCount:1});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:target.x,y:target.y,button:'left',clickCount:1});
  await sleep(60);
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:target.x,y:target.y,button:'left',clickCount:2});
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:target.x,y:target.y,button:'left',clickCount:2});
  await sleep(1500);
  const afterDbl = await ev(`document.getElementById('focus-bar').style.display`);
  const exB=exceptions.length;
  check('双击进聚焦', afterDbl==='flex' && exB-exA===0, `focus-bar=${afterDbl} | 异常:${exB-exA}`);
}
console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
console.log('总异常:', exceptions.length);
exceptions.slice(0,3).forEach(e=>console.log(' !',e.slice(0,100)));
ws.close();process.exit(0);
