// U21-5: 终端聚合 (手动开关) — 当前后端素材 (由页面实测决定期望值, 不写死节点数)
// 断言: 徽章数/成员数自洽 (展开前算期望) / 点击展开收起 / 定位折叠终端自动展开 / 聚合态游标不跳
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';

const p = await openTab('http://localhost:8720/#topo');
await sleep(8000);

const st0 = await p.ev(P.state);
console.log('  素材:', JSON.stringify(st0));
check('加载成功 (放射默认, 未聚合)', st0 && st0.nodes > 0 && st0.badges === 0 && st0.layout === '0', JSON.stringify(st0));

// 展开态下算期望: 每个父下终端数 ≥2 的会被折叠 (与实现规则一致: 候选=有父的 end_device)
const exp = await p.ev(`(function(){
  var c=window.__cy, byPar={}, stats={}, orphan=0, ed=0;
  c.nodes().forEach(function(n){var d=n.data();
    if(d.device_type!=='end_device')return;
    ed++;
    if(d.link_parent==null||!c.getElementById(''+d.link_parent).nonempty()){orphan++;return;}
    byPar[d.link_parent]=(byPar[d.link_parent]||0)+1;
    var s=stats[d.link_parent]||(stats[d.link_parent]={rejoining:0,offline:0,sleeping:0});
    if(s[d.behavior]!=null)s[d.behavior]++;});
  var badges=0,members=0,expStats={};
  for(var k in byPar){if(byPar[k]>=2){badges++;members+=byPar[k];expStats[k]=stats[k];}}
  return {ed:ed,orphan:orphan,badges:badges,members:members,byPar:byPar,expStats:expStats,
    visibleReal:c.nodes().length-(c.nodes('[is_badge]').length)};})()`);
console.log('  期望: 终端 ' + exp.ed + ' (无父 ' + exp.orphan + ') → 徽章 ' + exp.badges + ' 个 / 折叠 ' + exp.members + ' 台');

