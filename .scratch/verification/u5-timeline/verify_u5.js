// U5 时间线优化 — playwright 端到端验证 (Edge headless)
// 验证点: 类型下拉动态化 / 事件徽章 / 详情加载 / console 错误
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));
  page.on('response', r => { if (r.status() === 404) out.resp404 = (out.resp404 || []).concat(r.url()); });

  const out = {};
  await page.goto('http://127.0.0.1:8720/#tl', { waitUntil: 'networkidle' });
  out.typesFetch = await page.evaluate(async () => {
    try {
      const r = await fetch('/api/packets/types');
      const j = await r.json();
      return r.status + ' len=' + ((j && j.types) || []).length;
    } catch (e) { return 'FETCHERR ' + e.message; }
  });

  // 1. 类型下拉动态填充 (含 Leave + 计数) — waitForFunction 数 option (option 不可用 visible 检测)
  try {
    await page.waitForFunction(() => document.querySelectorAll('#tl-type option').length > 1, null, { timeout: 8000 });
    const typeOpts = await page.$$eval('#tl-type option', els => els.map(o => o.textContent));
    out.typeOpts = typeOpts.length;
    out.typeHasCount = typeOpts.some(t => t.includes('('));
  } catch (e) { out.typeOpts = 'FAIL: ' + e.message; }

  // 2. 查看 → 包列表 + 事件徽章
  await page.click('#tshow');
  try {
    await page.waitForSelector('#tltb tr.tl-row', { timeout: 8000 });
  } catch (e) {
    await page.waitForTimeout(1500);
    out.stat = await page.$eval('#tl-stat', el => el.textContent).catch(() => 'NO #tl-stat');
    out.tltbHtml = (await page.$eval('#tltb', el => el.innerHTML).catch(() => 'NO #tltb')).slice(0, 300);
    out.ts0 = await page.$eval('#tl-h0', el => el.value).catch(() => '?');
    out.ts1 = await page.$eval('#tl-h1', el => el.value).catch(() => '?');
    throw e;
  }
  const badgeInfo = await page.$$eval('#tltb .badge-ev', els =>
    els.map(b => b.className + ':' + b.textContent.trim()));
  out.badges = badgeInfo.slice(0, 6);

  // 3. 点击 Leave 行 → 详情面板 (不炸)
  const leaveRow = await page.$('#tltb tr.tl-row:has-text("Leave")');
  if (leaveRow) {
    await leaveRow.click();
    await page.waitForTimeout(900);
    out.leaveDetail = await page.$eval('#tl-detail', el => el.textContent.slice(0, 120).replace(/\n/g, ' '));
  } else { out.leaveDetail = 'NO LEAVE ROW'; }

  // 4. 点击 Network Status 行 → 详情面板
  const nsRow = await page.$('#tltb tr.tl-row:has-text("Network Status")');
  if (nsRow) {
    await nsRow.click();
    await page.waitForTimeout(900);
    out.nsDetail = await page.$eval('#tl-detail', el => el.textContent.slice(0, 120).replace(/\n/g, ' '));
  } else { out.nsDetail = 'NO NS ROW'; }

  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_timeline.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
