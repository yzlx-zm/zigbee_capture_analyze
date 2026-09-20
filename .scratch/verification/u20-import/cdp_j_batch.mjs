// U20-J CDP 验证: 面板"按段长批量拆" + 单窗拆分回归 (runSplit 重构后)
// 素材: 群控包 4.9MB / 108474 帧 / 43.5 分钟
import { openTab, sleep } from '../t3-manual/shot_lib.mjs';
const FILE = 'C:/Users/Administrator/Desktop/zigbee_capture/验证可用-记录/2-群控压测问题包.cubx';
const p = await openTab('http://localhost:8720/#import');
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', { cacheDisabled: true });
await p.send('Page.navigate', { url: 'http://localhost:8720/#import' });
await sleep(3000);

const node = await p.send('DOM.getDocument', { depth: -1, pierce: true });
const q = await p.send('DOM.querySelector', { nodeId: node.result.root.nodeId, selector: '#pfinp' });
await p.send('DOM.setFileInputFiles', { nodeId: q.result.nodeId, files: [FILE] });
await p.ev(`(function(){document.getElementById('pfinp').dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);

let panel = null;
for (let i = 0; i < 150; i++) {
  await sleep(1000);
  panel = await p.ev(`(function(){var el=document.getElementById('cubx-prescan');
    return {visible:el&&!el.classList.contains('hidden'),
            seg:document.getElementById('cs-seg')?document.getElementById('cs-seg').value:null,
            hint:document.getElementById('cs-seg-hint')?document.getElementById('cs-seg-hint').innerText:'',
            win:document.getElementById('cs-win')?document.getElementById('cs-win').innerText:''};})()`);
  if (panel && panel.visible && panel.hint) break;
}
console.log('[面板]', JSON.stringify(panel));
const segRow = await p.ev(`(function(){return {text:(document.querySelector('.cs-batch')||{}).innerText||''};})()`);
console.log('[批量拆区]', JSON.stringify(segRow));

// 段长 1 分钟 → 44 段 > 20 → 前端拦截
const over = await p.ev(`(function(){var i=document.getElementById('cs-seg');
  i.value='1'; i.dispatchEvent(new Event('input',{bubbles:true}));
  var b=document.getElementById('cs-go-batch');
  return {hint:document.getElementById('cs-seg-hint').innerText, disabled:b.disabled,
          cls:document.getElementById('cs-seg-hint').className};})()`);
console.log('[段长 1 分钟]', JSON.stringify(over));
await p.shot('.scratch/verification/u20-import/j_over_limit.jpg');

// 段长 5 分钟 → 9 段, 点击批量拆
const pre = await p.ev(`(function(){var i=document.getElementById('cs-seg');
  i.value='5'; i.dispatchEvent(new Event('input',{bubbles:true}));
  return {hint:document.getElementById('cs-seg-hint').innerText,
          disabled:document.getElementById('cs-go-batch').disabled};})()`);
console.log('[段长 5 分钟]', JSON.stringify(pre));
await p.ev(`(function(){document.getElementById('cs-go-batch').click();return 1;})()`);

let after = null;
for (let i = 0; i < 180; i++) {
  await sleep(1000);
  after = await p.ev(`(function(){
    var rows=[].map.call(document.querySelectorAll('.cs-sub-row'),function(r){return r.innerText.replace(/\\n/g,' ');});
    var sum=0; rows.forEach(function(t){var m=t.match(/([\\d,]+) 帧/); if(m) sum+=parseInt(m[1].replace(/,/g,''),10);});
    return {subs:rows.length, sum:sum, hint:document.getElementById('cs-seg-hint').innerText,
            last:rows[rows.length-1]||'', first:rows[0]||'', sb:document.getElementById('sb').innerText};})()`);
  if (after && /已拆/.test(after.hint || '')) break;
}
console.log('[批量拆后]', JSON.stringify(after, null, 1));
await p.shot('.scratch/verification/u20-import/j_batch_done.jpg');

// 单窗拆分回归 (runSplit 重构后行为一致): 1 分钟窗 → 再追加 1 条子包
const beforeSingle = after.subs;
await p.ev(`(function(){
  var s1=document.getElementById('cs-s1'),s2=document.getElementById('cs-s2');
  s1.value=+s1.min; s2.value=Math.min(+s1.min+60, +s1.max);
  s1.dispatchEvent(new Event('input',{bubbles:true}));
  document.getElementById('cs-go').click(); return 1;})()`);
let single = null;
for (let i = 0; i < 120; i++) {
  await sleep(1000);
  single = await p.ev(`(function(){
    var rows=[].map.call(document.querySelectorAll('.cs-sub-row'),function(r){return r.innerText.replace(/\\n/g,' ');});
    return {subs:rows.length, last:rows[rows.length-1]||'', prog:document.getElementById('imsg').innerText};})()`);
  if (single && single.subs > beforeSingle) break;
}
console.log('[单窗拆分回归]', JSON.stringify(single));
await p.ev(`(function(){var b=document.getElementById('cs-close');if(b)b.click();return 1;})()`);
console.log('exceptions:', p.exceptions.length ? p.exceptions : 'none');
await p.close();

const P = [];
const chk = (c, l) => P.push((c ? '✅ ' : '❌ ') + l);
chk(panel && panel.visible && /cs-batch/.test(segRow.text) || segRow.text.indexOf('批量拆') >= 0,
  '面板含"批量拆"控件: ' + segRow.text.replace(/\s+/g, ' ').slice(0, 70));
chk(/将拆为 9 段/.test(panel.hint || ''), '默认 5 分钟 → 段数预览 9 段: ' + panel.hint);
chk(over.disabled === true && /超过上限 20/.test(over.hint), '段长 1 分钟 (44 段) → 前端拦截: ' + over.hint);
chk(pre.disabled === false, '段长 5 分钟 → 按钮可用');
chk(after && after.subs === 9, `批量拆出 9 条子包 (实际 ${after && after.subs})`);
chk(after && after.sum === 108474, `子包帧数合计 = 源 108474 (实际 ${after && after.sum})`);
chk(after && /已拆 9 段/.test(after.hint), '完成提示: ' + (after && after.hint));
chk(single && single.subs === 10, `单窗拆分回归: 追加第 10 条 (实际 ${single && single.subs})`);
chk(p.exceptions.length === 0, '无运行时异常');
console.log(P.join('\n'));
process.exit(P.some(s => s.startsWith('❌')) ? 1 : 0);
