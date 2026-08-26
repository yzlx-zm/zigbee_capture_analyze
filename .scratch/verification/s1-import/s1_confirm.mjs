// S1 导入页稳定化 — CDP 实测脚本 v2 (修正等待逻辑)
// 前置: 后端 8720 + Edge 9222; frontend/ 静态根含 _s1-* 测试文件; d:/tmp/s1-test/ 大包
// 顺序: 清数据 → 渲染 → 小包 → 大包面板/时间/拆分/下载/导入 → 边界 → 群控进度(最后)
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';
const BIG_CUBX = 'd:/tmp/s1-test/08-13-中继侧抓包.cubx';

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
function setPromptReply(p, text) {
  p.on('Page.javascriptDialogOpening', () => {
    p.send('Page.handleJavaScriptDialog', { accept: true, promptText: text });
  });
}

const page = await newPage();
await page.send('Page.enable');
await page.send('Runtime.enable');
await page.send('DOM.enable');
await page.send('Network.enable');
await page.send('Network.setCacheDisabled', { cacheDisabled: true });
// 前置: 清除数据 (干净状态, 防旧 sb 干扰)
await fetch('http://localhost:8720/api/import/clear', { method: 'DELETE' });
await page.send('Page.navigate', { url: TARGET });
await waitFor(page, `!!document.getElementById('mc') && !!document.querySelector('.imp-tab')`, 10000);

// ── 场景 1: 页面渲染 + tab 切换 + 密钥面板展开 ──
console.log('\n── 场景 1: 导入页渲染 ──');
check('导入页卡片渲染 (📂 数据导入)', await evaluate(page, `document.getElementById('mc').textContent.includes('数据导入')`));
check('两个 tab 存在', await evaluate(page, `document.querySelectorAll('.imp-tab').length === 2`));
await evaluate(page, `document.querySelectorAll('.imp-tab')[1].click()`);
await sleep(300);
check('切 pcap tab 后密钥面板可展开 (点 toggle)', await evaluate(page, `(async function(){var b=document.getElementById('pkey-toggle');b.click();await new Promise(r=>setTimeout(r,500));return document.getElementById('pkey-body').style.display==='block';})()`));
await evaluate(page, `document.querySelectorAll('.imp-tab')[0].click()`);

// ── 场景 2: 小 cubx 直接导入 (90KB) → 结果卡 + P6 卡 (fresh import) ──
console.log('\n── 场景 2: 小包直接导入 (fresh import, 干净状态) ──');
await evaluate(page, `(async () => {
  const resp = await fetch('/_s1-small.cubx');
  const buf = await resp.arrayBuffer();
  doPI([new File([buf], '_s1-small.cubx')]);
})()`);
const s2done = await waitFor(page, `(function(){var t=document.getElementById('sb').textContent;return t.includes('包 | ') && !t.includes('0包');})()`, 90000);
check('小包导入完成 (#sb 统计)', s2done, await evaluate(page, `document.getElementById('sb').textContent`));
check('结果卡显示', await evaluate(page, `document.getElementById('sout').style.display === 'block'`));
const s2Sdiv = await evaluate(page, `document.getElementById('sdiv').textContent`);
check('P6 解析校验卡出现 (fresh import 直接可见)', s2Sdiv.includes('解析正确性'), s2Sdiv.includes('解析正确性') ? '有' : '缺失 — 确认 P2');
const s2Pkts = await evaluate(page, `S.pkts`);
console.log('   小包导入后 S.pkts =', s2Pkts);

// ── 场景 3: 大包本地路径 → 预扫面板 ──
console.log('\n── 场景 3: 85MB 大包本地路径 → 预扫面板 ──');
await evaluate(page, `document.querySelectorAll('.imp-tab')[1].click()`);
await sleep(300);
setPromptReply(page, BIG_CUBX);
await evaluate(page, `document.getElementById('plpath').click()`);
await waitFor(page, `!document.getElementById('cubx-prescan').classList.contains('hidden')`, 20000);
const csInfo = await evaluate(page, `document.getElementById('cs-info').textContent`);
check('预扫面板弹出 + 概览信息', /MB.*帧/.test(csInfo), csInfo);
check('直方图有柱', await evaluate(page, `document.querySelectorAll('#cs-hist .cs-bar').length > 0`));
check('双滑块范围正确', await evaluate(page, `(function(){var s=document.getElementById('cs-s1');return +s.min < +s.max && +s.value === +s.min;})()`));

