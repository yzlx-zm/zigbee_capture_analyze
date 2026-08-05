// U5 cubx 帧详情 fallback 验证: Link Status 邻居列表 / Leave 标志 / 详情无空白
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  await page.goto('http://127.0.0.1:8721/#tl', { waitUntil: 'networkidle' });
  await page.click('#tshow');
  await page.waitForSelector('#tltb tr.tl-row', { timeout: 8000 });

  // 1. Link Status 行 → 详情 (邻居列表)
  const lsRow = await page.$('#tltb tr.tl-row:has-text("Link Status")');
  if (lsRow) {
    await lsRow.click();
    await page.waitForTimeout(1000);
    out.lsDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 400));
  } else { out.lsDetail = 'NO LS ROW'; }

  // 2. Leave 行 → 详情 (rejoin/request 标志)
  const lvRow = await page.$('#tltb tr.tl-row:has-text("Leave")');
  if (lvRow) {
    await lvRow.click();
    await page.waitForTimeout(1000);
    out.lvDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 300));
  } else { out.lvDetail = 'NO LEAVE ROW'; }

  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_cubx_detail.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
