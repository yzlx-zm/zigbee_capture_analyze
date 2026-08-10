// U8 顺序修复验证: Fetch 延迟 /api/diag/l1 响应 2s → 验证最终 section 顺序仍为注册表顺序
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
await p.send('Fetch.enable', { patterns: [{ urlPattern: '*api/diag/l1*', requestStage: 'Request' }] });
const delayed = [];
p.ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.method === 'Fetch.requestPaused') {
    const reqId = m.params.requestId;
    if (delayed.length < 1) {
      delayed.push(reqId);
      setTimeout(() => p.send('Fetch.continueRequest', { requestId: reqId }), 2000);  // 延迟 L1 2s
    } else {
      p.send('Fetch.continueRequest', { requestId: reqId });
    }
  }
});
await p.send('Page.navigate', { url: TARGET });
// 3s 时 (L1 应已延迟中, L2/L3/L6 应已完成): 检查中间态顺序
await new Promise(r => setTimeout(r, 3000));
const mid = await p.send('Runtime.evaluate', { expression: `JSON.stringify(Array.from(document.querySelectorAll('.l1-sec h3')).map(h => h.textContent.trim()))`, returnByValue: true });
// 5s 时 (L1 已放行): 检查最终顺序
await new Promise(r => setTimeout(r, 2500));
const fin = await p.send('Runtime.evaluate', { expression: `JSON.stringify(Array.from(document.querySelectorAll('.l1-sec h3')).map(h => h.textContent.trim()))`, returnByValue: true });
p.close();
console.log('中间态 (L1 未完成) 顺序:', mid.result.result.value);
console.log('最终顺序:', fin.result.result.value);
