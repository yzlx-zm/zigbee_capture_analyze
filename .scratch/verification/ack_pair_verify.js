// APS Ack 配对前端验证 — 类型列命令名 + 详情配对行
const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));

  const out = {};
  await page.goto('http://127.0.0.1:8720/#tl', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  // 类型过滤选"全部" + 点击查看
  await page.evaluate(() => {
    const sel = document.querySelector('#tl-type');
    if (sel) { sel.value = ''; sel.dispatchEvent(new Event('change')); }
  });
  await page.click('#tshow').catch(() => {});
  try { await page.waitForSelector('#tltb tr.tl-row', { timeout: 8000 }); } catch (e) { out.loadErr = '列表未加载'; }

  // 1. 类型列显示命令名 (APS Cmd → VerifyKey/TransportKey)
  out.cmdRows = await page.$$eval('#tltb tr.tl-row', rows =>
    rows.map(r => r.textContent.trim().slice(0, 60))
      .filter(t => /VerifyKey|TransportKey|RequestKey|Confirm/i.test(t))
      .slice(0, 6));

  // 2. 点击 VerifyKey 行 → 详情面板配对行
  const vkRow = await page.$('#tltb tr.tl-row:has-text("VerifyKey")');
  if (vkRow) {
    await vkRow.click();
    await page.waitForTimeout(900);
    out.vkDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\n+/g, ' | ').slice(0, 300));
    out.hasPair = await page.evaluate(() => document.querySelector('#tl-detail .ack-pair') !== null);
  } else { out.vkDetail = 'NO VerifyKey ROW'; }

  // 3. 点击 APS Ack 行 → 详情面板配对行
  const ackRow = await page.$('#tltb tr.tl-row:has-text("APS Ack")');
  if (ackRow) {
    await ackRow.click();
    await page.waitForTimeout(900);
    out.ackDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\n+/g, ' | ').slice(0, 250));
  } else { out.ackDetail = 'NO APS Ack ROW'; }

  out.errors = errors;
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})();
