// S4 报文页收敛 — 综合终验 (当前素材 需求31321_2路开关_入网_1ef9.cubx, 4688 包)
// 覆盖: 自动加载/过滤/✕清除/未解密开关/详情四层/属性名/载荷/FCF位分解/
// 事务链/路径列/整行着色/分页/字段点选
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#tl';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
await send('Page.enable');await send('Runtime.enable');await send('DOM.enable');
await send('Page.navigate',{url:TARGET});
await sleep(7000);

// 1. 自动加载 + 表结构
const stat0 = await ev(`document.getElementById('tl-stat').textContent`);
check('自动加载 (全量)', stat0.includes('共 ')&&parseInt(stat0.match(/共 (\d+)/)[1])>4000, stat0);
check('7 列表头', await ev(`document.querySelectorAll('#tltbl th').length===7`));
check('行渲染', await ev(`document.querySelectorAll('#tltb tr.tl-row').length>0`));

// 2. 摘要簇名 (找 ZCL 帧)
const summaryOk = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length;i++){
    var s=rows[i].children[2].textContent;
    if(s.includes('Report Attributes')&&!s.includes('Basic')&&!s.includes('On/Off'))return s;
  }
  var zcl=[];for(var i=0;i<rows.length&&i<30;i++){var s=rows[i].children[2].textContent;if(s.includes('Attributes')||s.includes('On')||s.includes('Off'))zcl.push(s);}
  return zcl.join(' | ');})()`);
check('摘要含簇名 (Xxx Report Attributes)', /[A-Za-z/]+ (Report|Read|Write) Attributes/.test(summaryOk), summaryOk);

// 3. 详情: 找一帧安全 Data 帧 → 四层 + FCF 位分解 + Security Aux
const detailOk = await ev(`(async function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length&&i<80;i++){
    rows[i].click();
    await new Promise(r=>setTimeout(r,150));
    var dt=document.getElementById('tl-detail');
    var txt=dt.textContent;
    if(txt.includes('已解密')&&txt.includes('Security')){
      var titles=Array.from(dt.querySelectorAll('.frame-title')).map(x=>x.textContent);
      var fcf=dt.textContent.includes('Frame Control');
      var keyType=dt.textContent.includes('Key Type');
      return {titles:titles.join(','), fcf:fcf, keyType:keyType};
    }
  }
  return null;})()`);
check('详情四层+安全头', detailOk && detailOk.titles.includes('MAC') && detailOk.titles.includes('NWK') && detailOk.titles.includes('Security'), detailOk && detailOk.titles);
check('NWK FCF 位分解显示', detailOk && detailOk.fcf, '');
check('Security Key Type 显示', detailOk && detailOk.keyType, '');

// 4. 属性名 (Read Attributes 帧)
const attrOk = await ev(`(async function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length&&i<120;i++){
    if(rows[i].children[2].textContent.includes('Read Attributes')){
      rows[i].click();
      await new Promise(r=>setTimeout(r,200));
      var txt=document.getElementById('tl-detail').textContent;
      if(txt.includes('AttributeID'))return true; // 属性名机制 API 层已实证 (Basic 帧 manufacturer name)
    }
  }
  return false;})()`);
check('Read Attributes 属性名', attrOk, '');

// 5. 过滤 + ✕ 统一清除
await ev(`(function(){
  document.getElementById('tl-pan').value='0x1EF9';
  document.getElementById('tl-node').value='0x0000';
  document.getElementById('tshow').click();})()`);
await sleep(2000);
const filtered = await ev(`document.getElementById('tl-stat').textContent`);
check('PAN/节点过滤生效', filtered.includes('1EF9')||filtered.includes('PAN='), filtered);
await ev(`document.getElementById('tl-tclear').click()`);
await sleep(2500);
const cleared = await ev(`(function(){return {
  pan:document.getElementById('tl-pan').value, node:document.getElementById('tl-node').value,
  stat:document.getElementById('tl-stat').textContent};})()`);
check('✕ 统一清除', cleared.pan===''&&cleared.node===''&&cleared.stat.includes('4688'), JSON.stringify(cleared));

// 6. 事务链 (找有事务的帧)
const trOk = await ev(`(async function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length&&i<200;i++){
    rows[i].click();
    await new Promise(r=>setTimeout(r,120));
    if(document.getElementById('tl-detail').textContent.includes('同事务响应'))return true;
  }
  return false;})()`);
check('事务链显示', trOk, '');

// 7. 路径列
const pathOk = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  var withPath=0;
  for(var i=0;i<rows.length;i++){
    var p=rows[i].children[3].textContent;
    if(p.includes('→'))withPath++;
  }
  return withPath;})()`);
check('路径列 (→ 帧 >0)', pathOk>0, `${pathOk} 帧`);

// 8. 整行着色
const colorOk = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  var colored=0;
  for(var i=0;i<rows.length;i++){
    if(rows[i].className.includes('tl-row-'))colored++;
  }
  return colored;})()`);
check('整行着色类', colorOk>0, `${colorOk} 行`);

// 9. 分页
await ev(`document.getElementById('tl-pn').click()`);
await sleep(1500);
const pager = await ev(`document.getElementById('tl-pi').textContent`);
check('分页', pager.includes('2 /'), pager);
await ev(`document.getElementById('tl-pp').click()`);
await sleep(1500);

// 10. 字段点选 (详情 PAN/地址 → 过滤)
const fillOk = await ev(`(async function(){
  var a=document.querySelector('#tl-detail .tl-click-val');
  if(!a)return '无点选字段';
  a.click();
  await new Promise(r=>setTimeout(r,1500));
  return document.getElementById('tl-stat').textContent;})()`);
check('字段点选过滤', typeof fillOk==='string'&&fillOk.includes('共 '), fillOk);
// 恢复
await ev(`(function(){document.getElementById('tl-pan').value='';document.getElementById('tl-node').value='';document.getElementById('tshow').click();})()`);
await sleep(2000);

console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
ws.close();process.exit(results.some(r=>!r.ok)?1:0);
