// U15 前端验证: 节点页"示例"弹层 (帧分层解析+载荷字段) + 导出画像弹层 + 时间线详情载荷区
// 前置: 后端 8720 已导入 dimmer 素材 (需求32533_simon_dimmer_涂鸦入网_ce5b.cubx)
import { writeFileSync } from 'fs';
const CDP = 'http://127.0.0.1:9222';
async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, close: () => ws.close() };
}
async function shot(p, file) {
  const r = await p.send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(file, Buffer.from(r.result.data, 'base64'));
  console.log('📸', file);
}
async function wait(p, ms) { await new Promise(r => setTimeout(r, ms)); }
async function ev(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  return r.result.result ? r.result.result.value : null;
}

const p = await newPage();
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', { cacheDisabled: true });
await p.send('Page.enable');
await p.send('Page.navigate', { url: 'http://localhost:8720/#nodes' });
await wait(p, 6000);

// ── ① 节点页: 展开 dimmer 行 (0xCE5B) ──
const rows = await ev(p, `JSON.stringify({
  rowCount: document.querySelectorAll('.nd-row').length,
  dimmerRow: (function(){ var r=document.querySelectorAll('.nd-row'); for(var i=0;i<r.length;i++){ if(r[i].textContent.includes('CE5B')||r[i].textContent.includes('TS0601')) return r[i].dataset.aid; } return null; })()
})`);
console.log('节点行:', rows);
const aid = JSON.parse(rows).dimmerRow;
if (!aid) { console.log('❌ 未找到 dimmer 行'); process.exit(1); }
await ev(p, `document.querySelector('.nd-row[data-aid="${aid}"]').click()`);
await wait(p, 800);
const detail = await ev(p, `JSON.stringify({
  sampleBtns: document.querySelectorAll('.nd-sample').length,
  exportBtn: !!document.querySelector('.nd-export'),
  clusterRows: document.querySelectorAll('.nd-detail[data-for="${aid}"] .tbl tbody tr').length
})`);
console.log('展开详情:', detail);

// ── ② 点击"📄 示例" → 弹层 ──
await ev(p, `document.querySelector('.nd-sample').click()`);
await wait(p, 1500);
const modal = await ev(p, `JSON.stringify({
  exists: !!document.querySelector('.nd-modal'),
  title: document.querySelector('.nd-modal-title') ? document.querySelector('.nd-modal-title').textContent : '',
  layers: document.querySelectorAll('.nd-layer').length,
  payloadRows: document.querySelectorAll('.nd-payload-table tbody tr').length,
  firstPayload: document.querySelector('.nd-payload-table tbody tr') ? document.querySelector('.nd-payload-table tbody tr').textContent : '',
  text: document.querySelector('.nd-modal') ? document.querySelector('.nd-modal').innerText.slice(0, 600) : ''
})`);
console.log('示例弹层:', modal);
await shot(p, 'u15_sample_modal.png');
const modalData = JSON.parse(modal);

// ── ③ 关闭弹层 → 点"导出画像" ──
await ev(p, `document.querySelector('.nd-modal-close').click()`);
await wait(p, 500);
await ev(p, `document.querySelector('.nd-export').click()`);
await wait(p, 1500);
const ex = await ev(p, `JSON.stringify({
  title: document.querySelector('.nd-modal-title') ? document.querySelector('.nd-modal-title').textContent : '',
  dlBtns: document.querySelectorAll('.nd-modal [data-f]').length
})`);
console.log('导出弹层:', ex);
await shot(p, 'u15_export_modal.png');
await ev(p, `document.querySelector('.nd-modal-close').click()`);

// ── ④ 时间线详情: 涂鸦 0xEF00 帧载荷区 ──
await ev(p, `location.hash = 'tl'`);
await wait(p, 4000);
// 时间线默认空列表 → 点「🔍 查看」全量加载
await ev(p, `document.getElementById('tshow').click()`);
await wait(p, 4000);
const tl = await ev(p, `(function(){
  var rows = document.querySelectorAll('#tltb tr.tl-row');
  var found = null;
  for (var i=0;i<rows.length;i++){ if(rows[i].textContent && rows[i].textContent.includes('查询 DP')){ found=rows[i]; break; } }
  if(!found) return JSON.stringify({found:false, hint: rows.length+' 行', sample: rows[0] ? rows[0].textContent.slice(0,80) : ''});
  found.click();
  return JSON.stringify({found:true, pid: found.getAttribute('data-pid'), text: found.textContent.slice(0,120)});
})()`);
console.log('时间线定位涂鸦帧:', tl);
await wait(p, 2000);
const tlDetail = await ev(p, `JSON.stringify({
  detailPanel: !!document.getElementById('tl-detail'),
  hasPayloadParse: document.getElementById('tl-detail') ? document.getElementById('tl-detail').innerText.includes('载荷解析') : false,
  payloadText: document.getElementById('tl-detail') ? (function(){ var t=document.getElementById('tl-detail').innerText; var i=t.indexOf('载荷解析'); return i>=0? t.slice(i, i+300):''; })() : ''
})`);
console.log('时间线载荷区:', tlDetail);
await shot(p, 'u15_timeline_payload.png');

// ── 汇总 ──
const report = {
  nodes: JSON.parse(rows), detail: JSON.parse(detail), modal: modalData,
  export: JSON.parse(ex), timeline: JSON.parse(tl), timelineDetail: JSON.parse(tlDetail)
};
writeFileSync('u15-verify.json', JSON.stringify(report, null, 2));
console.log('✅ U15 验证完成, 结果见 u15-verify.json');
p.close();
