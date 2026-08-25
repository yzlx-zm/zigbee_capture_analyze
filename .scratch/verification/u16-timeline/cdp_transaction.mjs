// U16-7a 事务链验证 — 详情同事务响应区块 + 点击跳转高亮
const CDP = 'http://127.0.0.1:9222';
const TARGET = 'http://localhost:8720/#tl';

async function newPage() {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0;
  const pending = new Map();
  const consoleMsgs = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    if (m.method === 'Runtime.consoleAPICalled' || m.method === 'Runtime.exceptionThrown') consoleMsgs.push(JSON.stringify(m.params));
  };
  const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  return { ws, send, consoleMsgs, close: () => ws.close() };
}

async function evaluate(p, expr) {
  const r = await p.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.error) throw new Error(r.error.message);
  if (r.result && r.result.exceptionDetails) throw new Error('EVAL_EXC: ' + JSON.stringify(r.result.exceptionDetails));
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
await new Promise(r => setTimeout(r, 5000));

// 1. 每页 500 → 第 2 页 (idx 500-999, 含命令帧 idx 722)
await evaluate(page, `(()=>{const s=document.getElementById('tl-ps');s.value='500';s.dispatchEvent(new Event('change'));return true})()`);
await new Promise(r => setTimeout(r, 3000));
await evaluate(page, `document.getElementById('tl-pj').value='2'; document.getElementById('tl-pgo').click(); true`);
await new Promise(r => setTimeout(r, 3000));

// 2. 找到 packet_id=752 的行 (idx 722) 点击
const rowFound = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.dataset.pid==='722')?.click() || false`);
check('翻页定位命令帧 idx 722', rowFound === true || await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].some(r=>r.dataset.pid==='722')`));
await new Promise(r => setTimeout(r, 1500));

// 3. 详情含同事务响应区块
const trBlock = await evaluate(page, `(()=>{const b=[...document.querySelectorAll('#tl-detail .ack-pair')].find(x=>x.textContent.includes('同事务响应帧'));return b?b.textContent:null})()`);
console.log('  事务区块:', trBlock ? trBlock.slice(0, 120) : '(无)');
check('详情含「同事务响应帧」区块', trBlock !== null && trBlock.includes('Read Attributes Response'), trBlock?.slice(0, 100));
check('响应链接带证据标记 (同事务)', trBlock?.includes('同事务'), '');
check('响应链接带方向 S→C', trBlock?.includes('S→C'), '');

// 4. 点击响应链接 → 跳转响应帧 (idx 728) + 高亮
const targetBefore = await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.dataset.pid==='728')!==undefined`);
await evaluate(page, `(()=>{const a=[...document.querySelectorAll('#tl-detail .ack-jump')].find(x=>x.dataset.peer==='728');if(a){a.click();return true}return false})()`);
await new Promise(r => setTimeout(r, 2500));
const hlPid = await evaluate(page, `document.querySelector('#tltb tr.tl-row.hl')?.dataset.pid`);
const detailPid = await evaluate(page, `document.querySelector('#tl-detail')?.textContent.slice(0,80)`);
console.log(`  跳转后高亮行 pid=${hlPid} | 详情: ${detailPid?.slice(0,50)}`);
check('点击响应链接跳转目标帧', hlPid === '728', `hl=${hlPid}`);
const detailFull = await evaluate(page, `document.querySelector('#tl-detail')?.textContent || ''`);
check('跳转后详情为响应帧 (ZCL 层含命令名)', detailFull.includes('Read Attributes Response'), detailFull.slice(0, 100));

// 5. 无响应帧命令 (idx 728 Read Attributes Response 自身是响应, ack=730 无 resp) — 检查 ack 链接仍正常
await evaluate(page, `[...document.querySelectorAll('#tltb tr.tl-row')].find(r=>r.dataset.pid==='728')?.click(); true`);
await new Promise(r => setTimeout(r, 1500));
const ackPair = await evaluate(page, `document.querySelector('#tl-detail')?.textContent.includes('APS Ack 配对')`);
check('响应帧自身仍有 ack 配对', ackPair === true);

const errs = page.consoleMsgs.filter(m => m.includes('exceptionThrown') || /error/i.test(m));
console.log(errs.length ? '❌ console 错误: ' + errs.slice(0, 5).join(' | ') : '✅ 无 console 错误');

const failed = results.filter(r => !r.ok);
console.log(`\n== ${results.length - failed.length}/${results.length} 通过 ==`);
page.close();
process.exit(failed.length ? 1 : 0);
