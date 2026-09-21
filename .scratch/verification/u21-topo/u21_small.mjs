// U21-2: 小网络 (中继入网抓包(1): 10 节点 = 1 协调器 + 7 路由 + 2 终端, 1 个无链路证据)
// 断言: 分环正确 (1885 第1环 / 838D 第2环 / 8A41 最外无证据环) + 小网络不聚合 + 游标不跳
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';

const p = await openTab('http://localhost:8720/#topo');
await sleep(8000);

const st = await p.ev(P.state);
check('加载 10 节点小网络', st && st.nodes === 10, JSON.stringify(st));
const geo = await p.ev(P.geo);
console.log('  几何:', JSON.stringify({ rings: geo.rings, ringBad: geo.ringBad, cross: geo.cross, lblOv: geo.lblOv, hid: geo.lblHid, badge: geo.badge, bw: geo.w, bh: geo.h }));
const R = {}; geo.rows.forEach(r => R[r.aid.toString(16).toUpperCase()] = r);
console.log('  节点半径:', JSON.stringify(geo.rows.map(r => '0x' + r.aid.toString(16).toUpperCase() + ':d' + r.dep + '/R' + r.R)));
check('<50 节点不聚合 (badge=0)', geo.badge === 0, 'badge=' + geo.badge);
check('0x1885 在第 1 环', R['1885'] && R['1885'].dep === 1 && R['1885'].R === geo.rings['1'], JSON.stringify(R['1885']));
check('0x838D 在第 2 环 (半径 > 第1环)', R['838D'] && R['838D'].dep === 2 && R['838D'].R > geo.rings['1'], JSON.stringify(R['838D']));
check('0x8A41 无父证据 → 最外环 (dep 组 -1)', R['8A41'] && R['8A41'].dep === -1 && R['8A41'].R > (geo.rings['2'] || geo.rings['1']), JSON.stringify(R['8A41']));
check('同跳数同半径', geo.ringBad.length === 0, JSON.stringify(geo.ringBad));
check('树边零交叉', geo.cross === 0, String(geo.cross));
check('节点/标签无重叠', geo.nodeOv === 0 && geo.lblOv === 0, `node=${geo.nodeOv} lbl=${geo.lblOv} ${JSON.stringify(geo.lbp)}`);
check('小网络标签全显 (无隐藏)', geo.lblHid === 0, '隐藏 ' + geo.lblHid);

await p.shot('u21_small_relay.jpg');

// 游标稳定性
const posA = await p.ev(P.positions);
for (const v of [120, 400, 750, 500]) {
  await p.ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
  await sleep(400);
}
const posB = await p.ev(P.positions);
let moved = 0;
for (const k in posA) { const a = posA[k], b = posB[k]; if (!b || Math.hypot(a[0] - b[0], a[1] - b[1]) > 0.01) moved++; }
check('时刻游标拖动位置零变化', moved === 0, '位移 ' + moved);

// 布局切换回归
for (const [v, name] of [['1', '列式'], ['2', '自由'], ['0', '放射']]) {
  await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='${v}';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
  await sleep(v === '2' ? 3200 : 1800);
  const s2 = await p.ev(P.state);
  check('切' + name + ': 节点数不变', s2.nodes === 10, JSON.stringify(s2));
}
const posC = await p.ev(P.positions);
let diff = 0;
for (const k in posA) { const a = posA[k], b = posC[k]; if (!b || Math.hypot(a[0] - b[0], a[1] - b[1]) > 0.01) diff++; }
check('切回放射位置还原', diff === 0, '差异 ' + diff);

check('全程无 JS 异常', p.exceptions.length === 0, '异常 ' + p.exceptions.length + (p.exceptions[0] ? ': ' + String(p.exceptions[0]).slice(0, 120) : ''));
await p.shot('u21_small_after.jpg');
const ok = summary();
await p.close();
process.exit(ok ? 0 : 1);
