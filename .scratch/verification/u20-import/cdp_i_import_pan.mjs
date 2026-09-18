// U20-I CDP 验证: 选 PAN 后"取消 (整包导入)" → 只保留该 PAN 的帧
// 素材: 群控包 (主 PAN 0xA736 52047 帧 / 次 PAN 0x04DC 1598 帧)
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
for (let i = 0; i < 60; i++) {
  await sleep(1000);
  panel = await p.ev(`(function(){var el=document.getElementById('cubx-prescan');
    var sel=document.getElementById('cs-pan');
    return {visible:el&&!el.classList.contains('hidden'), opts:sel?[].map.call(sel.options,function(o){return o.text;}):null};})()`);
  if (panel && panel.visible && panel.opts) break;
}
console.log('[面板]', JSON.stringify(panel));

// 选次 PAN (0x04DC, 1598 帧) → 取消 = 整包导入 (按 PAN 过滤)
const picked = await p.ev(`(function(){
  var s=document.getElementById('cs-pan');
  var target=[].filter.call(s.options,function(o){return o.text.indexOf('0x04DC')===0;})[0];
  if(!target) return 'no-target';
  s.value=target.value; s.dispatchEvent(new Event('change',{bubbles:true}));
  document.getElementById('cs-cancel').click();
  return target.text;})()`);
console.log('[选择并整包导入]', picked);

let done = null;
for (let i = 0; i < 150; i++) {
  await sleep(1000);
  done = await p.ev(`(function(){
    var sdiv=document.getElementById('sdiv');
    var txt=sdiv?sdiv.innerText.replace(/\\n+/g,' | '):'';
    return {sb:document.getElementById('sb').innerText, card:txt.slice(0, 400),
            hasPanLine: txt.indexOf('已按 PAN')>=0};})()`);
  if (done && done.hasPanLine) break;
}
console.log('[导入结果]', JSON.stringify(done, null, 1));
await p.shot('.scratch/verification/u20-import/i_import_pan.jpg');
const st = await p.ev(`(function(){return {pkts:(window.S||{}).pkts, nodes:(window.S||{}).nodes};})()`);
console.log('[S]', JSON.stringify(st));
console.log('exceptions:', p.exceptions.length ? p.exceptions : 'none');
await p.close();

const P = [];
const chk = (c, l) => P.push((c ? '✅ ' : '❌ ') + l);
chk(/0x04DC/.test(picked), '选中次 PAN: ' + picked);
chk(done && done.hasPanLine, '结果卡显示 PAN 过滤说明');
chk(st && Math.abs(st.pkts - 1598) <= 5, `导入帧数 = 该 PAN 帧数 1598 ±5 (实际 ${st && st.pkts}; 预扫计数与过滤结果存在 ≤0.2% 畸形帧差, 见对账脚本)`);
chk(done && /解密/.test(done.card), '结果卡仍含解密统计');
chk(p.exceptions.length === 0, '无运行时异常');
console.log(P.join('\n'));
process.exit(P.some(s => s.startsWith('❌')) ? 1 : 0);
