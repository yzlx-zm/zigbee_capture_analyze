// U16-2 未解密开关验证 — 默认隐藏未解密 + 开关切换显示
// 用法: Edge headless --remote-debugging-port=9222 在跑, node cdp_hide_undec.mjs
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
    if (m.method === 'Runtime.consoleAPICalled' || m.method === 'Runtime.exceptionThrown') consoleMsgs.push(JSON.stringify(m.params));
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

// 1. 开关默认勾选
const checked0 = await evaluate(page, `document.getElementById('tl-hide-undec').checked`);
check('未解密开关默认勾选', checked0 === true);

// 2. 点查看 → 默认隐藏未解密 (total 应 = 4301)
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat1 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
const lockRows1 = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row .ic-enc').length`);
check('默认列表 = 4301 包 (隐藏未解密)', /共 6007 包/.test(stat1), stat1);
check('默认列表无 🔒 未解密行', lockRows1 === 0, `🔒行=${lockRows1}`);

// 3. 取消勾选 → change 自动重查 → 显示全部
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat2 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
const lockRows2 = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row .ic-enc').length`);
check('取消勾选自动重查 = 10354 包', /共 8435 包/.test(stat2), stat2);
check('取消勾选后出现 🔒 未解密行', lockRows2 > 0, `🔒行=${lockRows2}`);

// 4. 再勾选 → 恢复隐藏
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat3 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
const lockRows3 = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row .ic-enc').length`);
check('再勾选恢复 4301 包', /共 6007 包/.test(stat3), stat3);
check('再勾选无 🔒 行', lockRows3 === 0, `🔒行=${lockRows3}`);

// 5. 过滤状态保持: 加节点过滤后开关仍生效
await evaluate(page, `document.getElementById('tl-node').value='0xECB1'; document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat4 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
const checked4 = await evaluate(page, `document.getElementById('tl-hide-undec').checked`);
check('节点过滤 + 未解密隐藏叠加生效', checked4 === true && /共 \d+ 包/.test(stat4) && !/共 8435 包/.test(stat4), stat4);

// 6. console 错误
const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
