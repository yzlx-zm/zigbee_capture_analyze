// U5 ZDP 载荷明细验证: 详情面板 ZDP 层显示 EUI64/Req Type/Start Index
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  await page.goto('http://127.0.0.1:8721/#tl', { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.click('#tshow', { timeout: 8000 });
  await page.waitForTimeout(1500);

  // 找 ZDP: NWK Addr Req 行 (可能有 ZDP 徽章行)
  const row = await page.$('#tltb tr.tl-row:has-text("NWK Addr Req")');
  if (row) {
    await row.click();
    await page.waitForTimeout(1000);
    out.zdpDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 500));
  } else { out.zdpDetail = 'NO ZDP ROW (可能本页无此帧, 翻页或放宽过滤)'; }
  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_zdp.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
