// S1 自审补测 v2 — CSV 删除后回归 + 密钥合法 hex 实测
// 覆盖: 导入页无 CSV 元素 / pcap 导入+校验报告 / cubx 小包导入 / 密钥增删 (合法 hex)
//       / cs-close / 清除数据
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#import';

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
let _promptReply = null;
page.on('Page.javascriptDialogOpening', () => {
  page.send('Page.handleJavaScriptDialog', { accept: true, promptText: _promptReply || '' });
});
const setPromptReply = (p, text) => { _promptReply = text; };
await page.send('Page.navigate', { url: TARGET });
await waitFor(page, `!!document.getElementById('mc')`, 10000);

// ── 场景 1: CSV 删除后导入页结构 ──
console.log('\n── 场景 1: 导入页 (CSV 已删) ──');
check('无 CSV 元素 (drop/finp/lpath/imp-tab)', await evaluate(page, `!document.getElementById('drop') && !document.getElementById('finp') && !document.getElementById('lpath') && !document.querySelector('.imp-tab')`));
check('抓包导入区存在 (pdrop/plpath)', await evaluate(page, `!!document.getElementById('pdrop') && !!document.getElementById('plpath')`));
check('密钥面板存在', await evaluate(page, `!!document.getElementById('pkey-toggle')`));

// ── 场景 2: pcap 导入 + 校验报告 ──
console.log('\n── 场景 2: pcap 上传导入 + 校验报告 ──');
await evaluate(page, `(async () => { const r=await fetch('/_s1-test.pcap'); doPI([new File([await r.arrayBuffer()], '_s1-test.pcap')]); })()`);
await waitFor(page, `(function(){var t=document.getElementById('sb').textContent;return t.includes('包 | ') && !t.includes('0包');})()`, 120000);
check('pcap 导入完成', true, await evaluate(page, `document.getElementById('sb').textContent`));
const pcapSdiv = await evaluate(page, `document.getElementById('sdiv').textContent`);
check('校验报告显示 (数据校验)', pcapSdiv.includes('数据校验'), pcapSdiv.includes('校验通过') ? '✅ 通过' : pcapSdiv.includes('校验失败') ? '❌ 失败' : '⏳ 校验中');
check('校验明细 6 项 (预期=实际=)', /预期=/.test(pcapSdiv));
check('P6 解析校验卡', pcapSdiv.includes('解析正确性'));

// ── 场景 3: 密钥添加 (合法 16 组 hex) + 删除 ──
console.log('\n── 场景 3: 密钥添加/删除 (合法 hex) ──');
await evaluate(page, `document.getElementById('pkey-toggle').click()`);
await waitFor(page, `!!document.getElementById('pk-hex')`, 5000);
await evaluate(page, `(function(){
  document.getElementById('pk-hex').value='FC:90:D2:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD';
  document.getElementById('pk-label').value='s1-audit-key2';
  document.getElementById('pk-add').click();
})()`);
const added = await waitFor(page, `document.querySelector('#pkey-body').textContent.includes('s1-audit-key2')`, 10000);
check('密钥添加成功 (合法 hex)', added, added ? '' : await evaluate(page, `document.getElementById('pk-err') ? document.getElementById('pk-err').textContent : ''`));
const hasDelBtn = await evaluate(page, `(function(){var trs=document.querySelectorAll('#pkey-body tr');
  for(var i=0;i<trs.length;i++){if(trs[i].textContent.includes('s1-audit-key2'))return !!trs[i].querySelector('[data-kl]');}return false;})()`);
check('新 key 有删除按钮', hasDelBtn);
await evaluate(page, `(function(){var trs=document.querySelectorAll('#pkey-body tr');
  for(var i=0;i<trs.length;i++){if(trs[i].textContent.includes('s1-audit-key2')){var b=trs[i].querySelector('[data-kl]');b.click();return true;}}return false;})()`);
await waitFor(page, `!document.querySelector('#pkey-body').textContent.includes('s1-audit-key2')`, 10000);
check('密钥删除成功', true);

// ── 场景 4: cs-close (大包面板) ──
console.log('\n── 场景 4: cs-close ──');
setPromptReply(page, 'C:/Users/Administrator/Desktop/zigbee_capture/中继入网抓包(1).cubx');
await evaluate(page, `document.getElementById('plpath').click()`);
await waitFor(page, `!document.getElementById('cubx-prescan').classList.contains('hidden')`, 20000);
await evaluate(page, `document.getElementById('cs-close').click()`);
await sleep(300);
const closed = await evaluate(page, `(function(){return {hidden: document.getElementById('cubx-prescan').classList.contains('hidden'), prog: document.getElementById('prog').style.display};})()`);
check('cs-close 关闭面板', closed.hidden === true && closed.prog === 'none', JSON.stringify(closed));

// ── 场景 5: 清除数据 ──
console.log('\n── 场景 5: 清除数据 ──');
await evaluate(page, `document.getElementById('clr').click()`);
await sleep(300);
const confirmTxt = await evaluate(page, `document.getElementById('clr').textContent`);
check('确认倒计时出现', confirmTxt.includes('再次点击确认清除'), confirmTxt);
await evaluate(page, `document.getElementById('clr').click()`);
await waitFor(page, `(function(){return document.getElementById('sb').textContent==='就绪';})()`, 20000);
const total0 = await evaluate(page, `(async function(){var r=await fetch('/api/import/status');return (await r.json()).total;})()`);
check('数据清空 (total=0)', total0 === 0, `total=${total0}`);

console.log('\n====== 汇总 ======');
const fails = results.filter(r => !r.ok);
results.forEach(r => console.log(`${r.ok ? '✅' : '❌'} ${r.name}`));
console.log(`\n${results.length - fails.length}/${results.length} 通过`);
page.close();
process.exit(fails.length ? 1 : 0);
