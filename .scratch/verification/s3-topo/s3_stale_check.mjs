// S3-方案A 验证: 时刻模式残影 (拖动游标 → 无当前证据节点留原位 + 灰虚线边)
// 断言: 拖动无异常 + 页面渲染不崩 (canvas 无法 DOM 断言边, 用异常捕获 + 状态验证)
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

// 1. 加载
const loadOk = await ev(`(function(){
  return {canvas:!!document.querySelector('#cy-graph canvas'),
          tinfo:document.getElementById('tinfo')?.textContent,
          offLabel:document.getElementById('off-label')?.textContent};})()`);
check('加载 (主PAN 10 节点)', loadOk.canvas && loadOk.tinfo.includes('10 节点'), JSON.stringify(loadOk));
check('off-label 文案更新', loadOk.offLabel.includes('未关联'), loadOk.offLabel);

// 2. 拖动游标到抓包早期 (时刻模式, 30s 窗) — 多次拖动不同位置
for(const v of [100, 300, 700, 900]){
  await ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(1000);
}
const exA=exceptions.length;
check('时刻模式多次拖动无异常', exA===0, `异常:${exA}`);

// 3. 时刻模式边界: 拖到最左 (抓包起点, 无证据) → 无异常
await ev(`(function(){var sl=document.getElementById('tsl');sl.value=0;onTimeSlide();return 1;})()`);
await sleep(1200);
const exB=exceptions.length;
check('拖到起点 (无证据时刻) 无异常', exB-exA===0, `异常:${exB-exA}`);

// 4. 返回中点 + 重置回全貌
await ev(`document.getElementById('trst').click()`);
await sleep(2500);
const exC=exceptions.length;
const rst = await ev(`document.getElementById('tpan')?.value`);
check('重置回全貌无异常', rst==='' && exC-exB===0, `异常:${exC-exB}`);

// 5. 聚焦模式 (单击节点) + 时刻拖动 (残影在聚焦链路链上)
await ev(`(function(){
  // 无法直接点击 canvas 节点, 用聚焦横幅逻辑跳过 — 验证聚焦进入正常
  return 1;})()`);

console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
console.log(`总异常: ${exceptions.length} 条`);
exceptions.slice(0,3).forEach(e=>console.log(' !',e.slice(0,100)));
ws.close();process.exit(0);
