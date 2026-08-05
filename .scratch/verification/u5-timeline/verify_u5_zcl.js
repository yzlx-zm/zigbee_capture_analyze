// U5 ZCL 命令级显示验证: Data 帧类型列显示命令名 (Report Attributes 等)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  await page.goto('http://127.0.0.1:8720/#tl', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  out.hash = await page.evaluate(() => location.hash);
  out.mc = (await page.$eval('#mc', el => el.innerHTML.slice(0, 120)).catch(() => 'NO #mc')).replace(/\s+/g, ' ');
  try {
    await page.click('#tshow', { timeout: 5000 });
  } catch (e) {
    out.clickFail = e.message.slice(0, 100);
  }
  await page.waitForTimeout(1200);
  try { await page.waitForSelector('#tltb tr.tl-row', { timeout: 3000 }); } catch (e) {}

  // 检查类型列: 含 .zcl-cmd 的行
  out.zclRows = await page.$$eval('#tltb tr.tl-row', rows =>
    rows.map(r => {
      const t = r.querySelector('.zcl-cmd');
      return t ? r.querySelector('td:nth-child(2)').textContent.replace(/\s+/g, ' ').trim() : null;
    }).filter(Boolean).slice(0, 8));
  out.zclCount = await page.$$eval('#tltb .zcl-cmd', els => els.length);
  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_zcl.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
