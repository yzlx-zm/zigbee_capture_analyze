// S3 拓扑页最终稳定性终验 — 全功能覆盖 + 异常捕获
// 素材: 中继入网抓包(1).cubx (8435 帧, 主 PAN 0x580C) / test2 (92 节点) 切换验证
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#topo';
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

// 1. 加载 + 结构
const loadInfo = await ev(`(function(){
  return {canvas:!!document.querySelector('#cy-graph canvas'),
          tinfo:document.getElementById('tinfo')?.textContent||'NO',
          panList:document.querySelectorAll('.pan-row').length,
          legend:!!document.getElementById('legend-pop')};})()`);
check('加载 (canvas+tinfo)', loadInfo.canvas && /\d+ 节点/.test(loadInfo.tinfo), loadInfo.tinfo);
check('PAN 列表渲染', loadInfo.panList>0, `${loadInfo.panList} 个`);
check('图例存在', loadInfo.legend, '');

// 2. 节点搜索 + 聚焦 + 退出 (素材自适应: 取第一个有链路段的节点)
const testAid = await ev(`(function(){
  var ns=(S.topo&&S.topo.nodes)||[];
  var snaps=(S.topo&&S.topo.link_snapshots)||{};
  for(var i=0;i<ns.length;i++){if(snaps[''+ns[i].aid])return ns[i].aid;}
  return ns.length?ns[0].aid:null;})()`);
check('找到测试节点', testAid!=null, testAid!=null?('0x'+testAid.toString(16).toUpperCase().padStart(4,'0')):'');
// 修复: 嵌套模板字符串会原样输出 — 先拼好搜索值再注入
// ⚠️ testAid=0 (协调器) 是 falsy — 用 !=null 判断 (JS 经典坑)
const testHex = testAid!=null?('0x'+testAid.toString(16).toUpperCase().padStart(4,'0')):'';
await ev(`(function(){var s=document.getElementById('tsearch');s.value='${testHex}';s.dispatchEvent(new Event('input'));var it=document.querySelector('#tsearch-list .tsearch-item');if(it)it.click();return 1;})()`);
await sleep(1500);
const focus1 = await ev(`(function(){
  return {disp:document.getElementById('focus-bar').style.display,
          segs:document.querySelectorAll('.fhist-seg').length,
          switches:document.querySelectorAll('.fhist-switch').length,
          info:document.getElementById('fhist-info')?.textContent.slice(0,50)||''};})()`);
const E1=ex();
check('搜索聚焦 (时间轴+切换点)', focus1.disp==='flex' && focus1.segs>0 && E1-E0===0, JSON.stringify(focus1));
await ev(`document.getElementById('focus-exit').click()`);
await sleep(1200);
const E2=ex();
check('退出聚焦无异常', E2-E1===0, '');

// 3. 时刻游标拖动 (残影) — 多次拖动
for(const v of [0,300,600,1000]){
  await ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(900);
}
const E3=ex();
const curInfo = await ev(`(function(){
  return {tsCursor:document.getElementById('ts-cursor')?.style.left||'NO',
          label:document.getElementById('ttime-label')?.textContent||''};})()`);
check('时刻游标多位置拖动无异常', E3-E2===0, `异常:${E3-E2}`);
check('刻度条指针跟随', curInfo.tsCursor!=='NO', curInfo.tsCursor);

// 4. 布局切换往返 + 视图组
await ev(`document.getElementById('tviews').click()`);
await sleep(300);
await ev(`document.getElementById('tlay').click()`);
await sleep(1200);
await ev(`document.getElementById('tlay').click()`);
await sleep(1200);
const E4=ex();
const layBtn = await ev(`document.getElementById('tlay').textContent`);
check('布局切换+视图组无异常', E4-E3===0, `${layBtn} | 异常:${E4-E3}`);

