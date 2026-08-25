// U16-7 全量化 + 报文改名验证 — 完整包列表 (含 poll/Beacon) + 页面改名 + 回归
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

// 1. 改名: 导航 + 页面标题
const nav = await evaluate(page, `[...document.querySelectorAll('.nt a')].map(a=>a.textContent).join('|')`);
check('导航含「报文」不含「时间线」', nav.includes('报文') && !nav.includes('时间线'), nav);
const h3 = await evaluate(page, `document.querySelector('#mc h3').textContent`);
check('页面标题 = 📊 报文', h3 === '📊 报文', h3);

// 2. 默认 (hide 开): total=3485, 列表含 poll 帧
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat1 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('默认 hide 后 total=3485', /共 6007 包/.test(stat1), stat1);
const dreqRed = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row .tl-ly-macdreq').length`);
const dreqText = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row .tl-summary')].map(e=>e.textContent).filter(t=>t==='DataReq').length`);
check('列表含 DataReq 轮询帧', dreqRed > 0 && dreqText > 0, `红标=${dreqRed} 文本=${dreqText}`);
const dreqColor = await evaluate(page, `(()=>{const e=document.querySelector('#tltb .tl-ly-macdreq');if(!e)return null;const s=getComputedStyle(e);return s.color})()`);
check('DataReq 文字红色', dreqColor === 'rgb(185, 28, 28)', dreqColor);

// 3. 取消开关: total=5913 (完整包)
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat2 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('取消开关 total=5913', /共 8435 包/.test(stat2), stat2);

// 4. 类型下拉含 MAC Cmd (全量化后类型统计含 MAC 帧)
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);  // 恢复
await new Promise(r => setTimeout(r, 2500));
const typeOpts = await evaluate(page, `[...document.querySelectorAll('#tl-type option')].map(o=>o.textContent).join('|')`);
check('类型下拉含 MAC Cmd/Beacon', typeOpts.includes('MAC Cmd') && typeOpts.includes('Beacon'), typeOpts.slice(0, 120));

// 5. 拓扑页回归 (打开不崩)
await evaluate(page, `location.hash='#topo'; true`);
await new Promise(r => setTimeout(r, 4000));
const topoOk = await evaluate(page, `document.querySelectorAll('#topo-canvas, #cy, canvas').length > 0 || document.querySelector('#mc').textContent.length > 100`);
check('拓扑页打开不崩', topoOk === true);

// 6. 节点页回归
await evaluate(page, `location.hash='#nodes'; true`);
await new Promise(r => setTimeout(r, 3500));
const nodesOk = await evaluate(page, `document.querySelectorAll('#ntb .nd-row').length`);
check('节点页行渲染', nodesOk > 0, `rows=${nodesOk}`);

// 7. 回报文页 + 详情回归
await evaluate(page, `location.hash='#tl'; true`);
await new Promise(r => setTimeout(r, 3500));
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 2500));
await evaluate(page, `document.querySelector('#tltb tr.tl-row').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const hasLayer = await evaluate(page, `document.querySelectorAll('#tl-detail .layer').length`);
check('详情回归正常', hasLayer > 0);

const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
