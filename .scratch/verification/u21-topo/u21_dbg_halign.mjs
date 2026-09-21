// 语义探针: 在页面内造最小图, 测 text-halign left/right + text-margin-x ± 的实际方向
import { openTab, sleep } from './u21_lib.mjs';
const p = await openTab('http://localhost:8720/#topo');
await sleep(6000);
const r = await p.ev(`(function(){
  var d=document.createElement('div'); d.style.cssText='position:fixed;left:-9999px;width:400px;height:200px';
  document.body.appendChild(d);
  var mk=function(ha,mx){return };
  var els=[],sty=[{selector:'node',style:{'width':30,'height':30,'label':'data(label)','font-size':'10px','text-valign':'center','text-halign':'center','text-margin-x':0}}];
  var cases=[['top',6],['top',-6],['bottom',6],['bottom',-6],['top',0],['bottom',0]];
  cases.forEach(function(c,i){
    els.push({data:{id:'n_'+c[0]+'_'+c[1],label:'0xABCD'},position:{x:100,y:60+i*50}});
    sty.push({selector:'#n_'+c[0]+'_'+c[1],style:{'text-valign':c[0],'text-margin-y':c[1]+'px','text-halign':'center'}});
  });
  var t=window.cytoscape({container:d,elements:els,style:sty,layout:{name:'preset'}});
  var out=cases.map(function(c){
    var n=t.getElementById('n_'+c[0]+'_'+c[1]); var pos=n.position(); var bb=n.boundingBox();
    return {case:'valign='+c[0]+',my='+c[1],
      nodeCy:pos.y, bbTopRel:Math.round(bb.y1-pos.y), bbBotRel:Math.round(bb.y2-pos.y),
      labelSide:(bb.y2-pos.y)>15?'下':((pos.y-bb.y1)>15?'上':'居中/重叠')};
  });
  t.destroy(); d.remove();
  return out;})()`);
if (p.exceptions.length) console.log('异常:', p.exceptions.slice(-1));
r.forEach(x => console.log(JSON.stringify(x)));
await p.close(); process.exit(0);
