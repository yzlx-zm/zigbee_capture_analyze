// T3 截图 3: 导入页 / 拓扑页 / 报文页
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
const BASE = 'http://localhost:8720/';

let p = await openTab(BASE + '#import');
await sleep(4000);
const imp = await p.ev(`(function(){
  var body = document.body.innerText;
  var inputs = [...document.querySelectorAll('input[type=file]')].length;
  var keysBtn = [...document.querySelectorAll('button')].map(b=>b.innerText).filter(t=>/密钥|key/i.test(t));
  var panBtns = [...document.querySelectorAll('button')].map(b=>b.innerText).filter(t=>/导入|选择|浏览/.test(t));
  var sb = document.getElementById('sb')?.innerText || '';
  return {inputs, keysBtn, panBtns, sb, head: body.slice(0,180).replace(/\\n+/g,' | ')};})()`);
console.log('导入页:', JSON.stringify(imp, null, 1));
await p.shot(D + 'import_main.jpg');
await p.close();

p = await openTab(BASE + '#topo');
await sleep(15000);
const topo = await p.ev(`(function(){
  var body = document.body.innerText.replace(/\\n+/g,' ');
  var m = body.match(/图节点: (\\d+)[^|]*|图节点:(\\d+)/);
  var stat = body.indexOf('拓扑统计') >= 0 ? body.slice(body.indexOf('拓扑统计'), body.indexOf('拓扑统计')+220) : '';
  var sel = document.querySelector('select');
  return {stat: stat.slice(0,200), panOpts: sel ? sel.options.length : 0};})()`);
console.log('拓扑页:', JSON.stringify(topo, null, 1));
await p.shot(D + 'topo_main.jpg');
await p.close();

p = await openTab(BASE + '#tl');
await sleep(6000);
const tl = await p.ev(`(function(){
  var body = document.body.innerText;
  var rows = document.querySelectorAll('tbody tr, .pkt-row').length;
  var sel = document.querySelector('select');
  var chk = document.querySelectorAll('input[type=checkbox]').length;
  return {rows, selects: document.querySelectorAll('select').length, chk, sb: document.getElementById('sb')?.innerText,
          head: body.slice(0,150).replace(/\\n+/g,' | ')};})()`);
console.log('报文页:', JSON.stringify(tl, null, 1));
await p.shot(D + 'timeline_main.jpg');
await p.close();
console.log('s3 done');
