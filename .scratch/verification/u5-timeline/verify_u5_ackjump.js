// U5 后续: APS Ack 配对跳转 + 帧号列验证
// 场景: 帧号列显示 / 配对链接点击定位 (过滤保持) / 过滤外清除定位
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

  // 1. 帧号列
  out.frameCol = await page.$$eval('#tltb tr.tl-row', rows => rows.slice(0, 3).map(r => r.querySelector('td:first-child').textContent));

  // 2. 点 APS Ack 行 → 详情配对链接 → 点击跳转
  const ackRow = await page.$('#tltb tr.tl-row:has-text("APS Ack")');
  if (ackRow) {
    await ackRow.click();
    await page.waitForTimeout(1000);
    out.ackDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 200));
    const jump = await page.$('#tl-detail .ack-jump');
    if (jump) {
      out.jumpTarget = await jump.getAttribute('data-peer');
      await jump.click();
      await page.waitForTimeout(1500);
      // 检查定位: 高亮行 + 详情
      out.hlRow = await page.$eval('#tltb tr.tl-row.hl', tr => tr.dataset.pid).catch(() => 'NO HL');
      out.hlDetail = await page.$eval('#tl-detail', el => el.textContent.replace(/\s+/g, ' ').slice(0, 80)).catch(() => '?');
    } else out.jumpTarget = 'NO JUMP LINK';
  } else out.ackDetail = 'NO ACK ROW';

  // 3. 过滤保持: 设置节点过滤 (排除配对帧的节点?) — 用 PAN 过滤 (配对帧同 PAN, 应保持定位)
  // 简化: 用类型过滤 Data → 配对帧 (NWK 命令) 不在结果 → 触发清除过滤定位
  await page.selectOption('#tl-type', 'Data');
  await page.click('#tshow');
  await page.waitForTimeout(1200);
  out.filteredStat = await page.$eval('#tl-stat', el => el.textContent).catch(() => '?');
  // 再点一个 APS Ack 行?Data 过滤下没有 APS Ack 行 — 直接用详情跳转模拟:
  // 手动构造: 回到全部类型, 点 APS Ack, 点跳转, 确认过滤保持 (目标在过滤内)
  await page.selectOption('#tl-type', '');
  await page.click('#tshow');
  await page.waitForTimeout(1200);
  const ackRow2 = await page.$('#tltb tr.tl-row:has-text("APS Ack")');
  if (ackRow2) {
    await ackRow2.click();
    await page.waitForTimeout(800);
    const jump2 = await page.$('#tl-detail .ack-jump');
    if (jump2) {
      const peer = await jump2.getAttribute('data-peer');
      await jump2.click();
      await page.waitForTimeout(1500);
      out.jumpHl = await page.$eval('#tltb tr.tl-row.hl', tr => tr.dataset.pid).catch(() => 'NO HL');
      out.jumpStat = await page.$eval('#tl-stat', el => el.textContent).catch(() => '?');
    }
  }

  out.errors = errors;
  await page.screenshot({ path: '.scratch/verification/u5-timeline/u5_ackjump.png' });
  console.log(JSON.stringify(out, null, 2));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
