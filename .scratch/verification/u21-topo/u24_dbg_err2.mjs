import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
await sleep(6000);
const r = await p.ev(`(function(){
  try{ if(!window.S||!S.topo)return 'no S.topo';
    var before=!!window.__cy;
    // 直接触发页面重渲染路径 (页面自己吞了异常, 这里手动捕获)
    var el=document.getElementById('tgo'); el.click();
    return 'clicked, before='+before;
  }catch(e){ return 'err: '+e.message; }})()`);
console.log('触发:', r);
await sleep(3000);
console.log('state:', JSON.stringify(await p.ev(P.state)));
// 再试: 用 __cy 存在性 + 页面内 try 包裹 renderGraph 调用
const r2 = await p.ev(`(function(){
  try{ window.__cy=window.__cy||null; return 'cy='+!!window.__cy; }catch(e){ return 'e2: '+e.message; }})()`);
console.log(r2);
console.log('exceptions:', JSON.stringify(p.exceptions.slice(0,3)));
await p.close(); process.exit(0);
