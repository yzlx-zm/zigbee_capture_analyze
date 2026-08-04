// U6 bugfix 验证 — bug1 初始转圈 / bug2 清除后残留 (素材: 1-标准入网抓包-2.pcap)
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';

async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0;
  const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, close: () => ws.close() };
}
async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}
const results = [];
function check(name, cond, extra = '') { results.push({ name, ok: !!cond }); console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`); }

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 5000));

// Bug1: 初始加载 (后端有 335 包数据) → #prog 必须不可见
const progHidden = await evaluate(page, `(() => {
  const el = document.getElementById('prog');
  return getComputedStyle(el).display === 'none';
})()`);
check('初始无转圈 (prog display:none)', progHidden);
const spinVisible = await evaluate(page, `(() => {
  const el = document.getElementById('prog');
  return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
})()`);
check('初始 spin 不可见 (无几何)', !spinVisible);

// 切 pcap tab 展开密钥面板 (清除后验证统计清零用)
await evaluate(page, `document.querySelector('.imp-tab[data-tab="pcap"]').click(); true`);
await new Promise(r => setTimeout(r, 1200));
const statsBefore = await evaluate(page, `document.getElementById('pkey-body').textContent`);
check('清除前密钥统计有数据', /解密: 41\/205/.test(statsBefore), statsBefore.match(/解密:[^<]*/)?.[0]?.slice(0, 30));

// Bug2: 清除数据 → sout 必须隐藏 (inline display:none, 不靠类)
const clr = await evaluate(page, `(async () => {
  const b = document.getElementById('clr');
  b.click();                          // 进确认态
  await new Promise(r => setTimeout(r, 300));
  b.click();                          // 确认清除
  await new Promise(r => setTimeout(r, 1500)); // 等 fetch 完成
  const sout = document.getElementById('sout');
  const r = {
    soutDisplay: getComputedStyle(sout).display,
    sb: document.getElementById('sb').textContent,
    progDisplay: getComputedStyle(document.getElementById('prog')).display,
    verifyPassed: (window.S||{}).verifyPassed,
    keyStats: document.getElementById('pkey-body').textContent.match(/解密:[^<]*/)?.[0]?.slice(0, 30) || '(无统计)',
  };
  return r;
})()`);
check('清除后导入结果卡片消失', clr.soutDisplay === 'none', `display=${clr.soutDisplay}`);
check('状态栏复位', clr.sb === '就绪', clr.sb);
check('进度条停止', clr.progDisplay === 'none', `display=${clr.progDisplay}`);
check('导航锁定解除 (verifyPassed=null)', clr.verifyPassed === null, String(clr.verifyPassed));
check('密钥命中统计清零', /解密:\s*0\/0/.test(clr.keyStats) || /无统计/.test(clr.keyStats), clr.keyStats);

const fail = results.filter(r => !r.ok);
console.log(`\n==== ${results.length - fail.length}/${results.length} 通过 ====`);
page.close();
process.exit(fail.length ? 1 : 0);
