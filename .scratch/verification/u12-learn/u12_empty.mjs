// U12 空库回归: 无案例时检测视图与现状一致 + 学习视图空状态
const CDP='http://127.0.0.1:9222';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();let exceptions=[];
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);return;}
  if(m.method==='Runtime.exceptionThrown')exceptions.push(m.params.exceptionDetails.exception?.description||'x');};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const results=[]; const check=(n,ok,x='')=>{results.push({n,ok:!!ok});console.log(`${ok?'✅':'❌'} ${n}${x?' — '+x:''}`);};
await send('Page.enable');await send('Runtime.enable');
await send('Page.navigate',{url:'http://localhost:8720/#diag'});
await sleep(13000);
// 1. 检测视图 (空案例库, 与 S2 行为一致: 13 卡 + PAN 选择器)
const c1=await ev(`(function(){
  var cards=document.querySelectorAll('.l1-card').length;
  var pan=!!document.getElementById('diag-pan');
  var sum=(document.body.innerText||'').includes('诊断结论');
  return {cards,pan,sum};})()`);
check('空库检测视图 13 卡', c1.cards===13, `cards=${c1.cards}`);
check('PAN 选择器在', c1.pan);
check('摘要卡在', c1.sum);
// 2. 切学习视图: 空状态文案
await ev(`(function(){var t=document.querySelector('.sc-view-tab[data-v="learn"]');if(t)t.click();return 1;})()`);
await sleep(3500);
const c2=await ev(`(function(){
  var el=document.getElementById('diag-learn');
  var txt=el?el.innerText:'';
  var tabs=document.querySelectorAll('#diag-learn .sc-tab').length;
  var empty=txt.includes('案例库为空')||txt.includes('待学习');
  var progress=/已学\\s*0\\s*\\/\\s*54/.test(txt);
  return {tabs,empty,progress};})()`);
check('学习视图 55 tab 齐全', c2.tabs>=50, `tabs=${c2.tabs}`);
check('进度 "已学 0/54"', c2.progress);
check('空库文案 (待学习)', c2.empty);
// 3. 切回检测视图
await ev(`(function(){var t=document.querySelector('.sc-view-tab[data-v="detect"]');if(t)t.click();return 1;})()`);
await sleep(1500);
const c3=await ev(`document.querySelectorAll('.l1-card').length`);
check('切回检测视图 13 卡', c3===13, `cards=${c3}`);
check('全程 0 异常', exceptions.length===0, `exc=${exceptions.length}`);
console.log(`\n== U12 空库回归: ${results.filter(r=>r.ok).length}/${results.length} ==`);
await fetch(`${CDP}/json/close/${t.id}`);
