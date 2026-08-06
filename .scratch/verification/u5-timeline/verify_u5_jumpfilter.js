// U5 后续: 过滤外跳转 → 清除过滤定位 (用户强调的过滤保持场景)
// 场景: 类型过滤=APS Ack (原帧 Data 不在结果) → 点配对跳转 → 应清除过滤定位到帧 #31
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
  await page.click('#tshow');
  await page.waitForTimeout(1500);

  // 类型过滤 = APS Ack (目标原帧 31 是 Data → 不在结果内)
  await page.selectOption('#tl-type', 'APS Ack');
  await page.click('#tshow');
  await page.waitForTimeout(1200);
  out.filterStat = await page.$eval('#tl-stat', el => el.textContent);

  const ackRow = await page.$('#tltb tr.tl-row:has-text("APS Ack")');
  if (ackRow) {
    await ackRow.click();
    await page.waitForTimeout(800);
    const jump = await page.$('#tl-detail .ack-jump');
    if (jump) {
      out.peer = await jump.getAttribute('data-peer');
      await jump.click();
      await page.waitForTimeout(2000);
      out.statAfter = await page.$eval('#tl-stat', el => el.textContent).catch(() => '?');
      out.hl = await page.$eval('#tltb tr.tl-row.hl', tr => tr.dataset.pid).catch(() => 'NO HL');
      out.typeVal = await page.$eval('#tl-type', el => el.value).catch(() => '?');
      out.detail = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 60)).catch(() => '?');
    } else out.peer = 'NO JUMP';
  } else out.ackDetail = 'NO ACK ROW';
  out.errors = errors;
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
