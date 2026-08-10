// U8 错误路径验证: Fetch 拦截 /api/diag/l6 返回 404 → 单模块失败不阻塞整页
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#diag';
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
await p.send('Page.enable');
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', { cacheDisabled: true });
await p.send('Fetch.enable', { patterns: [{ urlPattern: '*api/diag/l6*', requestStage: 'Request' }] });
let intercepted = 0;
p.ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.method === 'Fetch.requestPaused') {
    intercepted++;
    p.send('Fetch.failRequest', { requestId: m.params.requestId, errorReason: 'NotFound' });
  }
});
await p.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 8000));
const nav = await p.send('Runtime.evaluate', { expression: 'location.href + " | bodyLen=" + document.body.innerText.length', returnByValue: true });
console.log('NAV:', nav.result.result.value);
const expr = "JSON.stringify({l1cards: document.querySelectorAll('.l1-card').length, sections: document.querySelectorAll('.l1-sec').length, hasSummary: document.body.innerText.includes('诊断结论'), hasL6: document.body.innerText.includes('L6 SED'), hasErr: document.body.innerText.includes('诊断数据加载失败'), bodyLen: document.body.innerText.length, bodyStart: document.body.innerText.slice(0,120)})";
const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true });
p.close();
const v = JSON.parse(r.result.result.value || "{}");
console.log('l6 请求被拦截:', intercepted);
console.log('l1cards:', v.l1cards, '| sections:', v.sections, '| 摘要:', v.hasSummary, '| L6 区显示:', v.hasL6, '| 整页错误:', v.hasErr);
console.log('摘要首行:', v.firstLine);
