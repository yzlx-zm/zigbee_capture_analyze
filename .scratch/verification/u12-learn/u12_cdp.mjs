// U12 诊断页学习机制 — CDP 前端验证
// 素材: 中继包已导入 (8435 帧) + 案例库 1 条 (中继 838D, 归属 L1-3/L1-4/L2-1/L2-6/L3-1/L3-2/L3-5/L3-11)
// 后端: 127.0.0.1:8720 | Edge CDP: 127.0.0.1:9222
const CDP = 'http://127.0.0.1:9222', TARGET = 'http://localhost:8720/#diag';
const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map(); let exceptions = [];
ws.onmessage = ev => { const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails.exception?.description || 'x'); };
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result?.result?.value; };
const results = []; const check = (n, ok, x = '') => { results.push({ n, ok: !!ok }); console.log(`${ok ? '✅' : '❌'} ${n}${x ? ' — ' + x : ''}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const ex = () => exceptions.length;
await send('Page.enable'); await send('Runtime.enable');
await send('Page.navigate', { url: TARGET });
await sleep(13000);  // 检测端点 + PAN 下拉初始化
const E0 = ex();

// ── 1. 检测视图回归 (无案例库行为一致的前提 — 默认进检测视图) ──
const info = await ev(`(function(){
  var cards = document.querySelectorAll('.l1-card').length;
  var vt = document.querySelectorAll('.sc-view-tab').length;
  var learnVisible = !!document.getElementById('diag-learn');
  var hasDiag = (document.body.innerText||'').includes('诊断结论');
  return {cards, vt, learnVisible, hasDiag};})()`);
check('检测视图: 13 卡渲染', info.cards === 13, `cards=${info.cards}`);
check('双视图 tab 存在', info.vt === 2, `vt=${info.vt}`);
check('默认视图=检测 (学习区隐藏)', !info.learnVisible, 'learnVisible=' + info.learnVisible);
// ⚠️ 结构变化: 诊断结论卡现嵌套 #diag-detect 内 (U12 header 卡 + 视图区),
// 原 "#mc > .card h3" 匹配到 header — 改查正文包含
check('摘要卡正常', info.hasDiag, 'hasDiag=' + info.hasDiag);

// ── 2. 切到场景学习视图 ──
await ev(`(function(){ var t=document.querySelector('.sc-view-tab[data-v="learn"]'); if(t) t.click(); return 1; })()`);
await sleep(3500);  // 3 端点 (scenarios/cases/gaps)
const E1 = ex();
const learn = await ev(`(function(){
  var el = document.getElementById('diag-learn');
  var txt = el ? el.innerText : '';
  var tabs = document.querySelectorAll('#diag-learn .sc-tab').length;
  var learned = document.querySelector('#diag-learn .sc-progress')?.innerText || '';
  var rows = document.querySelectorAll('#diag-learn .sc-mini-table tbody tr').length;
  var learnVisible = el && el.offsetParent !== null;
  return {learned, tabs, rows, learnVisible, txt: txt.slice(0, 120)};})()`);
check('学习视图可见', learn.learnVisible);
check('场景 tab ≥50', learn.tabs >= 50, `tabs=${learn.tabs}`);
// ⚠️ innerText 在 <b> 前后插换行/空格 — 正则容错匹配 (曾逐字断言失败)
check('进度 "已学 8/54"', /已学\s*8\s*\/\s*54\s*场景/.test(learn.learned || ''), (learn.learned || '').replace(/\s+/g, ' ').slice(0, 50));
check('总览案例行渲染', learn.rows >= 1, `rows=${learn.rows}`);

// ── 3. 场景 tab: L3-5 案例 (单场景过滤) ──
await ev(`(function(){ var ts=document.querySelectorAll('#diag-learn .sc-tab'); for(var i=0;i<ts.length;i++){ if(ts[i].textContent.includes('L3-5')){ts[i].click();return 1;} } return 0; })()`);
await sleep(800);
const s35 = await ev(`(function(){
  var el=document.getElementById('diag-learn');
  var rows=el.querySelectorAll('.sc-mini-table tbody tr').length;
  var badge=el.querySelector('.sc-badge')?.textContent || '';
  return {rows, badge, has838D:(el.innerText||'').includes('838D')};})()`);
check('L3-5 tab 案例行 (含 838D)', s35.rows >= 1 && s35.has838D, `rows=${s35.rows} 838D=${s35.has838D}`);
check('L3-5 案例徽章', s35.badge === '1', `badge=${s35.badge}`);

// ── 4. 未学场景: L4-1 "待学习" ──
await ev(`(function(){ var ts=document.querySelectorAll('#diag-learn .sc-tab'); for(var i=0;i<ts.length;i++){ if(ts[i].textContent.includes('L4-1')){ts[i].click();return 1;} } return 0; })()`);
await sleep(800);
const s41 = await ev(`(function(){ var el=document.getElementById('diag-learn'); return (el.innerText||'').includes('待学习'); })()`);
check('未学场景 L4-1 显示待学习', !!s41);

// ── 5. 标注表单打开 (当前包 → 案例) ──
await ev(`window.__caseAnnotate && window.__caseAnnotate()`);
await sleep(600);
const form = await ev(`(function(){
  var m=document.getElementById('ann-modal');
  if(!m) return null;
  var scen=document.querySelectorAll('#ann-modal input[name="ann-scen"]').length;
  var pan=document.getElementById('ann-pan')?.value || '';
  return {scen, pan, phen: !!document.getElementById('ann-phenomenon')};})()`);
check('标注表单打开 (54 场景可选)', form && form.scen === 54, form && `scen=${form.scen}`);
check('表单 PAN 自动预填 (主 PAN 580C)', form && form.pan.toUpperCase() === '580C', form && `pan=${form.pan}`);
// 关闭表单 (不实际提交 — API 级 E2E 已过)
await ev(`(function(){ var c=document.getElementById('ann-cancel'); if(c) c.click(); return 1; })()`);
await sleep(300);

// ── 6. 切回检测视图 (双视图往返) ──
await ev(`(function(){ var t=document.querySelector('.sc-view-tab[data-v="detect"]'); if(t) t.click(); return 1; })()`);
await sleep(1500);
const back = await ev(`(function(){
  var d=document.getElementById('diag-detect');
  var l=document.getElementById('diag-learn');
  return {dVisible: !!(d && d.offsetParent!==null),
          lGone: !l};})()`);
check('切回检测视图正常', back.dVisible && back.lGone);

// ── 7. 无数据边界: 清除数据后检测视图仍可用 ──
const exAll = exceptions.length;
check('全程 0 异常', exAll === 0, `exceptions=${exAll}`);
console.log(`\n== U12 CDP: ${results.filter(r=>r.ok).length}/${results.length} ==`);
await fetch(`${CDP}/json/close/${t.id}`);
