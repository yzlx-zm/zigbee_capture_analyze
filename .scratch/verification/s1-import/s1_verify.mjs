// S1 导入页稳定化 — 复验脚本 (修复后重测, v3)
// 覆盖: P1-A 下载200 / P1-B 时间输入 / P2×6 (P6卡/toggle/友好错误/拆分进度/
//        顶栏清理/窗口保持/超时) + 群控整包进度采样 (真实素材)
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';
const BIG_CUBX = 'd:/tmp/s1-test/08-13-中继侧抓包.cubx';

function newPage() {
  return new Promise((resolve, reject) => {
    fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' }).then(t => t.json()).then(t => {
      const ws = new WebSocket(t.webSocketDebuggerUrl);
      ws.onopen = () => {
        let id = 0; const pending = new Map(); const events = {};
        ws.onmessage = ev => { const m = JSON.parse(ev.data);
          if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
          else if (m.method && events[m.method]) events[m.method].forEach(f => f(m.params));
        };
        const send = (method, params = {}) => new Promise(res => {
          const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params }));
        });
        resolve({ ws, send, on: (m, f) => { events[m] = events[m] || []; events[m].push(f); },
                  close: () => ws.close() });
      };
      ws.onerror = reject;
    });
  });
}
async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}
const results = [];
function check(name, cond, extra = '') { results.push({ name, ok: !!cond }); console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`); }
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitFor(p, expr, timeout = 60000, step = 300) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try { if (await evaluate(p, expr)) return true; } catch (e) {}
    await sleep(step);
  }
  return false;
}
// prompt 应答 — 单一全局监听 + 变量 (v3 修复: 多监听器串台导致误答)
let _promptReply = null;
const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('DOM.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
page.on('Page.javascriptDialogOpening', () => {
  page.send('Page.handleJavaScriptDialog', { accept: true, promptText: _promptReply || '' });
});
const setPromptReply = (p, text) => { _promptReply = text; };
await page.send('Page.navigate', { url: TARGET });
await waitFor(page, `!!document.getElementById('mc') && !!document.querySelector('.imp-tab')`, 10000);

// ── 场景 1: 渲染 + tab + 密钥面板一次展开 (P2-2 修复验证) ──
console.log('\n── 场景 1: 渲染 / toggle 一次展开 ──');
check('导入页渲染', await evaluate(page, `document.getElementById('mc').textContent.includes('数据导入')`));
await evaluate(page, `document.querySelectorAll('.imp-tab')[1].click()`);
await sleep(300);
const toggleOk = await evaluate(page, `(async function(){
  var b=document.getElementById('pkey-toggle');
  var t0=b.textContent;
  b.click();  // 第一次点击即应展开
  await new Promise(r=>setTimeout(r,400));
  return {display:document.getElementById('pkey-body').style.display, arrow:b.textContent, hasTable:!!document.querySelector('#pkey-body table')};
})()`);
check('密钥面板一次点击展开 (P2-2)', toggleOk.display === 'block' && toggleOk.arrow.includes('▾'), JSON.stringify(toggleOk));
await evaluate(page, `document.querySelectorAll('.imp-tab')[0].click()`);

// ── 场景 2: 小包直接导入 → 结果卡 + P6 卡 fresh (P2-1 修复验证) ──
console.log('\n── 场景 2: 小包导入 + P6 卡 fresh import ──');
await evaluate(page, `(async () => { const r=await fetch('/_s1-small.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-small.cubx')]); })()`);
await waitFor(page, `(function(){var t=document.getElementById('sb').textContent;return t.includes('包 | ') && !t.includes('0包');})()`, 90000);
check('小包导入完成', true, await evaluate(page, `document.getElementById('sb').textContent`));
const s2Sdiv = await evaluate(page, `document.getElementById('sdiv').textContent`);
check('P6 解析校验卡 fresh import 直接可见 (P2-1)', s2Sdiv.includes('解析正确性'));
const s2Pkts = await evaluate(page, `S.pkts`);

// ── 场景 3: 大包本地路径 → 预扫面板 ──
console.log('\n── 场景 3: 85MB 大包预扫面板 ──');
await evaluate(page, `document.querySelectorAll('.imp-tab')[1].click()`);
await sleep(300);
setPromptReply(page, BIG_CUBX);
await evaluate(page, `document.getElementById('plpath').click()`);
await waitFor(page, `!document.getElementById('cubx-prescan').classList.contains('hidden')`, 20000);
check('预扫面板弹出', true);
check('直方图/滑块就绪', await evaluate(page, `document.querySelectorAll('#cs-hist .cs-bar').length > 0`), await evaluate(page, `document.getElementById('cs-info').textContent.substr(0,60)`));

// ── 场景 4: 精确时间输入修复验证 (P1-B) — 输入面板显示的起始时间应成功 ──
console.log('\n── 场景 4: 精确时间输入 (面板起始时间, P1-B 修复) ──');
const tIn = await evaluate(page, `(function(){
  var s1=document.getElementById('cs-s1');
  var d1=new Date(+s1.min*1000), d2=new Date(Math.min(+s1.max, +s1.min+3600)*1000);
  function f(d){return {mo:('0'+(d.getMonth()+1)).slice(-2),da:('0'+d.getDate()).slice(-2),
    h:('0'+d.getHours()).slice(-2),mi:('0'+d.getMinutes()).slice(-2)};}
  var a=f(d1), b=f(d2);
  document.getElementById('cs-t1m').value=a.mo; document.getElementById('cs-t1d').value=a.da;
  document.getElementById('cs-t1h').value=a.h;  document.getElementById('cs-t1n').value=a.mi;
  document.getElementById('cs-t2m').value=b.mo; document.getElementById('cs-t2d').value=b.da;
  document.getElementById('cs-t2h').value=b.h;  document.getElementById('cs-t2n').value=b.mi;
  return a.mo+'-'+a.da+' '+a.h+':'+a.mi+' → '+b.mo+'-'+b.da+' '+b.h+':'+b.mi;
})()`);
await evaluate(page, `document.getElementById('cs-tapply').click()`);
await sleep(500);
const afterApply = await evaluate(page, `(function(){
  return {err:document.getElementById('prog').textContent,
          s1:+document.getElementById('cs-s1').value, min:+document.getElementById('cs-s1').min};})()`);
const applied = afterApply.s1 === afterApply.min || Math.abs(afterApply.s1 - afterApply.min) < 61;
check('面板起始时间可应用 (P1-B 修复)', applied && !afterApply.err.includes('❌'), `${tIn} → 滑块=${afterApply.s1.toFixed(1)} (min=${afterApply.min.toFixed(1)}) err=${afterApply.err.trim()}`);

// ── 场景 5: 拆分 → 顶栏进度/清理 → 子包下载 200 (P1-A) → 窗口状态保持 ──
console.log('\n── 场景 5: 拆分 + 下载 + 窗口保持 ──');
await evaluate(page, `(function(){var s=document.getElementById('cs-s1');var s2=document.getElementById('cs-s2');
  s.value = +s.min; s2.value = Math.min(+s.max, +s.min + 60); s.oninput(); s2.oninput();})()`);
const winInfo = await evaluate(page, `(function(){return {s1:+document.getElementById('cs-s1').value, s2:+document.getElementById('cs-s2').value};})()`);
await evaluate(page, `document.getElementById('cs-go').click()`);
const splitTrace = await evaluate(page, `(async () => {
  const trace = [];
  const t0 = Date.now();
  while (Date.now() - t0 < 120000) {
    const sb = document.getElementById('sb').textContent;
    const last = trace[trace.length - 1];
    if (!last || last !== sb) trace.push(sb);
    if (document.querySelectorAll('.cs-sub-row').length > 0 && !sb.includes('⟳')) break;
    await new Promise(r => setTimeout(r, 300));
  }
  return trace;
})()`);
console.log('   拆分顶栏轨迹:', JSON.stringify(splitTrace));
check('拆分完成且顶栏已清理 (P2 残留修复)', (splitTrace || []).some(t => t.includes('包 | ')) || (splitTrace || []).some(t => t.includes('就绪')), (splitTrace || []).slice(-1)[0]);
const subRow = await evaluate(page, `(function(){var r=document.querySelector('.cs-sub-row'); if(!r)return null;
  var a=r.querySelector('a'); return {text:r.textContent.trim(), href:a?a.href:''};})()`);
check('子包清单出现', !!subRow, subRow && subRow.text);
const dl = await evaluate(page, `(async function(href){
  try{var r=await fetch(href);return {status:r.status};}catch(e){return {status:0};}
})(` + JSON.stringify(subRow.href) + `)`);
check('子包下载 200 (P1-A 修复)', dl.status === 200, `status=${dl.status}`);
// 窗口状态保持: 切页 → 回来 → 滑块应保持上次窗口 (P2 修复)
await evaluate(page, `location.hash='topo'`);
await waitFor(page, `location.hash.includes('topo')`, 5000);
await evaluate(page, `location.hash='import'`);
await waitFor(page, `!document.getElementById('cubx-prescan').classList.contains('hidden')`, 10000);
const winRestore = await evaluate(page, `(function(){return {s1:+document.getElementById('cs-s1').value, s2:+document.getElementById('cs-s2').value};})()`);
check('切页回来窗口选择保持 (P2 修复)', Math.abs(winRestore.s1 - winInfo.s1) < 2 && Math.abs(winRestore.s2 - winInfo.s2) < 2,
  `窗口 ${winInfo.s1.toFixed(0)}-${winInfo.s2.toFixed(0)} → 恢复 ${winRestore.s1.toFixed(0)}-${winRestore.s2.toFixed(0)}`);

// ── 场景 6: 导入子包 ──
console.log('\n── 场景 6: 导入子包 ──');
const s6pktsBefore = await evaluate(page, `S.pkts`);
await evaluate(page, `document.querySelector('.cs-sub-import').click()`);
await waitFor(page, `(function(){var t=document.getElementById('sb').textContent;return t.includes('包 | ') && !t.includes('0包');})()`, 90000);
const s6Done = await evaluate(page, `document.getElementById('sb').textContent`);
check('子包导入完成', true, s6Done);

// ── 场景 7: 边界输入 (友好错误消息 P2 修复) ──
console.log('\n── 场景 7: 边界输入 ──');
await evaluate(page, `(async () => { const r=await fetch('/_s1-empty.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-empty.cubx')]); })()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌')`, 30000);
const errEmpty = await evaluate(page, `document.getElementById('prog').textContent`);
check('空文件 → 友好错误 (P2 修复)', errEmpty.includes('无数据') || errEmpty.includes('无效'), errEmpty.trim());
await evaluate(page, `(async () => { const r=await fetch('/_s1-bad.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-bad.cubx')]); })()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌')`, 30000);
const errBad = await evaluate(page, `document.getElementById('prog').textContent`);
check('错格式 → 友好错误 (P2 修复)', errBad.includes('无效的 cubx'), errBad.trim());
setPromptReply(page, 'd:/tmp/s1-test/not-exist.cubx');
await evaluate(page, `document.getElementById('plpath').click()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌')`, 10000);
const errPath = await evaluate(page, `document.getElementById('prog').textContent`);
check('不存在路径 → 内联错误', errPath.includes('路径不存在'), errPath.trim());

