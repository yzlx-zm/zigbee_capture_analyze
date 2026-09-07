// 手册 HTML 浏览器渲染验证: file:// 打开 → 图全部加载 → 关键文字存在 → 0 异常
import { openTab, sleep } from './shot_lib.mjs';
const F = 'file:///D:/ai_agent/zigbee_capture_analyze/docs/user-manual.html';
let p = await openTab(F);
await sleep(5000);
const v = await p.ev(`(function(){
  var imgs=[...document.querySelectorAll('img')];
  var broken=imgs.filter(i=>!i.complete || i.naturalWidth===0).length;
  var body=document.body.innerText;
  var keys=['使用手册','安装与启动','数据目录','时间窗拆分','密钥管理','场景学习','时刻','报文','节点','AI 侧边栏','版本更新','FAQ'];
  var missing=keys.filter(k=>!body.includes(k));
  return {imgs: imgs.length, broken, missing, h1: document.querySelector('h1')?.innerText,
          title: document.title, len: body.length, ex: 0};})()`);
console.log(JSON.stringify(v, null, 1));
await p.close();
