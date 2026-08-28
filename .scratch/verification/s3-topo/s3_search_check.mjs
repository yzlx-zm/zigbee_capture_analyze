// S3 节点过滤验证: 侧栏搜索 + 🎯 聚焦按钮 + 聚焦横幅 4 行布局
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

// 1. 侧栏节点搜索存在
const hasSearch = await ev(`(function(){
  var s=document.getElementById('tsearch');
  return {input:!!s, list:!!document.getElementById('tsearch-list'),
          tfocus:!!document.getElementById('tfocus')};})()`);
check('搜索框/列表/聚焦按钮存在', hasSearch.input && hasSearch.list && hasSearch.tfocus, JSON.stringify(hasSearch));

// 2. 搜索匹配 (型号/地址)
const hits = await ev(`(function(){
  var s=document.getElementById('tsearch');
  s.value='0071';s.dispatchEvent(new Event('input'));
  var items=document.querySelectorAll('#tsearch-list .tsearch-item');
  return {count:items.length, first:items[0]?items[0].textContent.slice(0,40):''};})()`);
check('搜索 0071 匹配', hits.count>0, JSON.stringify(hits));

// 3. 点击搜索项 → 聚焦
await ev(`(function(){var it=document.querySelector('#tsearch-list .tsearch-item');if(it)it.click();return 1;})()`);
await sleep(1500);
const focus = await ev(`(function(){
  var b=document.getElementById('focus-bar');
  return {disp:b?b.style.display:'NO', title:document.querySelector('.fhist-aid')?.textContent||'NO',
          hint:document.querySelector('.fhist-hint')?.textContent||'NO',
          hist:!!document.getElementById('focus-hist'),
          info:document.getElementById('fhist-info')?.textContent.slice(0,50)||''};})()`);
const exA=exceptions.length;
check('搜索点击聚焦 (4行布局)', focus.disp==='flex' && focus.title.includes('聚焦') && focus.hist && exA===0, JSON.stringify(focus));

// 4. 🎯 聚焦按钮 (输入地址 → 聚焦)
await ev(`(function(){document.getElementById('focus-exit').click();return 1;})()`);
await sleep(1200);
await ev(`(function(){var t=document.getElementById('taddr');t.value='9F1B';document.getElementById('tfocus').click();return 1;})()`);
await sleep(1500);
const focusBtn = await ev(`document.querySelector('.fhist-aid')?.textContent||'NO'`);
const exB=exceptions.length;
check('🎯 按钮聚焦 0x9F1B', focusBtn.includes('9F1B') && exB-exA===0, `${focusBtn} | 异常:${exB-exA}`);

// 5. 退出
await ev(`document.getElementById('focus-exit').click()`);
await sleep(1200);
const exC=exceptions.length;
check('退出无异常', exC-exB===0, `异常:${exC-exB}`);

console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
console.log('总异常:', exceptions.length);
exceptions.slice(0,3).forEach(e=>console.log(' !',e.slice(0,100)));
ws.close();process.exit(0);
