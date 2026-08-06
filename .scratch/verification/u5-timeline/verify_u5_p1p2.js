// P1+P2 验证: 邻居表跳转清时间 (P1) / 时间线窗口→拓扑同步 (P2)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};

  // ── P2: 时间线设时间窗口 → 拓扑同步 ──
  await page.goto('http://127.0.0.1:8721/#tl', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  await page.selectOption('#tl-h0', '01'); await page.selectOption('#tl-m0', '42'); await page.selectOption('#tl-s0', '10');
  await page.selectOption('#tl-h1', '01'); await page.selectOption('#tl-m1', '42'); await page.selectOption('#tl-s1', '20');
  await page.click('#tshow');
  await page.waitForTimeout(1500);
  out.tlStat = await page.$eval('#tl-stat', el => el.textContent).catch(() => '?');

  await page.evaluate(() => { location.hash = 'topo'; });
  await page.waitForTimeout(3500);  // 等拓扑 init + 数据加载
  out.winSize = await page.$eval('#twin-size', el => el.value).catch(() => 'NO twin-size');
  out.timeLabel = await page.$eval('#ttime-label', el => el.textContent).catch(() => '?');
  out.slider = await page.$eval('#tsl', el => el.value).catch(() => '?');
  out.tinfo = await page.$eval('#tinfo', el => el.textContent).catch(() => '?');
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_p2_topo.png' });

  // ── P1: 邻居表行点击 → 时间线时间重置为抓包范围 ──
  await page.click('.bp-tab:has-text("邻居关系")', { timeout: 8000 }).catch(() => out.tabClick = 'FAIL');
  await page.waitForTimeout(1200);
  const nbRows = await page.$$eval('#bp-neighbors tr[onclick]', rs => rs.slice(0, 3).map(r => r.getAttribute('onclick'))).catch(() => []);
  out.nbRows = nbRows;
  if (nbRows.length) {
    await page.locator('#bp-neighbors tr[onclick]').first().click();
    await page.waitForFunction(() => location.hash.startsWith('#tl'), null, { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(2500);
    out.tlNode = await page.$eval('#tl-node', el => el.value).catch(() => '?');
    out.ts0 = await page.$eval('#tl-h0', el => el.value) + ':' + await page.$eval('#tl-m0', el => el.value) + ':' + await page.$eval('#tl-s0', el => el.value);
    out.ts1 = await page.$eval('#tl-h1', el => el.value) + ':' + await page.$eval('#tl-m1', el => el.value) + ':' + await page.$eval('#tl-s1', el => el.value);
    await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_p1_jump.png' });
  } else out.nbRows = 'NO NEIGHBOR ROWS (素材可能无邻居表)';

  out.errors = errors;
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
