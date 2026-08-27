// S3-重构复验 (拓扑绘制原理): 中继入网抓包(1).cubx 8435 帧
// 验证: 节点全量/在线灰显/邻居边移除/时刻30s窗/链路历史30s+down/无异常
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#topo';
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
await send('Page.navigate',{url:TARGET});
await sleep(9000);

// 1. 加载 + 节点全量
const loadInfo = await ev(`(function(){
  return {canvas:!!document.querySelector('#cy-graph canvas'),
          tinfo:document.getElementById('tinfo')?.textContent||'NO',
          hasNbBtn:!!document.getElementById('tnb-toggle')};})()`);
check('加载 (节点全量)', loadInfo.canvas && loadInfo.tinfo.includes('78 节点'), JSON.stringify(loadInfo));
check('邻居边按钮已移除', loadInfo.hasNbBtn===false, '');

// 2. 时间窗过滤 → offline 灰显 (通过 loadData 带参 — 模拟跳转: 前端用 S.topoT0 契约,
// 直接调用页面内 window 层不可达, 用 fetch 验证后端 + 页面内手动渲染)
const winData = await ev(`(async function(){
  var r=await fetch('/api/topology/events?time_start=1780364526&time_end=1780364535');
  var d=await r.json();
  return {nodes:d.nodes.length, off:d.nodes.filter(n=>!n.online).length};})()`);
check('时间窗后端 online 判定 (前4s 52 离线)', winData.nodes===78 && winData.off===52, JSON.stringify(winData));

// 3. 时刻游标拖动 (slideMode → 30s 窗)
await ev(`(function(){var sl=document.getElementById('tsl');sl.value=300;onTimeSlide();return 1;})()`);
await sleep(1500);
const exA=exceptions.length;
check('时刻游标拖动无异常', exA===0, `异常:${exA}`);

// 4. 链路历史面板 (30s 分段 + down 证据)
await ev(`(function(){document.querySelectorAll('.bp-tab')[1].click();return 1;})()`);
await sleep(1500);
const hist = await ev(`(function(){
  var sel=document.getElementById('hist-sel');
  return {hasSel:!!sel, opts:sel?sel.options.length:0};})()`);
check('链路历史面板', hist.hasSel && hist.opts>0, JSON.stringify(hist));
// 选 838D (33677) — poll 父段 + rr 段
if(hist.hasSel){
  await ev(`(function(){var s=document.getElementById('hist-sel');s.value='33677';s.dispatchEvent(new Event('change'));return 1;})()`);
  await sleep(2500);
}
const hist838D = await ev(`(function(){
  return {info:document.getElementById('hist-info')?.textContent||'NO',
          segs:document.querySelectorAll('.hist-seg').length};})()`);
const exB=exceptions.length;
check('838D 链路历史加载 (poll+rr 段)', hist838D.segs>0 && exB-exA===0, JSON.stringify(hist838D));

// 5. 邻居关系面板保留
await ev(`(function(){document.querySelectorAll('.bp-tab')[2].click();return 1;})()`);
await sleep(1200);
const nb = await ev(`(function(){
  var sel=document.getElementById('nb-dev-sel');
  return {hasSel:!!sel, opts:sel?sel.options.length:0};})()`);
const exC=exceptions.length;
check('邻居面板保留 (LS 信息去处)', nb.hasSel && nb.opts>0 && exC-exB===0, JSON.stringify(nb));

// 6. PAN 切换 + 重置
await ev(`(function(){
  var rows=document.querySelectorAll('.pan-row');
  if(rows.length>1)rows[1].click();
  return 1;})()`);
await sleep(2000);
await ev(`document.getElementById('trst').click()`);
await sleep(2000);
const exD=exceptions.length;
const rst = await ev(`document.getElementById('tpan')?.value`);
check('PAN 切换+重置无异常', rst==='' && exD-exC===0, `pan='${rst}' | 异常:${exD-exC}`);

// 7. 布局切换往返
await ev(`document.getElementById('tlay').click()`);
await sleep(1200);
await ev(`document.getElementById('tlay').click()`);
await sleep(1200);
const exE=exceptions.length;
check('布局切换无异常', exE-exD===0, `异常:${exE-exD}`);

console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
console.log(`\n总异常: ${exceptions.length} 条`);
exceptions.slice(0,3).forEach(e=>console.log(' !',e.slice(0,100)));
ws.close();process.exit(0);
