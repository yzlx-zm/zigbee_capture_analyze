// 节点页三方案 mockup 截图
import { writeFileSync } from 'fs';
const CDP = 'http://127.0.0.1:9222';
const URL = 'file:///D:/ai_agent/zigbee_capture_analyze/.scratch/verification/nodes-mockup.html';
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
await p.send('Page.navigate', { url: URL });
await new Promise(r => setTimeout(r, 1500));
const shot = await p.send('Page.captureScreenshot', { format: 'jpeg', quality: 92 });
p.close();
writeFileSync(process.argv[2] || 'nodes-mockup.jpg', Buffer.from(shot.result.data, 'base64'));
console.log('saved');
