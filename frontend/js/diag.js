// diag.js — 诊断页面模块 (ES module)
import { S, A } from './state.js';

reg('diag',function(){
  document.getElementById('mc').style.padding='16px';
  var h='<div class="card" style="margin-bottom:12px"><h3>🩺 网络诊断</h3>'
    +'<p style="font-size:11px;color:#94a3b8;margin-top:4px">基于协议数据 (Leave/Rejoin/Announce/Network Status) 的离线诊断</p></div>';

  A.get('/api/diag/offline').then(function(d){
    var devs=d.devices||[];
    if(!devs.length){
      h+='<div class="card" style="text-align:center;padding:24px;color:#94a3b8">'
        +'<p style="font-size:14px">✅ 未发现设备离网事件</p>'
        +'<p style="font-size:11px;margin-top:4px">当前抓包中没有 NWK Leave 或 Device Announce 帧</p></div>';
    }else{
      var s=d.summary||{};
      h+='<div class="card" style="margin-bottom:12px;background:#f0f9ff;border-left:3px solid #3b82f6">'
        +'<div style="font-size:13px;font-weight:600;margin-bottom:4px">📊 设备离线总览</div>'
        +'<div class="stats" style="font-size:12px">'
        +'<span>离网设备: <b style="color:#ef4444">'+s.total_devices_left+'</b></span>'
        +'<span>被踢: <b>'+s.kicked+'</b></span>'
        +'<span>主动: <b>'+s.voluntary+'</b></span>'
        +'<span>有重入网尝试: <b style="color:#3b82f6">'+s.with_rejoin+'</b></span>'
        +'</div></div>';
      for(var i=0;i<devs.length;i++){
        var dev=devs[i];
        var typeLabel=dev.device_type==='coordinator'?'协调器':dev.device_type==='router'?'路由器':'终端设备';
        var eui=dev.eui64||'未知';
        if(eui.length===16){eui=eui.slice(0,2)+':'+eui.slice(2,4)+':'+eui.slice(4,6)+':'+eui.slice(6,8)+':'+eui.slice(8,10)+':'+eui.slice(10,12)+':'+eui.slice(12,14)+':'+eui.slice(14,16);}

        h+='<div class="card diag-card" style="margin-bottom:10px">'
          +'<div class="diag-header">'
          +'<span style="font-weight:700;font-size:14px;font-family:monospace">'+dev.label+'</span>'
          +'<span style="font-size:11px;color:#64748b;font-family:monospace">'+eui+'</span>'
          +'<span class="badge" style="font-size:10px;background:#e2e8f0;padding:1px 6px;border-radius:4px">'+typeLabel+'</span>'
          +'</div>';

        var pe=dev.pre_events||{};
        h+='<div class="diag-timeline">';
        h+='<div class="diag-ev"><span class="diag-ic diag-ic-com">▸</span> 正常通信 (Link Status, Route Record, Data)</div>';
        if(pe.network_status_count>0){h+='<div class="diag-ev"><span class="diag-ic diag-ic-warn">⚠</span> Network Status ×'+pe.network_status_count+' (路由层异常前置信号)</div>';}
        if(pe.ieee_addr_req_count>0){h+='<div class="diag-ev"><span class="diag-ic diag-ic-info">🔍</span> IEEE Addr Req ×'+pe.ieee_addr_req_count+' (协调器查询设备身份)</div>';}
        var bursts=dev.leave_bursts||[];
        for(var b=0;b<bursts.length;b++){
          var burst=bursts[b];
          var bt=burst.burst_index===1?'第一波':burst.burst_index===2?'第二波':('第'+burst.burst_index+'波');
          var bc=burst.count>1?(' ×'+burst.count):'';
          var typeName=burst.type==='kicked'?'[被踢]':burst.type==='voluntary_permanent'?'[主动永久]':burst.type==='voluntary_rejoin'?'[主动暂离]':'[被踢·可重入]';
          h+='<div class="diag-ev"><span class="diag-ic diag-ic-leave">✕</span> '+bt+' Leave'+bc+' '+typeName+'</div>';
        }
        var rej=dev.rejoin_attempts||[];
        for(var r=0;r<rej.length;r++){
          var rj=rej[r];
          h+='<div class="diag-ev"><span class="diag-ic diag-ic-join">📢</span> Device Announce ×'+rj.announce_count+' (第'+rj.after_burst+'波Leave后 '+rj.delay_seconds+'s) ← 重入网尝试</div>';
        }
        h+='</div>';
        var diag=dev.diagnosis||{};
        h+='<div class="diag-conclusion" style="background:#fffbeb;border:1px solid #fcd34d;border-radius:6px;padding:8px 12px;margin-top:8px;font-size:12px">'
          +'<span style="font-weight:600;color:#92400e">诊断: </span>'
          +'<span style="color:#92400e">'+diag.summary+'</span>'
          +'</div>';
        h+='</div>';
      }
    }
    document.getElementById('mc').innerHTML=h;
  }).catch(function(e){
    document.getElementById('mc').innerHTML=h+'<div class="card" style="color:#dc2626">诊断数据加载失败: '+e.message+'</div>';
  });
});
