// 后台任务全局可见验证 — 导入中切页, 顶栏 #sb 任务状态, 完成/失败提示, 点击回导入页
// 素材: 07251230_26.cubx (30MB, 解析 ~97s 便于切页观察) + 页面构造损坏文件 (失败场景)
// 文件获取: 测试 cubx 临时复制到 frontend/_cdp-test.cubx (StaticFiles 根), 页面 fetch 拿真实字节
//   (CDP setFileInputFiles 在 headless Edge 注入无效; fetch /c/ 无静态映射)
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';

async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0;
  const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, close: () => ws.close() };
}
async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}
const results = [];
function check(name, cond, extra = '') { results.push({ name, ok: !!cond }); console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`); }
const curHash = () => evaluate(page, `location.hash.slice(1)`);

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('DOM.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 4000));

// ── 场景 1: 30MB cubx 导入中切到 topo 页 → 顶栏进度 → 完成提示 → 点击回导入页 ──
console.log('\n── 场景 1: 导入中切页, 顶栏任务状态 ──');
await evaluate(page, `(async () => {
  const resp = await fetch('/_cdp-test.cubx');
  const buf = await resp.arrayBuffer();
  const f = new File([buf], 'cdp-global-test.cubx');
  doPI([f]);
})()`);

const r1 = await evaluate(page, `(async () => {
  // 等 #sb 出现任务状态 (⟳) 后切到 topo 页
  const t0 = Date.now();
  while (Date.now() - t0 < 30000) {
    const sb = document.getElementById('sb').textContent;
    if (sb.includes('⟳')) break;
    await new Promise(r => setTimeout(r, 200));
  }
  const sbBeforeSwitch = document.getElementById('sb').textContent;
  location.hash = 'topo';
  // 在 topo 页采样 #sb (任务继续跑, 顶栏应持续显示进度)
  const trace = [];
  const t1 = Date.now();
  while (Date.now() - t1 < 150000) {
    const sb = document.getElementById('sb').textContent;
    const task = document.getElementById('sb').dataset.task;
    const last = trace[trace.length - 1];
    if (!last || last.sb !== sb || last.task !== task) trace.push({ t: Date.now() - t1, sb, task });
    if (sb.includes('完成') || sb.includes('失败')) break;
    await new Promise(r => setTimeout(r, 500));
  }
  return { sbBeforeSwitch, trace, final: trace[trace.length - 1] };
})()`);

check('导入中 #sb 出现任务进度 (⟳)', (r1.sbBeforeSwitch || '').includes('⟳'), r1.sbBeforeSwitch);
const runSamples = (r1.trace || []).filter(t => t.task === 'run');
check('切页后 #sb 持续显示进度 (run 态采样≥5)', runSamples.length >= 5, `采样 ${runSamples.length} 次`);
check('切页后进度数值增长', (() => {
  const pcts = runSamples.map(t => parseInt((t.sb.match(/(\d+)%/) || [])[1] || 0)).filter(Boolean);
  return pcts.length >= 2 && pcts[pcts.length - 1] > pcts[0];
})(), runSamples.length >= 2 ? runSamples[0].sb + ' → ' + runSamples[runSamples.length - 1].sb : '无采样');
const doneState = r1.final;
check('完成后 #sb 显示 完成·点击查看', doneState && doneState.sb.includes('完成') && doneState.task === 'done', doneState && doneState.sb);
check('完成后 topo 页未被自动刷新', await curHash() === 'topo' && !(await evaluate(page, `!!document.getElementById('sout')`)), await curHash());

// 点击 #sb → 跳回导入页, 结果恢复
await evaluate(page, `document.getElementById('sb').click()`);
await new Promise(r => setTimeout(r, 4000));
const backState = await evaluate(page, `({
  hash: location.hash.slice(1),
  sout: document.getElementById('sout').style.display,
  stats: document.getElementById('sdiv').textContent.slice(0, 120),
  sb: document.getElementById('sb').textContent,
  task: document.getElementById('sb').dataset.task || null
})`);
check('点击 #sb 跳回导入页', backState.hash === 'import', backState.hash);
check('导入结果自动恢复 (sout 可见 + 包统计)', backState.sout === 'block' && /包/.test(backState.stats), backState.stats);
check('#sb 恢复统计态 (task 无残留)', !backState.task, backState.sb);

// ── 场景 2: 失败 (页面构造损坏文件), 非导入页提示 → 点击回导入页看错误详情 ──
console.log('\n── 场景 2: 失败提示 ──');
await evaluate(page, `location.hash = 'topo'`);
await new Promise(r => setTimeout(r, 1000));
const r2 = await evaluate(page, `(async () => {
  const bad = new File([new Uint8Array(64)], 'bad.cubx');
  doPI([bad]);
  const t0 = Date.now();
  while (Date.now() - t0 < 30000) {
    const sb = document.getElementById('sb').textContent;
    if (sb.includes('失败')) break;
    await new Promise(r => setTimeout(r, 300));
  }
  const sbFail = document.getElementById('sb').textContent;
  const task = document.getElementById('sb').dataset.task;
  document.getElementById('sb').click();
  await new Promise(r => setTimeout(r, 2500));
  const errMsg = (document.getElementById('imsg') || {}).textContent || '';
  const errVisible = document.getElementById('prog') ? getComputedStyle(document.getElementById('prog')).display : '';
  return { sbFail, task, hash: location.hash.slice(1), errMsg, errVisible };
})()`);

check('失败后 #sb 显示 失败·点击查看', (r2.sbFail || '').includes('失败') && r2.task === 'err', r2.sbFail);
check('点击后跳回导入页', r2.hash === 'import', r2.hash);
check('错误详情内联恢复显示', r2.errVisible === 'flex' && r2.errMsg.includes('❌'), r2.errMsg || '(prog 不可见)');

// 清理: 恢复就绪态
await evaluate(page, `document.getElementById('clr') && (async () => { const b = document.getElementById('clr'); b.click(); b.click(); await new Promise(r => setTimeout(r, 1500)); })()`);
await new Promise(r => setTimeout(r, 2000));
check('#sb 恢复就绪', (await evaluate(page, `document.getElementById('sb').textContent`)) === '就绪');

const fails = results.filter(r => !r.ok);
console.log(`\n结果: ${results.length - fails.length}/${results.length} 通过`);
process.exit(fails.length ? 1 : 0);
