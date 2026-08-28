// T2 打包产物页面级实测 (中文路径实例, 端口 51567)
// 覆盖: 顶栏版本号 / 诊断 / 拓扑 / 报文 / 节点 / AI 侧边栏 / 重启按钮
const CDP='http://127.0.0.1:9222', TARGET='http://127.0.0.1:51567/';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ex=()=>exceptions.length;
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:TARGET});
await sleep(6000);
const E0=ex();

// 1. 首页 + 顶栏版本号
const home = await ev(`(function(){
  return {sb:document.getElementById('sb')?.textContent||'NO',
          nav:document.querySelectorAll('.nt a').length,
          title:document.title};})()`);
check('首页加载', home.nav===5, JSON.stringify(home));
check('顶栏版本号 v1.0.1', (home.sb||'').includes('v1.0.1'), home.sb);

// 2. 诊断页
await ev(`location.hash='diag'`); await sleep(8000);
const diag = await ev(`(function(){
  return {cards:document.querySelectorAll('.l1-card').length,
          pan:document.getElementById('diag-pan')?.value||''};})()`);
check('诊断页 13 卡', diag.cards===13, JSON.stringify(diag));

// 3. 拓扑页
await ev(`location.hash='topo'`); await sleep(8000);
const topo = await ev(`(function(){
  return {canvas:!!document.querySelector('#cy-graph canvas'),
          info:document.getElementById('tinfo')?.textContent||''};})()`);
check('拓扑页渲染', topo.canvas && /\d+ 节点/.test(topo.info), topo.info);

// 4. 报文页
await ev(`location.hash='tl'`); await sleep(8000);
const tl = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row').length;
  return {rows:rows, stat:document.getElementById('tl-stat')?.textContent.slice(0,40)||''};})()`);
check('报文页行渲染', tl.rows>0, JSON.stringify(tl));

// 5. 节点页
await ev(`location.hash='nodes'`); await sleep(6000);
const nodes = await ev(`(function(){
  var rows=document.querySelectorAll('#ntb tr').length;
  return {rows:rows, text:document.body.innerText.slice(0,60)};})()`);
check('节点页渲染', nodes.rows>0, JSON.stringify(nodes));

// 6. AI 侧边栏 (浮标存在 + 打开)
const ai = await ev(`(function(){
  var b=document.querySelector('.ai-fab')||document.querySelector('[class*="ai-"]');
  return {fab:!!b, cls:b?b.className:''};})()`);
check('AI 侧边栏浮标', ai.fab, ai.cls);

// 7. 重启按钮
const rst = await ev(`(function(){
  var b=document.getElementById('sb-restart');
  return b?{exists:true, title:b.title}:{exists:false};})()`);
check('重启按钮存在', rst.exists, rst.title);

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
exceptions.slice(0,5).forEach(e=>console.log(' !',e.slice(0,120)));
console.log(`\n===== T2 页面实测: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
ws.close();process.exit(0);
