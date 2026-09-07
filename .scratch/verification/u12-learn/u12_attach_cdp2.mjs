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
await ev(`(function(){var t=document.querySelector('.sc-view-tab[data-v="learn"]');if(t)t.click();return 1;})()`);
await sleep(3500);
const st=await ev(`(function(){
  // 案例行 = 含场景 tag L3-5 且含中继/838D 现象的行; 直接扫所有 mini-table 行
  var all=document.querySelectorAll('#diag-learn .sc-mini-table tbody tr');
  var caseRows=[];
  for(var i=0;i<all.length;i++){
    var h=all[i].innerHTML;
    if(h.includes('📦')||h.includes('📎补')||h.includes('838D')) caseRows.push(h);
  }
  var txt=caseRows.join('|');
  return {caseRows:caseRows.length, hasBox:txt.includes('📦'), hasAttach:txt.includes('📎补'),
          gapRows:(document.querySelectorAll('#diag-learn .sc-mini-table tbody tr').length-caseRows.length)};})()`);
check('案例行存在 (📦 或 📎补 或 838D)', st.caseRows>=1, `rows=${st.caseRows}`);
check('案例行显示 📦 (素材已补)', st.hasBox, st.hasAttach?('attached='+st.hasAttach):'');
check('差距表行 (L1-2 missed)', st.gapRows>=1, `gap=${st.gapRows}`);
check('0 异常', exceptions.length===0, `exc=${exceptions.length}`);
console.log(`\n== U12 补素材 CDP2: ${results.filter(r=>r.ok).length}/${results.length} ==`);
await fetch(`${CDP}/json/close/${t.id}`);
