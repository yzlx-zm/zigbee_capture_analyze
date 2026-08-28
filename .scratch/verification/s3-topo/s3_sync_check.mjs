// 指针滑块同步验证: 滑块 0/500/1000 → 指针 0%/50%/100%
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
// 聚焦 60A4 (证据只覆盖素材中段 — 曾指针先到底)
await ev(`(function(){var s=document.getElementById('tsearch');s.value='838D';s.dispatchEvent(new Event('input'));var it=document.querySelector('#tsearch-list .tsearch-item');if(it)it.click();return 1;})()`);
await sleep(1500);
// 链路历史面板
await ev(`(function(){document.querySelectorAll('.bp-tab')[1].click();return 1;})()`);
await sleep(1200);
await ev(`(function(){var sel=document.getElementById('hist-sel');sel.value=sel.options[sel.options.length-1].value;sel.dispatchEvent(new Event('change'));return 1;})()`);
await sleep(2200);
// 滑块 0/500/1000 → 双指针
const sync=[];
for(const v of [0,500,1000]){
  await ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(800);
  const p = await ev(`(function(){
    var f=document.getElementById('fhist-cur');
    var h=document.getElementById('hist-cur');
    return {f:f?f.style.left:'-', h:h?h.style.left:'-'};})()`);
  sync.push({v, ...p});
}
console.log(JSON.stringify(sync,null,1));
const ex=exceptions.length;
check('滑块 0 → 指针 0%', sync[0].f==='0%'&&sync[0].h==='0%', `${sync[0].f}/${sync[0].h}`);
check('滑块 500 → 指针 50%', Math.abs(parseFloat(sync[1].f)-50)<1&&Math.abs(parseFloat(sync[1].h)-50)<1, `${sync[1].f}/${sync[1].h}`);
check('滑块 1000 → 指针 100%', sync[2].f==='100%'&&sync[2].h==='100%', `${sync[2].f}/${sync[2].h}`);
check('无异常', ex===0, `异常:${ex}`);
console.log(`\n===== 汇总: ${results.filter(r=>r.ok).length}/${results.length} =====`);
ws.close();process.exit(0);
