// T3 截图 4: 节点页 (表格/展开/示例弹层) + 报文详情 + 诊断页重截
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
const BASE = 'http://localhost:8720/';

// ── 1. 节点页 ──
let p = await openTab(BASE + '#nodes');
await sleep(4000);
const nd = await p.ev(`(function(){
  var head = document.querySelector('thead')?.innerText.replace(/\\n+/g,'|') || '';
  var rows = document.querySelectorAll('tbody tr').length;
  var body = document.body.innerText.slice(0,200).replace(/\\n+/g,' ');
  return {head, rows, body};})()`);
console.log('节点页表头:', nd.head, '| rows:', nd.rows);
await p.shot(D + 'nodes_main.jpg');
// 展开 838D 行
const exp = await p.ev(`(function(){
  var trs = [...document.querySelectorAll('tbody tr')];
  for (var tr of trs) { if ((tr.innerText||'').includes('838D')) { var b=tr.querySelector('button'); if(b){b.click(); return tr.innerText.replace(/\\n+/g,'|').slice(0,200);} } }
  return 'NOTFOUND';})()`);
console.log('展开 838D:', exp);
await sleep(2500);
await p.shot(D + 'nodes_expand.jpg');
// 示例弹层 (找含 示例 按钮)
const dl = await p.ev(`(function(){
  var btns=[...document.querySelectorAll('button')].filter(b=>/示例|详情|导出/.test(b.innerText));
  return btns.map(b=>b.innerText).slice(0,8);})()`);
console.log('按钮:', JSON.stringify(dl));
const ex = await p.ev(`(function(){
  var btns=[...document.querySelectorAll('button')];
  for (var b of btns){ if(/示例/.test(b.innerText)){ b.click(); return 'clicked'; } } return 'none';})()`);
await sleep(1500);
if (ex === 'clicked') { await p.shot(D + 'nodes_example.jpg'); }
await p.ev(`document.querySelector('.modal, [class*=modal] button')?.click()`);
await p.close();

// ── 2. 报文页详情 ──
p = await openTab(BASE + '#tl');
await sleep(6000);
const rowN = await p.ev(`(function(){
  var rows = [...document.querySelectorAll('tbody tr')];
  if (rows.length > 0) { var row = rows[5]; row.click(); return row.innerText.slice(0,160).replace(/\\n+/g,'|'); }
  return 'none';})()`);
console.log('点行 6:', rowN);
await sleep(2500);
await p.shot(D + 'timeline_detail.jpg');
await p.close();

// ── 3. 诊断页 (重截, 新数据) ──
p = await openTab(BASE + '#diag');
await sleep(16000);
const di = await p.ev(`(function(){
  var body=document.body.innerText;
  var i=body.indexOf('诊断结论');
  var summary = i>=0 ? body.slice(i, i+150).replace(/\\n+/g,' ') : '';
  var cards=[...document.querySelectorAll('.l1-card')].map(c=>c.querySelector('h3')?.innerText||c.className);
  return {summary, cards: cards.length, cardTitles: cards.slice(0,20).join(' / ')};})()`);
console.log('诊断:', JSON.stringify(di, null, 1));
await p.shot(D + 'diag_detect2.jpg');
// 命中卡滚动
const hit = await p.ev(`(function(){
  var els=[...document.querySelectorAll('.l1-card')].filter(c=>/已发现|命中|HIT|疑似|问题/.test(c.innerText||''));
  var first = els[0]; if(first){ first.scrollIntoView({block:'start'}); return first.querySelector('h3')?.innerText; }
  return 'NO_HIT_CARD';})()`);
console.log('滚动到:', hit);
await sleep(900);
await p.shot(D + 'diag_hit.jpg');
await p.ev(`window.scrollTo(0,0)`);
// 学习视图
await p.ev(`(function(){var t=document.querySelector('.sc-view-tab[data-v="learn"]');if(t)t.click();return 1;})()`);
await sleep(4500);
await p.shot(D + 'diag_learn2.jpg');
await p.close();
console.log('s4 done');
