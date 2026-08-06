// 诊断页摘要卡渲染检查 — playwright (Edge headless)
const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 300)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 300)));

  const out = {};
  await page.goto('http://127.0.0.1:8720/#diag', { waitUntil: 'networkidle' });
  await page.waitForTimeout(4000);

  // 页面主体文本 (mc 容器)
  out.mcText = (await page.$eval('#mc', el => el.textContent).catch(() => 'NO #mc')).slice(0, 400);

  // 摘要卡特征: "诊断结论" 文本
  out.hasSummary = await page.evaluate(() => document.body.innerHTML.includes('诊断结论'));
  out.summaryText = await page.evaluate(() => {
    const m = document.body.innerHTML.match(/诊断结论[^<]{0,60}/g);
    return m ? m.slice(0, 5) : null;
  });

  // 卡片数量统计
  out.cardCount = await page.$$eval('.l1-card', els => els.length);
  out.cards = await page.$$eval('.l1-card h4', els => els.map(e => e.textContent.trim().slice(0, 50)));

  // 离线诊断卡
  out.offlineCards = await page.$$eval('.diag-card', els => els.length);
  out.emptyCards = await page.$$eval('.card.empty', els => els.map(e => e.textContent.trim().slice(0, 80)));

  out.errors = errors;
  console.log(JSON.stringify(out, null, 2));
  await page.screenshot({ path: '.scratch/verification/diag_now.png', fullPage: true });
  await browser.close();
})();
