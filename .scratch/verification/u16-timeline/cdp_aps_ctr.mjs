// U16-5 APS Ctr 列验证 — 表头 7 列 + counter 显示 + 回归
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

const th = await evaluate(page, `[...document.querySelectorAll('#tltbl thead th')].map(t=>t.textContent).join('|')`);
check('表头 7 列含 APS Ctr', th === '帧号|时间|摘要|路径|NWK Src|NWK Dst|APS Ctr', th);

await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));

// APS Ctr 列 (第 7 列): 有值帧 vs 无值帧
const ctrVals = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row td:nth-child(7)')].map(td=>td.textContent.trim())`);
const numCtr = ctrVals.filter(v=>/^\d+$/.test(v)).length;
const dashCtr = ctrVals.filter(v=>v==='—').length;
check('APS Ctr 列有数字值', numCtr > 0, `数字=${numCtr}`);
check('无 APS 帧显示 —', dashCtr > 0, `—=${dashCtr}`);
console.log('  APS Ctr 样本:', JSON.stringify(ctrVals.slice(0, 12)));

// 与详情面板 counter 对应 (点某帧, 详情 APS 层 counter 应与列表列一致)
const firstNumIdx = ctrVals.findIndex(v=>/^\d+$/.test(v));
await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row')[${firstNumIdx}].click(); true`);
await new Promise(r => setTimeout(r, 1500));
const detailCtr = await evaluate(page, `(()=>{const rows=[...document.querySelectorAll('#tl-detail .layer')];const aps=rows.find(l=>l.querySelector('.frame-title')?.textContent==='APS');const v=aps?[...aps.querySelectorAll('.field-row')].find(r=>r.querySelector('.k')?.textContent==='Counter')?.querySelector('.v')?.textContent:null;return v})()`);
check('列表 APS Ctr 与详情 Counter 一致', detailCtr !== null && detailCtr.trim() === ctrVals[firstNumIdx], `列表=${ctrVals[firstNumIdx]} 详情=${detailCtr}`);

// 回归: 未解密开关 + 摘要列
const stat = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('未解密开关仍生效', /共 6007 包/.test(stat), stat);

const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
