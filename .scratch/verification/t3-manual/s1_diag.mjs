// T3 截图 1: 诊断页 — 检测视图 (整页) + 学习视图
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';

// ── 1. 诊断页 检测视图 ──
let p = await openTab('http://localhost:8720/#diag');
await sleep(16000); // 检测端点 + PAN 下拉
// 提取结构 (手册文字事实来源)
const info = await p.ev(`(function(){
  var pan = document.querySelector('#pan-sel') ? document.getElementById('pan-sel') : null;
  var panTxt = pan ? pan.options[pan.selectedIndex]?.text : '';
  var cards = document.querySelectorAll('.l1-card').length;
  var tabs = document.querySelectorAll('.sc-view-tab').length;
  var txt = document.body.innerText;
  var hdr = txt.slice(txt.indexOf('诊断'), txt.indexOf('诊断') + 200).replace(/\s+/g,' ').slice(0,150);
  return {panTxt, cards, tabs, hdr, ex: p_exceptions};
})()`.replace('p_exceptions','0'));
console.log('诊断页结构:', JSON.stringify(info, null, 1));
await p.shot(D + 'diag_detect.jpg');
// 滚动中段: 命中卡区域
await p.ev(`(function(){ var el=document.querySelector('.l1-card'); if(el) el.scrollIntoView({block:'center'}); return 1; })()`);
await sleep(800);
await p.shot(D + 'diag_cards.jpg');
await p.ev(`window.scrollTo(0,0)`);
// ── 2. 学习视图 ──
await p.ev(`(function(){ var t=document.querySelector('.sc-view-tab[data-v="learn"]'); if(t) t.click(); return 1; })()`);
await sleep(4500);
const learn = await p.ev(`(function(){
  var el=document.getElementById('diag-learn'); var txt=el?el.innerText:'';
  var prog=el.querySelector('.sc-progress'); var tabN=el.querySelectorAll('.sc-tab').length;
  var rows=el.querySelectorAll('.sc-mini-table tbody tr').length;
  return {prog:prog?prog.innerText.replace(/\s+/g,' '):'', tabN, rows, head:(txt||'').slice(0,80).replace(/\s+/g,' ')};})()`);
console.log('学习视图:', JSON.stringify(learn));
await p.shot(D + 'diag_learn.jpg');
await p.close();
console.log('s1 done');
