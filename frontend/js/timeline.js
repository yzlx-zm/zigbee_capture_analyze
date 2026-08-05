// timeline.js — 时间线页面模块 (ES module)
import { S, A, sb, sr } from './state.js';

reg('tl', function(){
  // Init state: remember last filter
  if(!S.tlPan) S.tlPan='';
  if(!S.tlNode) S.tlNode='';
  if(!S.tlTs0H) S.tlTs0H=''; if(!S.tlTs0M) S.tlTs0M=''; if(!S.tlTs0S) S.tlTs0S='';
  if(!S.tlTs1H) S.tlTs1H=''; if(!S.tlTs1M) S.tlTs1M=''; if(!S.tlTs1S) S.tlTs1S='';
  if(!S.tlHasSearched) S.tlHasSearched=false;
  if(!S.tlType) S.tlType='';
  // Override PAN if jumped from topology
  if(S.topoPan){S.tlPan=S.topoPan; S.tlHasSearched=true;}
  // Override node filter if jumped from topology
  // ⚠️ 修复 (U5): 此前 topoAddr 未同步 → 拓扑点击节点跳转后节点框为空, 看到的是全 PAN 的包
  if(S.topoAddr){S.tlNode=S.topoAddr; S.tlHasSearched=true;}
  // topoT0/T1 时间窗口同步延迟到 import/status 回调 (需 tlCaptureStart 做字符串→时间戳转换;
  // 契约: 数字时间戳 (拓扑滑块) 或 "HH:MM:SS" 字符串 (时间线保存), 读侧兼容两者)

  // Build H/M/S dropdown helpers
  function hmssel(id,val,opts){var h='<select id="'+id+'" class="mono hm-sel">';for(var i=0;i<opts.length;i++){h+='<option value="'+opts[i]+'"'+(String(opts[i])===String(val)?' selected':'')+'>'+String(opts[i]).padStart(2,'0')+'</option>';}h+='</select>';return h;}
  var hourOpts=[];for(var hi=0;hi<24;hi++)hourOpts.push(hi);
  var minSecOpts=[];for(var mi=0;mi<60;mi++)minSecOpts.push(mi);

  document.getElementById('mc').innerHTML='<div class="card"><h3>📊 时间线</h3>'
    // Row 1: PAN + Node text inputs
    +'<div class="tl-bar">'
    +'<span class="t-label">PAN:</span><input id="tl-pan" placeholder="FEED" class="mono w-90" value="'+S.tlPan+'">'
    +'<span class="t-label">节点:</span><input id="tl-node" placeholder="0x0000 或 0000" class="mono w-130" value="'+S.tlNode+'">'
    +'</div>'
    // Row 2: Time dropdowns (start ~ end)
    +'<div class="tl-bar">'
    +'<span class="t-label">时间:</span>'
    +hmssel('tl-h0',S.tlTs0H,hourOpts)+'<span class="hm-colon">:</span>'+hmssel('tl-m0',S.tlTs0M,minSecOpts)+'<span class="hm-colon">:</span>'+hmssel('tl-s0',S.tlTs0S,minSecOpts)
    +'<span class="hm-colon">~</span>'
    +hmssel('tl-h1',S.tlTs1H,hourOpts)+'<span class="hm-colon">:</span>'+hmssel('tl-m1',S.tlTs1M,minSecOpts)+'<span class="hm-colon">:</span>'+hmssel('tl-s1',S.tlTs1S,minSecOpts)
    +'<button class="btn btn-o btn-s ml-1" id="tl-tclear" title="清除时间过滤">✕</button>'
    +'</div>'
    // Row 3: View button + status
    +'<div class="tl-bar">'
    +'<select id="tl-type" class="mono"><option value="">全部类型</option></select>'
    +'<button class="btn btn-p" id="tshow">🔍 查看</button>'
    +'<span id="tl-capture-info"></span>'
    +'<span id="tl-stat"></span></div>'
    // Summary
    +'<div id="tl-summary"></div>'
    // ═══ Left-Right split ═══
    +'<div class="tl-main">'
    // LEFT: packet table
    +'<div class="tl-table-wrap">'
    +'<table class="tbl" id="tltbl"><thead><tr>'
    +'<th>时间</th><th>类型</th><th>NWK Src</th><th>NWK Dst</th><th>安全</th><th>状态</th>'
    +'</tr></thead><tbody id="tltb"><tr><td colspan="6" class="tl-empty-cell">请输入过滤条件后点击「查看」</td></tr></tbody></table>'
    +'</div>'
    // RIGHT: protocol detail panel
    +'<div id="tl-detail">'
    +'<p class="empty-tip">← 点击左侧包列表中的帧<br>查看协议详情</p>'
    +'</div>'
    +'</div>'
    // Pagination
    +'<div id="tl-pager">'
    +'<button class="btn btn-o btn-s" id="tl-pp">上一页</button><span id="tl-pi">-</span><button class="btn btn-o btn-s" id="tl-pn">下一页</button>'
    +'<span>跳至</span><input id="tl-pj" class="w-45 t-10"><span>页</span><button class="btn btn-o btn-s" id="tl-pgo">Go</button>'
    +'<span>每页</span><select id="tl-ps"><option value="50">50</option><option value="100">100</option><option value="200" selected>200</option><option value="500">500</option></select></div></div>';

  var tlPage=1,tlLimit=200,tlTotal=0,tlCaptureStart=null,tlCaptureEnd=null;

  function tlFmtTs(ts){var d=new Date(ts*1000);return d.toISOString().substr(11,12);}

  // S.topoT0/T1 → 绝对时间戳 (Unix sec): 兼容数字 (拓扑滑块) / "HH:MM:SS" 字符串 (时间线保存)
  // ⚠️ 修复 (U5): 此前字符串格式直接 new Date(str*1000)=NaN → 时间下拉变全零
  function tlToTs(v){
    if(v==null)return null;
    if(typeof v==='number')return v;
    var parts=String(v).split(':');
    if(parts.length<2||tlCaptureStart==null)return null;
    var h=parseInt(parts[0]),m=parseInt(parts[1]),s=parseInt(parts[2])||0;
    if(isNaN(h)||isNaN(m))return null;
    var d=new Date(tlCaptureStart*1000);
    return Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate(),h,m,s)/1000;
  }

  function tlGetTimeFilter(){
    var h0=document.getElementById('tl-h0').value;
    var m0=document.getElementById('tl-m0').value;
    var s0=document.getElementById('tl-s0').value;
    var h1=document.getElementById('tl-h1').value;
    var m1=document.getElementById('tl-m1').value;
    var s1=document.getElementById('tl-s1').value;
    var ts0=String(h0).padStart(2,'0')+':'+String(m0).padStart(2,'0')+':'+String(s0).padStart(2,'0');
    var ts1=String(h1).padStart(2,'0')+':'+String(m1).padStart(2,'0')+':'+String(s1).padStart(2,'0');
    return {ts0:ts0, ts1:ts1};
  }

  function tlSaveFilter(){
    S.tlPan=document.getElementById('tl-pan').value.trim();
    S.tlNode=document.getElementById('tl-node').value.trim();
    S.tlTs0H=document.getElementById('tl-h0').value; S.tlTs0M=document.getElementById('tl-m0').value; S.tlTs0S=document.getElementById('tl-s0').value;
    S.tlTs1H=document.getElementById('tl-h1').value; S.tlTs1M=document.getElementById('tl-m1').value; S.tlTs1S=document.getElementById('tl-s1').value;
    S.tlType=document.getElementById('tl-type').value;
    S.tlHasSearched=true;
    // 双向联动: 时间线→拓扑 (节点+时间)
    S.topoAddr=S.tlNode||null;
    var tf=tlGetTimeFilter(); S.topoT0=tf.ts0; S.topoT1=tf.ts1;
  }

  function updPgr(){
    var mp=Math.ceil(tlTotal/tlLimit)||1;
    document.getElementById('tl-pi').textContent='第 '+tlPage+' / '+mp+' 页 (共 '+tlTotal+' 条)';
    document.getElementById('tl-pp').disabled=tlPage<=1;
    document.getElementById('tl-pn').disabled=tlPage>=mp;
  }

  // U5: 类型下拉从实际数据动态生成 (硬编码 13 类型 → /api/packets/types 全量统计)
  function tlFillTypes(){
    A.get('/api/packets/types').then(function(t){
      if(!t||!t.types||!t.types.length)return;
      var sel=document.getElementById('tl-type');
      if(sel.options.length<=1){
        for(var ti=0;ti<t.types.length;ti++){
          var tn=t.types[ti].name;
          sel.innerHTML+='<option value="'+tn+'"'+(S.tlType===tn?' selected':'')+'>'+tn+' ('+t.types[ti].count+')</option>';
        }
      }
    });
  }

  function search(){
    var panVal=document.getElementById('tl-pan').value.trim();
    var nodeVal=document.getElementById('tl-node').value.trim();
    // Normalize: strip 0x prefix
    if(panVal.match(/^0x/i))panVal=panVal.slice(2);
    if(nodeVal.match(/^0x/i))nodeVal=nodeVal.slice(2);
    var tf=tlGetTimeFilter();
    tlSaveFilter();
    // Build params
    var typeVal=document.getElementById('tl-type').value;
    var params='limit='+tlLimit+'&offset='+((tlPage-1)*tlLimit);
    if(panVal)params+='&pan='+panVal;
    if(nodeVal)params+='&addr='+nodeVal;
    if(tf.ts0)params+='&time_start='+encodeURIComponent(tf.ts0);
    if(tf.ts1)params+='&time_end='+encodeURIComponent(tf.ts1);
    if(typeVal)params+='&pkt_type='+encodeURIComponent(typeVal);
    // Show what we're querying
    document.getElementById('tl-stat').textContent='查询中... '+[panVal?'PAN='+panVal:'',nodeVal?'节点='+nodeVal:'',tf.ts0?'时间:'+tf.ts0+'~'+tf.ts1:''].filter(Boolean).join(' | ')||'全部包';
    // Summary params
    var sp=[];
    if(panVal)sp.push('pan='+panVal);
    if(nodeVal)sp.push('addr='+nodeVal);
    if(tf.ts0)sp.push('time_start='+encodeURIComponent(tf.ts0));
    if(tf.ts1)sp.push('time_end='+encodeURIComponent(tf.ts1));
    var sumUrl='/api/packets/summary'+(sp.length?'?'+sp.join('&'):'');
    // Fetch summary
    A.get(sumUrl).then(function(s){
      var el=document.getElementById('tl-summary');el.style.display='block';
      if(s.type==='device'){
        el.innerHTML='<b>设备 '+s.addr+'</b>: '+s.total_packets+' 包<br>'
          +Object.entries(s.type_counts||{}).map(function(e){return e[0]+'×'+e[1]}).join(' + ')+'<br>'
          +'⇄ 通信: '+(s.top_peers||[]).map(function(p){return p.addr+'('+p.count+')'}).join(', ');
      }else{
        el.innerHTML='<b>PAN '+s.pan+'</b>: '+s.total_packets+' 包 | '+s.active_devices+' 活跃设备<br>'
          +Object.entries(s.type_counts||{}).map(function(e){return e[0]+'×'+e[1]}).join(' + ');
      }
    }).catch(function(){});
    // 类型下拉兜底填充 (U5: 硬编码 13 类型 → /api/packets/types 全量统计; 主填充在 init 时)
    tlFillTypes();
    // Fetch packets
    A.get('/api/packets?'+params).then(function(d){
      var pkts=d.packets||[];tlTotal=d.total||pkts.length;
      var ctx=[panVal?'PAN='+panVal:'',nodeVal?'节点=0x'+nodeVal.toUpperCase():'',tf.ts0?'时间:'+tf.ts0+'~'+tf.ts1:''].filter(Boolean).join(' | ');
      document.getElementById('tl-stat').textContent='共 '+tlTotal+' 包'+(ctx?' ('+ctx+')':'');
      document.getElementById('tl-pager').style.display=tlTotal>0?'flex':'none';
      var h='';for(var i=0;i<pkts.length;i++){var p=pkts[i];
        var ts=tlFmtTs(p.ts);
        var ns=typeof p.nwk_src==='number'?'0x'+p.nwk_src.toString(16).toUpperCase():'-';
        var nd=typeof p.nwk_dst==='number'?'0x'+p.nwk_dst.toString(16).toUpperCase():'-';
        var isNwkCmdRow=(p.pkt_type==='Link Status'||p.pkt_type==='Route Request'||p.pkt_type==='Route Reply'||p.pkt_type==='Route Record'||p.pkt_type==='Network Status'||p.pkt_type==='Leave'||p.pkt_type.startsWith('NWK Cmd'));
        // 事件标记 (U5): Leave/Rejoin/NetworkStatus 行内徽章
        // 协议依据: NWK 0x04 Leave (bit5=rejoin, bit6=request) / 0x06-0x07 Rejoin / 0x03 Network Status
        var evBadge='';
        if(p.pkt_type==='Leave'){
          var lvTip='NWK Leave (0x04)'+(p.nwk_leave_request===1?' 设备主动申请离开':' 被命令离开')+(p.nwk_leave_rejoin===1?' 随后重入网':' 永久离开');
          evBadge=p.nwk_leave_rejoin===1?'<span class="badge-ev badge-rej" title="'+lvTip+'">🔄 重入网</span>'
                                      :'<span class="badge-ev badge-leave" title="'+lvTip+'">⛔ 离网</span>';
        }else if(p.pkt_type==='Rejoin Request'||p.pkt_type==='Rejoin Response'){
          var rjTip=p.pkt_type==='Rejoin Request'?'设备申请重新入网 (NWK 0x06)':'入网申请被响应 (NWK 0x07)';
          evBadge='<span class="badge-ev badge-rej" title="'+rjTip+'">🔄 '+p.pkt_type.replace('Rejoin ','')+'</span>';
        }else if(p.pkt_type==='Network Status'){
          evBadge='<span class="badge-ev badge-nstat" title="网络状态命令 (NWK 0x03), 详见右侧详情">⚠️ 状态</span>';
        }
        // ZCL 命令级显示 (U5): 解密 Data 帧类型列直接显示实际命令 (如 "Down / Close"),
        // 去掉笼统的 "Data"; 过滤仍按 pkt_type=Data (后端), 仅展示增强
        var typeDisp=p.pkt_type;
        if(p.decrypted&&p.zcl_cmd_name){
          typeDisp='<span class="zcl-cmd" title="ZCL 簇: '+(p.aps_cluster_name||'?')+' · 命令: '+p.zcl_cmd_name+'">'+p.zcl_cmd_name+'</span>';
        }else if(p.decrypted&&p.aps_cluster_name){
          typeDisp='<span class="zcl-cmd" title="ZCL 簇: '+p.aps_cluster_name+'">'+p.aps_cluster_name+'</span>';
        }
        var decIcon='';
        if(isNwkCmdRow){
          decIcon='<span class="ic-nwk" title="NWK命令">📡</span>';
        }else if(p.decrypted){
          decIcon='<span class="ic-dec" title="已解密">✅</span>';
        }else{
          decIcon='<span class="ic-enc" title="加密">🔒</span>';
        }
        var stat=(p.status||'')+' '+decIcon;
        h+='<tr data-pid="'+p.id+'" class="tl-row"><td>'+ts+'</td><td>'+typeDisp+evBadge+'</td><td>'+ns+'</td><td>'+nd+'</td><td>'+(p.security||'')+'</td><td>'+stat+'</td></tr>';}
      document.getElementById('tltb').innerHTML=h||'<tr><td colspan="6" class="tl-empty-row">无匹配数据'+(ctx?' — 条件: '+ctx:'')+'<br><span class="t-10">提示: 尝试放宽过滤条件（清空节点或 PAN 再查）</span></td></tr>';
      // Click-to-select handler
      document.querySelectorAll('#tltb tr.tl-row').forEach(function(tr){
        tr.addEventListener('click',function(){
          document.querySelectorAll('#tltb tr.tl-row').forEach(function(r){r.classList.remove('hl')});
          this.classList.add('hl');
          var pid=parseInt(this.dataset.pid);
          tlShowDetail(pid);
        });
      });
      updPgr();
    }).catch(function(e){document.getElementById('tl-stat').textContent='加载失败';});
  }

  // Detail panel renderer
  function tlShowDetail(pid){
    var panel=document.getElementById('tl-detail');
    panel.innerHTML='<p class="text-dim text-center">加载中...</p>';
    A.get('/api/packets/'+pid).then(function(d){
      if(!d||!d.layers){
        panel.innerHTML='<p class="text-danger text-center">无法加载帧详情</p>';
        return;
      }
      var html='<div class="frame-meta">帧 #'+pid+' | '+tlFmtTs(d.ts)+' | '+d.pkt_type+' | '+(d.decrypted?'<span class="text-success">已解密</span>':'<span class="text-danger">加密</span>')+'</div>';
      var layers=d.layers;
      // MAC layer (wpan)
      if(layers.wpan){
        html+=_tlLayer('MAC', '#d97706', [
          ['Frame Type', _tlMacType(layers.wpan)],
          ['Seq#', _tlF(layers.wpan,'wpan.seq_no')],
          ['Dest PAN', _tlA(layers.wpan,'wpan.dst_pan')],
          ['Dest Addr', _tlA(layers.wpan,'wpan.dst16')],
          ['Src Addr', _tlA(layers.wpan,'wpan.src16')],
          ['FCS OK', layers.wpan['wpan.fcs_ok']==='1'?'Yes':'No'],
        ]);
      }
      // NWK layer
      if(layers.zbee_nwk){
        var nwk=layers.zbee_nwk;
        var nwkFields=[];
        // Check for named NWK command
        var cmdName='';
        for(var ck in nwk){if(ck.startsWith('Command Frame:')){cmdName=ck.split(':')[1].trim();break;}}
        if(cmdName){nwkFields.push(['Command', cmdName]);}
        nwkFields.push(['Dest', _tlA2(nwk,'zbee_nwk.dst')]);
        nwkFields.push(['Src', _tlA2(nwk,'zbee_nwk.src')]);
        nwkFields.push(['Radius', _tlF(nwk,'zbee_nwk.radius')]);
        nwkFields.push(['Seq#', _tlF(nwk,'zbee_nwk.seqno')]);
        var fct=nwk['zbee_nwk.fcf_tree']||{};
        var secEnabled=fct['zbee_nwk.security']==='1';
        nwkFields.push(['Security', secEnabled?'Enabled':'Disabled']);
        html+=_tlLayer('NWK', '#2563eb', nwkFields);
        // Security header — always show if tshark parsed it
        var sec=nwk['ZigBee Security Header']||{};
        if(Object.keys(sec).length>0&&sec['zbee.sec.field']){
          var klabel=sec['zbee.sec.decryption_key']||(sec['zbee.sec.key']?'Key matched':'');
          html+=_tlLayer('Security', '#dc2626', [
            ['Level', _tlSecLevel(sec)],
            ['Frame Counter', sec['zbee.sec.counter']||'?'],
            ['Key Seq#', sec['zbee.sec.key_seqno']||'?'],
            ['MIC', sec['zbee.sec.mic']||'?'],
            ['Key', klabel||'None'],
          ]);
        }
        // NWK command-specific details
        var cmdVal=null;
        for(var ck2 in nwk){if(ck2.startsWith('Command Frame:')){cmdVal=nwk[ck2];break;}}
        if(cmdVal&&typeof cmdVal==='object'){
          // Link Status: neighbor list
          if(cmdName==='Link Status'){
            var nb=[];
            for(var lk in cmdVal){
              if(lk.startsWith('Link ')&&!lk.includes('count')&&!lk.includes('first')&&!lk.includes('last')){
                var li=cmdVal[lk];
                if(li&&li['zbee_nwk.cmd.link.address']){
                  var addr='0x'+parseInt(li['zbee_nwk.cmd.link.address'],16).toString(16).toUpperCase().padStart(4,'0');
                  var inc=li['zbee_nwk.cmd.link.incoming_cost']||'?';
                  var out=li['zbee_nwk.cmd.link.outgoing_cost']||'?';
                  var incColor=parseInt(inc)<=1?'#16a34a':parseInt(inc)<=3?'#d97706':'#dc2626';
                  var outColor=parseInt(out)<=1?'#16a34a':parseInt(out)<=3?'#d97706':'#dc2626';
                  nb.push([addr, '<span style=\"color:'+incColor+'\">in:'+inc+'</span> <span style=\"color:'+outColor+'\">out:'+out+'</span>']);
                }
              }
            }
            if(nb.length>0){
              html+=_tlLayer('Neighbors ('+nb.length+')', '#0891b2', nb);
            }
          }
          // Route Request
          if(cmdName==='Route Request'){
            var originator=nwk['zbee_nwk.src'];
            var dest=cmdVal['zbee_nwk.cmd.route.dest'];
            var nwkDst2=nwk['zbee_nwk.dst'];
            var origStr=originator?'0x'+parseInt(originator,16).toString(16).toUpperCase().padStart(4,'0'):'-';
            var destStr=dest?'0x'+parseInt(dest,16).toString(16).toUpperCase().padStart(4,'0'):'-';
            var relayStr2='-';
            if(originator&&nwkDst2){
              relayStr2='0x'+parseInt(originator,16).toString(16).toUpperCase().padStart(4,'0')+' → 0x'+parseInt(nwkDst2,16).toString(16).toUpperCase().padStart(4,'0');
            }
            var rq=[
              ['Originator', origStr, '发起路由请求的设备'],
              ['Target Dest', destStr, '路由目标地址'],
              ['Relay Hop', relayStr2, '当前转发此Request的路由器跳(NWK层)'],
              ['Path Cost', cmdVal['zbee_nwk.cmd.route.cost']||'0'],
              ['Route ID', cmdVal['zbee_nwk.cmd.route.id']||'?'],
              ['Options', _tlROpts(cmdVal['zbee_nwk.cmd.route.opts'])],
            ];
            html+=_tlLayer('Route Request', '#7c3aed', rq);
            if(originator&&dest){
              html+=_tlPath('Route', originator, dest);
            }
          }
          // Route Reply
          if(cmdName==='Route Reply'){
            var orig=cmdVal['zbee_nwk.cmd.route.orig']||'?';
            var resp=cmdVal['zbee_nwk.cmd.route.resp']||'?';
            var nwkSrc=nwk['zbee_nwk.src']; var nwkDst=nwk['zbee_nwk.dst'];
            var relayStr='-';
            if(nwkSrc&&nwkDst){
              relayStr='0x'+parseInt(nwkSrc,16).toString(16).toUpperCase().padStart(4,'0')+' → 0x'+parseInt(nwkDst,16).toString(16).toUpperCase().padStart(4,'0');
            }
            var rp=[
              ['Originator', _tlA2(cmdVal,'zbee_nwk.cmd.route.orig'), '发起路由请求的设备'],
              ['Responder', _tlA2(cmdVal,'zbee_nwk.cmd.route.resp'), '应答路由的目标设备'],
              ['Relay Hop', relayStr, '当前转发此Reply的路由器跳'],
              ['Path Cost', cmdVal['zbee_nwk.cmd.route.cost']||'0'],
              ['Route ID', cmdVal['zbee_nwk.cmd.route.id']||'?'],
            ];
            html+=_tlLayer('Route Reply', '#7c3aed', rp);
            if(orig!=='?'&&resp!=='?'){
              html+=_tlPath('Route', orig, resp);
            }
          }
          // Route Record
          if(cmdName==='Route Record'){
            var relayCount=parseInt(cmdVal['zbee_nwk.cmd.relay_count']||'0');
            var rrFields=[['Relay Count', String(relayCount), relayCount===0?'直连通信(单跳)':'经过'+relayCount+'个中继节点']];
            // Collect relay devices from tshark
            var relays=[];
            for(var rk in cmdVal){
              if(rk.indexOf('relay_device')>=0&&rk.indexOf('_tree')<0){
                var rv=cmdVal[rk];
                if(rv&&typeof rv!=='object'){
                  var rAddr='0x'+parseInt(rv,16).toString(16).toUpperCase().padStart(4,'0');
                  relays.push(rAddr);
                }
              }
            }
            if(relays.length>0){
              for(var ri=0;ri<relays.length;ri++){
                rrFields.push(['Relay '+(ri+1), relays[ri]]);
              }
            }
            if(relayCount>0&&relays.length===0){
              rrFields.push(['Relay List', '未解析 (tshark限制)']);
            }
            html+=_tlLayer('Route Record', '#7c3aed', rrFields);
            // Show path: NWK Src → [Relays] → NWK Dst
            if(relayCount>0){
              var nwkSrc2=nwk['zbee_nwk.src']; var nwkDst3=nwk['zbee_nwk.dst'];
              var pathNodes=[nwkSrc2].concat(relays).concat([nwkDst3]);
              var pathStr='';
              for(var pi=0;pi<pathNodes.length;pi++){
                if(pi>0)pathStr+=' <span class="path-arrow">→</span> ';
                var pn=pathNodes[pi];
                if(typeof pn==='string'&&pn.startsWith('0x'))pathStr+=pn;
                else if(pn)pathStr+='0x'+parseInt(pn,16).toString(16).toUpperCase().padStart(4,'0');
              }
              if(pathStr){
                var ph='<div class="path-block">';
                ph+='<div class="path-title">Record Path</div>';
                ph+='<div class="path-code">'+pathStr+'</div></div>';
                html+=ph;
              }
            }
          }
          // Network Status
          if(cmdName==='Network Status'){
            var stCode=cmdVal['zbee_nwk.cmd.status']||'?';
            var stNames={'0x00':'No Route Available','0x01':'Tree Link Failure','0x02':'Non-Tree Link Failure','0x03':'Low Battery','0x04':'No Routing Capacity','0x05':'No Indirect Capacity','0x06':'Indirect Transaction Expiry','0x07':'Target Unavailable','0x08':'Target Address Unallocated','0x09':'Parent Link Failure','0x0a':'Validate Route','0x0b':'Source Route Failure','0x0c':'Many-to-One Route Failure','0x0d':'Address Conflict','0x0e':'Verify Addresses','0x0f':'PAN ID Update','0x10':'Network Address Update','0x11':'Bad Frame Counter','0x12':'Bad Key Sequence Number','0x13':'Unknown Command'};
            var stExplain={'0x00':'无到目标的路由条目','0x01':'树状路由链路断开','0x02':'Mesh路由链路断开','0x03':'终端设备电量不足','0x04':'路由表已满,无法新增','0x07':'目标设备无响应','0x0b':'源路由路径中某跳不可达','0x0c':'集中器(协调器)Many-to-One下行路由失败','0x0d':'短地址冲突','0x11':'帧计数器异常(安全攻击或密钥不同步)'};
            var stName=stNames[stCode]||stCode;
            var stExp=stExplain[stCode]||'';
            var stDisplay=stName+' ('+stCode+')'+(stExp?' — '+stExp:'');
            var nwkSrc3=nwk['zbee_nwk.src']; var nwkDst4=nwk['zbee_nwk.dst'];
            var ctxStr='';
            if(nwkSrc3&&nwkDst4){
              ctxStr='0x'+parseInt(nwkSrc3,16).toString(16).toUpperCase().padStart(4,'0')+' → 0x'+parseInt(nwkDst4,16).toString(16).toUpperCase().padStart(4,'0');
            }
            html+=_tlLayer('Network Status', '#dc2626', [
              ['Status', stDisplay],
              ['Error Dest', _tlA2(cmdVal,'zbee_nwk.cmd.route.dest'), '路由失败的目标地址'],
              ['Reported By', ctxStr, '报告此错误的设备→接收方'],
            ]);
          }
          // Leave
          if(cmdName==='Leave'){
            var rejoin=cmdVal['zbee_nwk.cmd.leave.rejoin']||'0';
            var rmChildren=cmdVal['zbee_nwk.cmd.leave.remove_children']||'0';
            html+=_tlLayer('Leave', '#dc2626', [
              ['Rejoin', rejoin==='1'?'Yes (设备将重新入网)':'No (永久离开)'],
              ['Remove Children', rmChildren==='1'?'Yes (子节点也被移除)':'No'],
            ]);
          }
        }
      }
      // Detect NWK Command type first
      // ⚠️ 修复 (U5): 非 NWK 帧 (Beacon/ACK/MAC Cmd) 无 zbee_nwk 层, nwk=undefined
      // for-in 抛 TypeError → 整帧详情加载失败 (Cannot read properties of undefined)
      var isNwkCmd=false;
      if(nwk){
        for(var ck in nwk){if(ck.startsWith('Command Frame:')){isNwkCmd=true;break;}}
        if(!isNwkCmd){
          var fct2=nwk['zbee_nwk.fcf_tree']||{};
          isNwkCmd=(fct2['zbee_nwk.frame_type']==='0x0001');
        }
      }

      // APS — only for Data frames
      if(!isNwkCmd){
        if(layers.zbee_aps){
          var aps=layers.zbee_aps;
          html+=_tlLayer('APS', '#16a34a', [
            ['Cluster', _tlCluster(aps)],
            ['Profile', _tlA(aps,'zbee_aps.profile')],
            ['Src EP', aps['zbee_aps.src']||'?'],
            ['Dest EP', aps['zbee_aps.dst']||'?'],
            ['Counter', aps['zbee_aps.counter']||'?'],
          ]);
        }else if(!d.decrypted){
          html+=_tlLayer('APS', '#16a34a', [['Status','🔒 Encrypted']]);
        }
      }

      // ZDP layer (profile 0x0000) — always check, independent of NWK type
      if(layers.zbee_zdp){
        var zdp=layers.zbee_zdp;
        var zdpLabels={nwk_addr:'NWK Addr',seqno:'Seq#',status:'Status',manufacturer:'Mfr Code',max_buffer:'Max Buf',max_incoming_transfer:'Max In',max_outgoing_transfer:'Max Out',type:'Node Type',complex:'Complex Desc',user:'User Desc',frag_support:'Frag Support','freq.868mhz':'868 MHz','freq.900mhz':'900 MHz','freq.2400mhz':'2.4 GHz','freq.eu_sub_ghz':'EU Sub-GHz',server:'Server Mask',dcf:'Desc Capability',cinfo:'Complex Info',aps_flags:'APS Flags'};
        var zdpDesc={nwk_addr:'本节点16位网络地址',seqno:'ZDP事务序列号',status:'0x00=成功 其他=失败',manufacturer:'制造商ID 0x1141=SiliconLabs','Max Buf':'最大ASDU缓冲(bytes)','Max In':'最大接收传输大小(bytes)','Max Out':'最大发送传输大小(bytes)',type:'0=协调器 1=路由器 2=终端',complex:'是否有复杂描述符',user:'是否有用户描述符',frag_support:'是否支持APS分段传输','868 MHz':'868MHz频段(欧洲)','900 MHz':'900MHz频段(美洲)','2.4 GHz':'2.4GHz频段(全球常用)','EU Sub-GHz':'欧洲Sub-GHz频段','Server Mask':'系统服务能力(Trust/Bind/Discovery等)','Desc Capability':'扩展描述符能力标志',cinfo:'MAC能力(FFD/主电源/空闲接收/安全)',aps_flags:'APS层标志位'};
        function _zdpVal(k,v){
          if(k==='status'){var m={'0x00':'Success','0x80':'InvRequestType','0x81':'DeviceNotFound','0x82':'InvalidEP','0x83':'NotActive','0x84':'NotSupported','0x85':'Timeout','0x89':'NoDescriptor'};return (m[v]||v)+' ('+v+')';}
          if(k==='type'||k==='Node Type'){var mt={'0':'Coordinator','1':'Router','2':'End Device'};return (mt[v]||v);}
          if(k==='complex'||k==='Complex Desc'||k==='user'||k==='User Desc'){return v==='1'?'Yes (0x1)':'No (0x0)';}
          if(k==='frag_support'||k==='Frag Support'){return v==='1'?'Supported':'No';}
          return v;
        }
        var zdpFields=[];
        for(var zk in zdp){
          if(zk.indexOf('_tree')>=0)continue;
          // Node Descriptor sub-object FIRST (before typeof check)
          if(zk==='Node Descriptor'&&typeof zdp[zk]==='object'){
            var nd=zdp[zk];
            for(var ndk in nd){
              if(ndk.indexOf('_tree')>=0)continue;
              var nv=nd[ndk];
              if(typeof nv==='object')continue;
              var rawNd=ndk.replace('zbee_zdp.','').replace('node.','');
              zdpFields.push([zdpLabels[rawNd]||rawNd, _zdpVal(rawNd, nv), zdpDesc[rawNd]||'']);
            }
            continue;
          }
          var v=zdp[zk];
          if(typeof v==='object')continue;
          if(zk.startsWith('zbee_zdp.')){
            var raw=zk.replace('zbee_zdp.','');
            zdpFields.push([zdpLabels[raw]||raw, _zdpVal(raw, v), zdpDesc[raw]||'']);
          }
        }
        if(zdpFields.length>0){
          html+=_tlLayer('ZDP', '#059669', zdpFields);
        }
      }

      // ZCL — only for non-NWK-command Data frames
      if(!isNwkCmd){
        if(layers.zbee_zcl){
          var zcl=layers.zbee_zcl;
          var fcf=zcl['Frame Control Field']||{};
          var dir='?';
          if(typeof fcf==='object'&&fcf['zbee_zcl.dir']==='1')dir='Server→Client';
          else if(typeof fcf==='object'&&fcf['zbee_zcl.dir']==='0')dir='Client→Server';
          // ⚠️ 修复 (U5): 优先用后端按簇解析的命令名 (zcl_defs), 前端混合表兜底 —
          // 此前 0x01 在 Window Covering 簇被误标为 "OTA: Query Next Image"
          var zclCmd=d.zcl_cmd_name||_tlZclCmd(zcl);
          html+=_tlLayer('ZCL', '#7c3aed', [
            ['Command', zclCmd],
            ['Direction', dir],
            ['Seq#', zcl['zbee_zcl.cmd.tsn']||'?'],
          ]);
        }else if(!d.decrypted&&!isNwkCmd){
          var isZdp=aps&&_tlIsZdp(aps);
          if(!isZdp){
            html+=_tlLayer('ZCL', '#7c3aed', [['Status','🔒 Encrypted (需要 Network Key)']]);
          }
        }
      }
      panel.innerHTML=html;
    }).catch(function(e){
      panel.innerHTML='<p class="text-danger text-center">加载失败: '+e.message+'</p>';
    });
  }
  function _tlLayer(title, color, fields){
    // color = 协议层语义色 (数据驱动, 保留动态): MAC 橙 / NWK 蓝 / APS 紫 等
    var h='<div class="layer" style="border-left-color:'+color+'">';
    h+='<div class="frame-title" style="color:'+color+'">'+title+'</div>';
    for(var i=0;i<fields.length;i++){
      var desc=fields[i][2]||'';
      h+='<div class="field-row"><span class="k" title="'+desc+'">'+fields[i][0]+'</span><span class="v">'+fields[i][1]+'</span></div>';
    }
    h+='</div>';
    return h;
  }
  function _tlF(obj,key){var v=obj[key];return v?v:'-';}
  function _tlA(obj,key){var v=obj[key];return v?'0x'+parseInt(v,16).toString(16).toUpperCase():'-';}
  function _tlA2(obj,key){var v=obj[key];return v?'0x'+parseInt(v,16).toString(16).toUpperCase().padStart(4,'0'):'-';}
  function _tlMacType(wpan){
    var fcf=parseInt(wpan['wpan.fcf']||'0',16);
    var types={0:'Beacon',1:'Data',2:'ACK',3:'MAC Cmd'};
    return (types[fcf&0x07]||'?')+' [0x'+fcf.toString(16).toUpperCase()+']';
  }
  function _tlSecLevel(sec){
    var lv=sec['zbee.sec.sec_level']||'?';
    return 'Level '+lv;
  }
  function _tlCluster(aps){
    var cid=aps['zbee_aps.cluster']||aps['zbee_aps.zdp_cluster'];
    if(!cid)return '-';
    var profile=aps['zbee_aps.profile']||'';
    var num=parseInt(cid,16);
    // ZDP commands (profile 0x0000)
    if(profile==='0x0000'){
      var zdp={0x0000:'NWK Address Req',0x0001:'IEEE Address Req',0x0002:'Node Desc Req',0x0003:'Power Desc Req',0x0004:'Simple Desc Req',0x0005:'Active EP Req',0x0006:'Match Desc Req',0x0010:'End Device Announce',0x0013:'Device Announce',0x0031:'Mgmt LQI Req',0x0032:'Mgmt Routing Req',0x8002:'Node Desc Resp',0x8005:'Active EP Resp'};
      return (zdp[num]||'ZDP Cmd')+' (0x'+num.toString(16).toUpperCase()+')';
    }
    var names={0x0000:'Basic',0x0001:'Power',0x0003:'Identify',0x0004:'Groups',0x0005:'Scenes',0x0006:'On/Off',0x0008:'Level',0x0019:'OTA Upgrade',0x0101:'Door Lock',0x0102:'Window Covering',0x0300:'Color',0x0402:'Temperature',0x0405:'Humidity',0x0500:'IAS Zone',0xFCFA:'Private'};
    return (names[num]||'')+' (0x'+num.toString(16).toUpperCase()+')';
  }
  function _tlIsZdp(aps){return (aps['zbee_aps.profile']||'')==='0x0000';}
  function _tlZclCmd(zcl){
    var cid=zcl['zbee_zcl.cmd.id'];
    if(!cid)return '-';
    var names={0x00:'Read Attributes',0x01:'Read Attributes Resp',0x02:'Write Attributes',0x04:'Write Attributes Resp',0x06:'Config Report',0x07:'Config Report Resp',0x0A:'Report Attributes',0x0B:'Default Resp',0x00:'OTA: Image Notify',0x01:'OTA: Query Next Image',0x02:'OTA: Query Next Image Resp',0x03:'OTA: Image Block Req',0x05:'OTA: Image Block Resp',0x06:'OTA: Upgrade End Req',0x07:'OTA: Upgrade End Resp'};
    var num=parseInt(cid,16);
    return (names[num]||'')+' (0x'+num.toString(16).toUpperCase()+')';
  }
  function _tlROpts(opts){
    if(!opts)return '?';
    var n=parseInt(opts,16);
    var parts=[];
    if(n&0x01)parts.push('Multicast');
    if(n&0x08)parts.push('Many-to-One');
    if(n&0x10)parts.push('DestExt');
    if(n&0x20)parts.push('OrigExt');
    if(n&0x40)parts.push('RespExt');
    return parts.length>0?parts.join(', ') : '0x'+opts;
  }
  function _tlPath(title, from, to){
    var fromStr=(typeof from==='string'&&from)?'0x'+parseInt(from,16).toString(16).toUpperCase().padStart(4,'0'):from;
    var toStr=(typeof to==='string'&&to)?'0x'+parseInt(to,16).toString(16).toUpperCase().padStart(4,'0'):to;
    if(!fromStr||!toStr||fromStr==='0x0000'&&toStr==='0x0000')return'';
    var h='<div class="path-block">';
    h+='<div class="path-title">'+title+' Path</div>';
    h+='<div class="path-code">';
    h+=fromStr+' <span class="path-arrow">→</span> '+toStr;
    h+='</div></div>';
    return h;
  }

  // On Enter key in inputs, trigger search
  document.getElementById('tl-pan').addEventListener('keydown',function(e){if(e.key==='Enter'){tlPage=1;search()}});
  document.getElementById('tl-node').addEventListener('keydown',function(e){if(e.key==='Enter'){tlPage=1;search()}});

  // Clear time button — reset to capture start/end
  document.getElementById('tl-tclear').addEventListener('click',function(){
    if(tlCaptureStart&&tlCaptureEnd){
      var csd=new Date(tlCaptureStart*1000);var ced=new Date(tlCaptureEnd*1000);
      document.getElementById('tl-h0').value=csd.getUTCHours();document.getElementById('tl-m0').value=csd.getUTCMinutes();document.getElementById('tl-s0').value=csd.getUTCSeconds();
      document.getElementById('tl-h1').value=ced.getUTCHours();document.getElementById('tl-m1').value=ced.getUTCMinutes();document.getElementById('tl-s1').value=ced.getUTCSeconds();
    } else {
      document.getElementById('tl-h0').value='00';document.getElementById('tl-m0').value='00';document.getElementById('tl-s0').value='00';
      document.getElementById('tl-h1').value='00';document.getElementById('tl-m1').value='00';document.getElementById('tl-s1').value='00';
    }
  });

  // Search button
  document.getElementById('tshow').addEventListener('click',function(){tlPage=1;search()});
  // Pagination
  document.getElementById('tl-pp').addEventListener('click',function(){if(tlPage>1){tlPage--;search()}});
  document.getElementById('tl-pn').addEventListener('click',function(){tlPage++;search()});
  document.getElementById('tl-pgo').addEventListener('click',function(){var v=parseInt(document.getElementById('tl-pj').value);if(v>0){tlPage=v;search()}});
  document.getElementById('tl-ps').addEventListener('change',function(){tlLimit=parseInt(this.value);tlPage=1;search()});

  // Fetch capture time range for display + set default clock-time dropdowns
  A.get('/api/import/status').then(function(st){
    if(st.ts_start){tlCaptureStart=st.ts_start;tlCaptureEnd=st.ts_end;
      var capStartD=new Date(tlCaptureStart*1000);
      var capEndD=new Date(tlCaptureEnd*1000);
      var dur=tlCaptureEnd-tlCaptureStart;
      var durStr='';if(dur<60)durStr=dur.toFixed(0)+'秒';else if(dur<3600)durStr=(dur/60).toFixed(1)+'分钟';else durStr=(dur/3600).toFixed(1)+'小时';
      document.getElementById('tl-capture-info').textContent='抓包: '+tlFmtTs(tlCaptureStart)+' ~ '+tlFmtTs(tlCaptureEnd)+' ('+durStr+')';
      var capH=capStartD.getUTCHours();var capM=capStartD.getUTCMinutes();var capS=capStartD.getUTCSeconds();
      var endH=capEndD.getUTCHours();var endM=capEndD.getUTCMinutes();var endS=capEndD.getUTCSeconds();
      // 联动时间窗口同步 (延迟到此回调: tlCaptureStart 已就绪, tlToTs 可转换字符串格式)
      var t0n=tlToTs(S.topoT0), t1n=tlToTs(S.topoT1);
      if(t0n!=null){var d0n=new Date(t0n*1000);S.tlTs0H=String(d0n.getUTCHours());S.tlTs0M=String(d0n.getUTCMinutes());S.tlTs0S=String(d0n.getUTCSeconds());S.tlHasSearched=true;}
      if(t1n!=null){var d1n=new Date(t1n*1000);S.tlTs1H=String(d1n.getUTCHours());S.tlTs1M=String(d1n.getUTCMinutes());S.tlTs1S=String(d1n.getUTCSeconds());S.tlHasSearched=true;}
      // Detect if saved time values are invalid (from old offset semantics):
      // if saved start clock is more than 1h before capture start or after capture end, reset
      var savedSec0=parseInt(S.tlTs0H||'0')*3600+parseInt(S.tlTs0M||'0')*60+parseInt(S.tlTs0S||'0');
      var capSec=capH*3600+capM*60+capS;
      var endSec=endH*3600+endM*60+endS;
      // ⚠️ 修复 (U5): isNaN 兜底 (旧坏值 "NaN" 不会被区间比较捕获) + 拓扑跳转清空时间窗口时重置为抓包全范围
      var jumpedTopo=(S.topoPan&&S.topoT0==null&&S.topoT1==null);
      var needReset=!S.tlHasSearched||isNaN(savedSec0)||savedSec0<capSec-3600||savedSec0>endSec+3600||jumpedTopo;
      if(needReset){
        // Reset to capture range
        document.getElementById('tl-h0').value=capH;document.getElementById('tl-m0').value=capM;document.getElementById('tl-s0').value=capS;
        document.getElementById('tl-h1').value=endH;document.getElementById('tl-m1').value=endM;document.getElementById('tl-s1').value=endS;
        S.tlTs0H=String(capH);S.tlTs0M=String(capM);S.tlTs0S=String(capS);
        S.tlTs1H=String(endH);S.tlTs1M=String(endM);S.tlTs1S=String(endS);
      }
      // Auto-search after dropdowns are correct
      if(S.topoPan || S.tlHasSearched){
        tlPage=1; setTimeout(function(){search()},50);
      }
    }
  });
  // U5: 类型下拉页面加载即填充 (不依赖点查看; search() 内保留兜底)
  tlFillTypes();
});
