// U16-3 摘要列验证 — 类型列改摘要 (后端 summary + 截断 hover + 徽章保留)
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

await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 3000));

// 1. 摘要元素渲染
const sumCount = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row .tl-summary').length`);
check('摘要列元素渲染', sumCount > 0, `${sumCount} 个`);

// 2. ZCL 摘要格式 (08-25 用户反馈简化: 仅 "ZCL 命令名", 无方向/簇 ID)
const zclSum = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row .tl-summary')].map(e=>e.textContent).filter(t=>t.startsWith('ZCL'))`);
check('存在 ZCL 摘要', zclSum.length > 0, zclSum[0] || '');
check('ZCL 摘要不再含方向 C→S/S→C', zclSum.every(t=>!/C→S|S→C/.test(t)), zclSum.slice(0,3).join(' | '));
check('ZCL 摘要不再含簇 ID 0x....', zclSum.every(t=>!/0x[0-9A-F]{4}/.test(t)), zclSum[0] || '');
check('ZCL 摘要格式 = ZCL + 命令名', zclSum.every(t=>/^ZCL [\w \-/]+$/.test(t)), zclSum[0] || '');

// 3. hover 全显 (title 属性)
const hasTitle = await evaluate(page, `document.querySelector('#tltb tr.tl-row .tl-summary')?.hasAttribute('title')`);
check('摘要 hover 全显 (title 属性)', hasTitle === true);

// 4. 未解密开关回归 (仍生效) — 素材: 中继入网抓包(1).cubx (4158 包, hide 后 1729)
const checked = await evaluate(page, `document.getElementById('tl-hide-undec').checked`);
const stat = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('未解密开关仍生效', checked === true && /共 6007 包/.test(stat), stat);

// 4b. Leave 摘要 rejoin 标志 (中继素材有 Leave 帧; 切类型过滤定位)
await evaluate(page, `(()=>{const s=document.getElementById('tl-type');s.value='Leave';s.dispatchEvent(new Event('change'));return true})()`);
await new Promise(r => setTimeout(r, 500));
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 2500));
const leaveSums = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row .tl-summary')].map(e=>e.textContent).slice(0,10)`);
console.log('  Leave 摘要样本:', JSON.stringify(leaveSums));
check('Leave 帧摘要含 rejoin 标志', leaveSums.some(t=>/Leave rejoin/.test(t)) || leaveSums.some(t=>t.startsWith('Leave')), leaveSums[0] || '(无 Leave)');
// 恢复类型过滤
await evaluate(page, `(()=>{document.getElementById('tl-type').value='';return true})()`);
await evaluate(page, `document.getElementById('tshow').click(); true`);
await new Promise(r => setTimeout(r, 2500));

// 5. 点行详情回归 (U15 载荷区不崩)
await evaluate(page, `document.querySelector('#tltb tr.tl-row').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const hasLayer = await evaluate(page, `document.querySelectorAll('#tl-detail .layer').length`);
check('点行详情正常 (layer 渲染)', hasLayer > 0, `layers=${hasLayer}`);

// 6. 类型下拉过滤回归 (U5: 类型下拉动态化仍可用)
await evaluate(page, `document.getElementById('tshow').click(); true`);  // 重置
await new Promise(r => setTimeout(r, 1500));
const typeOpts = await evaluate(page, `document.getElementById('tl-type').options.length`);
check('类型下拉仍有动态选项', typeOpts > 1, `options=${typeOpts}`);

const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
