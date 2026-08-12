// U3 节点页行内展开验证 — CDP 驱动 (一次性验证工具, 素材: 中继入网抓包(1).cubx → 4157包/112节点)
// 用法: 先起 Edge --headless=new --remote-debugging-port=9222, 再 node cdp_test.mjs
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#nodes';

async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0;
  const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, close: () => ws.close() };
}

async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.error) throw new Error(r.error.message);
  if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}

const results = [];
function check(name, cond, extra = '') {
  results.push({ name, ok: !!cond });
  console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`);
}

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await new Promise(r => setTimeout(r, 3000));

// 1. 页面骨架 (只查主表: 邻居表嵌套在 detail 行内 → 用直接子代选择器)
// U9 (08-12): 精简 6 列 (地址|设备类型|厂商名|型号|出现次数|操作)
const thCount = await evaluate(page, `document.querySelectorAll('.nodes-table-wrap > table > thead th').length`);
check('表头列数 = 6 (U9 精简)', thCount === 6, `th=${thCount}`);
const thTxt = await evaluate(page, `[...document.querySelectorAll('.nodes-table-wrap > table > thead th')].map(t=>t.textContent).join('|')`);
check('表头含 厂商名/型号', thTxt.includes('厂商名') && thTxt.includes('型号'), thTxt);
check('表头不再含 PAN/协调器/包类型', !/PAN|协调器|包类型/.test(thTxt), thTxt);
const hiddenCount = await evaluate(page, `document.querySelectorAll('#ntb .nd-detail:not(.hidden)').length`);
check('详情行默认全部收起', hiddenCount === 0, `展开中的详情行=${hiddenCount}`);
const rowCount = await evaluate(page, `document.querySelectorAll('#ntb .nd-row').length`);
check('节点行数 = 112', rowCount === 112, `rows=${rowCount}`);
const firstType = await evaluate(page, `document.querySelector('#ntb .nd-row td:nth-child(2)').textContent`);
check('设备类型列有中文值', /协调器|路由|终端|未知/.test(firstType), firstType);
// 厂商/型号列 (有 Basic Read Attr Rsp 的节点; 无 → '-' 兜底)
const manufCol = await evaluate(page, `[...document.querySelectorAll('#ntb .nd-row')].map(r=>r.children[2].textContent).filter(v=>v!=='-').length`);
check('厂商名列有非空值 (Basic 属性提取)', manufCol > 0, `非空=${manufCol}`);
const modelCol = await evaluate(page, `[...document.querySelectorAll('#ntb .nd-row')].map(r=>r.children[3].textContent).filter(v=>v!=='-').length`);
check('型号列有非空值', modelCol > 0, `非空=${modelCol}`);
check('🎯 定位按钮 = 112 个', await evaluate(page, `document.querySelectorAll('#ntb .nd-locate').length`) === 112);

// 2. 行内展开 (0x1885 = aid 6277)
await evaluate(page, `document.querySelector('#ntb .nd-row[data-aid="6277"]').click(); true`);
await new Promise(r => setTimeout(r, 500));
const detail = await evaluate(page, `(()=>{const el=document.querySelector('.nd-detail[data-for="6277"]');return {hidden:el.classList.contains('hidden'),text:el.textContent};})()`);
check('点击 0x1885 行展开详情', !detail.hidden);
check('详情含首见/末见', /首见/.test(detail.text));
check('详情含 LQI/RSSI 统计', /LQI/.test(detail.text) && /RSSI/.test(detail.text));
check('详情含 EUI64 (70:b3:d5:2b:60:0b:db:be)', /70:b3:d5:2b:60:0b:db:be/.test(detail.text));
check('详情含设备类型 路由', /路由/.test(detail.text));
// U9: 控制命令 mini 表也是 .tbl — 邻居表是第一个 (限定选择器)
const nbRows = await evaluate(page, `document.querySelectorAll('.nd-detail[data-for="6277"] .tbl')[0].querySelectorAll('tr').length`);
check('0x1885 邻居表 5 行 (表头+4 邻居)', nbRows === 5, `rows=${nbRows}`);
const nbHasAsym = await evaluate(page, `/对称|OK|WEAK|ASYMM/.test(document.querySelector('.nd-detail[data-for="6277"] .tbl').textContent)`);
check('邻居表含链路质量列', nbHasAsym);
// U9: 端点统计 + 控制命令统计小节 (0x1885 中继节点)
const epText = await evaluate(page, `document.querySelector('.nd-detail[data-for="6277"]').textContent`);
check('展开含端点统计 (EP 0x01×57)', /EP 0x01×57/.test(epText), '见详情文本');
check('展开含控制命令小节 (簇/命令/方向/频率)', /Off|On|Report Attributes/.test(epText) && /频率/.test(epText), '见详情文本');

// 3. 收起
await evaluate(page, `document.querySelector('#ntb .nd-row[data-aid="6277"]').click(); true`);
const hidden2 = await evaluate(page, `document.querySelector('.nd-detail[data-for="6277"]').classList.contains('hidden')`);
check('再点一次收起详情', hidden2 === true);

// 4. 无邻居节点 (0x838D = 33677) 显示提示
await evaluate(page, `document.querySelector('#ntb .nd-row[data-aid="33677"]').click(); true`);
await new Promise(r => setTimeout(r, 300));
const noNb = await evaluate(page, `document.querySelector('.nd-detail[data-for="33677"]').textContent`);
check('0x838D 无邻居时显示提示', /无 Link Status/.test(noNb));
check('0x838D 也有 EUI64', /a4:c1:38:4c:5e:63:47:68/.test(noNb));

// 5. 🎯 定位按钮 → 跳转拓扑
await evaluate(page, `document.querySelector('#ntb .nd-locate').click(); true`);
await new Promise(r => setTimeout(r, 1500));
const jumped = await evaluate(page, `location.hash`);
const taddr = await evaluate(page, `document.getElementById('taddr') ? document.getElementById('taddr').value : null`);
check('🎯 跳转拓扑页', jumped === '#topo', jumped);
check('拓扑页 taddr 已填地址', !!taddr && taddr.length > 0, `taddr=${taddr}`);

// 6. 截图 (展开态)
await evaluate(page, `location.hash='nodes'; true`);
await new Promise(r => setTimeout(r, 2000));
await evaluate(page, `document.querySelector('#ntb .nd-row[data-aid="6277"]').click(); true`);
await new Promise(r => setTimeout(r, 500));
const shot = await page.send('Page.captureScreenshot', { format: 'png' });
const { writeFileSync } = await import('fs');
writeFileSync('u3_nodes.png', Buffer.from(shot.result.data, 'base64'));
console.log('📸 截图已保存 u3_nodes.png');

const failed = results.filter(r => !r.ok);
console.log(`\n结果: ${results.length - failed.length}/${results.length} 通过`);
page.close();
process.exit(failed.length ? 1 : 0);
