// T3 截图 6: 导入页 — 大包拆分面板 (4MB 素材真实触发) + 密钥面板展开
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#import');
await sleep(3500);
// CDP DOM: 注入文件到 #pfinp → change → doPI → upload-stage + prescan → 面板
const node = await p.send('DOM.getDocument', { depth: -1, pierce: true });
const q = await p.send('DOM.querySelector', { nodeId: node.result.root.nodeId, selector: '#pfinp' });
const F = 'C:/Users/Administrator/Desktop/zigbee_capture/07240934_26_0723_2300-0723_2310.cubx';
const sf = await p.send('DOM.setFileInputFiles', { nodeId: q.result.nodeId, files: [F] });
console.log('注入文件 ok');
await p.ev(`(function(){ var i=document.getElementById('pfinp'); i.dispatchEvent(new Event('change',{bubbles:true})); return 1;})()`);
await sleep(6000);
const panel = await p.ev(`(function(){
  var el=document.getElementById('cubx-prescan');
  var visible = el && !el.classList.contains('hidden');
  var info = document.getElementById('cs-info')?.innerText || '';
  var win = document.getElementById('cs-win')?.innerText || '';
  var bars = document.querySelectorAll('#cs-hist .cs-bar').length;
  var subs = document.querySelectorAll('.cs-sub-row').length;
  return {visible, info, win, bars, subs, sb: document.getElementById('sb')?.innerText};})()`);
console.log('拆分面板:', JSON.stringify(panel, null, 1));
await p.shot(D + 'import_split_panel.jpg');
// 密钥面板展开
await p.ev(`(function(){ var t=document.getElementById('pkey-toggle'); if(t && t.innerText.includes('▸')) t.click(); return 1;})()`);
await sleep(1500);
const keys = await p.ev(`(function(){
  var body=document.getElementById('pkey-body');
  var rows=body?body.querySelectorAll('tr').length:0;
  var txt=body?body.innerText.replace(/\\n+/g,'|').slice(0,300):'';
  return {rows, txt};})()`);
console.log('密钥面板:', JSON.stringify(keys));
await p.shot(D + 'import_keys.jpg');
// 关闭拆分面板 (换别的包 — 不导入, 保住 8435 数据)
await p.ev(`(function(){ var b=document.getElementById('cs-close'); if(b){b.click(); return 'closed';} return 'none';})()`);
await sleep(600);
const dataOk = await p.ev(`document.getElementById('sb')?.innerText`);
console.log('顶栏(数据应未变):', dataOk);
await p.close();
console.log('s6 done');
