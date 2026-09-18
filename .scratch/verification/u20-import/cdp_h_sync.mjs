// U20-H CDP 验证: 密钥面板手动刷新 Ubiqua 密钥 (DOM 断言, 无视觉)
// 用法: node cdp_h_sync.mjs [mock|down]
import { openTab, sleep } from '../t3-manual/shot_lib.mjs';
const MODE = process.argv[2] || 'mock';
const p = await openTab('http://localhost:8720/#import');
// 开发期禁用缓存: 改 JS 后模块 URL 未变, 浏览器会复用缓存 (项目铁律: 改前端要递增版本号)
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', { cacheDisabled: true });
await p.send('Page.navigate', { url: 'http://localhost:8720/#import' });
await sleep(3000);

// 展开密钥面板
await p.ev(`(function(){var t=document.getElementById('pkey-toggle');if(t&&t.innerText.includes('▸'))t.click();return 1;})()`);
await sleep(1500);

async function snap() {
  const raw = await p.send('Runtime.evaluate', {
    expression: `(function(){
      var body=document.getElementById('pkey-body');
      var btn=document.getElementById('pk-ubiqua');
      var msg=document.getElementById('pk-ubiqua-msg');
      var tds=body?[].slice.call(body.querySelectorAll('tr td:nth-child(2)')):[];
      var labels=tds.map(function(td){return td.innerText.trim();});
      return {hasBtn:!!btn, btnDisabled:btn?!!btn.disabled:null,
              msg:msg?msg.innerText:'', cls:msg?msg.className:'',
              rows:body?body.querySelectorAll('tr').length:0,
              net:labels.filter(function(l){return l.indexOf('Network')>=0;}).length,
              link:labels.filter(function(l){return l.indexOf('Link')>=0;}).length,
              labels:labels};})()`,
    returnByValue: true, awaitPromise: true });
  if (raw.result && raw.result.exceptionDetails) {
    console.log('!! evaluate 异常:', JSON.stringify(raw.result.exceptionDetails).slice(0, 300));
  }
  return raw.result && raw.result.result ? raw.result.result.value : undefined;
}

const before = await snap();
console.log('[点击前]', JSON.stringify(before));

await p.ev(`(function(){var b=document.getElementById('pk-ubiqua');if(b)b.click();return 1;})()`);
let after = null;
for (let i = 0; i < 20; i++) {          // 轮询到同步结束 (btn 恢复可用)
  await sleep(600);
  after = await snap();
  if (after && after.btnDisabled === false && after.msg.indexOf('同步中') < 0) break;
}
console.log(`[${MODE}]`, JSON.stringify(after, null, 1));
await p.shot(`.scratch/verification/u20-import/h_sync_${MODE}.jpg`);
console.log('exceptions:', p.exceptions.length ? p.exceptions : 'none');
await p.close();

const P = [];
const chk = (c, label) => P.push((c ? '✅ ' : '❌ ') + label);
if (MODE === 'mock') {
  chk(before.hasBtn, '密钥面板有"从 Ubiqua 刷新密钥"按钮');
  chk(after.msg.indexOf('从 Ubiqua 同步') >= 0, '同步成功提示: ' + after.msg);
  chk(/\+\d+ 个密钥 \(\d+ Network \/ \d+ Link\)/.test(after.msg), '提示含类型分项计数');
  chk(after.net >= 3 && after.link >= 3, `新增条目 Network ${after.net} / Link ${after.link}`);
  chk(after.rows > before.rows, `密钥行数 ${before.rows} → ${after.rows}`);
  chk(p.exceptions.length === 0, '无运行时异常');
} else {
  chk(after.msg.indexOf('Ubiqua 未运行') >= 0, 'Ubiqua 未运行提示: ' + after.msg);
  chk(after.cls.indexOf('text-danger') >= 0, '提示为错误样式');
  chk(after.rows === before.rows, '未运行时密钥行数不变');
}
console.log(P.join('\n'));
process.exit(P.some(s => s.startsWith('❌')) ? 1 : 0);
