// nodes.js — 节点列表页面模块 (ES module) — U3: 行内展开详情 (设备详情/邻居表/EUI64/LQI-RSSI)
import { S, A } from './state.js';

function fmtTs(ts){ if(ts==null)return '-'; var d=new Date(ts*1000);
  return d.getUTCHours().toString().padStart(2,'0')+':'+d.getUTCMinutes().toString().padStart(2,'0')+':'+d.getUTCSeconds().toString().padStart(2,'0'); }
// EUI64 16 位 hex → XX:XX:XX:XX:XX:XX:XX:XX (与 diag.js L1-4 卡片一致)
function fmtEui64(e){ if(!e)return null; if(e.length===16){var r=[];for(var i=0;i<16;i+=2)r.push(e.slice(i,i+2));return r.join(':');} return e; }
function devTypeName(t){ return {coordinator:'协调器',router:'路由',end_device:'终端',unknown:'未知'}[t]||t||'未知'; }
function asymBadge(l){
  if(!l)return '<span class="text-muted t-10">—</span>';
  return '<span class="badge '+(l==='ASYMM'?'text-danger':l==='WEAK'?'text-warn':'text-success')+'">'+l+'</span>';
}

reg('nodes',function(){
  document.getElementById('mc').innerHTML='<div class="card"><h3>📋 节点列表</h3><div class="nodes-search">'
    +'<input id="ns" placeholder="搜索地址 (如 0A11)" class="mono w-160"><button class="btn btn-p" id="ngo">搜索</button></div>'
    +'<div class="nodes-table-wrap"><table class="tbl"><thead><tr><th>地址</th><th>设备类型</th><th>出现次数</th><th>PAN</th><th>协调器</th><th>包类型</th><th>操作</th></tr></thead><tbody id="ntb"></tbody></table></div></div>';

  // 行内展开详情 (点击行切换; 🎯 定位按钮保留原跳转拓扑行为)
  function detailHtml(n,d){
    var eui=fmtEui64(d.eui64);
    var parts=[];
    parts.push('<div class="stats"><span>设备类型:'+devTypeName(n.device_type)+'</span>');
    parts.push('<span>首见:'+fmtTs(d.first_ts)+'</span><span>末见:'+fmtTs(d.last_ts)+'</span>');
    if(eui){parts.push('<span class="mono">EUI64:'+eui+'</span>');}
    else{parts.push('<span>EUI64:N/A (CSV 无 64 位地址)</span>');}
    parts.push('</div>');
    var lqi=d.lqi,rssi=d.rssi;
    var lqiTxt=lqi?('LQI '+lqi.avg+' ('+lqi.min+'~'+lqi.max+')'):'LQI N/A';
    var rssiTxt=rssi?('RSSI '+rssi.avg+' dBm ('+rssi.min+'~'+rssi.max+')'):'RSSI N/A';
    parts.push('<p class="t-11 text-muted">'+lqiTxt+' · '+rssiTxt+(lqi||rssi?'':' (CSV 导入无 LQI/RSSI)')+'</p>');
    var tc=d.type_counts||{}, tcs=Object.keys(tc);
    if(tcs.length){parts.push('<p class="t-11">帧类型: '+tcs.map(function(k){return k+':'+tc[k];}).join(' · ')+'</p>');}
    var nbs=d.neighbors||[];
    if(nbs.length){
      parts.push('<table class="tbl t-11 mt-1"><thead><tr><th>邻居</th><th>入向 cost</th><th>出向 cost</th><th>帧数</th><th>最近时间</th><th>链路质量</th></tr></thead><tbody>');
      for(var i=0;i<nbs.length;i++){var nb=nbs[i];
        parts.push('<tr><td class="mono">'+nb.label+'</td><td>'+nb.in_cost+'</td><td>'+nb.out_cost+'</td><td>'+nb.count+'</td><td>'+fmtTs(nb.last_seen)+'</td><td>'+asymBadge(nb.asym)+'</td></tr>');
      }
      parts.push('</tbody></table>');
    }else{
      parts.push('<p class="hint mt-1">无 Link Status 邻居数据 (需含链路状态帧的导入, 如 cubx)</p>');
    }
    return parts.join('');
  }

  function render(ns){
    var h='';var tb=document.getElementById('ntb');
    for(var i=0;i<ns.length;i++){var n=ns[i],d=n.detail||{};
      h+='<tr class="nd-row" data-aid="'+n.aid+'">'
        +'<td class="mono text-strong">'+n.label+'</td>'
        +'<td>'+devTypeName(n.device_type)+'</td>'
        +'<td>'+n.seen+'</td>'
        +'<td>'+(n.pan!=null?'0x'+n.pan.toString(16).toUpperCase():'-')+'</td>'
        +'<td>'+(n.is_coord?'✅':'')+'</td>'
        +'<td class="t-11 text-muted">'+(n.type_list||[]).join(', ')+'</td>'
        +'<td><button class="btn btn-o btn-sm nd-locate" title="在拓扑页定位此节点">🎯</button></td>'
        +'</tr>'
        +'<tr class="nd-detail hidden" data-for="'+n.aid+'"><td colspan="7">'+detailHtml(n,d)+'</td></tr>';
    }
    tb.innerHTML=h;
    tb.querySelectorAll('.nd-row').forEach(function(tr){
      tr.addEventListener('click',function(e){
        if(e.target.closest('.nd-locate'))return;   // 🎯 按钮不触发展开
        var drow=tb.querySelector('.nd-detail[data-for="'+tr.dataset.aid+'"]');
        if(drow)drow.classList.toggle('hidden');
      });
    });
    tb.querySelectorAll('.nd-locate').forEach(function(b){
      b.addEventListener('click',function(e){e.stopPropagation();
        var aid=b.closest('tr').dataset.aid;
        location.hash='topo';
        setTimeout(function(){var t=document.getElementById('taddr');if(t){t.value=parseInt(aid).toString(16).toUpperCase();var g=document.getElementById('tgo');if(g)g.click();}},100);
      });
    });
  }

  function load(q,pan){A.get('/api/nodes?search='+(q||'')+'&pan='+(pan||'')).then(render);}
  document.getElementById('ngo').addEventListener('click',function(){load(document.getElementById('ns').value,S.topoPan)});
  load('',S.topoPan);
});
