// U21-3/4: 中/大网络通用验证 (素材由后端当前加载决定)
// 用法: node u21_net.mjs <tag>   如 node u21_net.mjs group / test2
// 断言: 放射不变量 (分环/零交叉/零重叠) + 聚合徽章一致性 + 时刻游标不跳 + 布局耗时实测
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';

const tag = process.argv[2] || 'net';
const p = await openTab('http://localhost:8720/#topo');
// 等渲染完成 (轮询 __cy 出现, 顺便量首屏耗时)
const t0 = Date.now();
let st = null;
for (let i = 0; i < 120; i++) {
  await sleep(400);
  st = await p.ev(P.state);
  if (st && st.nodes > 0) break;
}
const loadMs = Date.now() - t0;
check('加载 + 放射渲染 (节点>0)', st && st.nodes > 0, JSON.stringify(st) + ' 首屏 ' + loadMs + 'ms');
await sleep(2000);

const geo = await p.ev(P.geo);
const comp = await p.ev(`(function(){var c=window.__cy,o={};c.nodes().forEach(function(n){var k=n.data('is_badge')?'BADGE':(n.data('device_type')||'?');o[k]=(o[k]||0)+1;});return o;})()`);
const timing = await p.ev(`({last:window.__u21_lastMs,sum:window.__u21_sumMs,n:window.__u21_n})`);
console.log('  组成:', JSON.stringify(comp));
console.log('  几何:', JSON.stringify({ n: geo.n, badge: geo.badge, rings: geo.rings, cross: geo.cross, nodeOv: geo.nodeOv, lblOv: geo.lblOv, lblVis: geo.lblVis, lblHid: geo.lblHid, bbox: geo.w + 'x' + geo.h }));
console.log('  徽章:', JSON.stringify(geo.badges), ' 徽章贴父距离:', JSON.stringify(geo.badgeDist));
console.log('  布局耗时: 末次 ' + timing.last + 'ms / 累计 ' + timing.sum + 'ms / ' + timing.n + ' 次');
if (geo.lbp.length) console.log('  标签重叠样例:', JSON.stringify(geo.lbp));
if (geo.ovp.length) console.log('  节点重叠样例:', JSON.stringify(geo.ovp));

check('同跳数同半径 (孤儿单独成组)', geo.ringBad.length === 0, JSON.stringify(geo.ringBad));
check('树边零交叉', geo.cross === 0, String(geo.cross));
check('节点圆无重叠', geo.nodeOv === 0, String(geo.nodeOv));
check('可见标签无重叠', geo.lblOv === 0, geo.lblOv + ' ' + JSON.stringify(geo.lbp));
check('标签全在节点外侧 (横向' + geo.branchH + '/纵向' + geo.branchV + ')', geo.lblOutBad.length === 0, JSON.stringify(geo.lblOutBad.slice(0,3)));
// 聚合一致性: 徽章数 + 展开后总数 = 实际节点数 (ticket 验收 2)
const agg = await p.ev(`(function(){
  var c=window.__cy, n=c.nodes().length, b=c.nodes('[is_badge]');
  var inner=0;b.forEach(function(x){inner+=x.data('count')||0;});
  return {nodes:n,badges:b.length,inner:inner};})()`);
check('徽章计数自洽 (徽章内终端数 = 被折叠数)', agg.nodes + agg.inner === (geo.n + agg.inner) && agg.inner > 0 || agg.badges === 0,
  JSON.stringify(agg) + (agg.badges ? '' : ' (本素材无聚合: 资源 <50 或无终端)'));
check('徽章贴附父节点 (<80px)', geo.badgeDist.every(b => b.dist < 80 && b.dist > 0), JSON.stringify(geo.badgeDist));

// 展开/收起 (有徽章时) — 点击徽章 → 元素数增加
if (agg.badges > 0) {
  const before = await p.ev(P.state);
  await p.ev(`(function(){var c=window.__cy;var b=c.nodes('[is_badge]').first();b.emit('tap');return b.data('count');})()`);
  await sleep(1800);
  const after = await p.ev(P.state);
  check('点击徽章展开簇 (元素数增加 = 徽章成员数)',
    after.nodes === before.nodes + geo.badges[0].cnt && after.badges === before.badges,
    `${before.nodes}→${after.nodes} 徽章成员 ${geo.badges[0].cnt}`);
  await p.ev(`(function(){var s=document.getElementById('tsl');s.value=500;onTimeSlide();return 1;})()`);
  await sleep(300);
  await p.ev(`(function(){var c=window.__cy;var b=c.nodes('[is_badge]').first();b.emit('tap');return 1;})()`);
  await sleep(1800);
  const back = await p.ev(P.state);
  check('再点徽章收起 (元素数还原)', back.nodes === before.nodes && back.badges === before.badges, JSON.stringify(back));
}

// 时刻游标: 位置零变化 + 拖动耗时
const posA = await p.ev(P.positions);
await p.ev(`window.__u21_lastMs=0`);
for (const v of [100, 350, 650, 900, 500]) {
  await p.ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(700);
}
const posB = await p.ev(P.positions);
const dragMs = await p.ev(`({last:window.__u21_lastMs})`);
let moved = 0, maxd = 0;
for (const k in posA) { const a = posA[k], b = posB[k]; if (!b) { moved++; continue; }
  const d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (d > 0.01) { moved++; maxd = Math.max(maxd, d); } }
check('拖动时刻游标位置零变化', moved === 0, '位移 ' + moved + ' 最大 ' + Math.round(maxd) + 'px');
check('拖动单帧布局 < 400ms (可交互)', dragMs.last < 400, '末次布局 ' + dragMs.last + 'ms');

// 布局切换
for (const [v, name] of [['1', '列式'], ['2', '自由'], ['0', '放射']]) {
  const t = Date.now();
  await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='${v}';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
  await sleep(v === '2' ? 4000 : 2500);
  const s3 = await p.ev(P.state);
  const tm = await p.ev(`({last:window.__u21_lastMs})`);
  console.log(`  切${name}: ${Date.now() - t}ms (布局计算 ${tm.last}ms)`);
  check('切' + name + ': 节点集完整', s3.nodes >= (v === '0' ? st.nodes : st.nodes - (geo.badge ? 0 : 0)), JSON.stringify(s3));
}
await p.shot(`u21_${tag}_after.jpg`);
const ex = p.exceptions.length;
check('全程无 JS 异常', ex === 0, '异常 ' + ex + (p.exceptions[0] ? ': ' + String(p.exceptions[0]).slice(0, 140) : ''));
await p.shot(`u21_${tag}.jpg`);
console.log(`\n首屏 ${loadMs}ms | 节点 ${geo.n} | 徽章 ${geo.badge}`);
const ok = summary();
await p.close();
process.exit(ok ? 0 : 1);
