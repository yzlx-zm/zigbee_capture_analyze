// S3 拓扑页稳定化 — 疑点 CDP 实测 v2 (异常捕获驱动, 素材: 需求31321_2路开关_入网_1ef9.cubx)
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#topo';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
// 异常捕获
let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);
  if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown'){
    exceptions.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text||'unknown');
  }
};
await send('Page.enable');await send('Runtime.enable');await send('Log.enable');
await send('Page.navigate',{url:TARGET});
await sleep(8000);
const ex0=exceptions.length;

// 0. 页面加载
const loadInfo = await ev(`(function(){
  return {canvas:!!document.querySelector('#cy-graph canvas'),
          tinfo:document.getElementById('tinfo')?.textContent||'NO',
          rows:document.querySelectorAll('#bp-routes .path-row').length};})()`);
check('拓扑页加载', loadInfo.canvas, JSON.stringify(loadInfo));

// 1. tlay 两次: 0→1 力导 → 0 固定列 (疑点: runLayout nd ReferenceError)
await ev(`document.getElementById('tlay').click()`);
await sleep(2000);
const exA=exceptions.length;
await ev(`document.getElementById('tlay').click()`);
await sleep(2000);
const exB=exceptions.length;
const layState = await ev(`(function(){
  return {btn:document.getElementById('tlay').textContent,
          canvas:!!document.querySelector('#cy-graph canvas'),
          tinfo:document.getElementById('tinfo').textContent};})()`);
const newEx=exceptions.slice(ex0);
check('tlay 两次无异常', exB-exA===0 && layState.canvas, `${JSON.stringify(layState)} | 新异常: ${newEx.length}条 ${newEx[0]?.slice(0,100)||''}`);

// 2. 路径行 hover → 图上高亮联动 (疑点: route 边无 path_idx → 永不匹配)
const hoverTest = await ev(`(function(){
  var rows=document.querySelectorAll('#bp-routes .path-row[data-pidx]');
  if(!rows.length)return {ok:false, reason:'NO path rows'};
  // 触发 mouseenter — 高亮逻辑在模块闭包内, 只能验证无异常
  rows[0].dispatchEvent(new MouseEvent('mouseenter',{bubbles:true}));
  return {ok:true, firstRow:rows[0].textContent.slice(0,60)};})()`);
await sleep(500);
const exC=exceptions.length;
check('路径行 hover 无异常', hoverTest.ok && exC-exB===0, JSON.stringify(hoverTest));

// 3. 路由边 tooltip (疑点: edge tooltip else 分支 path_idx+1 → NaN)
// Cytoscape 实例模块私有 — 代码层已确认 route 边数据无 path_idx (renderGraph line ~351)
// 间接验证: 检查页面是否有 NaN 痕迹的 tooltip 展示触发途径 — 跳过 DOM, 记代码证据
check('route 边 tooltip 数据源有 path_idx (代码证据)', false, '❌ cyEdges route 边缺 path_idx/hop — 见 renderGraph 边构建段');

// 4. 滑块拖动 (时刻游标 onTimeSlide 本地重渲染)
await ev(`(function(){var sl=document.getElementById('tsl');sl.value=250;onTimeSlide();return 1;})()`);
await sleep(1000);
const afterSlide = await ev(`(function(){
  return {canvas:!!document.querySelector('#cy-graph canvas'),
          label:document.getElementById('ttime-label')?.textContent||'NO'};})()`);
const exD=exceptions.length;
check('时刻游标拖动无异常', afterSlide.canvas && exD-exC===0, JSON.stringify(afterSlide));

// 5. 链路历史面板 (U13)
await ev(`(function(){document.querySelectorAll('.bp-tab')[1].click();return 1;})()`);
await sleep(1500);
const hist = await ev(`(function(){
  var sel=document.getElementById('hist-sel');
  return {hasSel:!!sel, selOpts:sel?sel.options.length:0,
          tlText:document.getElementById('hist-timeline')?.textContent.slice(0,50)||'NO'};})()`);
