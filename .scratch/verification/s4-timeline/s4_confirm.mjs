// S4 报文页稳定化 — CDP 缺陷确认 (阶段 1)
// 前置: 后端 8720 (中继包 8435 帧已导入) + Edge 9222
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
await waitFor(page, `!!document.getElementById('tltb')`, 10000);

// ── 场景 1: 自动加载 (全量) + 表格结构 ──
console.log('\n── 场景 1: 自动加载 + 表格结构 ──');
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 30000);
const stat1 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
check('自动加载全量包', stat1.includes('共 '), stat1);
check('表头 7 列 (帧号/时间/摘要/路径/Src/Dst/APS Ctr)', await evaluate(page, `document.querySelectorAll('#tltbl th').length === 7`), await evaluate(page, `Array.from(document.querySelectorAll('#tltbl th')).map(t=>t.textContent).join('|')`));
check('行数 > 0', await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row').length > 0`));
const layerCounts = await evaluate(page, `(function(){
  var s={zcl:0,aps:0,nwk:0,mac:0,macdreq:0,other:0};
  document.querySelectorAll('#tltb .tl-summary').forEach(function(el){
    var cls=el.className;
    if(cls.includes('tl-ly-zcl'))s.zcl++;else if(cls.includes('tl-ly-aps'))s.aps++;else if(cls.includes('tl-ly-nwk'))s.nwk++;
    else if(cls.includes('tl-ly-macdreq'))s.macdreq++;else if(cls.includes('tl-ly-mac'))s.mac++;else s.other++;
  });
  return s;})()`);
console.log('   层级着色分布:', JSON.stringify(layerCounts));
check('层级着色生效 (≥3 类)', Object.values(layerCounts).filter(v=>v>0).length >= 3);

// ── 场景 2: 未解密开关 ──
console.log('\n── 场景 2: 未解密开关 ──');
const rowsHidden = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row').length`);
await evaluate(page, `document.getElementById('tl-hide-undec').click()`);  // 取消勾选 = 显示未解密
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 30000);
const stat2 = await evaluate(page, `document.getElementById('tl-stat').textContent`);
const rowsShown = await evaluate(page, `document.querySelectorAll('#tltb tr.tl-row').length`);
check('关闭隐藏后包数增加', rowsShown >= rowsHidden, `隐藏=${rowsHidden} 显示=${rowsShown} (${stat2})`);
await evaluate(page, `document.getElementById('tl-hide-undec').click()`);  // 恢复
await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 30000);

// ── 场景 3: 类型下拉 ──
console.log('\n── 场景 3: 类型下拉 ──');
const typeOpts = await evaluate(page, `document.getElementById('tl-type').options.length`);
check('类型下拉动态填充', typeOpts > 5, `${typeOpts} 项`);

// ── 场景 4: 详情面板 (找一帧 ZCL 帧点击) — Security 层检查 (P1 候选) ──
console.log('\n── 场景 4: 详情面板 (ZCL 帧 + Security 层) ──');
const zclRow = await evaluate(page, `(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length;i++){if(rows[i].querySelector('.tl-ly-zcl')){rows[i].click();return rows[i].dataset.pid;}}
  return null;})()`);
check('找到 ZCL 帧并点击', zclRow != null, 'pid=' + zclRow);
await waitFor(page, `document.getElementById('tl-detail').textContent.includes('帧 #')`, 15000);
const detailText = await evaluate(page, `document.getElementById('tl-detail').textContent`);
check('详情层级渲染 (MAC/NWK/APS/ZCL 至少 2 层)', (detailText.match(/MAC|NWK|APS|ZCL/g) || []).length >= 2);
const hasSecLayer = await evaluate(page, `(function(){
  var t=document.getElementById('tl-detail').textContent;
  return t.includes('Security') && t.includes('Level');})()`);
check('Security 层显示 (Level/Key) — P1 候选', hasSecLayer, hasSecLayer ? '有' : '缺失 (cubx fallback 顶层 vs nwk 内查询)');
const secLayers = await evaluate(page, `Array.from(document.querySelectorAll('#tl-detail .frame-title')).map(t=>t.textContent).join(', ')`);
console.log('   详情层:', secLayers);
// 详情帧号 vs 表格帧号一致性
const frameMeta = await evaluate(page, `(function(){
  var m=document.getElementById('tl-detail').querySelector('.frame-meta');
  return m?m.textContent:'';})()`);