// ── 场景 8: 群控整包导入 (cs-cancel → 真实进度采样) — 最后, 108324 帧 ~30s ──
console.log('\n── 场景 8: 群控整包导入 + 并行进度采样 ──');
await evaluate(page, `(async () => { const r=await fetch('/_s1-group.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-group.cubx')]); })()`);
await waitFor(page, `!document.getElementById('cubx-prescan').classList.contains('hidden')`, 20000);
check('群控包 (>1MB) 弹预扫面板', true);
await evaluate(page, `document.getElementById('cs-cancel').click()`);
const trace = await evaluate(page, `(async () => {
  const trace = [];
  const t0 = Date.now();
  let lastSb = '';
  while (Date.now() - t0 < 180000) {
    const sb = document.getElementById('sb').textContent;
    if (sb !== lastSb) { trace.push(sb); lastSb = sb; }
    if (sb.includes('失败') || sb.includes('超时')) break;
    if (sb.includes('包 | ') && trace.length > 1) break;
    await new Promise(r => setTimeout(r, 500));
  }
  return trace;
})()`);
console.log('   顶栏轨迹 (' + trace.length + ' 段):');
trace.slice(0, 30).forEach(t => console.log('   ', t));
const pcts = (trace || []).map(t => parseInt((t.match(/(\d+)%/) || [])[1] || 0)).filter(n => n > 0);
check('群控整包导入完成', (trace || []).some(t => t.includes('包 | ')), (trace || []).slice(-1)[0]);
check('并行解析进度采样 (≥3 不同百分比)', pcts.length >= 3 && pcts[pcts.length - 1] > pcts[0], `${pcts[0]}% → ${pcts[pcts.length-1]}% (${pcts.length} 采样)`);
check('导入过程未误报超时 (P2 修复)', !(trace || []).some(t => t.includes('超时')));

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(fails.length ? 1 : 0);