// 5. 链路历史面板 (指针 + 段)
await ev(`(function(){document.querySelectorAll('.bp-tab')[1].click();return 1;})()`);
await sleep(1200);
await ev(`(function(){var sel=document.getElementById('hist-sel');if(sel){sel.value=sel.options[sel.options.length-1].value;sel.dispatchEvent(new Event('change'));}return 1;})()`);
await sleep(2200);
const hist = await ev(`(function(){
  return {segs:document.querySelectorAll('.hist-seg').length,
          cursor:!!document.getElementById('hist-cur'),
          info:document.getElementById('hist-info')?.textContent.slice(0,40)||''};})()`);
const E5=ex();
check('链路历史面板 (段+指针)', hist.segs>0 && hist.cursor && E5-E4===0, JSON.stringify(hist));

// 6. 邻居面板 (不对称列 + 色带)
await ev(`(function(){document.querySelectorAll('.bp-tab')[2].click();return 1;})()`);
await sleep(1200);
await ev(`(function(){var sel=document.getElementById('nb-dev-sel');if(sel){sel.value=sel.options[1].value;showNbTable();}return 1;})()`);
await sleep(800);
const nb = await ev(`(function(){
  var th=document.querySelector('#nb-detail th:nth-child(4)')?.textContent||'';
  var bg=document.querySelectorAll('#nb-detail td[style*="background"]').length;
  return {th4:th, bgCells:bg};})()`);
const E6=ex();
check('邻居表不对称列+色带', nb.th4==='不对称' && nb.bgCells>0 && E6-E5===0, JSON.stringify(nb));

// 7. 路由路径链行点击聚焦
await ev(`(function(){document.querySelectorAll('.bp-tab')[0].click();return 1;})()`);
await sleep(800);
await ev(`(function(){var r=document.querySelector('#bp-routes .path-row[data-pidx]');if(r)r.click();return 1;})()`);
await sleep(1500);
const rowFocus = await ev(`document.querySelector('.fhist-aid')?.textContent||'NO'`);
const E7=ex();
check('路径行点击聚焦', rowFocus.includes('聚焦') && E7-E6===0, rowFocus);
await ev(`document.getElementById('focus-exit').click()`);
await sleep(1000);

// 8. PAN 切换 + 重置
await ev(`(function(){var rows=document.querySelectorAll('.pan-row');if(rows.length>1)rows[1].click();return 1;})()`);
await sleep(2200);
await ev(`document.getElementById('trst').click()`);
await sleep(2200);
const E8=ex();
const rst = await ev(`document.getElementById('tpan')?.value`);
check('PAN 切换+重置无异常', rst==='' && E8-E7===0, `pan='${rst}' | 异常:${E8-E7}`);

// 9. tgo 动态文案
const dyn = await ev(`(function(){
  document.getElementById('taddr').value='838D';
  document.getElementById('taddr').dispatchEvent(new Event('input'));
  var t1=document.getElementById('tgo').textContent;
  document.getElementById('taddr').value='';
  document.getElementById('tpan').value='580C';
  document.getElementById('tpan').dispatchEvent(new Event('input'));
  var t2=document.getElementById('tgo').textContent;
  document.getElementById('tpan').value='';
  document.getElementById('tpan').dispatchEvent(new Event('input'));
  return {loc:t1, pan:t2};})()`);
check('tgo 动态 (定位/筛PAN)', dyn.loc==='🔍 定位' && dyn.pan==='🔍 筛PAN', JSON.stringify(dyn));

// 10. 空数据边界 (后端无数据时空态) — API 层验证
const emptyApi = await ev(`(async function(){
  try{var r=await fetch('/api/topology/events');var d=await r.json();
    return {nodes:d.nodes.length};}catch(e){return {err:String(e)};}})()`);
check('events API 正常响应', emptyApi.nodes>=0, JSON.stringify(emptyApi));

console.log(`\n===== S3 终验汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
results.forEach(r=>console.log(`${r.ok?'✅':'❌'} ${r.n}`));
console.log(`\n总异常: ${exceptions.length} 条`);
exceptions.slice(0,5).forEach(e=>console.log(' !',e.slice(0,120)));
ws.close();process.exit(0);
