// S2 诊断页最终稳定性终验 (2026-08-29) — 中继入网抓包(1) (真实故障素材)
// 覆盖: 加载/PAN 下拉/摘要/13 卡/L3-5 838D 命中/证据跳转/切 PAN/重跑/离线区/异常捕获
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

// 1. 加载 + PAN 下拉 + 摘要 (⚠️ 摘要卡 h3 含"诊断结论", header 是第一个 .card)
const info = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  var cs=document.querySelectorAll('.l1-card');
  var hs=document.querySelectorAll('#mc .card h3');var sum='NO';
  for(var i=0;i<hs.length;i++){if(hs[i].textContent.includes('诊断结论'))sum=hs[i].textContent;}
  return {pan:sel?sel.value:'NO', panN:sel?sel.options.length:0,
          cards:cs.length, secs:document.querySelectorAll('.l1-sec').length,
          sum:sum};})()`);
check('加载 13 卡 4 区', info.cards===13 && info.secs===4, JSON.stringify(info));
check('PAN 下拉全量 (默认主 PAN)', info.pan==='580C' && info.panN>=70, `pan=${info.pan} n=${info.panN}`);
check('摘要卡显示', info.sum.includes('诊断结论'), info.sum);

// 2. L3-5 真实故障命中 (838D R1)
const l35 = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
    if(h&&h.textContent.includes('设备收不到网关下发'))return cs[i].innerText;}
  return 'NO';})()`);
check('L3-5 命中 838D', l35.includes('838D') && l35.includes('下行'), l35.split('\n')[0]);

// 3. 摘要问题项 (L3-5 命中) — ⚠️ 摘要卡 h3 含"诊断结论" (header 是第一个 .card)
const sumTxt = await ev(`(function(){
  var cs=document.querySelectorAll('#mc .card h3');
  for(var i=0;i<cs.length;i++){if(cs[i].textContent.includes('诊断结论'))return cs[i].textContent;}
  return 'NO';})()`);
check('摘要发现问题', sumTxt.includes('发现问题'), sumTxt);

// 4. 证据表跳转 (L3-5 帧 → NS 0x0B) — ⚠️ 必须点 L3-5 卡内 .ev-jump (非全局首个)
await ev(`(function(){var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
    if(h&&h.textContent.includes('设备收不到网关下发')){var e=cs[i].querySelector('.ev-table');if(e)e.open=true;return 1;}}
  return 0;})()`);
await sleep(300);
const j = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
    if(h&&h.textContent.includes('设备收不到网关下发')){
      var a=cs[i].querySelector('.ev-jump');return a?a.textContent:null;}}
  return null;})()`);
check('L3-5 证据帧号可点击', j!=null, '#'+j);
if(j!=null){
  await ev(`(function(){
    var cs=document.querySelectorAll('.l1-card');
    for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
      if(h&&h.textContent.includes('设备收不到网关下发')){
        var a=cs[i].querySelector('.ev-jump');if(a){a.click();return 1;}}}
    return 0;})()`);
  await sleep(3500);
  const hl = await ev(`(function(){
    var tr=document.querySelector('#tltb tr.hl');
    return tr?tr.innerText.slice(0,80):'NO-HL';})()`);
  check('L3-5 跳转定位 NS 0x0B', hl.includes('SOURCE_ROUTE_FAIL')||hl.includes('Network Status'), hl.split('\n')[0].split('\t')[0]+' '+hl.split('\t')[2]);
  await ev(`location.hash='#diag'`); await sleep(1500);
}

// 5. 切 PAN (0xC3D3) + 重跑
await ev(`(function(){var sel=document.getElementById('diag-pan');
  for(var i=0;i<sel.options.length;i++){if(sel.options[i].value==='C3D3'){sel.value='C3D3';break;}}
  window.__diagPanChange('C3D3');return 1;})()`);
await sleep(6000);
const c3 = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  var t=document.getElementById('mc').innerText;
  return {pan:sel?sel.value:'', has838D:t.includes('838D')&&t.includes('命令收不到确认')};})()`);
check('切 0xC3D3 重跑', c3.pan==='C3D3', JSON.stringify(c3));

// 6. 重新诊断按钮 (回主 PAN)
await ev(`(function(){var sel=document.getElementById('diag-pan');sel.value='580C';window.__diagRerun();return 1;})()`);
await sleep(6000);
const rerun = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  var t=document.getElementById('mc').innerText;
  return {pan:sel?sel.value:'', has838D:t.includes('838D')};})()`);
check('重新诊断回主 PAN 838D 命中', rerun.pan==='580C' && rerun.has838D, JSON.stringify(rerun));

// 7. 离线区 (中继包有 Leave 事件)
const off = await ev(`(function(){
  var t=document.getElementById('mc').innerText;
  return {hasOffline:t.includes('设备离线总览')||t.includes('离网事件'),
          hasLeave:t.includes('Leave')};})()`);
check('离线区渲染', off.hasOffline, JSON.stringify(off));

// 8. 事件链卡
const chain = await ev(`(function(){
  var cs=document.querySelectorAll('#mc .card');
  for(var i=0;i<cs.length;i++){if(cs[i].textContent.includes('事件链提示'))return cs[i].innerText.slice(0,120);}
  return 'NO-CHAIN';})()`);
console.log('  事件链:', chain.slice(0,100).replace(/\n/g,' '));

// 9. API 边界: 非法 pan + 空数据端点
const apiBound = await ev(`(async function(){
  var out={};
  try{var r=await fetch('/api/diag/l3?pan=ZZZZ');out.invalid=(await r.json()).l3_5? 'ok':'unexpected';}catch(e){out.invalid='err:'+e;}
  try{var r2=await fetch('/api/diag/pans');var d2=await r2.json();out.pans=d2.pans.length>0?'ok':'empty';}catch(e){out.pans='err:'+e;}
  return out;})()`);
check('API 边界 (非法 pan/空 pans)', apiBound.invalid==='ok' && apiBound.pans==='ok', JSON.stringify(apiBound));

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
exceptions.slice(0,5).forEach(e=>console.log(' !',e.slice(0,150)));

console.log(`\n===== S2 稳定性终验: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
ws.close();process.exit(0);
