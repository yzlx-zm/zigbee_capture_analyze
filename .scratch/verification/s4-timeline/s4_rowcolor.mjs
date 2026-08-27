// S4: 整行层级着色验证 — 行文字色跟随层级 + 摘要无背景 + 选中行优先级
const CDP='http://127.0.0.1:9222', TARGET='http://localhost:8720/#tl';
const t=await (await fetch(`${CDP}/json/new?about:blank`,{method:'PUT'})).json();
const ws=new WebSocket(t.webSocketDebuggerUrl);await new Promise(r=>ws.onopen=r);
let id=0;const pending=new Map();
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);}};
const send=(method,params={})=>new Promise(res=>{const i=++id;pending.set(i,res);ws.send(JSON.stringify({id:i,method,params}));});
const ev=async expr=>{const r=await send('Runtime.evaluate',{expression:expr,returnByValue:true,awaitPromise:true});return r.result?.result?.value;};
const results=[];const check=(n,c,x='')=>{results.push({n,ok:!!c});console.log(`${c?'✅':'❌'} ${n}${x?' — '+x:''}`);};
await send('Page.enable');await send('Runtime.enable');await send('DOM.enable');
await send('Page.navigate',{url:TARGET});
await new Promise(r=>setTimeout(r,6000));
// 1. 行级类存在
const rowInfo = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  var classes={};
  for(var i=0;i<rows.length;i++){
    var c=rows[i].className;
    var m=c.match(/tl-row-(\w+)/);
    if(m)classes[m[1]]=(classes[m[1]]||0)+1;
  }
  return classes;})()`);
check('行级层级类存在 (≥3 类)', Object.keys(rowInfo).length>=3, JSON.stringify(rowInfo));
// 2. 整行文字色跟随层级 (取 zcl 行: 所有 td color 相同)
const zclRow = await ev(`(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row.tl-row-zcl');
  if(!rows.length)return null;
  var r=rows[0];
  var colors={};
  for(var j=0;j<r.children.length;j++){
    colors[getComputedStyle(r.children[j]).color]=true;
  }
  return {ncols:r.children.length, colors:Object.keys(colors)};})()`);
check('ZCL 行整行同色 (全部 td)', zclRow && zclRow.colors.length===1, JSON.stringify(zclRow));
// 3. 摘要无背景
const sumBg = await ev(`(function(){
  var s=document.querySelector('#tltb .tl-summary');
  if(!s)return null;
  return getComputedStyle(s).backgroundColor;
})()`);
check('摘要无淡背景 (transparent)', !sumBg || sumBg==='rgba(0, 0, 0, 0)' || sumBg==='transparent', sumBg);
// 4. 选中行优先级 (点击行 → hl → td 深色)
await ev(`(function(){var r=document.querySelector('#tltb tr.tl-row.tl-row-zcl');if(r)r.click();})()`);
await new Promise(r=>setTimeout(r,800));
const hlColor = await ev(`(function(){
  var r=document.querySelector('#tltb tr.hl');
  if(!r)return '无选中行';
  return getComputedStyle(r.children[0]).color;})()`);
check('选中行文字深色 (hl 优先级)', hlColor==='rgb(31, 41, 55)', hlColor);
console.log(`\n${results.filter(r=>r.ok).length}/${results.length} 通过`);
ws.close();process.exit(0);
