// nodes.js — 节点列表页面模块 (ES module)
// U3: 行内展开详情 (设备详情/邻居表/EUI64/LQI-RSSI)
// U9: 端点统计 + 控制命令统计
// U15: 控制命令 "📄 示例" 弹层 (帧分层解析视图) + "⬇️ 导出画像" (JSON+MD)
import { S, A } from './state.js';

function fmtTs(ts){ if(ts==null)return '-'; var d=new Date(ts*1000);
  // 时区修复 (08-13): 曾 getUTCHours (UTC 偏 8h) — 统一本地时间 (与抓包一致)
  return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')+':'+d.getSeconds().toString().padStart(2,'0'); }
// EUI64 16 位 hex → XX:XX:XX:XX:XX:XX:XX:XX (与 diag.js L1-4 卡片一致)
function fmtEui64(e){ if(!e)return null; if(e.length===16){var r=[];for(var i=0;i<16;i+=2)r.push(e.slice(i,i+2));return r.join(':');} return e; }
function devTypeName(t){ return {coordinator:'协调器',router:'路由',end_device:'终端',unknown:'未知'}[t]||t||'未知'; }
function asymBadge(l){
  if(!l)return '<span class="text-muted t-10">—</span>';
  return '<span class="badge '+(l==='ASYMM'?'text-danger':l==='WEAK'?'text-warn':'text-success')+'">'+l+'</span>';
}

// ── U15: 通用弹层 (示例帧解析 / 导出下载) ──
function openModal(title, contentHtml){
  var old=document.querySelector('.nd-modal');
  if(old)old.remove();
  var ov=document.createElement('div');
  ov.className='nd-modal';
  ov.innerHTML='<div class="nd-modal-box"><div class="nd-modal-title"><span>'+title+'</span>'
    +'<span class="nd-modal-close" title="关闭">✕</span></div>'+contentHtml+'</div>';
  document.body.appendChild(ov);
  ov.querySelector('.nd-modal-close').addEventListener('click',function(){ov.remove();});
  ov.addEventListener('click',function(e){if(e.target===ov)ov.remove();});
  return ov;
}

// 帧分层解析视图渲染 (与时间线详情同源: /api/packets/{id} 响应)
var ND_LAYERS={zbee_wpan:'MAC 层',zbee_nwk:'NWK 层','ZigBee Security Header':'安全头',
  zbee_aps:'APS 层',zbee_zcl:'ZCL 层',zbee_zdp:'ZDP 层'};
var ND_LCOLOR={zbee_wpan:'#ea580c',zbee_nwk:'#2563eb','ZigBee Security Header':'#64748b',
  zbee_aps:'#7c3aed',zbee_zcl:'#7c3aed',zbee_zdp:'#059669'};
function frameDetailHtml(d){
  var h='';
  h+='<div class="nd-frame-head mono">帧 #'+d.id+' (原始帧号 '+d.packet_id+') · '+fmtTs(d.ts)
    +' · '+d.pkt_type+(d.decrypted?' · 已解密':'')+'</div>';
  var layers=d.layers||{};
  for(var ln in layers){
    var lf=layers[ln];
    if(!lf||typeof lf!=='object')continue;
    h+='<div class="nd-layer" style="border-left-color:'+(ND_LCOLOR[ln]||'#94a3b8')+'">'
      +'<div class="nd-layer-title" style="color:'+(ND_LCOLOR[ln]||'#64748b')+'">'+(ND_LAYERS[ln]||ln)+'</div>';
    var keys=Object.keys(lf);
    for(var i=0;i<keys.length;i++){
      var k=keys[i],v=lf[k];
      if(typeof v==='object'){ // 嵌套子树 (如 Frame Control Field) — 展开一层
        for(var sk in v){ if(typeof v[sk]!=='object') h+='<div class="nd-field"><span class="k">'+k+'.'+sk+'</span><span class="v">'+v[sk]+'</span></div>'; }
      }else{
        h+='<div class="nd-field"><span class="k">'+k+'</span><span class="v">'+v+'</span></div>';
      }
    }
    h+='</div>';
  }
  // ZCL 载荷字段级解析 (U15)
  var pp=d.zcl_payload_parsed;
  if(pp!==undefined&&pp!==null){
    h+='<div class="nd-layer" style="border-left-color:#0891b2">'
      +'<div class="nd-layer-title" style="color:#0891b2">ZCL 载荷解析 ('+(pp.parser||'无')+')</div>';
    if(pp.fields&&pp.fields.length){
      h+='<table class="nd-payload-table"><thead><tr><th>字段</th><th>值</th><th>说明</th></tr></thead><tbody>';
      for(var fi=0;fi<pp.fields.length;fi++){var f=pp.fields[fi];
        h+='<tr><td>'+f.field+'</td><td class="v">'+f.value+'</td><td>'+((f.note||'').replace(/</g,'&lt;'))+'</td></tr>';
      }
      h+='</tbody></table>';
    }else{
      h+='<div class="nd-field"><span class="k">载荷</span><span class="v">无参数</span></div>';
    }
    if(pp.hex){h+='<div class="nd-frame-head mono" style="margin-top:6px">载荷 hex: '+pp.hex+'</div>';}
    h+='</div>';
  }
  return h;
}

function openSample(pid){
  openModal('📄 帧解析 #'+pid,'<div class="text-muted t-11">加载中...</div>');
  A.get('/api/packets/'+pid).then(function(d){
    var ov=document.querySelector('.nd-modal');
    if(!ov)return;
    var box=ov.querySelector('.nd-modal-box');
    box.innerHTML=box.querySelector('.nd-modal-title').outerHTML+frameDetailHtml(d);
  }).catch(function(e){
    var ov=document.querySelector('.nd-modal');
    if(ov)ov.querySelector('.nd-modal-box').innerHTML+='<div class="text-danger">加载失败: '+e.message+'</div>';
  });
}

function openExport(aid){
  var ov=openModal('⬇️ 节点画像导出 0x'+aid.toString(16).toUpperCase().padStart(4,'0'),
    '<div class="text-muted t-11">生成中...</div>');
  A.get('/api/nodes/'+aid+'/export').then(function(d){
    var box=ov.querySelector('.nd-modal-box');
    var blob=function(txt){return new Blob([txt],{type:'text/plain;charset=utf-8'});};
    var dl=function(name,url){var a=document.createElement('a');a.href=url;a.download=name;
      document.body.appendChild(a);a.click();a.remove();};
    box.innerHTML=box.querySelector('.nd-modal-title').outerHTML
      +'<p class="t-11">画像 JSON 与 Markdown 已生成, 选择下载:</p>'
      +'<p><button class="btn btn-p nd-dl" data-f="json">⬇️ 下载 JSON</button>'
      +'<button class="btn btn-o nd-dl" data-f="md">⬇️ 下载 Markdown</button></p>'
      +'<p class="text-muted t-10">内容: 节点画像 (厂商/型号/EUI64/端点) + 每类控制命令代表帧的分层解析。</p>';
    box.querySelector('[data-f="json"]').addEventListener('click',function(){
      dl('node_0x'+aid.toString(16).toUpperCase().padStart(4,'0')+'_profile.json',
        URL.createObjectURL(blob(d.json)));
    });
    box.querySelector('[data-f="md"]').addEventListener('click',function(){
      dl('node_0x'+aid.toString(16).toUpperCase().padStart(4,'0')+'_profile.md',
        URL.createObjectURL(blob(d.md)));
    });
  }).catch(function(e){
    ov.querySelector('.nd-modal-box').innerHTML+= '<div class="text-danger">导出失败: '+e.message+'</div>';
  });
}

reg('nodes',function(){
  // U9 (2026-08-12): 精简 6 列 — 去掉 PAN/协调器/包类型 (拓扑页均有);
  // 新增厂商名/型号 (Basic Read Attr Rsp 提取, 免人工查型号)
  document.getElementById('mc').innerHTML='<div class="card"><h3>📋 节点列表</h3><div class="nodes-search">'
    +'<input id="ns" placeholder="搜索地址 (如 0A11)" class="mono w-160"><button class="btn btn-p" id="ngo">搜索</button></div>'
    +'<div class="nodes-table-wrap"><table class="tbl"><thead><tr><th>地址</th><th>设备类型</th><th>厂商名</th><th>型号</th><th>出现次数</th><th>操作</th></tr></thead><tbody id="ntb"></tbody></table></div></div>';

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
    // U9: 端点统计 + 控制命令统计 (设备身份/控制方式查询)
    var eps=d.endpoints||[];
    if(eps.length){
      parts.push('<p class="t-11">端点: '+eps.map(function(e){
        var hex=e.ep.toString(16).toUpperCase(); if(hex.length<2)hex='0'+hex;
        return 'EP 0x'+hex+'×'+e.count;
      }).join(' · ')+'</p>');
    }
    var cls=d.clusters||[];
    if(cls.length){
      // U15: 每行加 "📄 示例" — 该命令最近一帧的分层解析视图弹层
      parts.push('<table class="tbl t-11 mt-1"><thead><tr><th>簇</th><th>命令</th><th>方向</th><th>频率</th><th></th></tr></thead><tbody>');
      for(var ci=0;ci<cls.length;ci++){var cc=cls[ci];
        var clName=cc.cluster_name||'0x'+(cc.cluster==null?'?':cc.cluster.toString(16).toUpperCase());
        var cmName=cc.cmd_name||'0x'+cc.cmd.toString(16).toUpperCase();
        var dirTxt=cc.dir==='Server→Client'?'S→C':cc.dir==='Client→Server'?'C→S':(cc.dir||'-');
        var btn=(cc.sample_pkt_id!=null)?'<button class="btn btn-o btn-sm nd-sample" data-pid="'+cc.sample_pkt_id+'" title="查看该命令最近一帧的分层解析">📄 示例</button>':'';
        parts.push('<tr><td class="mono">'+clName+'</td><td class="mono">'+cmName+'</td><td class="t-10 text-muted">'+dirTxt+'</td><td>'+cc.count+'</td><td>'+btn+'</td></tr>');
      }
      parts.push('</tbody></table>');
    }
    // U15: 节点画像导出 (JSON+MD)
    parts.push('<p class="mt-1"><button class="btn btn-s nd-export" data-aid="'+n.aid+'">⬇️ 导出画像</button>'
      +'<span class="t-10 text-muted" style="margin-left:8px">JSON+MD, 含画像与每类控制命令代表帧解析</span></p>');
    return parts.join('');
  }

  function render(ns){
    var h='';var tb=document.getElementById('ntb');
    for(var i=0;i<ns.length;i++){var n=ns[i],d=n.detail||{};
      h+='<tr class="nd-row" data-aid="'+n.aid+'">'
        +'<td class="mono text-strong">'+n.label+'</td>'
        +'<td>'+devTypeName(n.device_type)+'</td>'
        +'<td>'+(n.manufacturer_name||'-')+'</td>'
        +'<td>'+(n.model_id||'-')+'</td>'
        +'<td>'+n.seen+'</td>'
        +'<td><button class="btn btn-o btn-sm nd-locate" title="在拓扑页定位此节点">🎯</button></td>'
        +'</tr>'
        +'<tr class="nd-detail hidden" data-for="'+n.aid+'"><td colspan="6">'+detailHtml(n,d)+'</td></tr>';
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
    // U15: 📄 示例 → 帧解析弹层
    tb.querySelectorAll('.nd-sample').forEach(function(b){
      b.addEventListener('click',function(e){e.stopPropagation();
        openSample(parseInt(this.dataset.pid));
      });
    });
    // U15: ⬇️ 导出画像 (JSON+MD)
    tb.querySelectorAll('.nd-export').forEach(function(b){
      b.addEventListener('click',function(e){e.stopPropagation();
        openExport(parseInt(this.dataset.aid));
      });
    });
  }

  function load(q,pan){A.get('/api/nodes?search='+(q||'')+'&pan='+(pan||'')).then(render);}
  document.getElementById('ngo').addEventListener('click',function(){load(document.getElementById('ns').value,S.topoPan)});
  load('',S.topoPan);
});
