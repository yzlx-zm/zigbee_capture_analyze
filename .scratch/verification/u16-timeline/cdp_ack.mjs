// U16 ACK 帧验证 — 完整包含 MAC Ack: 显示/过滤/详情 pending
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

// 1. 默认 total = 8435 (含 Ack, 不被未解密过滤隐藏)
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const stat1 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
// hide 后 = 全明文帧 6007 (1729 解密 + 1756 MAC 明文 + 2522 Ack); Ack 无 NWK 安全不被隐藏
check('默认列表 = 6007 包 (含 MAC Ack, 不被未解密过滤隐藏)', /共 6007 包/.test(stat1), stat1);

// 2. 列表含 MAC Ack 摘要 (pending=1 的帧显示 "MAC Ack pending")
const ackSums = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row .tl-summary')].map(e=>e.textContent).filter(t=>t.startsWith('MAC Ack'))`);
check('列表显示 MAC Ack 摘要', ackSums.length > 0, `${ackSums.length} 个`);
check('摘要格式 = MAC Ack / MAC Ack pending', ackSums.every(t=>/^MAC Ack( pending)?$/.test(t)), JSON.stringify(ackSums.slice(0,5)));
const pendingSums = ackSums.filter(t=>t==='MAC Ack pending');
console.log(`  pending 标记帧: ${pendingSums.length} 个`);

// 3. 类型下拉含 Acknowledgement
const typeOpts = await evaluate(page, `[...document.querySelectorAll('#tl-type option')].map(o=>o.textContent).join('|')`);
check('类型下拉含 Acknowledgement (2522)', /Acknowledgement \(2522\)/.test(typeOpts), typeOpts.match(/Acknowledgement[^|]*/)?.[0] || '(无)');

// 4. 详情: Ack 帧有 Seq + Ack Pending 字段
await evaluate(page, `(()=>{const s=document.getElementById('tl-type');s.value='Acknowledgement';s.dispatchEvent(new Event('change'));return true})()`);
await new Promise(r => setTimeout(r, 500));
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 2500));
await evaluate(page, `document.querySelector('#tltb tr.tl-row').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const ackDetail = await evaluate(page, `(()=>{const rows=[...document.querySelectorAll('#tl-detail .layer')];const mac=rows.find(l=>l.querySelector('.frame-title')?.textContent==='MAC');if(!mac)return null;return [...mac.querySelectorAll('.field-row')].map(r=>r.querySelector('.k')?.textContent+':'+r.querySelector('.v')?.textContent)})()`);
console.log('  Ack 详情 MAC 层:', JSON.stringify(ackDetail));
check('Ack 详情含 Seq#', Array.isArray(ackDetail) && ackDetail.some(f=>f.startsWith('Seq#') && f!=='Seq#:?'), JSON.stringify(ackDetail));
check('Ack 详情含 Ack Pending', Array.isArray(ackDetail) && ackDetail.some(f=>f.startsWith('Ack Pending')), JSON.stringify(ackDetail));

// 4b. 恢复类型 + 取消开关 → 全量 8435
await evaluate(page, `(()=>{document.getElementById('tl-type').value='';return true})()`);
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 2500));
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 2500));
const stat2 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('取消开关 total=8435', /共 8435 包/.test(stat2), stat2);
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 2500));

// 5. 回归: 恢复类型 + 点 Data 帧详情
await evaluate(page, `(()=>{document.getElementById('tl-type').value='';return true})()`);
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
