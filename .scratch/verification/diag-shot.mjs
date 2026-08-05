// 诊断页截图验证 (2026-08-05): 顶部摘要 + 结论 + 证据表
// 用法: 先起 Edge --headless=new --remote-debugging-port=9222, 再 node diag-shot.mjs
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#diag';
import { writeFileSync } from 'fs';

async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, close: () => ws.close() };
}

const p = await newPage();
// 打开诊断页
await p.send('Page.enable');
await p.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 6000));  // 等 L1/L3/offline 渲染

// 检查页面内容
const r = await p.send('Runtime.evaluate', {
  expression: `JSON.stringify({
    summary: document.getElementById('diag-summary') ? document.getElementById('diag-summary').innerText.slice(0, 300) : 'NO-SUMMARY',
    l1cards: document.querySelectorAll('.l1-card').length,
    evTables: document.querySelectorAll('.ev-table').length,
    conclusions: document.querySelectorAll('.conclusion').length,
    bodyText: document.body.innerText.slice(0, 500)
  })`,
  returnByValue: true,
});
console.log('页面状态:', r.result.result.value);

// 全页截图
const shot = await p.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
writeFileSync('D:/ai_agent/zigbee_capture_analyze/.scratch/verification/diag-full.png', Buffer.from(shot.result.data, 'base64'));
console.log('截图已存 diag-full.png');
p.close();