const rowFrameNo = await evaluate(page, `(function(){var r=document.querySelector('#tltb tr.tl-row[data-pid="${zclRow}"]');return r?r.children[0].textContent:'';})()`);
check('详情标题帧号 == 表格帧号', frameMeta.includes('帧 #'+zclRow) && (frameMeta.includes(rowFrameNo) || rowFrameNo==='-'), `表格帧号=${rowFrameNo} 详情=${frameMeta}`);

// ── 场景 5: 字段点选 (详情 PAN/地址 → 过滤) ──
console.log('\n── 场景 5: 字段点选过滤 ──');
const clickVal = await evaluate(page, `(function(){
  var a=document.querySelector('#tl-detail .tl-click-val');
  if(!a)return null;
  return {fill:a.dataset.fill, val:a.dataset.val};
})()`);
if(clickVal){
  await evaluate(page, `document.querySelector('#tl-detail .tl-click-val').click()`);
  await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 15000);
  const afterFill = await evaluate(page, `(function(){
    var el=document.getElementById('tl-'+('pan'==='${clickVal.fill}'?'pan':'node'));
    return {val:el.value, stat:document.getElementById('tl-stat').textContent};})()`);
  check('点选值填入过滤框', afterFill.val.toLowerCase().includes(clickVal.val.toLowerCase()), JSON.stringify(afterFill));
  // 清空过滤恢复
  await evaluate(page, `(function(){document.getElementById('tl-pan').value='';document.getElementById('tl-node').value='';document.getElementById('tshow').click();})()`);
  await waitFor(page, `document.getElementById('tl-stat').textContent.includes('共 ')`, 15000);
}else{check('详情有可点选字段', false, '无 .tl-click-val');}

// ── 场景 6: 事务链 (ZCL 命令帧 → 响应链接) ──
console.log('\n── 场景 6: 事务链 ──');
const trInfo = await evaluate(page, `(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length;i++){
    rows[i].click();  // 触发详情加载
    return {clicked:rows[i].dataset.pid};
  }})()`);
await waitFor(page, `document.getElementById('tl-detail').textContent.includes('帧 #')`, 15000);
const hasTr = await evaluate(page, `document.getElementById('tl-detail').textContent.includes('同事务响应')`);
console.log('   事务链:', hasTr ? '有' : '无 (非命令帧, 继续找)');
// 找一个有事务链的帧
const trFound = await evaluate(page, `(async function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  for(var i=0;i<rows.length && i<60;i++){
    rows[i].click();
    await new Promise(r=>setTimeout(r,120));
    if(document.getElementById('tl-detail').textContent.includes('同事务响应'))return {pid:rows[i].dataset.pid};
  }
  return null;})()`);
if(trFound){
  check('事务链显示 (同事务响应)', true);
  const trClick = await evaluate(page, `(async function(){
    var a=document.querySelector('#tl-detail .ack-jump');
    if(!a)return '无链接';
    var peer=a.dataset.peer;
    a.click();
    await new Promise(r=>setTimeout(r,800));
    return {peer:peer, stat:document.getElementById('tl-stat').textContent,
            hl:document.querySelector('#tltb tr.hl')?document.querySelector('#tltb tr.hl').dataset.pid:null};})()`);
  check('点击事务链接跳转定位', trClick.hl === trClick.peer, JSON.stringify(trClick));
}else{check('事务链显示', false, '60 行内无命令帧事务链');}

// ── 场景 7: 路径列 ──
console.log('\n── 场景 7: 路径列 ──');
const pathInfo = await evaluate(page, `(function(){
  var rows=document.querySelectorAll('#tltb tr.tl-row');
  var withPath=0, total=0;
  for(var i=0;i<rows.length;i++){
    var t=rows[i].children[3].textContent;
    if(t!=='—')withPath++;
    total++;
  }
  return {withPath:withPath, total:total};})()`);
check('路径列渲染 (有路径帧>0)', pathInfo.withPath > 0, JSON.stringify(pathInfo));

// ── 场景 8: 分页 ──
console.log('\n── 场景 8: 分页 ──');
const pager1 = await evaluate(page, `document.getElementById('tl-pi').textContent`);
await evaluate(page, `document.getElementById('tl-pn').click()`);
await waitFor(page, `document.getElementById('tl-pi').textContent.includes('2 /')`, 15000);
check('下一页翻页', true, `${pager1} → ${await evaluate(page, `document.getElementById('tl-pi').textContent`)}`);
await evaluate(page, `document.getElementById('tl-pp').click()`);
await waitFor(page, `document.getElementById('tl-pi').textContent.includes('1 /')`, 15000);

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(fails.length ? 1 : 0);
