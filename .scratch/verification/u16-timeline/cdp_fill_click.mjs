// U16-1 字段点选过滤验证 — 点击详情字段 → 过滤框填入 + 列表刷新
// 用法: Edge headless --remote-debugging-port=9222 在跑, node cdp_fill_click.mjs
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#tl';

async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0;
  const pending = new Map();
  const consoleMsgs = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === 'Runtime.consoleAPICalled' || m.method === 'Runtime.exceptionThrown') {
      consoleMsgs.push(JSON.stringify(m.params));
    }
  };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, consoleMsgs, close: () => ws.close() };
}

async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.error) throw new Error(r.error.message);
  if (r.result && r.result.exceptionDetails) throw new Error('EVAL_EXC: ' + JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}

const results = [];
function check(name, cond, extra = '') {
  results.push({ name, ok: !!cond });
  console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`);
}

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 3500));

// 1. 触发查看 (无过滤 → 全量第一页)
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const rows = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row').length`);
check('时间线列表有数据', rows > 0, `rows=${rows}`);

// 2. 点第一行 → 等详情
await evaluate(page, `document.querySelector('#tltb tr.tl-row').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const clickable = await evaluate(page, `[...document.querySelectorAll('#tl-detail .tl-click-val')].map(a=>a.textContent + '@' + a.dataset.fill)`);
console.log('  可点字段:', JSON.stringify(clickable));
check('详情面板存在可点字段', clickable.length > 0, `${clickable.length} 个`);

if (clickable.length > 0) {
  // 3a. 点第一个 node 可点字段 (素材无关: 找 data-fill=node 的元素)
  const beforePan = await evaluate(page, `document.getElementById('tl-pan').value`);
  const beforeNode = await evaluate(page, `document.getElementById('tl-node').value`);
  await evaluate(page, `(()=>{const a=[...document.querySelectorAll('#tl-detail .tl-click-val')].find(x=>x.dataset.fill==='node');if(a){a.click();return true}return false})()`);
  await new Promise(r => setTimeout(r, 2500));
  const afterPan = await evaluate(page, `document.getElementById('tl-pan').value`);
  const afterNode = await evaluate(page, `document.getElementById('tl-node').value`);
  const stat = await evaluate(page, `document.getElementById('tl-stat').textContent`);
  console.log(`  [node] PAN: "${beforePan}"→"${afterPan}" | 节点: "${beforeNode}"→"${afterNode}" | stat: ${stat}`);
  check('点击 node 字段 → 节点框填入', beforeNode !== afterNode, `node=${afterNode}`);
  check('node 过滤后列表刷新', stat.includes('共'), stat);
  // 3b. 点第一个 pan 可点字段 (素材无关)
  await evaluate(page, `(()=>{const a=[...document.querySelectorAll('#tl-detail .tl-click-val')].find(x=>x.dataset.fill==='pan');if(a){a.click();return true}return false})()`);
  await new Promise(r => setTimeout(r, 2500));
  const pan2 = await evaluate(page, `document.getElementById('tl-pan').value`);
  const stat2 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
  console.log(`  [pan] PAN: →"${pan2}" | stat: ${stat2}`);
  check('点击 pan 字段 → PAN 框填入', pan2 !== '', `pan=${pan2}`);
  check('pan 过滤后列表刷新', stat2.includes('PAN='), stat2);
}

// 4. 检查 console 错误
const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
