// S1 后端重启按钮实测 — 点击 → confirm → 重启 → 轮询恢复 → 页面 reload
// 注意: 重启会丢当前导入数据 (预期行为, 用户已确认放最后测)
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

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('DOM.enable');
let reloaded = false;
page.on('Page.javascriptDialogOpening', () => {
  page.send('Page.handleJavaScriptDialog', { accept: true });
});
page.on('Page.loadEventFired', () => { reloaded = true; });

await page.send('Page.navigate', { url: TARGET });
await sleep(4000);

const preState = await evaluate(page, `document.getElementById('sb').textContent`);
console.log('   重启前 sb:', preState);

await evaluate(page, `document.getElementById('sb-restart').click()`);
await sleep(2000);
const midSb = await evaluate(page, `document.getElementById('sb').textContent`);
check('点击后显示重启状态', midSb.includes('重启'), midSb);

// 等待页面 reload (新后端就绪后 location.reload)
const t0 = Date.now();
while (Date.now() - t0 < 60000) {
  if (reloaded) break;
  await sleep(1000);
}
check('页面自动 reload', reloaded);
await sleep(4000);

// 新页面状态
const sb = await evaluate(page, `document.getElementById('sb') ? document.getElementById('sb').textContent : '(页面未加载)'`);
check('重启后页面可用', !sb.includes('页面未加载'), sb);
const apiOk = await evaluate(page, `(async function(){try{var r=await fetch('/api/import/status');var d=await r.json();return JSON.stringify(d);}catch(e){return 'ERR '+e.message;}})()`);
console.log('   重启后 status API:', apiOk);
check('重启后后端 API 正常 (数据已清, total=0)', apiOk.includes('"total":0'), apiOk);

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(fails.length ? 1 : 0);
