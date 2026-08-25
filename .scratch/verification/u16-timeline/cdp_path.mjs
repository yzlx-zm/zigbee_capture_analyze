// U16-4 路径列验证 — 安全/状态列 → 路径列 (下行 source route), decIcon 移摘要列前
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

// 1. 表头 7 列 (U16-5 加 APS Ctr)
const th = await evaluate(page, `[...document.querySelectorAll('#tltbl thead th')].map(t=>t.textContent).join('|')`);
check('表头 = 帧号|时间|摘要|路径|NWK Src|NWK Dst|APS Ctr', th === '帧号|时间|摘要|路径|NWK Src|NWK Dst|APS Ctr', th);
check('表头不再含 安全/状态/类型', !/安全|状态|类型/.test(th));

// 2. 查看 → 路径列渲染
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const dashCount = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row td:nth-child(4)')].filter(td=>td.textContent.trim()==='—').length`);
const pathCount = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row td:nth-child(4) .tl-path').length`);
check('无路径帧显示 —', dashCount > 0, `${dashCount} 行`);
console.log(`  路径列: 无路径(${dashCount}) 有路径(${pathCount})`);

// 3. 定位下行 source route 帧 (#1381/#1383: 0x0000→0xF67F 经 0x1885)
await evaluate(page, `document.getElementById('tl-node').value='0xF67F'; document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const paths = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row td:nth-child(4)')].map(td=>td.textContent.trim()).filter(t=>t!=='—')`);
console.log('  F67F 路径样本:', JSON.stringify(paths.slice(0,6)));
check('下行 source route 显示 →0x1885', paths.some(t=>t.includes('→0x1885')), paths[0] || '(无)');

// 4. decIcon 移摘要列前 (未解密开关关 → 看 🔒 在摘要列)
await evaluate(page, `document.getElementById('tl-node').value=''; document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const lockInSum = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row td:nth-child(3) .ic-enc').length`);
const stat = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('未解密帧 🔒 显示在摘要列(第3列)', lockInSum > 0, `🔒=${lockInSum} | ${stat}`);
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 2500));

// 4b. 路径点击展开/收起 (不触发行详情) — 先恢复 F67F 过滤确保页内有路径帧
await evaluate(page, `document.getElementById('tl-node').value='0xF67F'; document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 2500));
const detailBefore = await evaluate(page, `document.querySelector('#tl-detail .layer')?.querySelectorAll('div').length ?? 0`);
await evaluate(page, `document.querySelector('#tltb .tl-path').click(); true`);
await new Promise(r => setTimeout(r, 400));
const expanded1 = await evaluate(page, `document.querySelector('#tltb .tl-path').classList.contains('expanded')`);
const detailAfterClick = await evaluate(page, `document.querySelector('#tl-detail .layer')?.querySelectorAll('div').length ?? 0`);
check('点击路径 → expanded 类', expanded1 === true);
check('点击路径不触发详情打开', detailAfterClick === detailBefore, `detail div ${detailBefore}→${detailAfterClick}`);
await evaluate(page, `document.querySelector('#tltb .tl-path').click(); true`);
await new Promise(r => setTimeout(r, 300));
const expanded2 = await evaluate(page, `document.querySelector('#tltb .tl-path').classList.contains('expanded')`);
check('再点收起 (expanded 移除)', expanded2 === false);

// 5. 回归: 点行详情
await evaluate(page, `document.querySelector('#tltb tr.tl-row').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const hasLayer = await evaluate(page, `document.querySelectorAll('#tl-detail .layer').length`);
check('点行详情正常', hasLayer > 0, `layers=${hasLayer}`);

const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
