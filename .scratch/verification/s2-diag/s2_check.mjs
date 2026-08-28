// S2 诊断页稳定化 — 首轮 CDP 实测
// 素材: test2 (92 节点, 9 PAN, pcap 无 MAC 帧)
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
await sleep(12000);  // 5 端点并发, 最慢 l3/l6 ~1.8s×2
const E0=ex();

// 1. 加载结构: 卡片数 / 摘要 / 离网区
const info = await ev(`(function(){
  var cards=document.querySelectorAll('.l1-card').length;
  var secs=document.querySelectorAll('.l1-sec').length;
  var sum=document.querySelector('#mc > .card h3')?.textContent||'NO';
  var coverage=document.querySelector('.text-dim')?.textContent||'';
  var chain=document.querySelectorAll('#mc .card')[0]?.textContent||'';
  return {cards,secs,sum,coverage,chain:chain.slice(0,80)};})()`);
check('页面加载 13 卡 4 区', info.cards===13 && info.secs===4, `cards=${info.cards} secs=${info.secs}`);
check('摘要卡显示', info.sum.includes('诊断结论'), info.sum);
check('覆盖提示存在', info.coverage.includes('覆盖范围'), info.coverage.slice(0,60));
console.log('  coverage全文:', info.coverage.slice(0,120));
console.log('  chain全文:', info.chain.slice(0,120));

// 2. 事件链卡 (同设备多命中) — test2: 0x89F9 L3-1×L3-11 应触发
const chainCard = await ev(`(function(){
  var cs=document.querySelectorAll('#mc .card');
  for(var i=0;i<cs.length;i++){if(cs[i].textContent.includes('事件链提示'))return cs[i].textContent.slice(0,150);}
  return 'NO';})()`);
check('事件链卡 (0x89F9 交叉)', chainCard.includes('89F9'), chainCard.slice(0,100));

// 3. 设备 🔍报文 跳转 (U8 契约)
await ev(`(function(){var j=document.querySelector('.dev-jump');if(j)j.click();return 1;})()`);
await sleep(1500);
const jump = await ev(`location.hash`);
check('设备跳转报文页', jump.includes('#tl'), jump);
await ev(`location.hash='#diag'`);
await sleep(1500);

// 4. 证据表展开
await ev(`(function(){var d=document.querySelector('.ev-table');if(d)d.open=true;return 1;})()`);
const evt = await ev(`(function(){
  var t=document.querySelector('.ev-table table');
  return t?t.querySelectorAll('tbody tr').length:-1;})()`);
check('证据表可展开有行', evt>0, `rows=${evt}`);

// 5. L3-1 卡片内容 (多 PAN 串网检查: 命中设备数)
const l31 = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');if(h&&h.textContent.includes('命令收不到确认'))return cs[i].textContent.slice(0,300);}
  return 'NO';})()`);
console.log('  L3-1 卡内容:', l31.replace(/\\n/g,' ').slice(0,300));

// 6. 空数据边界 (后端无数据) — API 层
const empty = await ev(`(async function(){
  try{var r=await fetch('/api/diag/l3');var d=await r.json();
    return d.error?('error: '+d.error):('ok keys='+Object.keys(d).length);}catch(e){return 'err:'+e;}})()`);
check('diag/l3 API 响应', empty.startsWith('ok'), empty);

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
exceptions.slice(0,5).forEach(e=>console.log(' !',e.slice(0,150)));

console.log(`\n===== S2 首轮: ${results.filter(r=>r.ok).length}/${results.length} =====`);
ws.close();process.exit(0);
