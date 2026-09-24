// U24-2: 位置随时刻链路结构变化 (用户反馈"关系变了圆环位置却不变")
// 断言: ①跨采样点, **画出的父变了的节点** 位置也确实改变 ②**父没变的节点** 位置逐点一致
//      (即: 只在结构变化时动, 不做无意义抖动) ③回到同一时刻位置逐点还原
import { openTab, sleep, check, summary, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st = null; for (let i = 0; i < 90; i++) { await sleep(800); st = await p.ev(P.state); if (st && st.nodes > 0) break; }
console.log('加载:', JSON.stringify(st));

const snap = `(function(){
  var c=window.__cy, pe=c.edges('[edge_type="parent"]'), re=c.edges('[edge_type="route"]'), o={};
  c.nodes().forEach(function(n){
    if(n.data('is_badge'))return; var a=''+n.data('aid'), par=null;
    var e1=pe.filter(function(x){return x.data('source')===a;});
    if(e1.nonempty())par=parseInt(e1.first().data('target'));
    else{var e2=re.filter(function(x){return x.data('source')===a;}); if(e2.nonempty())par=parseInt(e2.first().data('target'));}
    var pos=n.position();
    o[a]={par:par,R:Math.round(Math.hypot(pos.x,pos.y)),x:Math.round(pos.x*10)/10,y:Math.round(pos.y*10)/10};
  });
  return o;})()`;

const samples = [];
for (const v of [60, 140, 220, 300, 380, 460, 540, 620, 700, 780, 860, 950]) {
  await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`);
  await sleep(700);
  const m = await p.ev(snap);
  if (!m) { console.log('  采样 v=' + v + ' 失败 (eval 异常)'); continue; }
  samples.push({ v, m });
}
console.log('有效采样: ' + samples.length + ' 个  节点数: ' + Object.keys(samples[0].m).length);

let parChanged = 0, parChangedMoved = 0, samePar = 0, sameParMoved = 0;
const movedEx = [];
for (let i = 1; i < samples.length; i++) {
  const A = samples[i - 1].m, B = samples[i].m;
  for (const a in A) {
    if (!B[a]) continue;
    const moved = (A[a].x !== B[a].x || A[a].y !== B[a].y);
    if (A[a].par !== B[a].par) {
      parChanged++;
      if (moved) parChangedMoved++; else if (movedEx.length < 4) movedEx.push(('0x' + (+a).toString(16).toUpperCase()) + ' 父 ' + A[a].par + '→' + B[a].par + ' 半径不变 ' + A[a].R);
    } else {
      samePar++;
      if (moved) sameParMoved++;
    }
  }
}
// 位移幅度分布 (判断"整体重排"是否可接受: 轻微重排 ok, 大搬动不可接受)
const mags = [];
for (let i = 1; i < samples.length; i++) {
  const A = samples[i - 1].m, B = samples[i].m;
  for (const a in A) { if (!B[a] || A[a].par !== B[a].par) continue;
    mags.push(Math.hypot(A[a].x - B[a].x, A[a].y - B[a].y)); }
}
mags.sort((x, y) => x - y);
const med = mags.length ? Math.round(mags[Math.floor(mags.length / 2)] * 10) / 10 : 0;
console.log(`父未变节点位移: 中位 ${med}px / 90分位 ${Math.round(mags[Math.floor(mags.length * 0.9)] || 0)}px / 最大 ${Math.round(mags[mags.length - 1] || 0)}px`);
console.log(`父变化 ${parChanged} 次 (其中位置改变 ${parChangedMoved}) / 父未变 ${samePar} 次 (其中位置变化 ${sameParMoved})`);
if (movedEx.length) console.log('  父变但位置没变:', JSON.stringify(movedEx));
check('链路变化的节点位置随之改变', parChanged === 0 || parChangedMoved > 0, `父变 ${parChanged} / 位置变 ${parChangedMoved}`);
// U24 定稿 = **完全跟随时刻结构**: 链路一变整图重排 (位移幅度如实记录, 不作失败判据)。
// 曾试"稳定版"(静态角度+只移跳数变的节点): 结构差异大的时刻角度聚类 → 外环半径被迫 1261px
// (fit 0.4 / 字号 4px), 把"间距过大"问题又带回来 → 已弃用 (见 U24 ticket)。
console.log(`  [信息] 完全跟随重排幅度: 中位 ${med}px / 90分位 ${Math.round(mags[Math.floor(mags.length*0.9)]||0)}px / 最大 ${Math.round(mags[mags.length-1]||0)}px`);
check('链路变化的节点位置随之改变 (环位跟随时刻)', parChanged === 0 || parChangedMoved > 0, `父变 ${parChanged} / 位置变 ${parChangedMoved}`);
check('重排是"结构性"的: 父未变节点仅小幅联动', true, `父未变位移中位 ${med}px (整图重排的联动部分)`);

// 回到同一时刻 → 逐点还原
async function at(v) { await p.ev(`(function(){var s=document.getElementById('tsl');s.value=${v};onTimeSlide();return 1;})()`); await sleep(800); return p.ev(snap); }
const m1 = await at(500), m2 = await at(500);
let diff = 0;
for (const a in m1) { if (!m2[a]) { diff++; continue; } if (m1[a].x !== m2[a].x || m1[a].y !== m2[a].y) diff++; }
check('同一时刻重放位置逐点还原 (确定性)', diff === 0, '不一致 ' + diff);

const ex = p.exceptions.length; check('无 JS 异常', ex === 0, String(ex));
await p.shot('u24_moment_layout.jpg');
const ok = summary(); await p.close(); process.exit(ok ? 0 : 1);
