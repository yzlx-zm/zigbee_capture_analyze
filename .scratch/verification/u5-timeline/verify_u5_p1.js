// P1 验证: 邻居表行点击跳转 → 时间线时间重置为抓包范围 (不清则残留旧窗口)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  // 全量数据进拓扑 (无时间线窗口)
  await page.goto('http://127.0.0.1:8721/#topo', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);
  out.tinfo = await page.$eval('#tinfo', el => el.textContent).catch(() => '?');

  // 邻居关系 tab → 选择设备 → 渲染邻居表行
  await page.click('.bp-tab:has-text("邻居关系")', { timeout: 8000 }).catch(e => out.tabClick = e.message.slice(0, 80));
  await page.waitForTimeout(1500);
  await page.selectOption('#nb-dev-sel', '0').catch(e => out.selFail = e.message.slice(0, 80));
  await page.waitForTimeout(1000);
  const rows = await page.$$eval('#bp-neighbors tr[onclick]', rs => rs.slice(0, 3).map(r => r.getAttribute('onclick'))).catch(() => []);
  out.nbRowCount = rows.length;
  if (rows.length) {
    out.firstRow = rows[0];
    // 先设一个旧时间窗口模拟残留 (修复前行为: topoT0/T1 保留, 跳转后不清理)
    await page.evaluate(() => { window.S.topoT0 = 1780364526; window.S.topoT1 = 1780364530; });
    await page.locator('#bp-neighbors tr[onclick]').first().click();
    await page.waitForFunction(() => location.hash.startsWith('#tl'), null, { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(2500);
    out.tlNode = await page.$eval('#tl-node', el => el.value).catch(() => '?');
    out.ts0 = await page.$eval('#tl-h0', el => el.value) + ':' + await page.$eval('#tl-m0', el => el.value) + ':' + await page.$eval('#tl-s0', el => el.value);
    out.ts1 = await page.$eval('#tl-h1', el => el.value) + ':' + await page.$eval('#tl-m1', el => el.value) + ':' + await page.$eval('#tl-s1', el => el.value);
    out.stat = await page.$eval('#tl-stat', el => el.textContent).catch(() => '?');
  }
  out.errors = errors;
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
