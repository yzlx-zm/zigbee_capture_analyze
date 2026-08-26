// S4 报文页稳定化 — 复验 (修复后): Security 层 / 详情帧号 / 主流程回归
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#tl';

function newPage() {
  return new Promise((resolve, reject) => {
    fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' }).then(t => t.json()).then(t => {
      const ws = new WebSocket(t.webSocketDebuggerUrl);
      ws.onopen = () => {
        let id = 0; const pending = new Map(); const events = {};
        ws.onmessage = ev => { const m = JSON.parse(ev.data);
          if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
          else if (m.method && events[m.method]) events[m.method].forEach(f => f(m.params));
        };
        const send = (method, params = {}) => new Promise(res => {
          const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params }));
        });
        resolve({ ws, send, on: (m, f) => { events[m] = events[m] || []; events[m].push(f); },
                  close: () => ws.close() });
      };
      ws.onerror = reject;
    });
  });
}
async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails));
  return r.result ? r.result.result.value : undefined;
}
const results = [];
function check(name, cond, extra = '') { results.push({ name, ok: !!cond }); console.log(`${cond ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`); }
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitFor(p, expr, timeout = 60000, step = 300) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try { if (await evaluate(p, expr)) return true; } catch (e) {}
    await sleep(step);
  }
  return false;
}

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('DOM.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
await page.send('Page.navigate', { url: TARGET });
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 30000);

// ── 场景 1: Security 层 (P1 修复验证) ──
console.log('\n── 场景 1: Security 层显示 (P1 修复) ──');
// 找一个已解密 ZCL/Data 帧
const secRow = await evaluate(page, `(async function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length;i++){
    rows[i].click();
    await new Promise(r=>setTimeout(r,150));
    var t=document.getElementById('tl-detail').textContent;
    if(t.includes('已解密')&&t.includes('Security'))return {pid:rows[i].dataset.pid};
  }
  return null;})()`);
check('详情 Security 层显示 (Level/Key)', !!secRow, secRow ? 'pid='+secRow.pid : '未找到已解密带安全头帧');
const secFields = await evaluate(page, `(function(){
  var layers=document.querySelectorAll('#tl-detail .layer');
  for(var i=0;i<layers.length;i++){
    if(layers[i].querySelector('.frame-title').textContent==='Security'){
      return layers[i].textContent.substr(0,120);
    }
  }return '';})()`);
console.log('   Security 层内容:', secFields.slice(0, 80));

// ── 场景 2: 详情帧号一致性 (P2 修复验证) ──
console.log('\n── 场景 2: 详情标题帧号 ──');
const frameInfo = await evaluate(page, `(function(){
  var m=document.querySelector('#tl-detail .frame-meta');
  var r=document.querySelector('#tltb tr.hl');
  return {meta:m?m.textContent:'', rowFrame:r?r.children[0].textContent:''};})()`);
check('详情标题含抓包帧号 (与表格一致)', frameInfo.meta.includes('抓包帧号 '+frameInfo.rowFrame), JSON.stringify(frameInfo));

// ── 场景 3: 事务链跳转 (中继包 id=722 有链) ──
console.log('\n── 场景 3: 事务链跳转 ──');
await evaluate(page, `(function(){
  document.getElementById('tl-node').value='0x0000';
  document.getElementById('tshow').click();})()`);
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 15000);
// 用 tlJumpFrame 直接跳 722 (事务链帧)
await evaluate(page, `tlJumpFrame(722)`);
await waitFor(page, `document.getElementById('tl-detail').textContent.includes('同事务响应')`, 15000);
check('事务链显示 (同事务响应)', await evaluate(page, `document.getElementById('tl-detail').textContent.includes('同事务响应')`));
const trJump = await evaluate(page, `(async function(){
  var a=document.querySelector('#tl-detail .ack-jump');
  if(!a)return '无链接';
  var peer=a.dataset.peer;
  a.click();
  await new Promise(r=>setTimeout(r,1200));
  var hl=document.querySelector('#tltb tr.hl');
  return {peer:peer, hl:hl?hl.dataset.pid:null, stat:document.getElementById('tl-stat').textContent};})()`);
check('事务链接跳转定位', trJump.hl === trJump.peer, JSON.stringify(trJump));
// 清过滤
await evaluate(page, `(function(){document.getElementById('tl-node').value='';document.getElementById('tshow').click();})()`);
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 15000);

// ── 场景 4: 主流程回归 (未解密开关 / 层级着色 / 路径列 API) ──
console.log('\n── 场景 4: 主流程回归 ──');
check('自动加载统计', await evaluate(page, `document.getElementById('tl-stat').textContent.includes('共 ')`), await evaluate(page, `document.getElementById('tl-stat').textContent`));
check('层级着色 ≥3 类', await evaluate(page, `(function(){var s=new Set();document.querySelectorAll('#tltb .tl-summary').forEach(function(e){s.add(e.className.replace('tl-summary','').trim())});return s.size>=3;})()`));
const pagerOk = await evaluate(page, `document.getElementById('tl-pi').textContent.includes('1 /')`);
check('分页显示', pagerOk, await evaluate(page, `document.getElementById('tl-pi').textContent`));
// 路径列: 找一帧有路径的 (API 已验证 1168 帧) — 跳到有路径帧所在页
await evaluate(page, `tlJumpFrame(102)`);
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 15000);
const pathCell = await evaluate(page, `(function(){var r=document.querySelector('#tltb tr.hl');return r?r.children[3].textContent:'';})()`);
check('路径列渲染 (跳转后帧有路径或 —)', pathCell !== '', pathCell);

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(fails.length ? 1 : 0);
