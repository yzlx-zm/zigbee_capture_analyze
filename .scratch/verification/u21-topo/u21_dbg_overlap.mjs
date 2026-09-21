// U21 调试: 聚合态坐标/包围盒 dump (定位节点/标签重叠)
import { openTab, sleep, P } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
let st = null;
for (let i = 0; i < 80; i++) { await sleep(900); st = await p.ev(P.state); if (st && st.nodes > 0) break; }
console.log('加载态:', JSON.stringify(st));
await p.ev(`document.getElementById('tagg').click()`);   // 打开手动聚合 (重叠出现在聚合态)
await sleep(2500);
console.log('聚合态:', JSON.stringify(await p.ev(P.state)));
const out = await p.ev(`(function(){
  var c=window.__cy, rows=[];
  c.nodes().forEach(function(n){
    var d=n.data(), pos=n.position(), bb=n.renderedBoundingBox();
    rows.push({id:n.id(), aid:(d.aid==null?null:('0x'+Number(d.aid).toString(16).toUpperCase())),
      badge:!!d.is_badge, x:Math.round(pos.x), y:Math.round(pos.y),
      R:Math.round(Math.sqrt(pos.x*pos.x+pos.y*pos.y)),
      deg:Math.round(((Math.atan2(pos.y,pos.x)*180/Math.PI)+360)%360),
      bx:[Math.round(bb.x1),Math.round(bb.y1),Math.round(bb.x2),Math.round(bb.y2)],
      lbl:String(d.label).split(String.fromCharCode(10)).join('|')});
  });
  var ov=[];
  for(var i=0;i<rows.length;i++)for(var j=i+1;j<rows.length;j++){
    var A=rows[i].bx,B=rows[j].bx;
    var ox=Math.min(A[2],B[2])-Math.max(A[0],B[0]), oy=Math.min(A[3],B[3])-Math.max(A[1],B[1]);
    if(ox>1&&oy>1)ov.push([rows[i].id+'/'+rows[i].lbl, rows[j].id+'/'+rows[j].lbl, ox+'x'+oy]);
  }
  return {rows:rows, ov:ov};
})()`);
if (p.exceptions.length) console.log('eval 异常:', JSON.stringify(p.exceptions.slice(-2)));
if (!out) { await p.close(); process.exit(1); }
console.log('重叠对:', JSON.stringify(out.ov));
out.rows.forEach(r => console.log(JSON.stringify(r)));
await p.close();
process.exit(0);