if (exp.badges === 0) { console.log('⚠️ 本素材无可聚合簇 → 跳过聚合断言'); }
else {
  await p.ev(`document.getElementById('tagg').click()`);
  await sleep(2200);
  const st1 = await p.ev(P.state);
  const geo1 = await p.ev(P.geo);
  const inner = geo1.badges.reduce((a, b) => a + b.cnt, 0);
  console.log('  聚合后:', JSON.stringify(st1), '徽章:', JSON.stringify(geo1.badges.map(b => b.lbl)));
  check('徽章数 = 期望簇数', st1.badges === exp.badges, `${st1.badges} vs ${exp.badges}`);
  check('徽章成员合计 = 期望折叠数', inner === exp.members, `${inner} vs ${exp.members}`);
  check('可见实节点 + 成员 = 总节点', st1.nodes - st1.badges + inner === st0.nodes - 0,
    `${st1.nodes - st1.badges}+${inner} vs ${st0.nodes}`);
  check('徽章贴附父节点 (<80px)', geo1.badgeDist.every(b => b.dist > 0 && b.dist < 80), JSON.stringify(geo1.badgeDist));
  check('徽章标签 ×N 与成员数一致', geo1.badges.every(b => b.lbl.indexOf('×' + b.cnt) === 0), JSON.stringify(geo1.badges.map(b => b.lbl)));
  check('聚合态: 零交叉/零重叠', geo1.cross === 0 && geo1.nodeOv === 0 && geo1.lblOv === 0,
    JSON.stringify({ c: geo1.cross, n: geo1.nodeOv, l: geo1.lblOv, lbp: geo1.lbp }));
  // 状态汇总一致性: 徽章状态 = 折叠前同簇终端的实际状态 (U14 信息不丢)
  const stCmp = geo1.badges.map(b => {
    const e = exp.expStats[b.pa] || { rejoining: 0, offline: 0, sleeping: 0 };
    return { id: b.id, stats: b.stats, expect: e, ok: b.stats.rejoining === e.rejoining && b.stats.offline === e.offline && b.stats.sleeping === e.sleeping };
  });
  check('徽章状态汇总 = 折叠前同簇终端状态 (U14 信息不丢)', stCmp.every(b => b.ok), JSON.stringify(stCmp));
  check('有状态时徽章标签带图标', stCmp.every(b => (b.stats.rejoining || b.stats.offline || b.stats.sleeping) ? /⚠️|⛔|💤/.test(geo1.badges.find(x => x.id === b.id).lbl) : true),
    JSON.stringify(geo1.badges.map(b => b.lbl)));
  await p.shot('.scratch/verification/u21-topo/u21_agg_on.jpg');

  // 聚合态游标
  const posA = await p.ev(P.positions);
  for (const v of [150, 500, 850]) {
    await p.ev(`(function(){var sl=document.getElementById('tsl');sl.value=${v};onTimeSlide();return 1;})()`);
    await sleep(500);
  }
  const posB = await p.ev(P.positions);
  let mv = 0; for (const k in posA) { const a = posA[k], b = posB[k]; if (!b || Math.hypot(a[0] - b[0], a[1] - b[1]) > 0.01) mv++; }
  check('聚合态拖动游标位置零变化', mv === 0, '位移 ' + mv);

  // 展开/收起
  const big = geo1.badges.reduce((a, b) => b.cnt > a.cnt ? b : a);
  await p.ev(`(function(){window.__cy.getElementById('${big.id}').emit('tap');return 1;})()`);
  await sleep(2000);
  const st2 = await p.ev(P.state);
  const geo2 = await p.ev(P.geo);
  check('点击 ×' + big.cnt + ' 徽章 → 展开', st2.nodes - st2.badges === (st1.nodes - st1.badges) + big.cnt && st2.badges === st1.badges,
    `${st1.nodes - st1.badges}→${st2.nodes - st2.badges} 实节点 (展开 ${big.cnt})`);
  const openB = geo2.badges.filter(b => b.open);
  check('展开态徽章标 ▾', openB.length === 1 && /▾/.test(openB[0].lbl), JSON.stringify(openB.map(b => b.lbl)));
  check('展开后零交叉/零重叠', geo2.cross === 0 && geo2.nodeOv === 0 && geo2.lblOv === 0, JSON.stringify({ c: geo2.cross, n: geo2.nodeOv, l: geo2.lblOv, lbp: geo2.lbp }));
  await p.shot('.scratch/verification/u21-topo/u21_agg_open.jpg');
  await p.ev(`(function(){window.__cy.getElementById('${big.id}').emit('tap');return 1;})()`);
  await sleep(1800);
  const st3 = await p.ev(P.state);
  check('再点击 → 收起还原', st3.nodes === st1.nodes && st3.badges === st1.badges, JSON.stringify(st3));

  // 定位折叠终端 → 自动展开 + 高亮
  const member = await p.ev(`(function(){return window.__cy.getElementById('${big.id}').data('members')[0];})()`);
  const memHex = member.toString(16).toUpperCase().padStart(4, '0');
  console.log('  定位折叠终端 0x' + memHex);
  await p.ev(`(function(){var i=document.getElementById('taddr');i.value='${memHex}';
    i.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('tgo').click();return 1;})()`);
  await sleep(2200);
  const loc = await p.ev(`(function(){var n=window.__cy.getElementById('${member}');
    return {exists:n.nonempty(),hl:n.hasClass('highlight'),title:(document.getElementById('taddr')||{}).title};})()`);
  check('定位折叠终端 → 自动展开该簇 + 高亮', loc.exists && loc.hl, JSON.stringify(loc));
  await p.shot('.scratch/verification/u21-topo/u21_agg_locate.jpg');

  // 关闭聚合
  await p.ev(`document.getElementById('tagg').click()`);
  await sleep(1800);
  const st4 = await p.ev(P.state);
  check('关闭聚合 → 全展开还原', st4.nodes === st0.nodes && st4.badges === 0, JSON.stringify(st4));

  // 非放射下点聚合 → 切回放射
  await p.ev(`(function(){var s=document.getElementById('tlaymode');s.value='1';s.dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
  await sleep(2000);
  await p.ev(`document.getElementById('tagg').click()`);
  await sleep(2200);
  const st5 = await p.ev(P.state);
  check('列式下点聚合 → 自动切回放射并聚合', st5.layout === '0' && st5.badges === exp.badges, JSON.stringify(st5));
  await p.ev(`document.getElementById('tagg').click()`);
  await sleep(1500);
}
const btn = await p.ev(`(function(){var b=document.getElementById('tagg');return {text:b.textContent,on:b.classList.contains('on'),title:b.title};})()`);
check('聚合按钮常显 (不在 ⋯ 视图 收纳内)', btn.text.indexOf('聚合') >= 0, JSON.stringify(btn));
const ex = p.exceptions.length;
check('全程无 JS 异常', ex === 0, '异常 ' + ex + (p.exceptions[0] ? ': ' + String(p.exceptions[0]).slice(0, 140) : ''));
const ok = summary();
await p.close();
process.exit(ok ? 0 : 1);