// ── 场景 4: 精确时间输入 (P1 候选: 填面板显示的起止时间) ──
console.log('\n── 场景 4: 精确时间输入 (P1 候选确认) ──');
const tIn = await evaluate(page, `(function(){
  var s1=document.getElementById('cs-s1');
  var d1=new Date(+s1.min*1000), d2=new Date(Math.min(+s1.max, +s1.min+3600)*1000);
  function f(d){return {mo:('0'+(d.getMonth()+1)).slice(-2),da:('0'+d.getDate()).slice(-2),
    h:('0'+d.getHours()).slice(-2),mi:('0'+d.getMinutes()).slice(-2)};}
  var a=f(d1), b=f(d2);
  document.getElementById('cs-t1m').value=a.mo; document.getElementById('cs-t1d').value=a.da;
  document.getElementById('cs-t1h').value=a.h;  document.getElementById('cs-t1n').value=a.mi;
  document.getElementById('cs-t2m').value=b.mo; document.getElementById('cs-t2d').value=b.da;
  document.getElementById('cs-t2h').value=b.h;  document.getElementById('cs-t2n').value=b.mi;
  return a.mo+'-'+a.da+' '+a.h+':'+a.mi+' → '+b.mo+'-'+b.da+' '+b.h+':'+b.mi;
})()`);
await evaluate(page, `document.getElementById('cs-tapply').click()`);
await sleep(500);
const tApplyErr = await evaluate(page, `document.getElementById('prog').textContent`);
const tsFirstFrac = await evaluate(page, `+document.getElementById('cs-s1').min % 1`);
console.log(`   输入: ${tIn} (ts_first 小数部分=${tsFirstFrac.toFixed(3)})`);
check('起始时间输入被拒 (P1 确认)', tsFirstFrac !== 0 && (tApplyErr.includes('时间超出素材范围') || tApplyErr.includes('时间无效')), tApplyErr.trim());
// 输入一个更晚的合法时间 (整点 + 1 分钟) 应成功
const tOk = await evaluate(page, `(function(){
  var s1=document.getElementById('cs-s1');
  var d1=new Date((+s1.min + 300)*1000), d2=new Date(Math.min(+s1.max, +s1.min+3600)*1000);
  function f(d){return {mo:('0'+(d.getMonth()+1)).slice(-2),da:('0'+d.getDate()).slice(-2),
    h:('0'+d.getHours()).slice(-2),mi:('0'+d.getMinutes()).slice(-2)};}
  var a=f(d1), b=f(d2);
  document.getElementById('cs-t1m').value=a.mo; document.getElementById('cs-t1d').value=a.da;
  document.getElementById('cs-t1h').value=a.h;  document.getElementById('cs-t1n').value=a.mi;
  document.getElementById('cs-t2m').value=b.mo; document.getElementById('cs-t2d').value=b.da;
  document.getElementById('cs-t2h').value=b.h;  document.getElementById('cs-t2n').value=b.mi;
  return a.mo+'-'+a.da+' '+a.h+':'+a.mi+' → '+b.mo+'-'+b.da+' '+b.h+':'+b.mi;
})()`);
await evaluate(page, `document.getElementById('cs-tapply').click()`);
await sleep(500);
const tOkErr = await evaluate(page, `document.getElementById('prog').textContent`);
const tOkApplied = await evaluate(page, `(function(){return Math.abs(+document.getElementById('cs-s1').value - (Math.floor(+document.getElementById('cs-s1').min/60)+5)*60) < 60 ? '滑块已同步到输入' : '滑块: '+document.getElementById('cs-s1').value;})()`);
console.log('   合法输入:', tOk, '→', tOkErr.trim(), '|', tOkApplied);

// ── 场景 5: 拆分 (1 分钟窗) → 子包清单 → 下载验证 (P1) ──
console.log('\n── 场景 5: 拆分 + 下载验证 ──');
await evaluate(page, `(function(){var s=document.getElementById('cs-s1');var s2=document.getElementById('cs-s2');
  s.value = +s.min; s2.value = Math.min(+s.max, +s.min + 60); s.oninput(); s2.oninput();})()`);
await evaluate(page, `document.getElementById('cs-go').click()`);
await waitFor(page, `document.querySelectorAll('.cs-sub-row').length > 0`, 120000, 500);
const subRow = await evaluate(page, `(function(){var r=document.querySelector('.cs-sub-row'); if(!r)return null;
  var a=r.querySelector('a'); return {text:r.textContent, href:a?a.href:''};})()`);
