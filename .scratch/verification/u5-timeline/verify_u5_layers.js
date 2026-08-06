// U5 各层明细验证: Route Request 详情 (Originator/Dest/Cost) + Device Announce (ZDP 载荷)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  await page.goto('http://127.0.0.1:8721/#tl', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  await page.click('#tshow', { timeout: 8000 });
  await page.waitForTimeout(1500);

  // 1. Route Request 行 → 详情
  const rr = await page.$('#tltb tr.tl-row:has-text("Route Request")');
  if (rr) {
    await rr.click();
    await page.waitForTimeout(1000);
    out.routeReq = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 450));
  } else out.routeReq = 'NO ROW';

  // 2. Device Announce 行 → 详情 (ZDP 载荷)
  const da = await page.$('#tltb tr.tl-row:has-text("Device Announce")');
  if (da) {
    await da.click();
    await page.waitForTimeout(1000);
    out.devAnnounce = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 450));
  } else out.devAnnounce = 'NO ROW';

  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_layers.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