const exE=exceptions.length;
check('链路历史面板', hist.hasSel && hist.selOpts>0 && exE-exD===0, JSON.stringify(hist));
// 选第一个节点 → 加载分段
if(hist.hasSel&&hist.selOpts>0){
  await ev(`(function(){var sel=document.getElementById('hist-sel');sel.value=sel.options[0].value;sel.dispatchEvent(new Event('change'));return 1;})()`);
  await sleep(2000);
}
const histLoad = await ev(`(function(){
  return {info:document.getElementById('hist-info')?.textContent||'NO',
          segs:document.querySelectorAll('.hist-seg').length};})()`);
const exF=exceptions.length;
check('链路历史加载无异常', exF-exE===0, JSON.stringify(histLoad));

// 6. 邻居关系面板
await ev(`(function(){document.querySelectorAll('.bp-tab')[2].click();return 1;})()`);
await sleep(1500);
const nb = await ev(`(function(){
  var sel=document.getElementById('nb-dev-sel');
  return {hasSel:!!sel, opts:sel?sel.options.length:0};})()`);
const exG=exceptions.length;
check('邻居关系面板', nb.hasSel && exG-exF===0, JSON.stringify(nb));
// 选第一个设备 → 表格
if(nb.hasSel&&nb.opts>0){
  await ev(`(function(){var sel=document.getElementById('nb-dev-sel');sel.value=sel.options[1].value;showNbTable();return 1;})()`);
  await sleep(800);
}
const nbDetail = await ev(`document.getElementById('nb-detail')?.innerHTML.length||0`);
const exH=exceptions.length;
check('邻居明细表格', nbDetail>50 && exH-exG===0, `detailLen=${nbDetail}`);

// 7. 折叠交互 (4 section 折叠 + 展开全部)
const fold = await ev(`(function(){
  var heads=document.querySelectorAll('#bp-routes .fold-head');
  if(heads.length<2)return {ok:false,heads:heads.length};
  heads[0].click();
  var b0=document.querySelector('[data-body="'+heads[0].dataset.sec+'"]');
  var folded=b0.style.display==='none';
  heads[0].click(); // 展开回
  return {ok:true, heads:heads.length, folded:folded};})()`);
check('折叠交互', fold.ok && fold.folded, JSON.stringify(fold));

// 8. 时间窗过滤联动 (S.topoT0/T1 → 请求带参数) — 通过滑块窗口档位不可用, 直接调用接口层验证
const tf = await ev(`(function(){
  // 拓扑页无窗口档位控件 (twin-size 已删), 时间窗由时间线页/聚焦条带参 —
  // 验证 events 端点带 time_start/end 行为 (后端已支持, 前端 loadData 透传)
  return {hasTwinSize:!!document.getElementById('twin-size')};})()`);
check('twin-size 控件已删 (getWinSize 引用已删元素=死代码)', tf.hasTwinSize===false, '');

// 9. PAN 切换 (多 PAN)
await ev(`(function(){
  var rows=document.querySelectorAll('.pan-row');
  if(rows.length>1)rows[1].click();
  return 1;})()`);
await sleep(2500);
const panState = await ev(`(function(){
  return {panInput:document.getElementById('tpan').value,
          canvas:!!document.querySelector('#cy-graph canvas'),
          tinfo:document.getElementById('tinfo').textContent};})()`);
const exI=exceptions.length;
check('PAN 切换无异常', panState.canvas && panState.panInput!=='' && exI-exH===0, JSON.stringify(panState));

// 10. 重置
await ev(`document.getElementById('trst').click()`);
await sleep(2500);
const rstState = await ev(`(function(){
  return {panInput:document.getElementById('tpan').value,
          canvas:!!document.querySelector('#cy-graph canvas')};})()`);
const exJ=exceptions.length;
check('重置恢复无异常', rstState.panInput==='' && rstState.canvas && exJ-exI===0, JSON.stringify(rstState));

console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
console.log(`\n总异常: ${exceptions.length} 条: ${exceptions.map(e=>e.slice(0,80)).join(' | ')}`);
ws.close();process.exit(0);
