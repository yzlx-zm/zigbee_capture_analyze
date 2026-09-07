// T3 使用手册 — CDP 截图共用库 (复用 u12/u13 范式)
// 用法: import { openTab, shot, ev, sleep } from './shot_lib.mjs'
export const CDP = 'http://127.0.0.1:9222';
const fs = await import('fs');
const fsp = await import('fs/promises');

export async function openTab(url, { width = 1440, height = 940, scale = 1 } = {}) {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(); const exceptions = [];
  ws.onmessage = ev => { const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails?.exception?.description || 'x'); };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  const evf = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result?.result?.value; };
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: scale, mobile: false });
  await send('Page.navigate', { url });
  return {
    id: t.id, ws, send, ev: evf,
    exceptions,
    shot: async (path) => {
      const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 88, captureBeyondViewport: true });
      await fsp.mkdir(path.substring(0, path.lastIndexOf('/')), { recursive: true });
      await fs.promises.writeFile(path, Buffer.from(r.result.data, 'base64'));
      console.log('📷', path);
    },
    close: () => fetch(`${CDP}/json/close/${t.id}`),
  };
}
export const sleep = ms => new Promise(r => setTimeout(r, ms));
