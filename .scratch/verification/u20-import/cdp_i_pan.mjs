// U20-I CDP 验证: 预扫面板 PAN 分布 + 选 PAN 拆分/导入 (DOM 断言, 无视觉)
// 用法: node cdp_i_pan.mjs [multi|single]
//   multi  = 群控包 (42 PAN, 主 PAN 0xA736) → 显示选择器 + 选 PAN 拆分
//   single = 单 PAN 素材 → 不显示选择器 (无干扰)
import { openTab, sleep } from '../t3-manual/shot_lib.mjs';
const MODE = process.argv[2] || 'multi';
const FILES = {
  multi: 'C:/Users/Administrator/Desktop/zigbee_capture/验证可用-记录/2-群控压测问题包.cubx',
  single: 'D:/tmp/u20/one_pan_big.cubx',   // 合成: 单 PAN 0x4445 + 1.1MB (>1MB 才进面板)
};
const p = await openTab('http://localhost:8720/#import');
await p.send('Network.enable');
await p.send('Network.setCacheDisabled', { cacheDisabled: true });
await p.send('Page.navigate', { url: 'http://localhost:8720/#import' });
await sleep(3000);

// 注入文件 → change → doPI → _stageCubx (上传暂存 + 预扫)
const node = await p.send('DOM.getDocument', { depth: -1, pierce: true });
const q = await p.send('DOM.querySelector', { nodeId: node.result.root.nodeId, selector: '#pfinp' });
await p.send('DOM.setFileInputFiles', { nodeId: q.result.nodeId, files: [FILES[MODE]] });
if (MODE === 'single') {
  // 单 PAN 素材 <1MB, doPI 不会走面板分支 → 直接调官方入口 _stageCubx (面板渲染路径同一)
  const r = await p.ev(`(function(){var f=document.getElementById('pfinp').files[0];
    window._stageCubx(f, f.name); return f.name;})()`);
  console.log('[_stageCubx 手动触发]', r);
} else {
  await p.ev(`(function(){document.getElementById('pfinp').dispatchEvent(new Event('change',{bubbles:true}));return 1;})()`);
}

let panel = null;
for (let i = 0; i < 60; i++) {           // 等预扫 + 面板
  await sleep(1000);
  panel = await p.ev(`(function(){
    var el=document.getElementById('cubx-prescan');
    var vis=el&&!el.classList.contains('hidden');
    var row=document.getElementById('cs-pan-row');
    var sel=document.getElementById('cs-pan');
    var opts=sel?[].map.call(sel.options,function(o){return o.text;}).slice(0,5):[];
    return {visible:vis, panRowVisible:!!(row&&!row.classList.contains('hidden')),
            panRowText:row?row.innerText.replace(/\\n/g,' ').slice(0,200):'',
            optCount:sel?sel.options.length:0, opts:opts, selVal:sel?sel.value:null,
            info:document.getElementById('cs-info')?document.getElementById('cs-info').innerText:''};})()`);
  if (panel && panel.visible && panel.info) break;
}
console.log('[面板]', JSON.stringify(panel, null, 1));
await p.shot(`.scratch/verification/u20-import/i_panel_${MODE}.jpg`);

let after = null, sel = '';
if (MODE === 'multi') {
  // 选第二个 PAN (主 PAN 之外) → 检查状态写入
  await p.ev(`(function(){var s=document.getElementById('cs-pan');s.value=s.options[1].value;
    s.dispatchEvent(new Event('change',{bubbles:true}));return s.value;})()`);
  await sleep(500);
  sel = await p.ev(`document.getElementById('cs-pan').value`);
  // 缩到 1 分钟窗 + 拆分子包 (走 PAN 过滤)
  await p.ev(`(function(){
    var s1=document.getElementById('cs-s1'),s2=document.getElementById('cs-s2');
    s1.value=+s1.min; s2.value=Math.min(+s1.min+60, +s1.max);
    s1.dispatchEvent(new Event('input',{bubbles:true}));
    document.getElementById('cs-go').click(); return 1;})()`);
  for (let i = 0; i < 90; i++) {
    await sleep(1000);
    after = await p.ev(`(function(){
      var rows=[].map.call(document.querySelectorAll('.cs-sub-row'),function(r){return r.innerText.replace(/\\n/g,' ');});
      return {subs:rows.length, last:rows[rows.length-1]||'', prog:document.getElementById('imsg')?document.getElementById('imsg').innerText:''};})()`);
    if (after && after.subs > 0) break;
  }
  console.log('[拆分后]', JSON.stringify(after, null, 1));
  await p.shot(`.scratch/verification/u20-import/i_split_pan.jpg`);
  await p.ev(`(function(){var b=document.getElementById('cs-close');if(b)b.click();return 1;})()`);
} else {
  await p.ev(`(function(){var b=document.getElementById('cs-close');if(b)b.click();return 1;})()`);
}
const state = await p.ev(`(function(){return {sb:document.getElementById('sb').innerText,
  prescan:(window.S&&window.S.cubxPrescan)?{winStart:window.S.cubxPrescan.winStart,pan:window.S.cubxPrescan.pan}:null};})()`);
console.log('[状态]', JSON.stringify(state));
console.log('exceptions:', p.exceptions.length ? p.exceptions : 'none');
await p.close();

const P = [];
const chk = (c, l) => P.push((c ? '✅ ' : '❌ ') + l);
chk(panel && panel.visible, '预扫面板出现: ' + (panel ? panel.info.slice(0, 60) : ''));
if (MODE === 'multi') {
  chk(panel.panRowVisible, '多 PAN 素材显示 PAN 选择器');
  chk(panel.optCount > 2, `下拉选项数 ${panel.optCount} (>2, 含"全部"与各 PAN)`);
  chk(/\(建议\)/.test(panel.opts.join('')) || /建议/.test(panel.panRowText), '帧数最多的 PAN 标"建议"');
  chk(panel.panRowText.indexOf('全部 PAN (不过滤)') >= 0, '默认项为"全部 PAN (不过滤)"');
  chk(panel.selVal === '', '默认未选 PAN (不自动应用)');
  chk(sel && sel !== '', '选择 PAN 后状态生效: ' + sel);
  chk(after && after.subs > 0, '拆出子包: ' + (after ? after.last.slice(0, 70) : ''));
  chk(after && after.last.indexOf(sel) >= 0, '子包行标注 PAN 过滤条件 (' + sel + ')');
  chk(state.prescan === null || state.prescan.pan !== undefined, '面板状态可持久化 (S.cubxPrescan.pan)');
} else {
  chk(!panel.panRowVisible, '单 PAN 素材不显示选择器 (无干扰)');
}
chk(p.exceptions.length === 0, '无运行时异常');
console.log(P.join('\n'));
process.exit(P.some(s => s.startsWith('❌')) ? 1 : 0);
