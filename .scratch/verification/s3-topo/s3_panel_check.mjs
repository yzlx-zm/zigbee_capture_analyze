// S3 底部面板信息验证: 路径行点击聚焦 / 链路历史指针 / 邻居表不对称+色带
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

// 1. 路径行点击 → 聚焦
const rowClick = await ev(`(function(){
  var rows=document.querySelectorAll('#bp-routes .path-row[data-pidx]');
  if(!rows.length)return {ok:false};
  rows[0].click();
  return {ok:true};})()`);
await sleep(1500);
const focusTitle = await ev(`document.querySelector('.fhist-aid')?.textContent||'NO'`);
const exA=exceptions.length;
check('路径行点击进聚焦', rowClick.ok && focusTitle.includes('聚焦') && exA===0, `${focusTitle} | 异常:${exA}`);
// 退出聚焦
await ev(`document.getElementById('focus-exit')?.click()`);
await sleep(1200);

// 2. 链路历史面板指针
await ev(`(function(){document.querySelectorAll('.bp-tab')[1].click();return 1;})()`);
await sleep(1500);
const hist = await ev(`(function(){
  var sel=document.getElementById('hist-sel');
  if(!sel)return {ok:false};
  sel.value=sel.options[sel.options.length-1].value;
  sel.dispatchEvent(new Event('change'));
  return {ok:true};})()`);
await sleep(2200);
const histCur = await ev(`(function(){
  var cur=document.getElementById('hist-cur');
  return {exists:!!cur, left:cur?cur.style.left:'NO'};})()`);
// 拖动主滑块 → 指针移动
const before = await ev(`document.getElementById('hist-cur')?.style.left`);
await ev(`(function(){var sl=document.getElementById('tsl');sl.value=300;onTimeSlide();return 1;})()`);
await sleep(1000);
const after = await ev(`document.getElementById('hist-cur')?.style.left`);
const exB=exceptions.length;
check('链路历史指针存在', hist.ok && histCur.exists, JSON.stringify(histCur));
check('滑块拖动指针跟随', before!==after && exB-exA===0, `${before}→${after} | 异常:${exB-exA}`);

// 3. 邻居表不对称+色带
await ev(`(function(){document.querySelectorAll('.bp-tab')[2].click();return 1;})()`);
await sleep(1200);
const nb = await ev(`(function(){
  var sel=document.getElementById('nb-dev-sel');
  if(!sel)return {ok:false};
  sel.value=sel.options[1].value;showNbTable();
  return {ok:true};})()`);
await sleep(800);
const nbTbl = await ev(`(function(){
  var detail=document.getElementById('nb-detail');
  var th=detail?detail.querySelector('th:nth-child(4)')?.textContent:'';
  var cells=detail?detail.querySelectorAll('td[style*="background"]').length:0;
  var asym=detail?detail.querySelectorAll('td[style*="color"]').length:0;
  return {th4:th, bgCells:cells, rows:detail?detail.querySelectorAll('tr').length:0};})()`);
const exC=exceptions.length;
check('邻居表不对称列+色带', nb.ok && nbTbl.th4==='不对称' && nbTbl.bgCells>0 && exC-exB===0, JSON.stringify(nbTbl));

console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
console.log('总异常:', exceptions.length);
exceptions.slice(0,3).forEach(e=>console.log(' !',e.slice(0,100)));
ws.close();process.exit(0);
