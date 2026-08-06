// 诊断页摘要独立渲染验证 — 正常 / L6 500 / L2 500 三场景
const { chromium } = require('playwright-core');

async function run(label, failUrl) {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message.slice(0, 200)));
  if (failUrl) {
    await page.route('**/api/diag/' + failUrl, route => route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"simulated"}' }));
  }
  await page.goto('http://127.0.0.1:8720/#diag', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  const out = await page.evaluate(() => {
    const t = document.body.innerText;
    return {
      hasSummary: t.includes('诊断结论'),
      summary: (t.match(/诊断结论[^\n]*/g) || [])[0] || null,
      probs: (t.match(/：.{0,80}/g) || []).filter(x => x.length > 2).slice(0, 8),
      cardCount: document.querySelectorAll('.l1-card').length,
      hasL6: t.includes('L6 SED 专项'),
      hasL2: t.includes('L2 在线维持'),
    };
  });
  out.errors = errors;
  await browser.close();
  console.log('── ' + label + ' ──');
  console.log(JSON.stringify(out, null, 1));
  return out;
}

(async () => {
  const a = await run('S1 正常渲染');
  const b = await run('S2 /api/diag/l6 → 500', 'l6');
  const c = await run('S3 /api/diag/l2 → 500', 'l2');

  const ok = a.hasSummary && b.hasSummary && c.hasSummary;
  console.log('\n结论: ' + (ok ? 'PASS' : 'FAIL') + ' (三场景摘要均渲染)');
  console.log('S1 摘要:', a.summary, '| S2:', b.summary, '| S3:', c.summary);
})();
