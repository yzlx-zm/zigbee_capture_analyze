// S2 追加验证 (2026-08-29 用户反馈): PAN 下拉全量列表
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#diag';
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
await sleep(9000);
const E0=ex();

// 1. 下拉全量 PAN (73 个) + 默认主 PAN
const panInfo = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  if(!sel)return {err:'NO-SEL'};
  var opts=[];
  for(var i=0;i<sel.options.length;i++){opts.push(sel.options[i].value+':'+sel.options[i].textContent.replace(/\\s+/g,' ').trim());}
  return {value:sel.value, count:sel.options.length, sample:opts.slice(0,6), hasC3D3:opts.some(function(o){return o.indexOf('C3D3')>=0;}), has2200:opts.some(function(o){return o.indexOf('2200')>=0;})};})()`);
check('下拉全量 PAN (73)', panInfo.count>=70, `${panInfo.count} 个`);
check('默认主 PAN 0x580C', panInfo.value==='580C', panInfo.value);
check('含异 PAN 0xC3D3/0x2200', panInfo.hasC3D3 && panInfo.has2200, '');
console.log('  选项样例:', JSON.stringify(panInfo.sample));

// 2. 切到 0xC3D3 → 诊断该网络 (L3-1 等重算)
await ev(`window.__diagPanChange('C3D3')`);
await sleep(6000);
const c3d3 = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  var cards=document.querySelectorAll('.l1-card').length;
  return {value:sel?sel.value:'', cards:cards};})()`);
check('切 0xC3D3 重跑', c3d3.value==='C3D3' && c3d3.cards===13, JSON.stringify(c3d3));

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
console.log(`\n===== PAN 全量验证: ${results.filter(r=>r.ok).length}/${results.length} =====`);
ws.close();process.exit(0);
