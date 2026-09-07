// T3 截图 5: 节点页展开/示例弹层 + AI 侧边栏 (面板/设置)
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
const BASE = 'http://localhost:8720/';
let p;

// ── 1. 节点页: 展开 838D 行 ──
p = await openTab(BASE + '#nodes');
await sleep(4000);
const r = await p.ev(`(function(){
  var rows=[...document.querySelectorAll('tr.nd-row')];
  for(var tr of rows){ if((tr.innerText||'').includes('838D')){ tr.click(); return tr.innerText.replace(/\\n+/g,'|'); } }
  return 'NOTFOUND';})()`);
console.log('838D 行:', r);
await sleep(2500);
const hasDetail = await p.ev(`(function(){
  var d=document.querySelector('.nd-detail[data-for]'); return d ? !d.classList.contains('hidden') : false;})()`);
console.log('展开可见:', hasDetail);
await p.shot(D + 'nodes_expand2.jpg');
// 滚动到控制命令统计表 (含 📄 示例按钮)
const sam = await p.ev(`(function(){
  var b=document.querySelector('.nd-sample'); if(!b) return 'NO_SAMPLE_BTN';
  b.scrollIntoView({block:'center'}); return 1;})()`);
await sleep(700);
if (sam === 1) { await p.shot(D + 'nodes_clusters.jpg'); }
// 点示例 → 弹层
const op = await p.ev(`(function(){
  var b=document.querySelector('.nd-sample'); if(!b) return 'none'; b.click(); return 'ok';})()`);
await sleep(2000);
await p.shot(D + 'nodes_example2.jpg');
const exTxt = await p.ev(`(function(){
  var m=document.querySelector('.nd-modal-box, [class*=modal]');
  return m ? m.innerText.slice(0,200).replace(/\\n+/g,'|') : '';})()`);
console.log('示例弹层文本:', exTxt.slice(0,150));
// 关闭弹层
await p.ev(`(function(){ var b=document.querySelector('.nd-modal-box .btn, [class*=modal] button'); if(b)b.click(); return 1;})()`);
await p.close();

// ── 2. AI 侧边栏 ──
p = await openTab(BASE + '#diag');
await sleep(7000);
const fab = await p.ev(`(function(){ var f=document.getElementById('zc-ai-fab'); if(!f) return 'NO_FAB'; f.click(); return 'clicked';})()`);
console.log('fab:', fab);
await sleep(1500);
const panel = await p.ev(`(function(){
  var p=document.getElementById('zc-ai-panel'); if(!p) return null;
  return {visible: p.offsetParent!==null, txt: p.innerText.slice(0,120).replace(/\\n+/g,'|')};})()`);
console.log('AI 面板:', JSON.stringify(panel));
await p.shot(D + 'ai_panel.jpg');
// 切设置 tab
const cfg = await p.ev(`(function(){
  var t=[...document.querySelectorAll('#zc-ai-panel button, #zc-ai-panel [role=tab]')].find(b=>/设置|配置/.test(b.innerText));
  if(t){t.click(); return 'clicked';} return 'none';})()`);
console.log('设置 tab:', cfg);
await sleep(1200);
const keyState = await p.ev(`(function(){
  var s=document.getElementById('zc-ai-key-state'); var k=document.getElementById('zc-ai-key');
  return {state: s?s.innerText:'', keyType: k?k.type:'', keyLen: k?k.value.length:-1, base: (document.getElementById('zc-ai-base')||{}).value||''};})()`);
console.log('key 状态:', JSON.stringify(keyState));
await p.shot(D + 'ai_config.jpg');
// 切回对话 tab, 发一条纯知识问题 (不涉及包 → 知识检索)
const backTab = await p.ev(`(function(){
  var t=[...document.querySelectorAll('#zc-ai-panel button, #zc-ai-panel [role=tab]')].find(b=>/对话|知识|问答/.test(b.innerText));
  if(t){t.click(); return 'clicked';} return 'none';})()`);
await sleep(800);
const sent = await p.ev(`(function(){
  var i=document.getElementById('zc-ai-in'); var s=document.getElementById('zc-ai-send');
  if(!i||!s) return 'NO_INPUT';
  i.value='Zigbee 设备入网流程中哪些因素会导致入网失败？'; s.click(); return 'sent';})()`);
console.log('发送知识问题:', sent);
await sleep(20000);
await p.shot(D + 'ai_kb_result.jpg');
const kb = await p.ev(`(function(){
  var m=document.getElementById('zc-ai-msgs'); return m?m.innerText.slice(0,300).replace(/\\n+/g,'|'):'';})()`);
console.log('KB 结果:', kb.slice(0,220));
await p.close();
console.log('s5 done');
