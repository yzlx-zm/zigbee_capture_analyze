// U25: 底部面板 收起/展开 + 拖拽缩放 → 绘图区扩大 (节点更清楚)
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<90;i++){await sleep(800); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
const m0 = await p.ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();
  return {gh:Math.round(g.height), zoom:Math.round(window.__cy.zoom()*1000)/1000,
    bp:Math.round(document.getElementById('bottom-panels').getBoundingClientRect().height),
    tog:!!document.getElementById('bp-tog'), rz:!!document.getElementById('bp-resize')};})()`);
console.log('初始:', JSON.stringify(m0), JSON.stringify(st));
check('收起按钮 + 拖拽把手存在', m0.tog && m0.rz);
// 收起
await p.ev(`document.getElementById('bp-tog').click()`); await sleep(900);
const m1 = await p.ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();
  return {gh:Math.round(g.height), zoom:Math.round(window.__cy.zoom()*1000)/1000,
    bp:Math.round(document.getElementById('bottom-panels').getBoundingClientRect().height),
    txt:document.getElementById('bp-tog').textContent,
    bodyVisible:(document.getElementById('bp-routes').offsetParent!==null)};})()`);
console.log('收起后:', JSON.stringify(m1));
check('收起: 面板变矮 + 绘图区变高 + fit 放大', m1.bp<m0.bp && m1.gh>m0.gh, `面板 ${m0.bp}→${m1.bp}, 图高 ${m0.gh}→${m1.gh}`);
check('收起: 按钮文案切换 + body 隐藏', /展开/.test(m1.txt) && !m1.bodyVisible, m1.txt);
// 展开
await p.ev(`document.getElementById('bp-tog').click()`); await sleep(900);
const m2 = await p.ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();
  return {gh:Math.round(g.height), bp:Math.round(document.getElementById('bottom-panels').getBoundingClientRect().height),
    txt:document.getElementById('bp-tog').textContent};})()`);
console.log('展开后:', JSON.stringify(m2));
check('展开: 高度还原', Math.abs(m2.bp-m0.bp)<3 && /收起/.test(m2.txt), `面板 ${m2.bp} (原 ${m0.bp})`);
// 拖拽缩放 (合成 pointer 事件)
const drag = await p.ev(`(function(){
  var rz=document.getElementById('bp-resize'), bp=document.getElementById('bottom-panels');
  var r=rz.getBoundingClientRect();
  function ev(type,y){return new PointerEvent(type,{clientX:r.left+40,clientY:y,bubbles:true,pointerId:1});}
  rz.dispatchEvent(ev('pointerdown', r.top));
  rz.dispatchEvent(ev('pointermove', r.top-120));
  rz.dispatchEvent(ev('pointerup', r.top-120));
  return {bp:Math.round(bp.getBoundingClientRect().height)};})()`);
await sleep(800);
const m3 = await p.ev(`(function(){var g=document.getElementById('cy-graph').getBoundingClientRect();
  return {gh:Math.round(g.height), bp:Math.round(document.getElementById('bottom-panels').getBoundingClientRect().height),
    saved:localStorage.getItem('topoBpHeight')};})()`);
console.log('拖高 120px 后:', JSON.stringify(m3), ' (拖拽返回', JSON.stringify(drag), ')');
check('拖拽把手可放大面板 (绘图区相应变小)', m3.bp>m2.bp+80, `面板 ${m2.bp}→${m3.bp}`);
check('拖拽后高度已持久化 (localStorage)', !!m3.saved, String(m3.saved));
const ex=p.exceptions.length; check('无 JS 异常', ex===0, String(ex));
await p.shot('u25_panel.jpg');
const ok=summary(); await p.close(); process.exit(ok?0:1);
