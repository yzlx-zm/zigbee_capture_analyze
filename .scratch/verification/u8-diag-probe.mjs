// U8 诊断页对比探针: 抓完整 bodyText + DOM 结构计数 (重构前后对比用)
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
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', {cacheDisabled: true});
await p.send('Page.enable');
await p.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 8000));
const r = await p.send('Runtime.evaluate', { expression: `JSON.stringify({
  l1cards: document.querySelectorAll('.l1-card').length,
  jumpLinks: Array.from(document.querySelectorAll('.dev-jump')).map(function(a){return a.textContent;}).slice(0,4),
  evTables: document.querySelectorAll('.ev-table').length,
  conclusions: document.querySelectorAll('.conclusion').length,
  divs: document.querySelectorAll('.dev').length,
  sections: document.querySelectorAll('.l1-sec').length,
  hasCoverage: document.body.innerText.includes('覆盖范围'),
  bodyText: document.body.innerText
})`, returnByValue: true });
p.close();
writeFileSync(process.argv[2] || 'u8-probe.json', r.result.result.value);
console.log('saved, l1cards:', JSON.parse(r.result.result.value).l1cards, 'sections:', JSON.parse(r.result.result.value).sections);
