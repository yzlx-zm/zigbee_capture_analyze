// S2 群控包验证: L3-2 归因修复页面级 (16 锁, 非 0x0000) + 卡片白话
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
await sleep(10000);
const E0=ex();

// 1. L3-2 卡: 16 台锁, 无 0x0000 设备行
const l32 = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
    if(h&&h.textContent.includes('命令送达但未执行'))return cs[i].innerText;}
  return 'NO';})()`);
const devCount = (l32.match(/🔍报文/g)||[]).length;
check('L3-2 16 台锁设备行', devCount===16, `${devCount} 台`);
check('L3-2 无 0x0000 行', !l32.includes('0x0000'), '');
console.log('  L3-2 前 3 行:', l32.split('\n').filter(l=>l.includes('🔍报文')).slice(0,3).join(' | '));

// 2. 摘要卡 (问题项数)
const sum = await ev(`(function(){
  var cs=document.querySelectorAll('#mc .card');
  for(var i=0;i<cs.length;i++){if(cs[i].textContent.includes('诊断结论'))return cs[i].innerText;}
  return 'NO';})()`);
console.log('  摘要:', sum.split('\n')[0]);

// 3. 空数据边界 (后端无数据时的 diag 端点) — API 层
const emptyApi = await ev(`(async function(){
  try{var r=await fetch('/api/diag/l1?pan=ZZZZ');var d=await r.json();
    return d.error?('error: '+d.error.slice(0,30)):'unexpected';}catch(e){return 'err:'+e;}})()`);
console.log('  非法 PAN 边界:', emptyApi);

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
console.log(`\n===== 群控 L3-2 验证: ${results.filter(r=>r.ok).length}/${results.length} =====`);
ws.close();process.exit(0);
