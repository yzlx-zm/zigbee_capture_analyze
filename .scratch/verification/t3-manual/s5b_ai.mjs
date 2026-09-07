// AI 知识检索重测: 发问 → 观察消息区 (成功结果/失败降级文案都截图)
import { openTab, sleep } from './shot_lib.mjs';
const D = '.scratch/verification/t3-manual/';
let p = await openTab('http://localhost:8720/#diag');
await sleep(6000);
await p.ev(`(function(){ var f=document.getElementById('zc-ai-fab'); f.click(); return 1;})()`);
await sleep(1200);
await p.ev(`(function(){
  var i=document.getElementById('zc-ai-in');
  i.value='Zigbee 协调器与路由器的区别是什么？';
  i.dispatchEvent(new Event('input',{bubbles:true}));
  return 1;})()`);
await sleep(400);
const sendState = await p.ev(`(function(){
  var s=document.getElementById('zc-ai-send');
  return {disabled: s.disabled, txt: s.innerText};})()`);
console.log('send 状态:', JSON.stringify(sendState));
await p.ev(`document.getElementById('zc-ai-send').click()`);
await sleep(3000);
const st1 = await p.ev(`(function(){
  var m=document.getElementById('zc-ai-msgs'); return m?m.innerText.slice(0,400).replace(/\\n+/g,'|'):'NO_MSGS';})()`);
console.log('3s 后:', st1.slice(0,300));
await sleep(25000);
const st2 = await p.ev(`(function(){
  var m=document.getElementById('zc-ai-msgs'); return m?m.innerText.slice(0,600).replace(/\\n+/g,'|'):'NO_MSGS';})()`);
console.log('28s 后:', st2.slice(0,500));
await p.shot(D + 'ai_kb_result2.jpg');
const ex = await p.ev(`(function(){ var el=document.querySelector('.ai-system,.ai-error,#zc-ai-msgs .err,#zc-ai-msgs .ai-error'); return el?el.innerText:'NO_ERR_EL';})()`);
console.log('错误元素:', ex.slice(0,200));
await p.close();
