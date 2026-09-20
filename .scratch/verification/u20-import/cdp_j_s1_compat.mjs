// U20-J 附: S1 修复项兼容复验 (精确时间输入 ±60s clamp + 子包清单/导入按钮)
// 背景: 原 S1 复验脚本 (s1-import/s1_verify2.mjs) 已失效 — 引用 CSV tab (.imp-tab,
// S1 自审已删除) 与临时 fixture (/_s1-*.cubx 已不存在); 本脚本覆盖受 U20 影响的
// 同等行为: 时间输入应用 (窗口标签更新) + 拆分 → 子包清单按钮齐全.
import { openTab, sleep } from '../t3-manual/shot_lib.mjs';
const FILE = 'C:/Users/Administrator/Desktop/zigbee_capture/验证可用-记录/2-群控压测问题包.cubx';
const p = await openTab('http://localhost:8720/#import');
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', { cacheDisabled: true });
await p.send('Page.navigate', { url: 'http://localhost:8720/#import' });
await sleep(3000);
const node = await p.send('DOM.getDocument', { depth: -1, pierce: true });
const q = await p.send('DOM.querySelector', { nodeId: node.result.root.nodeId, selector: '#pfinp' });
await p.send('DOM.setFileInputFiles', { nodeId: q.result.nodeId, files: [FILE] });
await p.ev(`(function(){document.getElementById('pfinp').dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
let ok = false;
for (let i = 0; i < 150; i++) {
  await sleep(1000);
  ok = await p.ev(`(function(){var el=document.getElementById('cubx-prescan');
    return !!(el && !el.classList.contains('hidden') && document.getElementById('cs-seg-hint').innerText);})()`);
  if (ok) break;
}
console.log('面板就绪:', ok);

// ── 1) 精确时间输入: 用素材首末时间 (分钟粒度) → 应用 → 窗口标签应更新 ──
const applied = await p.ev(`(function(){
  var el=document.getElementById('cubx-prescan');
  var f=new Date((+el.dataset.tsFirst)*1000), l=new Date((+el.dataset.tsLast)*1000);
  function fill(pre,d){ document.getElementById(pre+'m').value=String(d.getMonth()+1);
    document.getElementById(pre+'d').value=String(d.getDate());
    document.getElementById(pre+'h').value=String(d.getHours()).padStart(2,'0');
    document.getElementById(pre+'n').value=String(d.getMinutes()).padStart(2,'0'); }
  fill('cs-t1', f); fill('cs-t2', l);
  document.getElementById('cs-tapply').click();
  var s1=document.getElementById('cs-s1'), s2=document.getElementById('cs-s2');
  return {win:document.getElementById('cs-win').innerText, err:document.getElementById('imsg').innerText,
          s1:+s1.value, s2:+s2.value, first:+el.dataset.tsFirst, last:+el.dataset.tsLast,
          spanMin:Math.round((+s2.value - +s1.value)/60)};})()`);
console.log('[时间输入应用]', JSON.stringify(applied));
await p.shot('.scratch/verification/u20-import/j_s1_timeinput.jpg');

// ── 2) 拆分 → 子包清单含 下载 + 导入此子包 ──
await p.ev(`(function(){document.getElementById('cs-go').click();return 1;})()`);
let subs = null;
for (let i = 0; i < 120; i++) {
  await sleep(1000);
  subs = await p.ev(`(function(){var rows=document.querySelectorAll('.cs-sub-row');
    return {n:rows.length, dl:document.querySelectorAll('.cs-sub-row a[href*="/api/cubx/download"]').length,
            imp:document.querySelectorAll('.cs-sub-import').length,
            text:rows.length?rows[rows.length-1].innerText.replace(/\\n/g,' '):''};})()`);
  if (subs && subs.n > 0) break;
}
console.log('[子包清单]', JSON.stringify(subs));
console.log('exceptions:', p.exceptions.length ? p.exceptions : 'none');
await p.close();

const P = [];
const chk = (c, l) => P.push((c ? '✅ ' : '❌ ') + l);
chk(!/超出素材范围/.test(applied.err), '精确时间输入被接受 (S1 ±60s clamp) — ' + applied.err.trim());
chk(/窗口/.test(applied.win) && applied.spanMin > 40, '窗口标签更新为整段 (' + applied.spanMin + ' 分钟)');
// 精确时间输入是分钟粒度 (S1 设计): 起止被 clamp 进素材范围内即可,
// 末分钟按"该分钟起点"截断 (Δ ≤ 60s) — 语义记录在 ticket, 不擅改
chk(applied.s1 >= applied.first - 0.001 && applied.s2 <= applied.last + 0.001
    && (applied.last - applied.s2) <= 60 && (applied.s1 - applied.first) <= 60,
  `窗口在素材范围内 (起 Δ ${(applied.s1 - applied.first).toFixed(1)}s / 末 Δ ${(applied.last - applied.s2).toFixed(1)}s)`);
chk(subs && subs.n >= 1, '拆分产出子包 (' + (subs && subs.text.slice(0, 50)) + ')');
chk(subs && subs.dl === subs.n && subs.imp === subs.n, '每条子包含 下载 + 导入按钮');
chk(p.exceptions.length === 0, '无运行时异常');
console.log(P.join('\n'));
process.exit(P.some(s => s.startsWith('❌')) ? 1 : 0);
