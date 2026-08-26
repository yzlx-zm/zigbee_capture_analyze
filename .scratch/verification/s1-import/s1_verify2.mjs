// S1 复验补充 — 场景 7a 空文件错误 + 场景 8 群控真实整包导入 (修正面板等待)
// v3 教训: 面板已开时 waitFor 立即通过 → cs-cancel 误操作旧包 (dataset.path 未更新)
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';

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

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('DOM.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await waitFor(page, `!!document.getElementById('mc')`, 10000);

// ── 场景 A: 空文件错误消息 (重测 v3 的 ❌) ──
console.log('\n── 场景 A: 空文件错误消息 ──');
await evaluate(page, `(async () => { const r=await fetch('/_s1-empty.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-empty.cubx')]); })()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌')`, 30000);
const errEmpty = await evaluate(page, `document.getElementById('prog').textContent`);
check('空文件 → 友好错误', errEmpty.includes('无效') || errEmpty.includes('无数据'), errEmpty.trim());

// ── 场景 B: 群控整包导入 (面板等待修正: 等 cs-info 更新为群控文件) ──
console.log('\n── 场景 B: 群控包整包导入 (真实素材) ──');
await evaluate(page, `document.querySelectorAll('.imp-tab')[1].click()`);
await sleep(200);
await evaluate(page, `(async () => { const r=await fetch('/_s1-group.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-group.cubx')]); })()`);
// 等待 stageCubx 完成: cs-info 出现 "4.9MB" (群控包) 且面板可见
const stageOk = await waitFor(page, `(function(){
  var p=document.getElementById('cubx-prescan');
  if(p.classList.contains('hidden'))return false;
  return document.getElementById('cs-info').textContent.includes('MB')
      && document.getElementById('cs-info').textContent.includes('物理帧 108474');
})()`, 30000);
check('群控面板弹出且 dataset.path 已更新为群控暂存', stageOk, await evaluate(page, `document.getElementById('cs-info').textContent`));
const stagePath = await evaluate(page, `document.getElementById('cubx-prescan').dataset.path`);
console.log('   面板 path:', stagePath);
check('面板 path 为暂存目录群控文件', /cubx_stage/.test(stagePath) && /_s1-group/.test(stagePath), stagePath);
await evaluate(page, `document.getElementById('cs-cancel').click()`);
const trace = await evaluate(page, `(async () => {
  const trace = [];
  const t0 = Date.now();
  let lastSb = '';
  while (Date.now() - t0 < 240000) {
    const sb = document.getElementById('sb').textContent;
    if (sb !== lastSb) { trace.push(sb); lastSb = sb; }
    if (sb.includes('失败') || sb.includes('超时')) break;
    // 完成: 群控导入后 sb 变为统计且经历了进度 (首个统计是导入前的, 忽略)
    if (sb.includes('包 | ') && trace.filter(t=>t.includes('包 | ')).length >= 2) break;
    await new Promise(r => setTimeout(r, 500));
  }
  return trace;
})()`);
console.log('   顶栏轨迹 (' + trace.length + ' 段):');
trace.forEach(t => console.log('   ', t));
const pcts = (trace || []).map(t => parseInt((t.match(/(\d+)%/) || [])[1] || 0)).filter(n => n > 0);
const doneSb = (trace || []).filter(t => t.includes('包 | '));
check('群控整包导入完成', doneSb.length >= 2, doneSb.slice(-1)[0]);
check('并行解析进度采样 (≥3 不同百分比)', pcts.length >= 3 && pcts[pcts.length - 1] > pcts[0], `${pcts[0]}% → ${pcts[pcts.length-1]}% (${pcts.length} 采样)`);
check('导入过程未误报超时', !(trace || []).some(t => t.includes('超时')));
const total = await evaluate(page, `S.pkts`);
console.log('   导入后 S.pkts =', total);

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(fails.length ? 1 : 0);
