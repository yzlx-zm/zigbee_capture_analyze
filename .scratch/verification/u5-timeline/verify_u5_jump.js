// U5 跳转 bug 验证: 拓扑点击节点 → 时间线 (Bug A: 节点过滤同步 / Bug B: 时间不 NaN 不全零)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  await page.goto('http://127.0.0.1:8720/#topo', { waitUntil: 'networkidle' });
  // 切到层级树 tab (渲染 #tree-root)
  await page.click('.bp-tab:has-text("层级树")', { timeout: 8000 }).catch(() => out.tabClick = 'FAIL');
  // 等拓扑节点列表
  await page.waitForSelector('#tree-root .node', { timeout: 10000 });
  // 记录第一个可点击节点地址 (非 coord 优先)
  const nodeInfo = await page.$$eval('#tree-root .node', els => els.map(e => e.textContent.trim()).slice(0, 8));
  out.topoNodes = nodeInfo;

  // 点击第一个 node (取含 0x 的; 排除 coord 0x0000)
  const target = await page.$$eval('#tree-root .node', els => {
    for (const e of els) { const t = e.textContent.trim(); if (t.startsWith('0x') && t !== '0x0000') return t; }
    return null;
  });
  out.clickedNode = target;
  if (!target) { console.log(JSON.stringify({ ...out, errors }, null, 2)); await browser.close(); return; }

  // 点击该节点 → 触发 topo.js 节点 click 处理 (S.topoAddr + hash='tl')
  // 未归类组 collapsed 子节点不可见 → 用 locator 点击第一个可见 .node
  await page.locator('#tree-root .node').first().click({ timeout: 5000 })
    .catch(e => { out.clickFail = e.message.slice(0, 120); });

  // 等 hash 跳转 + timeline 初始化 (hash 变化 + 页面 HTML 渲染 + 自动搜索)
  await page.waitForFunction(() => location.hash.startsWith('#tl'), null, { timeout: 8000 })
    .catch(() => out.hashWait = 'FAIL');
  try {
    await page.waitForSelector('#tl-h0', { timeout: 8000 });
  } catch (e) {
    out.hashNow = await page.evaluate(() => location.hash);
    out.mcHtml = (await page.$eval('#mc', el => el.innerHTML).catch(() => 'NO #mc')).slice(0, 200);
    console.log('DEBUG_OUT ' + JSON.stringify(out, null, 1));
    throw e;
  }
  await page.waitForTimeout(2500);  // 等 auto-search

  out.hash = await page.evaluate(() => location.hash);
  out.tlNodeVal = await page.$eval('#tl-node', el => el.value).catch(() => 'NO #tl-node');
  out.ts0 = await page.$eval('#tl-h0', el => el.value) + ':' + await page.$eval('#tl-m0', el => el.value) + ':' + await page.$eval('#tl-s0', el => el.value);
  out.ts1 = await page.$eval('#tl-h1', el => el.value) + ':' + await page.$eval('#tl-m1', el => el.value) + ':' + await page.$eval('#tl-s1', el => el.value);
  out.stat = await page.$eval('#tl-stat', el => el.textContent).catch(() => 'NO #tl-stat');
  out.rowCount = await page.$$eval('#tltb tr.tl-row', els => els.length).catch(() => -1);
  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_jump.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
