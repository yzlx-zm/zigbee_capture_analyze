// U8-2 跳转验证: 点击诊断卡设备行的 ⏱ → hash=#tl + 时间线节点过滤 = 该设备
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
await p.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 8000));
// 点击第一个 ⏱ (设备行跳时间线)
const click = await p.send('Runtime.evaluate', { expression: `(function(){
  var el = document.querySelector('.dev-jump[href="#tl"]');
  if (!el) return 'NO-JUMP-LINK';
  el.click();
  return 'clicked';
})()`, returnByValue: true });
console.log('点击:', click.result.result.value);
await new Promise(r => setTimeout(r, 4000));  // 等时间线页加载
const st = await p.send('Runtime.evaluate', { expression: `JSON.stringify({
  hash: location.hash,
  tlNode: (window.S||{}).tlNode || '',
  topoAddr: (window.S||{}).topoAddr || '',
  tlLoaded: document.body.innerText.includes('时间线')
})`, returnByValue: true });
p.close();
console.log('跳转后:', st.result.result.value);
