// U13 路由路径链折叠/展开验证 (2026-08-26) — v2: 复用现有 target, 导航刷新
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#topo';
import { writeFileSync } from 'fs';

// 从 /json/list 选一个 #topo target 连接 (不新建页面, 避免 target 爆炸)
const list = await (await fetch(`${CDP}/json/list`)).json();
const tgt = list.find(t => t.type === 'page' && t.url.includes('#topo')) || list.find(t => t.type === 'page');
if (!tgt) { console.error('无可用 target'); process.exit(1); }
console.log('连接 target:', tgt.url.slice(0, 60));

const ws = new WebSocket(tgt.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map();
const errors = [];
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type))
    errors.push(m.params.args.map(a => a.value || a.description || '').join(' ').slice(0, 300));
  if (m.method === 'Runtime.exceptionThrown') errors.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text).slice(0, 300));
};
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evalv = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  return r.result?.result?.value;
};

await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', { url: TARGET });

// 轮询等待 fold-head 渲染 (最多 40s)
let ready = false;
for (let i = 0; i < 40; i++) {
  await new Promise(r => setTimeout(r, 1000));
  const n = await evalv(`document.querySelectorAll('#bp-routes .fold-head').length`).catch(() => 0);
  if (n >= 3) { ready = true; console.log(`fold-head 已渲染 (${n} 个), 等待 ${i + 1}s`); break; }
}
if (!ready) { console.error('❌ 40s 内 fold-head 未渲染'); process.exit(1); }
await new Promise(r => setTimeout(r, 1500));

// ── 1. 初始结构 ──
const init = await evalv(`JSON.stringify({
  heads: [...document.querySelectorAll('#bp-routes .fold-head')].map(h => ({
    sec: h.dataset.sec, arrow: h.querySelector('.fold-arrow').textContent, text: h.innerText.slice(0, 55)
  })),
  bodies: [...document.querySelectorAll('#bp-routes .path-body')].map(b => ({
    sec: b.dataset.body, rows: b.querySelectorAll('.path-row').length, visible: b.style.display !== 'none'
  })),
  expandBtns: [...document.querySelectorAll('.expand-all')].map(x => x.dataset.sec + ':' + x.innerText.slice(0, 25)),
  totalRows: document.querySelectorAll('#bp-routes .path-row').length
})`);
console.log('═══ 1. 初始结构 ═══');
console.log(JSON.parse(init));

// ── 2. 点击"下行"头部折叠 ──
await evalv(`document.querySelector('#bp-routes .fold-head[data-sec="down"]').click()`);
await new Promise(r => setTimeout(r, 300));
console.log('═══ 2. 折叠 down ═══', await evalv(`JSON.stringify({
  arrow: document.querySelector('#bp-routes .fold-head[data-sec="down"] .fold-arrow').textContent,
  hidden: document.querySelector('#bp-routes .path-body[data-body="down"]').style.display
})`));

// ── 3. 再点展开 ──
await evalv(`document.querySelector('#bp-routes .fold-head[data-sec="down"]').click()`);
await new Promise(r => setTimeout(r, 300));
console.log('═══ 3. 展开 down ═══', await evalv(`JSON.stringify({
  arrow: document.querySelector('#bp-routes .fold-head[data-sec="down"] .fold-arrow').textContent,
  hidden: document.querySelector('#bp-routes .path-body[data-body="down"]').style.display
})`));

// ── 4. 上行: 截断 → 展开全部 → 收起 ──
const upBefore = await evalv(`document.querySelector('#bp-routes .path-body[data-body="up"]').querySelectorAll('.path-row').length`);
await evalv(`[...document.querySelectorAll('.expand-all')].find(x => x.dataset.sec === 'up')?.click()`);
await new Promise(r => setTimeout(r, 600));
const upAfter = await evalv(`JSON.stringify({
  rows: document.querySelector('#bp-routes .path-body[data-body="up"]').querySelectorAll('.path-row').length,
  btns: [...document.querySelectorAll('.expand-all')].map(x => x.dataset.sec + ':' + x.innerText.slice(0, 25))
})`);
await evalv(`[...document.querySelectorAll('.expand-all')].find(x => x.dataset.sec === 'up')?.click()`);
await new Promise(r => setTimeout(r, 600));
const upCollapse = await evalv(`document.querySelector('#bp-routes .path-body[data-body="up"]').querySelectorAll('.path-row').length`);
console.log('═══ 4. 上行 截断→展开→收起 ═══');
console.log('截断:', upBefore, '| 展开:', upAfter, '| 收起:', upCollapse);

// ── 5. 重绘后折叠状态保留 (折叠 down 后触发 up 展开全部重绘) ──
await evalv(`document.querySelector('#bp-routes .fold-head[data-sec="down"]').click()`);
await evalv(`[...document.querySelectorAll('.expand-all')].find(x => x.dataset.sec === 'up')?.click()`);
await new Promise(r => setTimeout(r, 600));
console.log('═══ 5. 重绘后状态保留 ═══', await evalv(`JSON.stringify({
  downArrow: document.querySelector('#bp-routes .fold-head[data-sec="down"] .fold-arrow').textContent,
  downHidden: document.querySelector('#bp-routes .path-body[data-body="down"]').style.display,
  upRows: document.querySelector('#bp-routes .path-body[data-body="up"]').querySelectorAll('.path-row').length
})`));

// ── 截图 (折叠 down 状态) ──
const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
writeFileSync('D:/ai_agent/zigbee_capture_analyze/.scratch/verification/u13_fold_verify.png', Buffer.from(shot.result.data, 'base64'));
console.log('截图: u13_fold_verify.png');
console.log('═══ 控制台错误 ═══', errors.length ? errors.slice(0, 10) : '(无)');
ws.close();
