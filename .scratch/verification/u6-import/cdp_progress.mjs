// U6 真实进度条验证 — 页面触发导入, 采样进度条 (素材: 1-标准入网抓包-2.pcap)
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

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 4000));

// 页面内触发 pcap 导入 (构造 File 调 doPI), 高频采样进度条
const samples = await evaluate(page, `(async () => {
  const resp = await fetch('/c/Users/Administrator/Desktop/zigbee_capture/验证可用-记录/1-标准入网抓包-2.pcap');
  const buf = await resp.arrayBuffer();
  const f = new File([buf], 'progress-test.pcap');
  doPI([f]);
  const trace = [];
  const t0 = Date.now();
  while (Date.now() - t0 < 60000) {
    const bar = document.getElementById('pbar');
    const fill = document.getElementById('pfill');
    const msg = document.getElementById('imsg').textContent;
    const visible = bar && getComputedStyle(bar).display !== 'none';
    const busy = document.getElementById('mc').classList.contains('busy');
    const last = trace[trace.length - 1];
    if (!last || last.w !== fill.style.width || last.msg !== msg || last.visible !== visible) {
      trace.push({ t: Date.now() - t0, w: fill.style.width, msg, visible, busy });
    }
    const done = document.getElementById('sout').style.display === 'block' && /335包|335/.test(document.getElementById('sdiv').textContent);
    if (done) { trace.push({ t: Date.now() - t0, w: fill.style.width, msg: 'DONE', visible: false, busy: false }); break; }
    await new Promise(r => setTimeout(r, 80));
  }
  return trace;
})()`);
check('进度条出现 (pbar 可见)', samples.some(s => s.visible), `共 ${samples.length} 个采样`);
check('进度条宽度有变化', new Set(samples.filter(s => s.w).map(s => s.w)).size >= 2, samples.filter(s=>s.w).map(s=>s.w).join(' → ').slice(0, 60));
check('busy 期间禁用', samples.some(s => s.busy));
check('完成后结果渲染', samples.length && samples[samples.length - 1].msg === 'DONE');
console.log('  采样轨迹:');
for (const s of samples.slice(0, 25)) console.log(`   t=${String(s.t).padStart(4)}ms w=${s.w.padStart(5)} busy=${s.busy} visible=${s.visible} ${s.msg}`);

// 并发防护: 导入进行中再提交 → 应被拒
const race = await evaluate(page, `(async () => {
  const resp = await fetch('/c/Users/Administrator/Desktop/zigbee_capture/验证可用-记录/1-标准入网抓包-2.pcap');
  const buf = await resp.arrayBuffer();
  const f = new File([buf], 'race-test.pcap');
  const r1 = await new Promise(res => { doPI([f]); setTimeout(() => res(true), 50); });
  const r2 = await fetch('http://localhost:8720/api/import/pcap', { method: 'POST', body: (() => { const fd = new FormData(); fd.append('files', f); return fd; })() }).then(r => r.json());
  return { r2 };
})()`);
check('并发防护 (第二个任务被拒)', race.r2.error && /已有导入任务/.test(race.r2.error), JSON.stringify(race.r2).slice(0, 80));

const fail = results.filter(r => !r.ok);
console.log(`\n==== ${results.length - fail.length}/${results.length} 通过 ====`);
page.close();
process.exit(fail.length ? 1 : 0);
