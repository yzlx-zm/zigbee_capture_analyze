// U16-6 层级着色验证 — 摘要列文字+底色按 layer, 行其余列不染
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

// 1. 各类 layer 类名渲染 (全量, 取消未解密开关以便看 other/mac)
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
await new Promise(r => setTimeout(r, 2500));
const clsCount = await evaluate(page, `(()=>{const c={};document.querySelectorAll('#tltb tr.tl-row .tl-summary').forEach(e=>{const m=e.className.match(/tl-ly-\\S+/);if(m)c[m[0]]=(c[m[0]]||0)+1});return c})()`);
console.log('  着色类分布:', JSON.stringify(clsCount));
check('zcl 类存在', (clsCount['tl-ly-zcl']||0) > 0);
check('nwk 类存在', (clsCount['tl-ly-nwk']||0) > 0);
check('aps 类存在', (clsCount['tl-ly-aps']||0) > 0);
check('other 类存在 (未解密 Data)', (clsCount['tl-ly-other']||0) > 0);

// 2. 计算样式: zcl 绿 / nwk 蓝 / aps 紫
const colors = await evaluate(page, `(()=>{const g=c=>{const e=document.querySelector('.tl-summary.'+c);if(!e)return null;const s=getComputedStyle(e);return {color:s.color,bg:s.backgroundColor}};return {zcl:g('tl-ly-zcl'),nwk:g('tl-ly-nwk'),aps:g('tl-ly-aps')}})()`);
console.log('  计算样式:', JSON.stringify(colors));
check('ZCL 文字绿', colors.zcl && /rgb\(22, 101, 52\)|#166534|22, ?101, ?52/.test(colors.zcl.color), colors.zcl?.color);
check('ZCL 底色非透明', colors.zcl && colors.zcl.bg !== 'rgba(0, 0, 0, 0)' && colors.zcl.bg !== 'transparent', colors.zcl?.bg);
check('NWK 文字蓝', colors.nwk && /rgb\(29, 78, 216\)|29, ?78, ?216/.test(colors.nwk.color), colors.nwk?.color);
check('APS 文字紫', colors.aps && /rgb\(109, 40, 217\)|109, ?40, ?217/.test(colors.aps.color), colors.aps?.color);

// 3. 行其余列不染: 取一个 zcl 行, 检查 NWK Src 列(第5列)背景透明
const rowBg = await evaluate(page, `(()=>{const tr=[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.querySelector('.tl-ly-zcl'));if(!tr)return null;return getComputedStyle(tr.children[4]).backgroundColor})()`);
check('行其余列不染 (NWK Src 背景透明)', rowBg !== null && (rowBg === 'rgba(0, 0, 0, 0)' || rowBg === 'transparent'), rowBg);

// 4. 恢复开关 + 回归
await evaluate(page, `document.getElementById('tl-hide-undec').click(); true`);
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
