// S2 诊断页终验 — PAN 过滤 + 证据跳转 + 覆盖提示动态 + 重跑按钮 + 异常捕获
// 素材: test2 (9 PAN, 主 PAN 0xFEED; L3-1 全 PAN 5 台 / 主 PAN 2 台)
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

// 1. 加载 + PAN 选择器 (默认主 PAN 0xFEED)
const loadInfo = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  return {panSel:sel?sel.value:'NO',
          panOpts:sel?sel.options.length:0,
          rerun:!!document.getElementById('diag-rerun'),
          cards:document.querySelectorAll('.l1-card').length};})()`);
check('PAN 选择器默认主 PAN', loadInfo.panSel==='FEED' && loadInfo.panOpts>=9, `pan=${loadInfo.panSel} opts=${loadInfo.panOpts}`);
check('重新诊断按钮存在', loadInfo.rerun, '');

// 2. 主 PAN 下 L3-1 卡只含主网络设备 (0x6A54/0xB3AD, 无 0x89F9/0x77D0)
const l31text = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
    if(h&&h.textContent.includes('命令收不到确认'))return cs[i].innerText;}
  return 'NO';})()`);
check('L3-1 主 PAN 2 台 (无异 PAN)', l31text.includes('6A54') && l31text.includes('B3AD') && !l31text.includes('89F9') && !l31text.includes('77D0'), l31text.slice(0,120).replace(/\n/g,' '));

// 3. 事件链卡不含异 PAN 设备 (0x89F9/0x77D0 属 0x2310)
const chain = await ev(`(function(){
  var cs=document.querySelectorAll('#mc .card');
  for(var i=0;i<cs.length;i++){if(cs[i].textContent.includes('事件链提示'))return cs[i].innerText;}
  return 'NO-CHAIN';})()`);
check('事件链仅主 PAN', !chain.includes('89F9') && !chain.includes('77D0'), chain.slice(0,120).replace(/\n/g,' '));

// 4. 证据表展开 + 帧号跳转 (ev-jump)
await ev(`(function(){var d=document.querySelector('.ev-table');if(d)d.open=true;return 1;})()`);
await sleep(300);
const jump = await ev(`(function(){
  var j=document.querySelector('.ev-jump');
  return j?{exists:true, href:j.getAttribute('href'), id:j.textContent}:{exists:false};})()`);
check('证据帧号可跳转', jump.exists && jump.href==='#tl', JSON.stringify(jump));
// 点击跳转 → #tl (帧定位由 timeline 端验证)
if(jump.exists){
  await ev(`document.querySelector('.ev-jump').click()`);
  await sleep(2000);
  const hash = await ev(`location.hash`);
  check('证据帧点击 → 报文页', hash.includes('#tl'), hash);
  // 帧定位: tl 表有该行且高亮
  const hl = await ev(`(function(){
    var tr=document.querySelector('#tltb tr.hl');
    return tr?('pid='+tr.dataset.pid):'NO-HL';})()`);
  console.log('  定位行:', hl);
  await ev(`location.hash='#diag'`); await sleep(1500);
}

// 5. 切 PAN 到 0x2310 → 重新加载 (异 PAN 网络)
const panOpt = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  for(var i=0;i<sel.options.length;i++){if(sel.options[i].value==='2310'){sel.value='2310';return '2310';}}
  return 'NO-2310';})()`);
check('0x2310 PAN 选项存在', panOpt==='2310', panOpt);
if(panOpt==='2310'){
  await ev(`window.__diagPanChange('2310')`);
  await sleep(5000);
  const l31b = await ev(`(function(){
    var cs=document.querySelectorAll('.l1-card');
    for(var i=0;i<cs.length;i++){var h=cs[i].querySelector('h4');
      if(h&&h.textContent.includes('命令收不到确认'))return cs[i].innerText;}
    return 'NO';})()`);
  check('切 0x2310 后 L3-1 只剩该网络设备', l31b.includes('89F9') && l31b.includes('77D0') && !l31b.includes('6A54'), l31b.slice(0,120).replace(/\n/g,' '));
}

// 6. 重新诊断按钮 (重置回主 PAN)
await ev(`(function(){var sel=document.getElementById('diag-pan');sel.value='FEED';window.__diagRerun();return 1;})()`);
await sleep(5000);
const rerun = await ev(`(function(){
  var cs=document.querySelectorAll('.l1-card');
  var t=document.getElementById('mc').innerText;
  return {cards:cs.length, has6a54:t.includes('6A54'), has89f9:t.includes('89F9')};})()`);
check('重新诊断恢复主 PAN', rerun.cards===13 && rerun.has6a54 && !rerun.has89f9, JSON.stringify(rerun));

// 7. 覆盖提示动态化 — 0x75AD PAN 无 HIT (后端已验证) → 摘要卡显示覆盖提示
const pan75 = await ev(`(function(){
  var sel=document.getElementById('diag-pan');
  for(var i=0;i<sel.options.length;i++){if(sel.options[i].value==='75AD'){sel.value='75AD';window.__diagPanChange('75AD');return 'ok';}}
  return 'NO';})()`);
await sleep(5000);
const covText = await ev(`(function(){
  var els=document.querySelectorAll('#mc .text-dim');
  for(var i=0;i<els.length;i++){if(els[i].textContent.includes('覆盖范围'))return els[i].textContent;}
  return 'NO';})()`);
check('无 HIT PAN 显示覆盖提示', covText.includes('覆盖范围'), covText.slice(0,80));
check('覆盖提示数字动态 (13/55)', covText.includes('13/55'), covText.slice(0,80));

const E1=ex();
check('全程 0 异常', E1-E0===0, `异常:${E1-E0}`);
exceptions.slice(0,5).forEach(e=>console.log(' !',e.slice(0,120)));

console.log(`\n===== S2 终验: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
ws.close();process.exit(0);
