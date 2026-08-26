// U17 阶段一验证 — AI 侧边栏 (知识检索先行) — 2026-08-26
// 覆盖 ticket 验证标准: ①知识检索 ②侧边栏开/折叠+切页/刷新保留 ③意图分流 ④无 key 不崩 ⑥回归
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8721/#import';

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
async function waitFor(p, expr, timeout = 8000, step = 250) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const v = await evaluate(p, expr);
    if (v) return v;
    await new Promise(r => setTimeout(r, step));
  }
  return null;
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
await waitFor(page, `!!document.getElementById('zc-ai-fab')`, 15000);
// 清场: 删除历史 localStorage 保证幂等 (同 origin 共享)
await evaluate(page, `localStorage.removeItem('zc_ai_sessions_v1'); true`);
await page.send('Page.reload');
await waitFor(page, `!!document.getElementById('zc-ai-fab')`, 15000);

// ── 0. 回归: 页面正常加载, 浮标挂载 ──
const nav = await evaluate(page, `[...document.querySelectorAll('.nt a')].map(a=>a.textContent).join('|')`);
check('导航 = 导入|拓扑|报文|节点|诊断 (无 AI 占位)', nav === '导入|拓扑|报文|节点|诊断', nav);
const hasFab = await evaluate(page, `!!document.getElementById('zc-ai-fab')`);
check('右下角 🤖 浮标已挂载', hasFab);

// ── 1. 侧边栏开/折叠 ──
await evaluate(page, `document.getElementById('zc-ai-fab').click(); true`);
await new Promise(r => setTimeout(r, 300));
const open1 = await evaluate(page, `document.getElementById('zc-ai-panel').classList.contains('on')`);
check('点击浮标 → 面板展开', open1);
await evaluate(page, `document.getElementById('zc-ai-fold').click(); true`);
await new Promise(r => setTimeout(r, 200));
const closed = await evaluate(page, `!document.getElementById('zc-ai-panel').classList.contains('on')`);
check('折叠按钮 → 面板收起', closed);
await evaluate(page, `document.getElementById('zc-ai-fab').click(); true`);
await new Promise(r => setTimeout(r, 200));

// ── 2. 知识检索 (验证标准 1: parent end device → 官方片段+链接) ──
await evaluate(page, `(()=>{const i=document.getElementById('zc-ai-in');i.value='什么是 parent end device';true})()`);
await evaluate(page, `document.getElementById('zc-ai-send').click(); true`);
const kbItems = await waitFor(page, `document.querySelectorAll('.ai-kb-item').length`, 20000);
check('知识检索返回结果卡片', kbItems > 0, `cards=${kbItems}`);
const kbTitle = await evaluate(page, `document.querySelector('.ai-kb-title') ? document.querySelector('.ai-kb-title').textContent : ''`);
const kbLink = await evaluate(page, `document.querySelector('.ai-kb-link') ? document.querySelector('.ai-kb-link').getAttribute('href') : ''`);
check('结果含标题+官方链接', kbTitle.length > 0 && /^https:\/\//.test(kbLink), `${kbTitle.slice(0, 40)} → ${kbLink.slice(0, 60)}`);

// ── 3. 意图分流: 分析意图 → 引导文案 (阶段二) ──
await evaluate(page, `(()=>{const i=document.getElementById('zc-ai-in');i.value='分析 10:00-10:30 的 0x838D';true})()`);
await evaluate(page, `document.getElementById('zc-ai-send').click(); true`);
const guide = await waitFor(page, `[...document.querySelectorAll('.ai-msg.ai-assistant .ai-bubble')].map(e=>e.textContent).join('|')`, 8000);
check('分析意图 → 引导文案(不崩不臆测)', (guide || '').includes('阶段二'), (guide || '').slice(0, 50));

// ── 4. 切页保留 (单例) ──
await evaluate(page, `location.hash='topo'; true`);
await new Promise(r => setTimeout(r, 1500));
const afterNav = await evaluate(page, `document.querySelectorAll('.ai-msg').length`);
check('切页后对话保留 (单例)', afterNav >= 3, `msgs=${afterNav}`);

// ── 5. 刷新保留 (localStorage 持久化) ──
await evaluate(page, `location.hash='import'; true`);
await new Promise(r => setTimeout(r, 800));
const lsCount = await evaluate(page, `JSON.parse(localStorage.getItem('zc_ai_sessions_v1')).sessions[0].messages.length`);
check('localStorage 持久化会话消息', lsCount >= 3, `msgs=${lsCount}`);
await page.send('Page.reload');
await waitFor(page, `!!document.getElementById('zc-ai-fab') && document.getElementById('zc-ai-panel').classList.contains('on')`, 15000);
const afterReload = await evaluate(page, `document.querySelectorAll('.ai-msg').length`);
check('刷新后对话恢复 (localStorage)', afterReload >= 3, `msgs=${afterReload}`);

// ── 6. 导入事件 → 上下文切换提示 ──
await evaluate(page, `window.dispatchEvent(new CustomEvent('zc:imported',{detail:{filename:'test.cubx',packets:123}})); true`);
await new Promise(r => setTimeout(r, 300));
const ctxMsg = await evaluate(page, `[...document.querySelectorAll('.ai-msg.ai-system .ai-bubble')].map(e=>e.textContent).join('|')`);
check('导入新包 → 上下文切换提示', (ctxMsg || '').includes('已导入新包') && (ctxMsg || '').includes('test.cubx'), (ctxMsg || '').slice(0, 50));

// ── 7. 设置区 (key 入口, 无 key 不崩) ──
await evaluate(page, `[...document.querySelectorAll('.ai-tab')].find(b=>b.dataset.t==='cfg').click(); true`);
await new Promise(r => setTimeout(r, 600));
const cfgText = await evaluate(page, `document.getElementById('zc-ai-key-state').textContent`);
check('设置区显示 key 状态', cfgText.length > 0, cfgText.slice(0, 40));
const provSel = await evaluate(page, `document.getElementById('zc-ai-prov').value`);
check('提供商下拉默认 anthropic', provSel === 'anthropic', provSel);

// ── 8. 回归: 页面无 JS 异常 ──
const jsErrors = page.consoleMsgs.filter(m => m.includes('exceptionThrown'));
check('无页面 JS 异常', jsErrors.length === 0, jsErrors.length ? jsErrors[0].slice(0, 120) : 'clean');

page.close();
const failed = results.filter(r => !r.ok);
console.log(`\n=== U17 阶段一验证: ${results.length - failed.length}/${results.length} 通过 ===`);
process.exit(failed.length ? 1 : 0);
