// S2 证据帧跳转端到端 (2026-08-29 用户反馈修复验证)
// 中继包主 PAN 0x580C: L3-5 838D 证据帧 (id=5067 packet_id=5185 NS SOURCE_ROUTE_FAIL)
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

// 1. 找到 L3-5 卡第一个证据跳转链接, 记录其 id 文本
// ⚠️ 注意: .ev-jump 文本 = packet_id (抓包帧号 5185), data-pid = id (索引 5067) — 两者不同但同帧
const jumpInfo = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
    if(h&&h.textContent.includes('设备收不到网关下发')){
      var evt=cs[i].querySelector('.ev-table'); if(evt)evt.open=true;
      var j=cs[i].querySelector('.ev-jump');
      return j?{pid:j.textContent, href:j.getAttribute('href')}:null;}}
  return null;})()`);
check('找到 L3-5 证据帧跳转', !!jumpInfo && jumpInfo.href==='#tl', JSON.stringify(jumpInfo));

// 2. 点击跳转 → 报文页定位
if(jumpInfo){
  await ev(`(function(){var cs=document.querySelectorAll('.l1-card');
    for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
      if(h&&h.textContent.includes('设备收不到网关下发')){
        var j=cs[i].querySelector('.ev-jump'); if(j){j.click(); return 1;}}}
    return 0;})()`);
  await sleep(4000);  // 报文页加载 + 定位
  const loc = await ev(`(function(){
    var tr=document.querySelector('#tltb tr.hl');
    return {hash:location.hash,
            hlPid:tr?tr.dataset.pid:null,
            hlText:tr?tr.innerText.slice(0,80):null,
            stat:document.getElementById('tl-stat')?.textContent.slice(0,60)||''};})()`);
  check('跳转报文页', loc.hash.includes('#tl'), loc.hash);
  // data-pid = id (索引); 高亮行 packet_id 列应 = 证据帧 packet_id
  check('定位行 packet_id=' + jumpInfo.pid, (loc.hlText||'').startsWith(jumpInfo.pid + '\t'), `hl=${loc.hlPid}`);
  check('定位帧为 NS 0x0B', (loc.hlText||'').includes('SOURCE_ROUTE_FAIL') || (loc.hlText||'').includes('Network Status'), loc.hlText);
  console.log('  定位行:', loc.hlText, '|', loc.stat);
}

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
console.log(`\n===== 跳转端到端: ${results.filter(r=>r.ok).length}/${results.length} =====`);
ws.close();process.exit(0);