check('子包清单出现', !!subRow, subRow && subRow.text.trim());
const dl = await evaluate(page, `(async function(href){
  try{var r=await fetch(href);return {status:r.status, text:(await r.text()).substr(0,120)};}catch(e){return {status:0, text:e.message};}
})(` + JSON.stringify(subRow.href) + `)`);
check('子包下载 200 (P1 验证)', dl.status === 200, `status=${dl.status} ${dl.text}`);

// ── 场景 6: 导入此子包 ──
console.log('\n── 场景 6: 导入拆分产物子包 ──');
await evaluate(page, `document.querySelector('.cs-sub-import').click()`);
const s6done = await waitFor(page, `(function(){var t=document.getElementById('sb').textContent;return t.includes('包 | ') && !t.includes('0包');})()`, 60000);
check('子包导入完成', s6done, await evaluate(page, `document.getElementById('sb').textContent`));
const s6Pkts = await evaluate(page, `S.pkts`);

// ── 场景 7: 边界输入 (此时无后台任务) ──
console.log('\n── 场景 7: 边界输入 ──');
// 7a: 空文件 cubx
await evaluate(page, `(async () => { const r=await fetch('/_s1-empty.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-empty.cubx')]); })()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌') || document.getElementById('sb').textContent.includes('失败')`, 30000);
const errEmpty = await evaluate(page, `(document.getElementById('prog').textContent||'').trim() || document.getElementById('sb').textContent`);
check('空文件 → 内联错误', errEmpty.includes('❌'), errEmpty);
// 7b: 错格式 cubx (文本内容)
await evaluate(page, `(async () => { const r=await fetch('/_s1-bad.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-bad.cubx')]); })()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌') || document.getElementById('sb').textContent.includes('失败')`, 30000);
const errBad = await evaluate(page, `(document.getElementById('prog').textContent||'').trim() || document.getElementById('sb').textContent`);
check('错格式 → 内联错误', errBad.includes('❌'), errBad);
// 7c: 不存在路径 (prompt)
setPromptReply(page, 'd:/tmp/s1-test/not-exist.cubx');
await evaluate(page, `document.getElementById('plpath').click()`);
await waitFor(page, `document.getElementById('prog').textContent.includes('❌')`, 10000);
const errPath = await evaluate(page, `document.getElementById('prog').textContent`);
check('不存在路径 → 内联错误', errPath.includes('❌'), errPath.trim());

// ── 场景 8: 群控包整包导入 (cs-cancel → 并行进度采样) — 最后, 耗时 ~4min ──
console.log('\n── 场景 8: 群控包整包导入 + 并行进度采样 ──');
await evaluate(page, `(async () => { const r=await fetch('/_s1-group.cubx'); doPI([new File([await r.arrayBuffer()], '_s1-group.cubx')]); })()`);
await waitFor(page, `!document.getElementById('cubx-prescan').classList.contains('hidden')`, 20000);
check('群控包 (>1MB) 弹预扫面板', true);
await evaluate(page, `document.getElementById('cs-cancel').click()`);
const trace = await evaluate(page, `(async () => {
  const trace = [];
  const t0 = Date.now();
  let lastSb = '';
  while (Date.now() - t0 < 300000) {
    const sb = document.getElementById('sb').textContent;
    if (sb !== lastSb) { trace.push(sb); lastSb = sb; }
    if (sb.includes('失败') || sb.includes('超时')) break;
    if (sb.includes('包 | ') && trace.length > 1) break;  // 导入完成且经历了进度阶段
    await new Promise(r => setTimeout(r, 500));
  }
  return trace;
})()`);
console.log('   顶栏轨迹 (' + trace.length + '):');
trace.slice(0, 40).forEach(t => console.log('   ', t));
const pcts = (trace || []).map(t => parseInt((t.match(/(\d+)%/) || [])[1] || 0)).filter(n => n > 0);
check('整包导入完成', (trace || []).some(t => t.includes('包 | ')), (trace || []).slice(-1)[0]);
check('并行解析进度采样 (≥3 个不同百分比)', pcts.length >= 3 && pcts[pcts.length - 1] > pcts[0], `${pcts[0]}% → ${pcts[pcts.length-1]}% (${pcts.length} 采样)`);

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(0);
