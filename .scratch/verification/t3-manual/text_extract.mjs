// 报文页/诊断页 UI 文案提取 (手册文字事实源)
import { openTab, sleep } from './shot_lib.mjs';
let p = await openTab('http://localhost:8720/#tl');
await sleep(6500);
const tl = await p.ev(`(function(){
  var th=[...document.querySelectorAll('thead th')].map(x=>x.innerText).join('|');
  var tr=[...document.querySelectorAll('tbody tr')].slice(0,3).map(x=>x.innerText.replace(/\\n+/g,'|'));
  var labels=[...document.querySelectorAll('label')].map(x=>x.innerText);
  var filters=[...document.querySelectorAll('.tl-filter, .f-row, [class*=filter]')].length;
  var body=document.body.innerText;
  var i0=body.indexOf('PAN:');
  return {th, rows:tr, labels, filters, around: i0>=0? body.slice(i0, i0+300).replace(/\\n+/g,'|'):'NOPAN'};})()`);
console.log(JSON.stringify(tl, null, 1));
await p.close();

p = await openTab('http://localhost:8720/#diag');
await sleep(16000);
const di = await p.ev(`(function(){
  // 卡头结构: 编号小角标 + 白话标题
  var card=document.querySelector('.l1-card');
  var inner = card ? card.outerHTML.slice(0, 900) : '';
  return {sample: inner};})()`);
console.log('卡片 HTML 样本:', di.sample.replace(/\n+/g,''));
await p.close();
