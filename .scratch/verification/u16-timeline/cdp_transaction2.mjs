// U16-7a 收紧修正验证 — VerifyKeyConfirm 无误配 + 折叠展示
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
await new Promise(r => setTimeout(r, 5000));

// 0. 取消未解密过滤 → 全量 8435 (索引 1:1, 翻页可精确定位)
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 2500));

// 1. Write Attributes 命令帧 (idx 733) — 有响应
await evaluate(page, `(()=>{const s=document.getElementById('tl-ps');s.value='500';s.dispatchEvent(new Event('change'));return true})()`);
await new Promise(r => setTimeout(r, 2500));
await evaluate(page, `document.getElementById('tl-pj').value='2'; document.getElementById('tl-pgo').click(); true`);
await new Promise(r => setTimeout(r, 3000));
await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.dataset.pid==='733')?.click(); true`);
await new Promise(r => setTimeout(r, 1500));
const d733 = await evaluate(page, `document.querySelector('#tl-detail')?.textContent || ''`);
check('Write Attributes 有同事务响应', d733.includes('同事务响应'), d733.slice(0, 80));

// 2. VerifyKeyConfirm 帧 (idx 3298, 第 7 页) — 无误配 + 有 ack
await evaluate(page, `document.getElementById('tl-pj').value='7'; document.getElementById('tl-pgo').click(); true`);
await new Promise(r => setTimeout(r, 3000));
const found3298 = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].some(r=>r.dataset.pid==='3298')`);
check('翻页定位 VerifyKeyConfirm idx 3298', found3298 === true);
await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.dataset.pid==='3298')?.click(); true`);
await new Promise(r => setTimeout(r, 1500));
const d3298 = await evaluate(page, `document.querySelector('#tl-detail')?.textContent || ''`);
const hasRespBlock3298 = d3298.includes('同事务响应');
const hasAck3298 = d3298.includes('APS Ack 配对');
check('VerifyKeyConfirm 无误配响应区块', hasRespBlock3298 === false, hasRespBlock3298 ? '仍误配!' : '无响应区块 ✓');
check('VerifyKeyConfirm 仍有 ack 配对', hasAck3298 === true, '');

// 3. 折叠帧 (idx 5222 Write Attributes 10 响应, 第 11 页) — 展开/收起
await evaluate(page, `document.getElementById('tl-pj').value='11'; document.getElementById('tl-pgo').click(); true`);
await new Promise(r => setTimeout(r, 3000));
await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.dataset.pid==='5222')?.click(); true`);
await new Promise(r => setTimeout(r, 1500));
const toggleInfo = await evaluate(page, `(()=>{const t=document.querySelector('#tl-detail .tr-toggle');if(!t)return null;const hid=t.nextElementSibling;return {toggleText:t.textContent, hiddenDisplay:hid.style.display, links:document.querySelectorAll('#tl-detail .tr-hidden a').length}})()`);
console.log('  折叠状态:', JSON.stringify(toggleInfo));
check('响应 >5 显示「展开全部」', toggleInfo !== null && toggleInfo.toggleText === '展开全部', JSON.stringify(toggleInfo));
check('隐藏区含全部剩余链接', toggleInfo !== null && toggleInfo.links > 0, `hidden links=${toggleInfo?.links}`);
await evaluate(page, `document.querySelector('#tl-detail .tr-toggle').click(); true`);
await new Promise(r => setTimeout(r, 400));
const afterExpand = await evaluate(page, `(()=>{const t=document.querySelector('#tl-detail .tr-toggle');return {text:t?.textContent, display:t?.nextElementSibling?.style.display}})()`);
check('点击后展开 (收起 + 显示全部)', afterExpand !== null && afterExpand.text === '收起' && afterExpand.display === '', JSON.stringify(afterExpand));
await evaluate(page, `document.querySelector('#tl-detail .tr-toggle').click(); true`);
await new Promise(r => setTimeout(r, 300));
const afterCollapse = await evaluate(page, `document.querySelector('#tl-detail .tr-toggle')?.textContent`);
check('再点收起恢复', afterCollapse === '展开全部', afterCollapse);

const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
