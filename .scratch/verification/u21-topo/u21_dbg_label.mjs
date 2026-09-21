// U21 调试: 标签是否在节点外侧 (bbox 比节点大 → 在外部; 相等 → 被压在节点内部)
import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st=null; for(let i=0;i<80;i++){await sleep(900); st=await p.ev(P.state); if(st&&st.nodes>0)break;}
console.log('加载:', JSON.stringify(st));
const r = await p.ev(`(function(){
  var c=window.__cy, out=[];
  c.nodes().forEach(function(n){
    if(n.data('is_badge'))return;
    var pos=n.position(), bb=n.boundingBox(), w=n.width(), h=n.height();
    var R=Math.sqrt(pos.x*pos.x+pos.y*pos.y);
    var deg=Math.round(((Math.atan2(pos.y,pos.x)*180/Math.PI)+360)%360);
    out.push({aid:'0x'+Number(n.data('aid')).toString(16).toUpperCase(), deg:deg, R:Math.round(R),
      ha:n.style('text-halign'), va:n.style('text-valign'), mx:n.style('text-margin-x'), my:n.style('text-margin-y'),
      nw:Math.round(w), nh:Math.round(h), bw:Math.round(bb.w), bh:Math.round(bb.h),
      outside:(bb.w>w+3||bb.h>h+3)});
  });
  return out;})()`);
const bad=r.filter(x=>!x.outside), good=r.filter(x=>x.outside);
console.log('标签在节点内部/未超出:', bad.length, ' 在外:', good.length);
console.log('--- 内部样例 ---'); bad.slice(0,8).forEach(x=>console.log(JSON.stringify(x)));
console.log('--- 外部样例 ---'); good.slice(0,5).forEach(x=>console.log(JSON.stringify(x)));
await p.close(); process.exit(0);
