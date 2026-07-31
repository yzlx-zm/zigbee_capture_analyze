// nodes.js — 节点列表页面模块 (ES module)
import { S, A } from './state.js';

reg('nodes',function(){
  document.getElementById('mc').innerHTML='<div class="card"><h3>📋 节点列表</h3><div style="display:flex;gap:8px;margin-bottom:8px">'
    +'<input id="ns" placeholder="搜索地址 (如 0A11)" style="width:160px;font-family:monospace"><button class="btn btn-p" id="ngo">搜索</button></div>'
    +'<div style="max-height:calc(100vh - 200px);overflow:auto"><table class="tbl"><thead><tr><th>地址</th><th>出现次数</th><th>PAN</th><th>协调器</th><th>包类型</th></tr></thead><tbody id="ntb"></tbody></table></div></div>';
  function load(q,pan){A.get('/api/nodes?search='+(q||'')+'&pan='+(pan||'')).then(function(ns){
      var h='';for(var i=0;i<ns.length;i++){var n=ns[i];
        h+='<tr data-aid="'+n.aid+'" style="cursor:pointer"><td>'+n.label+'</td><td>'+n.seen+'</td><td>'+(n.pan!=null?'0x'+n.pan.toString(16).toUpperCase():'-')+'</td><td>'+(n.is_coord?'✅':'')+'</td><td>'+(n.type_list||[]).join(', ')+'</td></tr>';}
      document.getElementById('ntb').innerHTML=h;
      document.querySelectorAll('#ntb tr').forEach(function(tr){tr.addEventListener('click',function(){location.hash='topo';setTimeout(function(){document.getElementById('taddr').value=tr.dataset.aid?parseInt(tr.dataset.aid).toString(16).toUpperCase():'';document.getElementById('tgo').click()},100)})});
    });}
  document.getElementById('ngo').addEventListener('click',function(){load(document.getElementById('ns').value,S.topoPan)});
  load('',S.topoPan);
});
