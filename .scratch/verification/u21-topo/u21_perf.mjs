// U21/U22 性能诊断: 拓扑页在大素材 (173 万帧) 的加载与交互耗时拆分
// 断言: 首屏 / 首个 events 请求耗时 / 布局耗时 / 拖游标 / 切布局 / 切 PAN 全部有实测数字
import { openTab, sleep, P } from './u21_lib.mjs';

const tNav = Date.now();
const p = await openTab('http://localhost:8720/#topo');
let st = null, firstRenderMs = null;
for (let i = 0; i < 600; i++) { await sleep(200); st = await p.ev(P.state); if (st && st.nodes > 0) { firstRenderMs = Date.now() - tNav; break; } }
await sleep(2500);
const net = await p.ev('window.__net||[]');
const layout0 = await p.ev('({last:window.__u21_lastMs,sum:window.__u21_sumMs,n:window.__u21_n})');
const nav = await p.ev(`(function(){var t=performance.getEntriesByType('navigation')[0]||{};return {dom:t.domContentLoadedEventEnd?Math.round(t.domContentLoadedEventEnd):null,load:t.loadEventEnd?Math.round(t.loadEventEnd):null};})()`);

console.log('=== 冷启动 (导入后第一次) ===');
console.log('  首屏 (nav → 图出现节点): ' + firstRenderMs + 'ms');
console.log('  DOMContentLoaded/load: ' + JSON.stringify(nav));
console.log('  网络请求:');
net.forEach(n => console.log(`    ${String(n.dur).padStart(6)}ms  start=${String(n.start).padStart(6)}ms  ${n.status}  ${n.u}`));
console.log('  布局应用 (last/sum/n): ' + JSON.stringify(layout0));
console.log('  节点/边/徽章: ' + JSON.stringify(await p.ev(P.state)));

// 拖游标 5 帧
const t1 = Date.now();
await p.ev('window.__u21_lastMs=0;window.__u21_sumMs=0;window.__u21_n=0');
for (const v of [100, 300, 500, 700, 900]) {
  await p.ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(800);
}
const drag = await p.ev('({last:window.__u21_lastMs,sum:window.__u21_sumMs,n:window.__u21_n})');
console.log('=== 拖游标 (5 帧) ===  墙钟 ' + (Date.now() - t1) + 'ms  布局: ' + JSON.stringify(drag));

// 切布局三档
for (const [v, name] of [['1', '列式'], ['2', '自由'], ['0', '放射']]) {
  const t = Date.now();
  await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='${v}';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
  await sleep(v === '2' ? 4200 : 2600);
  const l = await p.ev('({last:window.__u21_lastMs})');
  console.log(`=== 切${name} === 墙钟 ${Date.now() - t}ms (布局 ${l.last}ms)`);
}

// 再测一次 events 请求 (热: 服务端已缓存)
const t2 = Date.now();
const warm = await p.ev(`fetch('/api/topology/events').then(r=>r.json()).then(d=>({ms:0,nodes:d.nodes.length}))`);
const warmMs = Date.now() - t2;
console.log('=== events 端点热请求 === 墙钟 ' + warmMs + 'ms ' + JSON.stringify(warm));
console.log('=== 网络总计 ===');
(await p.ev('window.__net||[]')).forEach(n => console.log(`    ${String(n.dur).padStart(6)}ms  ${n.u}`));
console.log('异常: ' + p.exceptions.length);
await p.close();
process.exit(0);
