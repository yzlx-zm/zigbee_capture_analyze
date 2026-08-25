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
  // U16-2: 未解密包默认隐藏 (开关在过滤行; 仅首次进入时默认开, 不覆盖用户选择)
  if(typeof S.tlHideUndec==='undefined') S.tlHideUndec=true;
  // Override PAN if jumped from topology
  if(S.topoPan){S.tlPan=S.topoPan; S.tlHasSearched=true;}
  // Override node filter if jumped from topology
  // ⚠️ 修复 (U5): 此前 topoAddr 未同步 → 拓扑点击节点跳转后节点框为空, 看到的是全 PAN 的包
  if(S.topoAddr){S.tlNode=S.topoAddr; S.tlHasSearched=true;}
  // topoT0/T1 时间窗口同步延迟到 import/status 回调 (需 tlCaptureStart 做字符串→时间戳转换;
  // 契约: 数字时间戳 (拓扑滑块) 或 "HH:MM:SS" 字符串 (时间线保存), 读侧兼容两者)

  // Build H/M/S dropdown helpers
  // ⚠️ 修复 (08-13 审核): 加空选项 — 此前无 selected 时浏览器默认选中 0 →
  // 时间过滤恒为 00:00:00~00:00:00 → 初始点查看直接空结果 (实锤 total=0)
  function hmssel(id,val,opts){var h='<select id="'+id+'" class="mono hm-sel"><option value="">-</option>';for(var i=0;i<opts.length;i++){h+='<option value="'+opts[i]+'"'+(String(opts[i])===String(val)?' selected':'')+'>'+String(opts[i]).padStart(2,'0')+'</option>';}h+='</select>';return h;}
  var hourOpts=[];for(var hi=0;hi<24;hi++)hourOpts.push(hi);
  var minSecOpts=[];for(var mi=0;mi<60;mi++)minSecOpts.push(mi);

  document.getElementById('mc').innerHTML='<div class="card"><h3>📊 报文</h3>'
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
    // U16-2 未解密开关 (默认勾选 = 隐藏未解密帧; 切换后自动重查)
    +'<label class="t-10" title="勾选后隐藏未解密帧 (切换自动重查)"><input type="checkbox" id="tl-hide-undec"'+(S.tlHideUndec?' checked':'')+'> 🔒 未解密</label>'
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
    // U16-4 (2026-08-25): 安全/状态两列 → 路径列 (安全信息详情面板已有, 列表不占列)
    // U16-5 (2026-08-25): 加 APS Ctr 列 (分析消息回复情况)
    +'<th>帧号</th><th>时间</th><th>摘要</th><th>路径</th><th>NWK Src</th><th>NWK Dst</th><th>APS Ctr</th>'
    +'</tr></thead><tbody id="tltb"><tr><td colspan="7" class="tl-empty-cell">请输入过滤条件后点击「查看」</td></tr></tbody></table>'
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
  var tlPendingJump=null;  // 待定位帧 (APS Ack 配对跳转; search 完成后消费)

  // ⚠️ 时区修复 (08-13 用户反馈: 时间线与实际抓包差 8 小时):
  // 曾用 toISOString() = UTC; 抓包/导入页为本地时间 (+8) → 统一本地时区
  function tlFmtTs(ts){var d=new Date(ts*1000);
    return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')+':'+d.getSeconds().toString().padStart(2,'0');}

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
    // 时区修复 (08-13): 输入为本地时间 → 本地 Date 构建 epoch (曾 Date.UTC 偏 8h)
    return new Date(d.getFullYear(),d.getMonth(),d.getDate(),h,m,s).getTime()/1000;
  }

  function tlGetTimeFilter(){
    // 空选项 (value="") 表示不限时间 — 任一字段为空则整体不参与过滤
    // (08-13 审核修复: 曾恒产生 00:00:00 导致初始空结果)
    var h0=document.getElementById('tl-h0').value;
    var m0=document.getElementById('tl-m0').value;
    var s0=document.getElementById('tl-s0').value;
    var h1=document.getElementById('tl-h1').value;
    var m1=document.getElementById('tl-m1').value;
    var s1=document.getElementById('tl-s1').value;
    var ts0=(h0!==''&&m0!==''&&s0!=='')
      ? String(h0).padStart(2,'0')+':'+String(m0).padStart(2,'0')+':'+String(s0).padStart(2,'0') : '';
    var ts1=(h1!==''&&m1!==''&&s1!=='')
      ? String(h1).padStart(2,'0')+':'+String(m1).padStart(2,'0')+':'+String(s1).padStart(2,'0') : '';
    return {ts0:ts0, ts1:ts1};
  }

  function tlSaveFilter(){
    S.tlPan=document.getElementById('tl-pan').value.trim();
    S.tlNode=document.getElementById('tl-node').value.trim();
    S.tlTs0H=document.getElementById('tl-h0').value; S.tlTs0M=document.getElementById('tl-m0').value; S.tlTs0S=document.getElementById('tl-s0').value;
    S.tlTs1H=document.getElementById('tl-h1').value; S.tlTs1M=document.getElementById('tl-m1').value; S.tlTs1S=document.getElementById('tl-s1').value;
    S.tlType=document.getElementById('tl-type').value;
    S.tlHideUndec=document.getElementById('tl-hide-undec').checked;
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

  // U5 后续: 从 DOM 构建查询参数 (search 与跳转定位复用)
  function tlQueryParams(limit,offset){
    var q='limit='+limit+'&offset='+offset;
    var panVal=document.getElementById('tl-pan').value.trim();
    var nodeVal=document.getElementById('tl-node').value.trim();
    if(panVal.match(/^0x/i))panVal=panVal.slice(2);
    if(nodeVal.match(/^0x/i))nodeVal=nodeVal.slice(2);
    var tf=tlGetTimeFilter();
    var typeVal=document.getElementById('tl-type').value;
    if(panVal)q+='&pan='+panVal;
    if(nodeVal)q+='&addr='+nodeVal;
    if(tf.ts0)q+='&time_start='+encodeURIComponent(tf.ts0);
    if(tf.ts1)q+='&time_end='+encodeURIComponent(tf.ts1);
    if(typeVal)q+='&pkt_type='+encodeURIComponent(typeVal);
    // U16-2: 未解密开关勾选 → 后端隐藏未解密帧
    if(document.getElementById('tl-hide-undec').checked)q+='&hide_undecrypted=1';
    return q;
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
    var params=tlQueryParams(tlLimit,(tlPage-1)*tlLimit);
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
        // U16-3 摘要列 (2026-08-25): 类型列改后端 summary 简述 (如 "ZCL On/Off C→S 0x0006" /
        // "Leave rejoin"), 长文本截断 hover 全显; 事件徽章 (U5) 保留在摘要后
        // U16-6 层级着色 (2026-08-25): 摘要文字+底色按 layer (ZCL绿/APS紫/NWK蓝/MAC DataReq红/其他灰)
        var lyCls='tl-ly-other';
        if(p.layer==='zcl')lyCls='tl-ly-zcl';
        else if(p.layer==='aps')lyCls='tl-ly-aps';
        else if(p.layer==='nwk')lyCls='tl-ly-nwk';
        else if(p.layer==='mac_dreq')lyCls='tl-ly-macdreq';
        else if(p.layer==='mac')lyCls='tl-ly-mac';
        var typeDisp=p.summary
          ? '<span class="tl-summary '+lyCls+'" title="'+p.summary+'">'+p.summary+'</span>'
          : p.pkt_type;
        // 08-25 用户反馈: ✅ (已解密) 图标在摘要列无上下文且无信息量 → 移除;
        // 🔒 仅对「有 NWK 安全但解密失败」的帧显示 — 明文 MAC 帧 (poll/Beacon/Ack)
        // decrypted=False 但无需解密, 不标锁 (08-25 全量化后自查修正); 📡 NWK 命令标记
        var decIcon='';
        if(isNwkCmdRow){
          decIcon='<span class="ic-nwk" title="NWK命令">📡</span>';
        }else if(!p.decrypted&&p.nwk_security){
          decIcon='<span class="ic-enc" title="NWK 安全未解密">🔒</span>';
        }
        // U16-4 路径列 (完整路径): 起点→中继→终点 (0x0000→0x1885→0xF67F), 无中继 → —
        // (08-25 用户反馈: 只显示中继 "→0x1885" 不直观 → 完整路径一行自洽)
        // U16-4b: path_relays = 下行 source route 优先, 上行帧用 RR 证据补路径 (后端已合并)
        var pathStr='—';
        var pathRelays=p.path_relays||p.nwk_relays;
        if(pathRelays&&pathRelays.length){
          var pathNodes=[];
          if(typeof p.nwk_src==='number')pathNodes.push('0x'+p.nwk_src.toString(16).toUpperCase().padStart(4,'0'));
          for(var ri=0;ri<pathRelays.length;ri++)pathNodes.push('0x'+pathRelays[ri].toString(16).toUpperCase().padStart(4,'0'));
          if(typeof p.nwk_dst==='number')pathNodes.push('0x'+p.nwk_dst.toString(16).toUpperCase().padStart(4,'0'));
          pathStr='<span class="tl-path" title="路径: '+pathNodes.join(' → ')+'">'+pathNodes.join('→')+'</span>';
        }
        // U16-4: decIcon (✅/🔒/📡) 原在状态列, 随列删除移到摘要列前
        // U16-5: APS Ctr 列 (请求/ack 帧 counter 肉眼对应)
        var apsCtr=typeof p.aps_counter==='number'?String(p.aps_counter):'—';
        h+='<tr data-pid="'+p.id+'" class="tl-row"><td>'+(p.packet_id!=null?p.packet_id:'-')+'</td><td>'+ts+'</td><td>'+decIcon+typeDisp+evBadge+'</td><td>'+pathStr+'</td><td>'+ns+'</td><td>'+nd+'</td><td>'+apsCtr+'</td></tr>';}
      document.getElementById('tltb').innerHTML=h||'<tr><td colspan="7" class="tl-empty-row">无匹配数据'+(ctx?' — 条件: '+ctx:'')+'<br><span class="t-10">提示: 尝试放宽过滤条件（清空节点或 PAN 再查）</span></td></tr>';
      // Click-to-select handler
      document.querySelectorAll('#tltb tr.tl-row').forEach(function(tr){
        tr.addEventListener('click',function(){
          document.querySelectorAll('#tltb tr.tl-row').forEach(function(r){r.classList.remove('hl')});
          this.classList.add('hl');
          var pid=parseInt(this.dataset.pid);
          tlShowDetail(pid);
        });
      });
      // U16-4 路径展开/收起 (08-25 用户反馈: 路径过长处理): 点击行内展开全路径, 再点收起
      document.querySelectorAll('#tltb .tl-path').forEach(function(sp){
        sp.addEventListener('click',function(e){
          e.stopPropagation();  // 不触发行点击详情
          this.classList.toggle('expanded');
        });
      });
      updPgr();
      // 跳转定位 (U5 后续: APS Ack 配对): search 完成后消费 tlPendingJump
      if(tlPendingJump!=null){
        var jtr=document.querySelector('#tltb tr.tl-row[data-pid="'+tlPendingJump+'"]');
        if(jtr){ tlHighlightRow(jtr); }
        else { document.getElementById('tl-stat').textContent='⚠️ 帧 #'+tlPendingJump+' 不在数据中'; }
        tlPendingJump=null;
      }
    }).catch(function(e){document.getElementById('tl-stat').textContent='加载失败';});
  }

  // 高亮定位行 (滚动可见 + .hl + 加载详情)
  function tlHighlightRow(tr){
    document.querySelectorAll('#tltb tr.tl-row').forEach(function(r){r.classList.remove('hl')});
    tr.classList.add('hl');
    tr.scrollIntoView({block:'center',behavior:'smooth'});
    tlShowDetail(parseInt(tr.dataset.pid));
  }

  // U16-1 字段点选过滤 (2026-08-25): 详情字段值 (PAN/短地址) → 填入过滤框 + 自动查看
  // ⚠️ 修复 (08-25 CDP 复现): fill 语义值 'pan'/'node' 需映射到过滤框元素 id ('tl-pan'/'tl-node')
  function tlFillAndSearch(target, val){
    var ids={pan:'tl-pan', node:'tl-node'};
    var el=document.getElementById(ids[target]);
    if(!el)return;
    var v=String(val||'').trim().replace(/^0x/i,'').replace(/[^0-9a-fA-F]/g,'');
    if(!v)return;
    el.value='0x'+v.toUpperCase().padStart(4,'0');
    tlPage=1; search();
  }

  // APS Ack 配对跳转 (U5 后续): 本页有 → 直接定位 (过滤完全保持);
  // 过滤内其他页 → 翻页定位 (过滤保持); 过滤外 → 清除过滤重查定位
  function tlJumpToFrame(peerId){
    var tr=document.querySelector('#tltb tr.tl-row[data-pid="'+peerId+'"]');
    if(tr){ tlHighlightRow(tr); return; }
    var step=500;
    function tryPage(off){
      A.get('/api/packets?'+tlQueryParams(step,off)).then(function(d){
        if(!d||!d.packets)return;
        var hitIdx=-1;
        for(var i=0;i<d.packets.length;i++){if(d.packets[i].id===peerId){hitIdx=off+i;break;}}
        if(hitIdx>=0){
          tlPage=Math.floor(hitIdx/tlLimit)+1;
          tlPendingJump=peerId;
          search();
        }else if(d.total>off+step){
          tryPage(off+step);
        }else{
          tlClearFiltersForJump(peerId);
        }
      }).catch(function(){ tlClearFiltersForJump(peerId); });
    }
    tryPage(0);
  }

  // 目标帧不在当前过滤内 → 清除过滤定位 (时间重置为抓包全范围, 与 ✕ 按钮一致)
  function tlClearFiltersForJump(peerId){
    document.getElementById('tl-pan').value='';
    document.getElementById('tl-node').value='';
    document.getElementById('tl-type').value='';
    // U16-2: 目标帧可能是未解密帧 → 清过滤时同步取消未解密隐藏, 保证定位能找到
    document.getElementById('tl-hide-undec').checked=false;
    S.tlHideUndec=false;
    if(tlCaptureStart&&tlCaptureEnd){
      var csd=new Date(tlCaptureStart*1000);var ced=new Date(tlCaptureEnd*1000);
      document.getElementById('tl-h0').value=csd.getHours();document.getElementById('tl-m0').value=csd.getMinutes();document.getElementById('tl-s0').value=csd.getSeconds();
      document.getElementById('tl-h1').value=ced.getHours();document.getElementById('tl-m1').value=ced.getMinutes();document.getElementById('tl-s1').value=ced.getSeconds();
    }
    document.getElementById('tl-stat').textContent='🔍 帧 #'+peerId+' 不在当前过滤内, 已清除过滤定位';
    tlPage=1; tlPendingJump=peerId; search();
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
      // APS Ack 配对 (2026-08-06: 字段级 counter 匹配)
      if(d.aps_ack_pair){
        var pk=d.aps_ack_pair;
        html+='<div class="ack-pair" style="margin:6px 0;padding:4px 8px;border-left:3px solid #16a34a;background:#f0fdf4;font-size:11px">'
          +(pk.kind==='ack_to'?'✅ '+pk.text:'📩 '+pk.text)
          +' <span class="text-dim">(APS Ack 配对'+(pk.kind==='ack_to'?', </span><a class="ack-jump" href="javascript:void(0)" data-peer="'+pk.peer_id+'">点击帧 #'+pk.peer_id+' 查看原帧</a><span class="text-dim">)':'<span class="text-dim">)')
          +'</span></div>';
      }
      // U16-7a 事务链 (2026-08-25): 同事务响应帧 (仅同 ZCL tsn 铁证; 展示折叠 前5+展开)
      if(d.transaction&&d.transaction.responses&&d.transaction.responses.length){
        var respArr=d.transaction.responses;
        var trLinks=[];
        for(var ti=0;ti<respArr.length;ti++){
          var rf=respArr[ti];
          var dirTxt=rf.zcl_direction==='Server→Client'?'S→C':(rf.zcl_direction==='Client→Server'?'C→S':'');
          var name=rf.zcl_cmd_name||rf.pkt_type;
          trLinks.push('<a class="ack-jump" href="javascript:void(0)" data-peer="'+rf.id+'" title="跳转响应帧">#'
            +rf.packet_id+' '+name+' '+dirTxt+'</a>');
        }
        var trHtml='<div class="ack-pair" style="margin:6px 0;padding:4px 8px;border-left:3px solid #7c3aed;background:#f5f3ff;font-size:11px">'
          +'📩 同事务响应 ('+respArr.length+'): '+trLinks.slice(0,5).join(' · ');
        if(trLinks.length>5){
          trHtml+=' <a class="tr-toggle" href="javascript:void(0)" data-count="'+trLinks.length+'">展开全部</a>'
            +'<span class="tr-hidden" style="display:none"> · '+trLinks.slice(5).join(' · ')+'</span>';
        }
        trHtml+='</div>';
        html+=trHtml;
      }
      var layers=d.layers;
      // MAC layer (wpan)
      if(layers.wpan){
        var wpanF=[['Frame Type', _tlMacType(layers.wpan)],
          ['Seq#', _tlF(layers.wpan,'wpan.seq_no')],
          // U16-1 字段点选 (2026-08-25): PAN/地址值可点 → 填入过滤框 + 自动查看
          ['Dest PAN', _tlA(layers.wpan,'wpan.dst_pan'), '', 'pan'],
          ['Dest Addr', _tlA(layers.wpan,'wpan.dst16'), '', 'node'],
          ['Src Addr', _tlA(layers.wpan,'wpan.src16'), '', 'node'],
          ['FCS OK', layers.wpan['wpan.fcs_ok']==='1'?'Yes':'No']];
        // MAC 命令帧/Beacon 明细 (cubx fallback; L1-1/L1-2 入网流程)
        if(layers.wpan['wpan.cmd_id']!=null){
          var mcid=parseInt(layers.wpan['wpan.cmd_id']);
          wpanF.push(['MAC Cmd', _tlMacCmdName(mcid), '入网流程命令']);
        }
        if(layers.wpan['wpan.src64'])wpanF.push(['Src EUI64', layers.wpan['wpan.src64']]);
        if(layers.wpan['wpan.dst64'])wpanF.push(['Dest EUI64', layers.wpan['wpan.dst64']]);
        // U16 (2026-08-25): ACK 帧 frame pending 位 (协调器有数据待取, poll 流程信号)
        if(layers.wpan['wpan.ack_pending']!=null){
          wpanF.push(['Ack Pending', layers.wpan['wpan.ack_pending']==='1'?'有数据待取':'无', 'ACK 帧 FCF frame pending 位']);
        }
        if(layers.wpan['wpan.beacon_pan']!=null){
          wpanF.push(['Beacon PAN', _tlA(layers.wpan,'wpan.beacon_pan'), '', 'pan']);
          wpanF.push(['Permit Join', layers.wpan['wpan.beacon_permit']==='1'?'允许':'不允许']);
        }
        html+=_tlLayer('MAC', '#d97706', wpanF);
      }
      // NWK layer
      if(layers.zbee_nwk){
        var nwk=layers.zbee_nwk;
        var nwkFields=[];
        // Check for named NWK command
        var cmdName='';
        for(var ck in nwk){if(ck.startsWith('Command Frame:')){cmdName=ck.split(':')[1].trim();break;}}
        if(cmdName){nwkFields.push(['Command', cmdName]);}
        // U16-1 字段点选: NWK 源/目标可点 → 填入节点过滤框
        nwkFields.push(['Dest', _tlA2(nwk,'zbee_nwk.dst'), '', 'node']);
        nwkFields.push(['Src', _tlA2(nwk,'zbee_nwk.src'), '', 'node']);
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
          var apsF=[['Cluster', _tlCluster(aps)],
            ['Profile', _tlA(aps,'zbee_aps.profile')],
            ['Src EP', aps['zbee_aps.src']||'?'],
            ['Dest EP', aps['zbee_aps.dst']||'?'],
            ['Counter', aps['zbee_aps.counter']||'?']];
          // APS 命令帧明细 (cubx fallback; L1-3 密钥流程 / L1-4 踢人)
          if(aps['zbee_aps.cmd_id']!=null){
            var acid=parseInt(aps['zbee_aps.cmd_id'],16);
            apsF.push(['Command', aps['zbee_aps.cmd_name']||_tlApsCmdName(acid)]);
            if(aps['zbee_aps.cmd_key_type']!=null){
              var kt=parseInt(aps['zbee_aps.cmd_key_type'],16);
              apsF.push(['Key Type', kt===1?'Network Key':kt===4?'TC Link Key':'0x'+kt.toString(16)]);
            }
            if(aps['zbee_aps.cmd_remove_target'])apsF.push(['Remove Target', aps['zbee_aps.cmd_remove_target'], '被移除设备 EUI64 (踢人)']);
            if(aps['zbee_aps.cmd_update_status']!=null){
              var us=parseInt(aps['zbee_aps.cmd_update_status']);
              apsF.push(['Update Status', us===1?'UNSECURED_JOIN':us===2?'DEVICE_LEFT':'0x'+us.toString(16)]);
            }
          }
          // APS 可靠性字段 (2026-08-06: L3-1 配对基础)
          if(aps['zbee_aps.ack_req']!=null){
            apsF.push(['Ack Req', aps['zbee_aps.ack_req']==='1'?'要求确认':'未要求', aps['zbee_aps.ack_req']==='1'?'该帧要求 APS 确认, 应收到 ack':'无 ack 期望']);
          }
          if(aps['zbee_aps.ack_format']!=null){
            apsF.push(['Ack Format', aps['zbee_aps.ack_format']==='0'?'沿用原帧 Counter':'新 Counter', 'ack 帧 FCF bit4']);
          }
          html+=_tlLayer('APS', '#16a34a', apsF);
        }else if(!d.decrypted){
          html+=_tlLayer('APS', '#16a34a', [['Status','🔒 Encrypted']]);
        }
      }

      // ZDP layer (profile 0x0000) — always check, independent of NWK type
      if(layers.zbee_zdp){
        var zdp=layers.zbee_zdp;
        var zdpLabels={nwk_addr:'NWK Addr',seqno:'Seq#',status:'Status',manufacturer:'Mfr Code',max_buffer:'Max Buf',max_incoming_transfer:'Max In',max_outgoing_transfer:'Max Out',type:'Node Type',complex:'Complex Desc',user:'User Desc',frag_support:'Frag Support','freq.868mhz':'868 MHz','freq.900mhz':'900 MHz','freq.2400mhz':'2.4 GHz','freq.eu_sub_ghz':'EU Sub-GHz',server:'Server Mask',dcf:'Desc Capability',cinfo:'Complex Info',aps_flags:'APS Flags',
          zdp_cmd_nwk_addr:'NWK Addr',zdp_cmd_eui64:'IEEE Addr',zdp_cmd_capability:'能力',zdp_cmd_start_index:'Start Index',zdp_cmd_req_type:'Req Type',zdp_cmd_num_assoc:'Assoc 数'};
        var zdpDesc={nwk_addr:'本节点16位网络地址',seqno:'ZDP事务序列号',status:'0x00=成功 其他=失败',manufacturer:'制造商ID 0x1141=SiliconLabs','Max Buf':'最大ASDU缓冲(bytes)','Max In':'最大接收传输大小(bytes)','Max Out':'最大发送传输大小(bytes)',type:'0=协调器 1=路由器 2=终端',complex:'是否有复杂描述符',user:'是否有用户描述符',frag_support:'是否支持APS分段传输','868 MHz':'868MHz频段(欧洲)','900 MHz':'900MHz频段(美洲)','2.4 GHz':'2.4GHz频段(全球常用)','EU Sub-GHz':'欧洲Sub-GHz频段','Server Mask':'系统服务能力(Trust/Bind/Discovery等)','Desc Capability':'扩展描述符能力标志',cinfo:'MAC能力(FFD/主电源/空闲接收/安全)',aps_flags:'APS层标志位',
          zdp_cmd_nwk_addr:'ZDP 命令目标短地址',zdp_cmd_eui64:'ZDP 命令携带的 IEEE 长地址',zdp_cmd_capability:'设备能力位 (类型/电源/RxOnWhenIdle)',zdp_cmd_start_index:'关联设备起始索引',zdp_cmd_req_type:'应答模式 (0=单设备)',zdp_cmd_num_assoc:'关联设备数量'};
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
          var zclFields=[
            ['Command', zclCmd],
            ['Direction', dir],
            ['Seq#', zcl['zbee_zcl.cmd.tsn']||'?'],
          ];
          // U9 改进 (08-13): Read Attr Rsp 属性记录展示 (厂商/型号等, cubx 路径)
          var attrs=d.zcl_attr_reads||[];
          if(attrs.length){
            zclFields.push(['属性记录', attrs.length+' 项']);
            for(var ai=0;ai<attrs.length;ai++){var ar=attrs[ai];
              var nm=ar.attr_id===0x0004?'manufacturer_name':ar.attr_id===0x0005?'model_id':'';
              var valTxt=ar.status===0?(ar.value!=null?String(ar.value):'(无值)'):'status 0x'+ar.status.toString(16);
              zclFields.push(['attr 0x'+ar.attr_id.toString(16).toUpperCase().padStart(4,'0')+(nm?' '+nm:''), valTxt]);
            }
          }
          // U15 (08-24): ZCL 命令载荷字段级解析 (标准簇/涂鸦 0xEF00/字节兜底, 与节点页同源)
          var pp=d.zcl_payload_parsed;
          if(pp&&pp.fields&&pp.fields.length){
            zclFields.push(['载荷解析', '('+(pp.parser||'?')+') '+pp.fields.length+' 字段']);
            for(var pi=0;pi<pp.fields.length;pi++){var pf=pp.fields[pi];
              zclFields.push([pf.field, pf.value, pf.note||'']);
            }
            if(pp.hex)zclFields.push(['载荷 hex', pp.hex]);
          }
          html+=_tlLayer('ZCL', '#7c3aed', zclFields);
        }else if(!d.decrypted&&!isNwkCmd){
          var isZdp=aps&&_tlIsZdp(aps);
          if(!isZdp){
            html+=_tlLayer('ZCL', '#7c3aed', [['Status','🔒 Encrypted (需要 Network Key)']]);
          }
        }
      }
      panel.innerHTML=html;
          // APS Ack 配对跳转 (U5 后续): 点击帧号链接 → 定位时间线对应行
      panel.querySelectorAll('.ack-jump').forEach(function(a){
        a.addEventListener('click',function(e){
          e.preventDefault();
          tlJumpToFrame(parseInt(this.dataset.peer));
        });
      });
      // U16-1 字段点选过滤 (2026-08-25): 详情字段值 → 填入过滤框 + 自动查看
      panel.querySelectorAll('.tl-click-val').forEach(function(a){
        a.addEventListener('click',function(e){
          e.preventDefault();
          tlFillAndSearch(this.dataset.fill, this.dataset.val);
        });
      });
      // U16-7a 事务链折叠 (2026-08-25): 响应帧 >5 时 展开/收起
      panel.querySelectorAll('.tr-toggle').forEach(function(a){
        a.addEventListener('click',function(e){
          e.preventDefault();
          var hid=this.nextElementSibling;
          var n=parseInt(this.dataset.count);
          if(hid.style.display==='none'){hid.style.display='';this.textContent='收起';}
          else{hid.style.display='none';this.textContent='展开全部';}
        });
      });
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
      var val=fields[i][1];
      var fill=fields[i][3];  // U16-1: 'pan'|'node' → 值渲染为可点, 点击填入过滤框
      if(fill&&String(val).match(/^0x[0-9a-fA-F]+$/)){
        val='<a class="tl-click-val" href="javascript:void(0)" data-fill="'+fill+'" data-val="'+val+'" title="点击填入'+(fill==='pan'?'PAN':'节点')+'过滤框">'+val+'</a>';
      }
      h+='<div class="field-row"><span class="k" title="'+desc+'">'+fields[i][0]+'</span><span class="v">'+val+'</span></div>';
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
  // MAC 命令名 (scapy dot15d4.py:327 源码级映射, zigbee 协议; 08-25 修正: 旧表 3/4/5/8 错位)
  function _tlMacCmdName(id){
    var names={1:'AssocReq (入网请求)',2:'AssocResp (入网应答)',3:'DisassocNotify (解除关联)',4:'DataReq (轮询)',5:'PANIDConflict',6:'OrphanNotify',7:'BeaconReq (信标请求)',8:'CoordRealign',9:'GTSReq'};
    return names[id]||'0x'+id.toString(16);
  }
  // APS 命令名 (Zigbee spec; L1-3 密钥流程)
  function _tlApsCmdName(id){
    var names={5:'TransportKey (密钥分发)',6:'UpdateDevice',7:'RemoveDevice (踢人)',8:'RequestKey',9:'SwitchKey',15:'VerifyKey',16:'ConfirmKey',17:'Tunnel'};
    return (names[id]||'0x'+id.toString(16))+' (0x'+id.toString(16).toUpperCase().padStart(2,'0')+')';
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
    // ⚠️ 兜底只保留全局命令表 (ZCL spec 2.3.1 frame type=0), 不得混入簇/OTA 命令:
    // 此前 0x00/0x01/0x02 重复键被 OTA 表覆盖 (0x00 → 'OTA: Image Notify' 等),
    // 且无 cluster/frame_type 维度无法正确命名 — 簇命令名由后端 zcl_defs
    // (zcl_cmd_name, frame_type 区分) 提供, 兜底仅为后端无名字时的原始 ID 展示
    var names={0x00:'Read Attributes',0x01:'Read Attributes Response',0x02:'Write Attributes',0x03:'Write Attributes Undivided',0x04:'Write Attributes Response',0x05:'Write Attributes No Response',0x06:'Configure Reporting',0x07:'Configure Reporting Response',0x08:'Read Reporting Configuration',0x09:'Read Reporting Configuration Response',0x0A:'Report Attributes',0x0B:'Default Response',0x0C:'Discover Attributes',0x0D:'Discover Attributes Response'};
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
      document.getElementById('tl-h0').value=csd.getHours();document.getElementById('tl-m0').value=csd.getMinutes();document.getElementById('tl-s0').value=csd.getSeconds();
      document.getElementById('tl-h1').value=ced.getHours();document.getElementById('tl-m1').value=ced.getMinutes();document.getElementById('tl-s1').value=ced.getSeconds();
    } else {
      document.getElementById('tl-h0').value='00';document.getElementById('tl-m0').value='00';document.getElementById('tl-s0').value='00';
      document.getElementById('tl-h1').value='00';document.getElementById('tl-m1').value='00';document.getElementById('tl-s1').value='00';
    }
  });

  // Search button
  document.getElementById('tshow').addEventListener('click',function(){tlPage=1;search()});
  // U16-2 未解密开关: 切换即重查 (无需点查看)
  document.getElementById('tl-hide-undec').addEventListener('change',function(){tlPage=1;search()});
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
      var capH=capStartD.getHours();var capM=capStartD.getMinutes();var capS=capStartD.getSeconds();
      var endH=capEndD.getHours();var endM=capEndD.getMinutes();var endS=capEndD.getSeconds();
      // 联动时间窗口同步 (延迟到此回调: tlCaptureStart 已就绪, tlToTs 可转换字符串格式)
      var t0n=tlToTs(S.topoT0), t1n=tlToTs(S.topoT1);
      if(t0n!=null){var d0n=new Date(t0n*1000);S.tlTs0H=String(d0n.getHours());S.tlTs0M=String(d0n.getMinutes());S.tlTs0S=String(d0n.getSeconds());S.tlHasSearched=true;}
      if(t1n!=null){var d1n=new Date(t1n*1000);S.tlTs1H=String(d1n.getHours());S.tlTs1M=String(d1n.getMinutes());S.tlTs1S=String(d1n.getSeconds());S.tlHasSearched=true;}
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
      // U16 (2026-08-25 用户反馈): 进页面默认展示全部包 (无过滤全量), 不再等用户点查看;
      // topoPan/tlHasSearched 跳转联动仍在 (值会从 DOM 读, 此处只需无条件触发一次)
      tlPage=1; setTimeout(function(){search()},50);
    }
  });
  // U5: 类型下拉页面加载即填充 (不依赖点查看; search() 内保留兜底)
  tlFillTypes();
});
