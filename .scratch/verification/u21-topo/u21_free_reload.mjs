// U21-6: 自由布局 × 页面重进 (cy 新建) — 曾会全堆原点 (renderGraph 不重排位置的边界)
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';

const p = await openTab('http://localhost:8720/#topo');
await sleep(9000);
const st0 = await p.ev(P.state);
check('初次加载', st0 && st0.nodes > 0, JSON.stringify(st0));

// 切自由 + 等力导
await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='2';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
await sleep(4500);
const fr = await p.ev(`(function(){var c=window.__cy,o=[];c.nodes().forEach(function(n){o.push(n.position());});
  var mid=o.filter(function(q){return Math.abs(q.x)<1&&Math.abs(q.y)<1;}).length;
  return {n:o.length,at0:mid,layout:(document.getElementById('tlaymode')||{}).value};})()`);
check('切自由: 力导生效 (非全体原点)', fr.layout === '2' && fr.at0 < fr.n * 0.5, JSON.stringify(fr));

// 重进页面 (cy 销毁重建, curLayout 模块级保留 = 自由) → 必须重跑力导
await p.send('Page.navigate', { url: 'http://localhost:8720/#topo' });
await sleep(11000);
const st1 = await p.ev(P.state);
const geo = await p.ev(`(function(){var c=window.__cy,o=[];c.nodes().forEach(function(n){o.push(n.position());});
  var mid=o.filter(function(q){return Math.abs(q.x)<1&&Math.abs(q.y)<1;}).length;
  var bb=c.nodes().boundingBox();
  return {n:o.length,at0:mid,w:Math.round(bb.w),h:Math.round(bb.h),layout:(document.getElementById('tlaymode')||{}).value};})()`);
check('重进页面: 布局档位保留 (自由)', st1 && st1.layout === '2', JSON.stringify(st1));
check('重进页面: 自由布局重新排布 (无原点堆叠)', geo.at0 < geo.n * 0.5 && geo.w > 10, JSON.stringify(geo));

// 切回放射 → 位置正常
await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='0';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
await sleep(2500);
const g2 = await p.ev(P.geo);
check('切回放射: 分环正常', g2.ringBad.length === 0 && g2.cross === 0, JSON.stringify({ ringBad: g2.ringBad, cross: g2.cross }));
const ex = p.exceptions.length;
check('全程无异常', ex === 0, '异常 ' + ex + (p.exceptions[0] ? ': ' + String(p.exceptions[0]).slice(0, 120) : ''));
const ok = summary();
await p.close();
process.exit(ok ? 0 : 1);
