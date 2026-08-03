// diag.js — 诊断页面模块 (ES module)
import { S, A } from './state.js';

reg('diag',function(){
  document.getElementById('mc').style.padding='16px';
  var h='<div class="card" style="margin-bottom:12px"><h3>🩺 网络诊断</h3>'
    +'<p style="font-size:11px;color:#94a3b8;margin-top:4px">基于协议数据 (Leave/Rejoin/Announce/Network Status) 的离线诊断</p></div>';

  // ── L1 入网检测区 (文档→测试→工具工作流验证) ──
  A.get('/api/diag/l1').then(function(l1d){
    if(l1d && l1d.error){
      h+='<div class="card" style="margin-bottom:12px;background:#fef2f2;border-left:3px solid #dc2626">'
        +'<h3 style="color:#dc2626">L1 入网检测</h3>'
        +'<p style="font-size:11px;color:#94a3b8">'+l1d.error+' (L1 检测需要 .cubx 导入, pcap 无 MAC 帧)</p></div>';
      return;
    }
    var l1 = l1d ? (l1d.l1_1||{}) : {};
    var l2 = l1d ? (l1d.l1_2||{}) : {};
    var vc1 = l1.verdict==='HEALTHY' ? '#16a34a' : (l1.verdict==='L1-1_HIT' ? '#dc2626' : '#f59e0b');
    var vc2 = l2.verdict==='HEALTHY' ? '#16a34a' : (l2.verdict==='L1-2_HIT_REJECTED' ? '#dc2626' : '#f59e0b');
    h+='<div class="card" style="margin-bottom:12px;background:#f8fafc;border-left:3px solid #3b82f6">'
      +'<h3 style="font-size:13px;margin-bottom:8px">🔍 L1 入网检测 <span style="font-size:10px;color:#94a3b8;font-weight:400">(文档→测试→工具)</span></h3>'
      +'<div style="display:flex;gap:16px;flex-wrap:wrap">'
      // L1-1
      +'<div style="flex:1;min-width:280px;background:#fff;border-radius:6px;padding:10px;border:1px solid #e2e8f0">'
      +'<div style="font-weight:600;font-size:12px;margin-bottom:4px">L1-1 发现失败: <span style="color:'+vc1+';font-weight:700">'+l1.verdict+'</span> <span style="color:#94a3b8;font-size:10px" title="置信度: 高=直接证据/中=帧模式/低=推断/不可判定=数据不足">置信度:'+l1.confidence+'</span></div>'
      +'<div style="font-size:11px;color:#475569;line-height:1.6">'
      +'Beacon Request: <b>'+l1.beacon_request_count+'</b> 个 | 命中 <b style="color:'+vc1+'">'+l1.hit_count+'/'+l1.beacon_request_count+'</b> ('+(l1.hit_rate*100).toFixed(0)+'%)<br>'
      +'最大连续MISS: <b>'+l1.max_consecutive_miss+'</b> (判定阈值≥2)<br>'
      +(l1.delay_summary_ms ? '响应延迟: <b>'+l1.delay_summary_ms.min+'~'+l1.delay_summary_ms.max+'</b>ms (median '+l1.delay_summary_ms.median+')' : '')
      +'</div></div>'
      // L1-2
      +'<div style="flex:1;min-width:280px;background:#fff;border-radius:6px;padding:10px;border:1px solid #e2e8f0">'
      +'<div style="font-weight:600;font-size:12px;margin-bottom:4px">L1-2 Association: <span style="color:'+vc2+';font-weight:700">'+l2.verdict+'</span> <span style="color:#94a3b8;font-size:10px" title="置信度: 高=直接证据/中=帧模式/低=推断/不可判定=数据不足">置信度:'+l2.confidence+'</span></div>'
      +'<div style="font-size:11px;color:#475569;line-height:1.6">'
      +'AssocReq: <b>'+l2.assoc_req_count+'</b> | 成功 <b style="color:#16a34a">'+l2.success_count+'</b> | 无响应 <b style="color:#f59e0b">'+l2.no_response_count+'</b> | 拒绝 <b style="color:#dc2626">'+l2.rejected_count+'</b><br>'
      +'<span style="color:#64748b">'+l2.summary+'</span>'
      +'</div></div>'
      +'</div></div>';
    // 渲染 L1 后再渲染离线诊断
    document.getElementById('mc').innerHTML=h;
    renderOffline();
  }).catch(function(){
    // L1 失败不阻塞离线诊断
    document.getElementById('mc').innerHTML=h;
    renderOffline();
  });

  function renderOffline(){
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
  }
});
