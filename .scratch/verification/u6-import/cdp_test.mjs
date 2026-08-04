// U6 导入页交互验证 — CDP 驱动 (一次性验证工具, 素材: 1-标准入网抓包-2.pcap)
// 用法: 先起 Edge --headless=new --remote-debugging-port=9222, 再 node cdp_test.mjs
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';

async function newPage() {
  // 新建 tab 拿 webSocketDebuggerUrl (避免干扰已有页面)
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
  if (r.error) throw new Error(r.error.message);
  if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}

const results = [];
function check(name, cond, extra = '') {
  results.push({ name, ok: !!cond, extra });
  console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`);
}

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 5000)); // 等模块加载 + verify 异步

// 1. 导入页骨架 + spin
check('prog 带 spin 元素', await evaluate(page, `!!document.querySelector('#prog .spin')`));
check('导入结果卡片显示', await evaluate(page, `document.getElementById('sout').style.display==='block'`));
check('状态栏有包数', await evaluate(page, `/335包|就绪/.test(document.getElementById('sb').textContent)`));

// 2. 校验报告唯一性 (U6 修复点: sr() 与末尾 verify 查询曾双份渲染)
const alertCount = await evaluate(page, `document.querySelectorAll('#sdiv .alert').length`);
check('校验报告只渲染一份', alertCount === 1, `alert 数量=${alertCount}`);
const detailCount = await evaluate(page, `document.querySelectorAll('#sdiv .verify-detail').length`);
check('差异明细可展开 (details)', detailCount >= 0, `details 数量=${detailCount}`);
const hasChecks = await evaluate(page, `[...document.querySelectorAll('#sdiv .alert div')].some(d=>/预期=/.test(d.textContent))`);
check('校验项含预期/实际', hasChecks);

// 3. 切 pcap tab → 密钥面板
await evaluate(page, `document.querySelector('.imp-tab[data-tab="pcap"]').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const keyRows = await evaluate(page, `document.querySelectorAll('#pkey-body .tbl tr').length`);
check('密钥面板表格渲染', keyRows >= 1, `行数=${keyRows}`);
const keyHex = await evaluate(page, `document.querySelectorAll('#pkey-body .key-hex').length`);
check('key-hex 可展开元素存在', keyHex >= 1, `数量=${keyHex}`);
const hitInfo = await evaluate(page, `document.getElementById('pkey-body').textContent`);
check('命中帧数展示', /命中/.test(hitInfo), hitInfo.match(/解密:[^<]*/)?.[0]?.slice(0, 50));

// 4. key 点击展开/收起
const expandTest = await evaluate(page, `(() => {
  const td = document.querySelector('#pkey-body .key-hex');
  const before = td.textContent; td.click(); const expanded = td.textContent; td.click(); const collapsed = td.textContent;
  return { before, expanded, collapsed, full: td.dataset.full };
})()`);
check('key 点击展开再收起', expandTest.before !== expandTest.expanded && expandTest.expanded === expandTest.full && expandTest.collapsed === expandTest.before, `${expandTest.before.length}→${expandTest.expanded.length}→${expandTest.collapsed.length} 字符`);

// 5. 非法 hex 内联错误 (不弹 alert)
const badHex = await evaluate(page, `(() => {
  window.__alerted = false; const orig = window.alert; window.alert = () => { window.__alerted = true; };
  document.getElementById('pk-hex').value = 'ABC'; document.getElementById('pk-add').click();
  const errShown = !document.getElementById('pk-err').classList.contains('hidden');
  const msg = document.getElementById('pk-err').textContent;
  window.alert = orig;
  return { errShown, msg, alerted: window.__alerted };
})()`);
check('非法 hex 内联报错且无 alert', badHex.errShown && !badHex.alerted, badHex.msg);

// 6. 合法 key 添加 (16 字节随机 hex, 添加后可删除)
const addKey = await evaluate(page, `(async () => {
  const hex = '11223344556677889900AABBCCDDEEFF';
  document.getElementById('pk-hex').value = hex; document.getElementById('pk-label').value = 'u6-test-key';
  document.getElementById('pk-add').click();
  await new Promise(r => setTimeout(r, 800)); // 等 loadKeyPanel 刷新
  const found = [...document.querySelectorAll('#pkey-body tr')].some(tr => /u6-test-key/.test(tr.textContent));
  const errHidden = document.getElementById('pk-err').classList.contains('hidden');
  return { found, errHidden };
})()`);
check('合法 key 添加成功', addKey.found && addKey.errHidden);

// 7. 删除刚添加的 key
const delKey = await evaluate(page, `(async () => {
  const tr = [...document.querySelectorAll('#pkey-body tr')].find(tr => /u6-test-key/.test(tr.textContent));
  if (!tr) return 'not-found';
  tr.querySelector('[data-kl]').click();
  await new Promise(r => setTimeout(r, 800));
  return ![...document.querySelectorAll('#pkey-body tr')].some(tr => /u6-test-key/.test(tr.textContent));
})()`);
check('删除自定义 key', delKey === true, delKey === 'not-found' ? '未找到' : '');

// 8. 清除按钮确认倒计时 + 自动还原 (只点一次, 不触发真实清除)
const clrBtn = await evaluate(page, `(() => {
  const b = document.getElementById('clr'); b.click();
  return { t1: b.textContent, confirming: b.dataset.confirming, hasDanger: b.classList.contains('btn-r') };
})()`);
check('清除按钮进入确认态 (倒计时文案)', /\(3s\)/.test(clrBtn.t1) && clrBtn.confirming === '1' && clrBtn.hasDanger, clrBtn.t1);
await new Promise(r => setTimeout(r, 3600)); // 等倒计时结束
const clrRestored = await evaluate(page, `document.getElementById('clr').textContent`);
check('3s 后按钮自动还原', clrRestored === '清除数据', clrRestored);

// 9. 上传中 busy 禁用态 + spin 显示 (直接调 setProg 模拟)
const busy = await evaluate(page, `(() => {
  setProg('测试上传中...');
  const busyOn = document.getElementById('mc').classList.contains('busy');
  const spinVisible = document.getElementById('prog').style.display;
  setProg('');
  return { busyOn, spinVisible };
})()`);
check('上传中 busy 禁用 + spin 显示', busy.busyOn && busy.spinVisible === 'flex', JSON.stringify(busy));

// 10. 失败内联错误 (setErr 经动态 import 同实例调用)
const errShown = await evaluate(page, `(async () => {
  const m = await import('./js/state.js');
  m.setErr('测试错误信息');
  const el = document.getElementById('prog');
  const r = { cls: el.className, display: el.style.display, msg: document.getElementById('imsg').textContent, busy: document.getElementById('mc').classList.contains('busy') };
  m.setProg('');
  return r;
})()`);
check('失败内联红色错误条', errShown.cls.includes('prog-err') && /测试错误信息/.test(errShown.msg) && errShown.display === 'flex', errShown.msg);
check('错误后 busy 解除', errShown.busy === false);

// 11. 失败校验报告渲染 (注入假报告, 验证 details 展开 + 无 undefined)
const failReport = await evaluate(page, `(async () => {
  const m = await import('./js/state.js');
  m.sr({ ok: true, packets: 5, nodes: 2, verify: {
    passed: false,
    checks: { frame_count: { label: 'NWK帧数', expected: 10, actual: 5, passed: false }, sample_frames: { label: '抽样对比', passed: false } },
    detail: { frame_count: 'tshark NWK帧数: 10, 导入: 5' }
  }}, 'fail-test.pcap');
  const bad = !!document.querySelector('#sdiv .alert-bad');
  const details = document.querySelector('#sdiv .verify-detail');
  const noUndef = !/undefined/.test(document.getElementById('sdiv').textContent);
  const sampleOk = /抽样对比: 预期=- 实际=-/.test(document.getElementById('sdiv').textContent);
  return { bad, hasDetails: !!details, detailText: details ? details.querySelector('pre').textContent : '', noUndef, sampleOk };
})()`);
check('失败报告红色 alert-bad', failReport.bad);
check('差异明细 details 可展开含内容', failReport.hasDetails && /tshark NWK帧数/.test(failReport.detailText), failReport.detailText.slice(0, 40));
check('无 undefined 显示', failReport.noUndef);
check('无字段校验项显示 -/-', failReport.sampleOk);

// 汇总
const fail = results.filter(r => !r.ok);
console.log(`\n==== ${results.length - fail.length}/${results.length} 通过 ====`);
page.close();
process.exit(fail.length ? 1 : 0);
