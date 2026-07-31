// topo.js — 拓扑页面模块 (ES module)
// reg('topo',...) 回调体 + 全部拓扑渲染/布局/事件逻辑
import { S, A, sb, fmtTs } from './state.js';

// ── 模块私有变量 (不可被其他模块 import) ──
let cy = null, topoData = null, hlNode = null;
let tCenter = null, tSliderTO = null, curLayout = 0;
let tsStart = 0, tsEnd = 0;

  document.getElementById('mc').style.padding='0';
  var h='<div style="display:flex;height:calc(100vh - 44px)">'
    // ── 左侧边栏 ──
    +'<div id="tside" style="width:340px;flex-shrink:0;overflow-y:auto;padding:8px;background:#fff;border-right:1px solid #e2e8f0;transition:width 0.3s">'
    +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
    +'<button class="btn btn-o" id="tside-tog" title="折叠侧边栏" style="font-size:10px;padding:2px 6px">◀ 折叠</button>'
    +'<span id="tinfo" style="font-size:11px;color:#64748b"></span></div>'
    +'<div class="card" style="padding:8px"><h3 style="font-size:12px;margin-bottom:4px">📊 拓扑统计</h3><div id="tstat"></div></div>'
    +'<div class="card" style="padding:8px"><h3 style="font-size:12px;margin-bottom:4px">📡 PAN 列表</h3><div id="pan-list" style="max-height:200px;overflow-y:auto"></div></div>'
    +'<div class="card" style="padding:8px"><h3 style="font-size:12px;margin-bottom:4px">📋 不对称链路</h3><div id="tasym"></div></div>'
    +'</div>'
    // ── 主区域 ──
    +'<div style="flex:1;display:flex;flex-direction:column;overflow:hidden">'
    // 工具栏
    +'<div style="display:flex;gap:6px;padding:8px;background:#fff;border-bottom:1px solid #e2e8f0;flex-wrap:wrap;align-items:center">'
    +'<input id="tpan" placeholder="PAN (16B6)" style="width:100px;font-family:monospace;font-size:11px">'
    +'<input id="taddr" placeholder="地址" style="width:90px;font-family:monospace;font-size:11px">'
    +'<button class="btn btn-p" id="tgo" style="font-size:10px">🔍 筛选</button><button class="btn btn-o" id="trst" style="font-size:10px">重置</button>'
    +'<span style="color:#cbd5e1">|</span>'
    +'<button class="btn btn-o" id="tfit" style="font-size:10px">⊞ 适应</button>'
    +'<button class="btn btn-o" id="tlay" style="font-size:10px" title="切换布局">📐 层次</button>'
    +'<button class="btn btn-o" id="tshow-all" style="font-size:10px" title="显示/隐藏静默节点">👁 静默节点</button>'
    +'<button class="btn btn-o" id="thl-clear" style="font-size:10px" title="清除高亮">🔆 清除高亮</button>'
    +'<span style="color:#cbd5e1">|</span>'
    +'<span style="font-size:10px">图例:</span>'
    +'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f59e0b"></span><span style="font-size:10px">Coord</span>'
    +'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#3b82f6"></span><span style="font-size:10px">Router</span>'
    +'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#16a34a"></span><span style="font-size:10px">EndDev</span>'
    +'<span style="display:inline-block;width:12px;height:12px;background:#94a3b8"></span><span style="font-size:10px">Unknown</span>'
    +'<span style="margin-left:4px;font-size:10px">边:绿&gt;80% 黄&gt;50% 红 | 紫色虚线=路由路径 | 灰色点=静默节点</span>'
    +'</div>'
    // ── 时间控制条: 单滑块(窗口中心) + 窗口大小 ──
    +'<div style="display:flex;gap:8px;padding:4px 8px;background:#f8fafc;border-bottom:1px solid #e2e8f0;align-items:center;flex-wrap:wrap">'
    +'<span style="font-size:10px;color:#64748b;white-space:nowrap">⏱ 窗口:</span>'
    +'<select id="twin-size" style="font-size:10px;padding:1px 4px">'
    +'<option value="30">30s</option><option value="60">60s</option><option value="120">120s</option><option value="300">300s</option><option value="9999" selected>全部</option></select>'
    +'<button class="btn btn-o" id="tstep-bwd" style="font-size:10px;padding:1px 6px" title="前移">◀</button>'
    +'<input type="range" id="tsl" min="0" max="1000" value="500" style="flex:1;min-width:140px;height:18px;cursor:pointer" oninput="onTimeSlide()">'
    +'<button class="btn btn-o" id="tstep-fwd" style="font-size:10px;padding:1px 6px" title="后移">▶</button>'
    +'<span id="ttime-label" style="font-size:10px;color:#64748b;white-space:nowrap;min-width:240px">--:--:-- ~ --:--:--</span>'
    +'</div>'
    // Cytoscape 图
    +'<div id="cy-graph" style="flex:1;min-height:360px;background:#fafbfc;position:relative">'
    +'<div id="off-frame" style="position:absolute;border:2px dashed #94a3b8;border-radius:6px;background:rgba(148,163,184,0.06);pointer-events:none;display:none;z-index:2"></div>'
    +'<div id="off-label" style="position:absolute;left:4px;top:50%;transform:translateY(-50%);writing-mode:vertical-rl;font-size:10px;color:#92400e;padding:6px 10px;border:2px solid #f59e0b;border-radius:4px;background:#fffbeb;pointer-events:none;display:none;font-weight:600;z-index:5">📡 仅LS可见</div>'
    +'</div>'
    // 底部面板 (路由路径链 + 层级树)
    +'<div style="border-top:2px solid #e2e8f0;background:#fff;max-height:220px;overflow-y:auto" id="bottom-panels">'
    +'<div style="display:flex;border-bottom:1px solid #e2e8f0">'
    +'<button class="btn bp-tab on" style="border-radius:0;border:none;border-bottom:2px solid #3b82f6;font-size:11px;padding:6px 14px" onclick="togBpTab(\'routes\',this)">🛤️ 路由路径链</button>'
    +'<button class="btn bp-tab" style="border-radius:0;border:none;border-bottom:2px solid transparent;font-size:11px;padding:6px 14px" onclick="togBpTab(\'neighbors\',this)">📡 邻居关系</button>'
    +'<button class="btn bp-tab" style="border-radius:0;border:none;border-bottom:2px solid transparent;font-size:11px;padding:6px 14px" onclick="togBpTab(\'tree\',this)">🌳 层级树</button>'
    +'</div>'
    +'<div id="bp-routes" style="padding:8px"></div>'
    +'<div id="bp-neighbors" style="padding:8px;display:none"></div>'
    +'<div id="bp-tree" style="padding:8px;display:none"><ul class="tree" id="tree-root"></ul></div>'
    +'</div>'
    +'</div></div>';
  document.getElementById('mc').innerHTML=h;

  // ═══ 状态变量 ═══

  // ═══ 数据加载 ═══
  function loadData(panVal, callback, t0, t1){
    var params=[];
    if(panVal) params.push('pan='+panVal);
    if(t0!=null) params.push('time_start='+t0);
    if(t1!=null) params.push('time_end='+t1);
    var url='/api/topology/events'+(params.length?'?'+params.join('&'):'');
    A.get(url).then(function(d){
      topoData=d; S.topo=d;
      try{ if(callback) callback(d); }catch(e){ console.error('renderGraph error:',e); }
      try{ renderSidebar(d); }catch(e){ console.error('renderSidebar error:',e); }
    }).catch(function(e){
      console.error('loadData error:',e);
      document.getElementById('tinfo').textContent='数据加载失败';
    });
  }

  // ═══ 侧边栏渲染 ═══
  function renderSidebar(d){
    if(!d) return;
    var ns=d.nodes||[], es=d.edges||[], rps=d.route_paths||[];
    var probes=d.route_probes||[], failures=d.route_failures||[];
    document.getElementById('tinfo').textContent=ns.length+' 节点 | 主PAN:0x'+(d.main_pan!=null?d.main_pan.toString(16).toUpperCase():'?');
    var nbt=d.neighbor_tables||{};
    var nbDevCount=Object.keys(nbt).length;
    var nbTotal=0; for(var k in nbt){nbTotal+=Object.keys(nbt[k]).length;}
    // 活跃节点统计
    var activeSet={};
    for(var i=0;i<es.length;i++){activeSet[es[i].src]=true; activeSet[es[i].dst]=true;}
    for(var i=0;i<rps.length;i++){
      var rp=rps[i]; activeSet[rp.src]=true; activeSet[rp.dst]=true;
      for(var j=0;j<(rp.relays||[]).length;j++) activeSet[rp.relays[j]]=true;
    }
    var activeCount=Object.keys(activeSet).length;
    document.getElementById('tstat').innerHTML='<div class="stats">'
      +'<span>图节点: <b style=\"color:#16a34a\">'+activeCount+'</b>活跃</span><span style=\"color:#94a3b8\">'+(ns.length-activeCount)+'静默</span>'
      +'<span>图边: <b>'+es.length+'</b>数据流</span>'
      +'<span style=\"color:#7c3aed\">'+rps.length+'路径↑</span>'
      +(probes.length>0?'<span style=\"color:#3b82f6\">'+probes.length+'探测↓</span>':'')
      +(failures.length>0?'<span style=\"color:#ef4444\">'+failures.length+'失败✕</span>':'')
      +'<span>📡 LS邻居:<b>'+nbTotal+'</b></span><span>LS设备:'+nbDevCount+'</span>'
      +'</div>';
    // PAN list
    var pl=d.pan_list||[];
    var ph='<table class="tbl"><tr><th>PAN</th><th>包数</th></tr>';
    for(var i=0;i<pl.length;i++){ph+='<tr class="pan-row" data-pan="'+pl[i].pan+'" style="cursor:pointer"><td>'+pl[i].label+'</td><td>'+pl[i].count+'</td><td><button class="btn btn-o btn-s pan-tl-btn" data-pan="'+pl[i].pan+'" style="font-size:10px">→TL</button></td></tr>';}
    document.getElementById('pan-list').innerHTML=ph+'</table>';
    document.querySelectorAll('.pan-row').forEach(function(r){r.addEventListener('click',function(e){if(e.target.classList.contains('pan-tl-btn'))return;var pv=parseInt(this.dataset.pan);var ps=pv.toString(16).toUpperCase();document.getElementById('tpan').value=ps;S.topoPan=ps;loadData(ps,function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){} })})});
    document.querySelectorAll('.pan-tl-btn').forEach(function(b){b.addEventListener('click',function(e){e.stopPropagation();S.topoPan=parseInt(this.dataset.pan).toString(16).toUpperCase();S.topoT0=null;S.topoT1=null;location.hash='tl'})});
    // Asymmetric links — 只显示WEAK和ASYMM级别, 点击可高亮图中节点
    var al=d.asymmetric_links||[];
    var alFiltered=[]; for(var i=0;i<al.length;i++){if(al[i].level!=='OK') alFiltered.push(al[i]);}
    var ah='';
    var alTitle='📋 不对称链路 ('+alFiltered.length+'条, 不含OK)';
    document.querySelector('#tasym').parentElement.querySelector('h3').textContent=alTitle;
    if(alFiltered.length===0){ah='<p style="font-size:10px;color:#16a34a">✅ 未发现不对称链路</p>';}
    else{
      ah='<table class="tbl"><tr><th>A</th><th>B</th><th>A→B</th><th>B→A</th><th>差</th></tr>';
      var maxShow=Math.min(alFiltered.length,15);
      for(var i=0;i<maxShow;i++){
        var a=alFiltered[i];var lc=a.level==='WEAK'?'#d97706':'#dc2626';
        ah+='<tr class="asym-row" data-a="'+a.a+'" data-b="'+a.b+'" style="cursor:pointer">'
          +'<td>0x'+a.a.toString(16).toUpperCase().padStart(4,'0')+'</td><td>0x'+a.b.toString(16).toUpperCase().padStart(4,'0')+'</td>'
          +'<td>'+a.a_to_b_cost+'</td><td>'+a.b_to_a_cost+'</td><td style="color:'+lc+';font-weight:600">'+a.diff+'</td></tr>';
      }
      if(alFiltered.length>maxShow) ah+='<tr><td colspan="5" style="color:#94a3b8;text-align:center">...还有'+(alFiltered.length-maxShow)+'条</td></tr>';
      ah+='</table>';
    }
    document.getElementById('tasym').innerHTML=ah;
    // 点击不对称链路行 → 图中高亮双节点
    document.querySelectorAll('.asym-row').forEach(function(r){
      r.addEventListener('click',function(){
        var a=parseInt(this.dataset.a); var b=parseInt(this.dataset.b);
        if(!cy) return;
        clearHighlight();
        var na=cy.getElementById(''+a); var nb=cy.getElementById(''+b);
        if(na){na.addClass('highlight'); na.connectedEdges().forEach(function(e){e.addClass('highlight');});}
        if(nb){nb.addClass('highlight'); nb.connectedEdges().forEach(function(e){e.addClass('highlight');});}
        hlNode=null; // 不使用单节点高亮
      });
    });
  }

  // ═══ Cytoscape 力导向图 (路径着色 + 流量背景) ═══

  function renderGraph(d){
    if(!d) return;
    var nbt=d.neighbor_tables||{};
    var ns=d.nodes||[];
    if(ns.length===0){if(cy){cy.destroy();cy=null;}document.getElementById('tinfo').textContent='该PAN无节点数据';return;}
    if(ns.length<10){curLayout=1;} // 小PAN默认力导, 固定列无意义
    var es=d.edges||[];
    var rps=d.route_paths||[];

    // ── 路径节点集合 ──
    var pathNodes={};
    for(var i=0;i<rps.length;i++){
      var rp=rps[i];
      var full=[rp.src].concat(rp.relays||[]).concat([rp.dst]);
      for(var j=0;j<full.length;j++){
        if(!pathNodes[full[j]]) pathNodes[full[j]]=[];
        pathNodes[full[j]].push(i);
      }
    }

    // ── 节点 ──
    var cyNodes=[];
    var hasPaths=rps.length>0;  // 无 Route Record 路径时全部按"在路径上"渲染, 否则 offpath 会让整图隐形
    for(var i=0;i<ns.length;i++){
      var n=ns[i]; var aid=n.aid;
      var dt=n.device_type||'unknown';
      var onPath=(!hasPaths)||!!pathNodes[aid]||aid===0;  // 无路径全可见; 协调器永远可见
      cyNodes.push({
        data:{id:''+aid, label:'0x'+aid.toString(16).toUpperCase().padStart(4,'0'), aid:aid, device_type:dt, seen:n.seen, on_path:onPath},
        classes:(onPath?dt+' onpath':'offpath')
      });
    }

    // ── 边: 数据流量 → 灰色细线背景 ──
    var cyEdges=[];
    var trafficSeen={};
    for(var i=0;i<es.length;i++){
      var e=es[i];
      var ek=Math.min(e.src,e.dst)+'-'+Math.max(e.src,e.dst);
      if(trafficSeen[ek]) continue;
      trafficSeen[ek]=true;
      cyEdges.push({
        data:{id:'t-'+ek, source:''+e.src, target:''+e.dst, count:e.count||0, edge_type:'traffic'},
        classes:'traffic-bg'
      });
    }

    // ── 边: Route Record 路径 (跳过不存在的节点, 避免PAN切换空图) ──
    var cyNodeIds={}; for(var ni=0;ni<cyNodes.length;ni++)cyNodeIds[cyNodes[ni].data.id]=true;
    for(var i=0;i<rps.length;i++){
      var rp=rps[i];
      var full=[rp.src].concat(rp.relays||[]).concat([rp.dst]);
      for(var j=0;j<full.length-1;j++){
        var sid=''+full[j]; var tid=''+full[j+1];
        if(!cyNodeIds[sid]||!cyNodeIds[tid]) continue; // 跨PAN节点跳过
        var hasFilter=S.topoT0!=null||S.topoT1!=null;
        var solid=hasFilter?(rp.active!==false):rp.is_current;
        cyEdges.push({
          data:{id:'rp-'+i+'-'+j, source:sid, target:tid, path_idx:i, hop:j, path_str:rp.path_str, is_current:rp.is_current, active:rp.active, edge_type:'route'},
          classes:'route-path path-c'+ci+(solid?'':' historical')
        });
      }
    }

    // 保存用户缩放状态
    var userZoom=null, userPan=null;
    if(cy){userZoom=cy.zoom();userPan=cy.pan();}

    // ── 初始化 Cytoscape ──
    if(cy){cy.destroy();}
    cy=cytoscape({
      container: document.getElementById('cy-graph'),
      elements: cyNodes.concat(cyEdges),
      style: [
        // 节点基础
        {selector:'node', style:{'background-color':'#3b82f6','label':'data(label)','font-size':'9px','color':'#1e293b','text-valign':'bottom','text-halign':'center','text-margin-y':4,'border-width':1,'border-color':'#fff','width':28,'height':28}},
        {selector:'node.coordinator', style:{'background-color':'#f59e0b','border-color':'#d97706','border-width':2,'font-weight':'bold','width':50,'height':50,'text-margin-y':6}},
        {selector:'node.router', style:{'background-color':'#3b82f6'}},
        {selector:'node.end_device', style:{'background-color':'#16a34a','shape':'triangle','width':18,'height':18}},
        // 路径节点: 紫框
        {selector:'node.onpath', style:{'border-width':3,'border-color':'#7c3aed'}},
        // 路径外节点: 半透明缩小
        {selector:'node.offpath', style:{'background-color':'#e2e8f0','opacity':0.3,'width':10,'height':10,'font-size':'7px','color':'#94a3b8','text-opacity':0}},
        // 高亮/淡出
        {selector:'node.highlight', style:{'border-color':'#ef4444','border-width':3,'shadow-color':'#ef4444','shadow-blur':8,'shadow-opacity':0.5}},
        {selector:'node.faded', style:{'opacity':0.12}},
        // 边默认 → 灰色背景
        {selector:'edge', style:{'width':0.8,'line-color':'#d1d5db','target-arrow-color':'#d1d5db','target-arrow-shape':'triangle','arrow-scale':0.5,'curve-style':'bezier','opacity':0.25}},
        // 路径边: 粗箭头 (当前路由)
        {selector:'edge.route-path', style:{'width':3.5,'target-arrow-shape':'triangle','arrow-scale':1.3,'curve-style':'bezier','opacity':0.9}},
        // 历史路径: 虚线 + 半透明
        {selector:'edge.route-path.historical', style:{'line-style':'dashed','opacity':0.4,'width':2}},
        // 路径颜色 class (8色)
        {selector:'edge.path-c0', style:{'line-color':'#e74c3c','target-arrow-color':'#e74c3c'}},
        {selector:'edge.path-c1', style:{'line-color':'#3498db','target-arrow-color':'#3498db'}},
        {selector:'edge.path-c2', style:{'line-color':'#2ecc71','target-arrow-color':'#2ecc71'}},
        {selector:'edge.path-c3', style:{'line-color':'#e67e22','target-arrow-color':'#e67e22'}},
        {selector:'edge.path-c4', style:{'line-color':'#9b59b6','target-arrow-color':'#9b59b6'}},
        {selector:'edge.path-c5', style:{'line-color':'#1abc9c','target-arrow-color':'#1abc9c'}},
        {selector:'edge.path-c6', style:{'line-color':'#f39c12','target-arrow-color':'#f39c12'}},
        {selector:'edge.path-c7', style:{'line-color':'#e91e63','target-arrow-color':'#e91e63'}},
        // 高亮/淡出
        {selector:'edge.highlight', style:{'opacity':1,'width':5}},
        {selector:'edge.faded', style:{'opacity':0.04}},
      ],
      wheelSensitivity:0.3,
    });

    // ── 交互事件 ──
    var tooltip=document.createElement('div');tooltip.id='cy-tt';tooltip.style.cssText='position:absolute;display:none;background:#1e293b;color:#fff;padding:6px 10px;border-radius:6px;font-size:11px;pointer-events:none;z-index:999;max-width:280px;white-space:pre-line';
    document.getElementById('cy-graph').appendChild(tooltip);

    cy.on('mouseover','node',function(e){var n=e.target;var d=n.data();var nbtEntry=nbt[d.aid];var nbCount=nbtEntry?Object.keys(nbtEntry).length:0;tooltip.innerHTML='<b>'+d.label+'</b>\n类型:'+(d.device_type==='coordinator'?'协调器':d.device_type==='router'?'路由器':d.device_type==='end_device'?'终端设备':'未知')+'\n'+(d.on_path?'在路径上':'不在路径上')+'\nLS邻居:'+nbCount;tooltip.style.display='block';updateTooltipPos(e);});
    cy.on('mouseout','node',function(){tooltip.style.display='none';});
    cy.on('mouseover','edge',function(e){var ed=e.target;var d=ed.data();if(d.edge_type==='traffic'){tooltip.innerHTML='<b>数据流</b>\n0x'+d.source.toString(16).toUpperCase()+' ↔ 0x'+d.target.toString(16).toUpperCase()+'\n'+d.count+' 包';}else{var hf=S.topoT0!=null||S.topoT1!=null;var st=hf?(d.active!==false?'● 活跃':'◌ 窗口外'):(d.is_current?'● 当前':'◌ 历史');tooltip.innerHTML='<b>路径 #'+(d.path_idx+1)+' 第'+(d.hop+1)+'跳</b>\n'+st+'\n'+d.path_str;};tooltip.style.display='block';updateTooltipPos(e);});
    cy.on('mouseout','edge',function(){tooltip.style.display='none';});

    function updateTooltipPos(e){var r=e.renderedPosition||e.position;var gb=document.getElementById('cy-graph').getBoundingClientRect();tooltip.style.left=(gb.left+r.x+12)+'px';tooltip.style.top=(gb.top+r.y-10)+'px';}

    // Click → 跳转时间线
    cy.on('tap','node',function(e){var n=e.target;var aid=n.data('aid');S.topoAddr='0x'+aid.toString(16).toUpperCase().padStart(4,'0');S.topoT0=null;S.topoT1=null;location.hash='tl';});

    // 双击 → 高亮/淡出
    cy.on('dbltap','node',function(e){var n=e.target;var aid=n.data('aid');if(hlNode===aid){clearHighlight();return;}hlNode=aid;highlightNode(aid);});

    // 默认固定列 — 深度+布局+fit一体化
    (function(){
      var nd={};nd[0]=0;var chg=true;
      while(chg){chg=false;cy.edges().forEach(function(e){if(e.data('edge_type')!=='route')return;var s=parseInt(e.data('source')),t=parseInt(e.data('target'));if(nd[s]!=null){var nd2=nd[s]+1;if(nd[t]==null||nd2<nd[t]){nd[t]=nd2;chg=true;}}if(nd[t]!=null){var nd2=nd[t]+1;if(nd[s]==null||nd2<nd[s]){nd[s]=nd2;chg=true;}}});}
      var pathMax=0;for(var k in nd)if(nd[k]>pathMax)pathMax=nd[k];
      var topoNbt2=S.topo?S.topo.neighbor_tables:null;
      if(topoNbt2&&topoNbt2[0]){for(var nbStr2 in topoNbt2[0]){var nba2=parseInt(nbStr2);if(nd[nba2]==null)nd[nba2]=1;}}
      var chg2=true;while(chg2){chg2=false;for(var a2 in topoNbt2||{}){var ai2=parseInt(a2);var ndv=nd[ai2];if(ndv==null||ndv>=99||ndv>=pathMax)continue;var nbs2=topoNbt2[ai2]||{};for(var nb2 in nbs2){var bi2=parseInt(nb2);var ndv2=nd[bi2];if(ndv2==null||ndv2==99){if(ndv+1<=pathMax){nd[bi2]=ndv+1;chg2=true;}}}}}
      cy.nodes().forEach(function(n){var aid=n.data('aid');if(nd[aid]==null)nd[aid]=99;n.style('display','element');var d=nd[aid];if(d==null)d=99;var isOnPath2=n.data('on_path')===true;if(!isOnPath2){n.style('background-color','#f59e0b');n.style('border-color','#d97706');n.style('opacity','0.9');n.connectedEdges().forEach(function(e){if(e.data('edge_type')==='traffic'){e.style('line-color','#f59e0b');e.style('target-arrow-color','#f59e0b');e.style('opacity','0.6');}});}else{n.style('opacity','1');}});
      var cols={};cy.nodes().forEach(function(n){var d=nd[n.data('aid')];if(d==null)d=99;if(!cols[d])cols[d]=[];cols[d].push(n);});
      var pos={},offAll=[];cy.nodes().forEach(function(n){var d=nd[n.data('aid')];if(d==null)d=99;if(d<99&&!n.data('on_path'))offAll.push(n);});
      var offCols=Math.max(3,Math.ceil(offAll.length/12));if(offCols<1)offCols=1;var offPerCol=Math.ceil(offAll.length/offCols),offStartX=-(offCols+2)*200;
      for(var c=0;c<offCols;c++){var chunk=offAll.slice(c*offPerCol,(c+1)*offPerCol),ch=Math.max(300,chunk.length*36);chunk.forEach(function(n,i){pos[n.id()]={x:offStartX+c*200,y:-(ch/2)+(ch/(chunk.length+1))*(i+1)};});}
      pos['0']={x:-200,y:0};
      var rColX=0;for(var d2=1;d2<=pathMax;d2++){var nds3=cols[d2];if(!nds3)continue;nds3=nds3.filter(function(n){return nd[n.data('aid')]!=null&&nd[n.data('aid')]<99;});var pNodes=nds3.filter(function(n){return n.data('on_path');});if(pNodes.length===0){rColX+=200;continue;}var ch3=Math.max(300,pNodes.length*48);pNodes.forEach(function(n,i){pos[n.id()]={x:rColX,y:-(ch3/2)+(ch3/(pNodes.length+1))*(i+1)};});rColX+=200;}
      var d99=cols[99]||[];for(var oi=0;oi<d99.length;oi++){pos[d99[oi].id()]={x:rColX+100+(oi%15)*28,y:-200+Math.floor(oi/15)*24};}
      cy.layout({name:'preset',positions:pos,fit:true,padding:40}).run();
      if(userZoom!=null){cy.zoom(userZoom);cy.pan(userPan);}  // 恢复用户缩放
      document.getElementById('off-label').style.display='block';
      document.getElementById('tlay').textContent='▦ 固定列';
    })();
  }

  // ═══ 布局引擎 ═══
  function runLayout(){
    if(!cy) return;
    // BFS深度: Route Record路径
    var nodeDepth={}; nodeDepth[0]=0;
    var chg=true;while(chg){chg=false;
      cy.edges().forEach(function(e){if(e.data('edge_type')!=='route')return;
        var s=parseInt(e.data('source'));var t=parseInt(e.data('target'));
        if(nodeDepth[s]!=null){var nd=nodeDepth[s]+1;if(nodeDepth[t]==null||nd<nodeDepth[t]){nodeDepth[t]=nd;chg=true;}}
        if(nodeDepth[t]!=null){var nd=nodeDepth[t]+1;if(nodeDepth[s]==null||nd<nodeDepth[s]){nodeDepth[s]=nd;chg=true;}}
      });
    }
    var pathMax=0; for(var k in nodeDepth)if(nodeDepth[k]>pathMax)pathMax=nodeDepth[k];

    // LS邻居表补充off-path深度(最多pathMax列, 放左侧)
    var topoNbt=S.topo?S.topo.neighbor_tables:null;
    if(topoNbt&&topoNbt[0]){for(var nbStr in topoNbt[0]){var nba=parseInt(nbStr);if(nodeDepth[nba]==null)nodeDepth[nba]=1;}}
    var chg=true;while(chg){chg=false;
      for(var a in topoNbt||{}){var ai=parseInt(a);var nd=nodeDepth[ai];if(nd==null||nd>=99||nd>=pathMax)continue;
        var nbs=topoNbt[ai]||{};
        for(var nb in nbs){var bi=parseInt(nb);var nd2=nodeDepth[bi];if(nd2==null||nd2==99){if(nd+1<=pathMax){nodeDepth[bi]=nd+1;chg=true;}}}
      }
    }
    cy.nodes().forEach(function(n){var aid=n.data('aid');if(nodeDepth[aid]==null)nodeDepth[aid]=99;});

    if(curLayout===0){  // fixed column
      // off-path节点换琥珀色+连线换可见色
      cy.nodes().forEach(function(n){n.style('display','element');var d=nd[n.data('aid')];if(d==null)d=99;
        var isOnPath=n.data('on_path')===true; // 严格true才算路径节点
        if(!isOnPath){n.style('background-color','#f59e0b');n.style('border-color','#d97706');n.style('opacity','0.9');
          n.connectedEdges().forEach(function(e){if(e.data('edge_type')==='traffic'){e.style('line-color','#f59e0b');e.style('target-arrow-color','#f59e0b');e.style('opacity','0.6');}});
        }
        else{n.style('opacity','1');}
      });

      var cols={}; cy.nodes().forEach(function(n){var d=nodeDepth[n.data('aid')];if(d==null)d=99;if(!cols[d])cols[d]=[];cols[d].push(n);});
      var posMap={};
      // left: off-path均分多列(~12节点/列)
      var offAll=[]; cy.nodes().forEach(function(n){var d=nodeDepth[n.data('aid')];if(d==null)d=99;if(d<99&&!n.data('on_path'))offAll.push(n);});
      var offCols=Math.max(3,Math.ceil(offAll.length/12)); if(offCols<1)offCols=1;
      var offPerCol=Math.ceil(offAll.length/offCols);
      var offStartX=-(offCols+2)*200;
      for(var c=0;c<offCols;c++){var chunk=offAll.slice(c*offPerCol,(c+1)*offPerCol);var ch=Math.max(300,chunk.length*36);chunk.forEach(function(n,i){posMap[n.id()]={x:offStartX+c*200,y:-(ch/2)+(ch/(chunk.length+1))*(i+1)};});}
      // coordinator
      posMap['0']={x:-200,y:0};
      // right: path columns (depth 1..pathMax)
      var rColX=0;
      for(var d=1;d<=pathMax;d++){var nds2=cols[d];if(!nds2)continue;nds2=nds2.filter(function(n){return nodeDepth[n.data('aid')]!=null&&nodeDepth[n.data('aid')]<99;});var pNodes=nds2.filter(function(n){return n.data('on_path');});if(pNodes.length===0){rColX+=200;continue;}var ch2=Math.max(300,pNodes.length*48);pNodes.forEach(function(n,i){var y=-(ch2/2)+(ch2/(pNodes.length+1))*(i+1);posMap[n.id()]={x:rColX,y:y};});rColX+=200;}
      // depth>=99 compact grid far right
      var d99=cols[99]||[]; for(var oi=0;oi<d99.length;oi++){posMap[d99[oi].id()]={x:rColX+100+(oi%15)*28,y:-200+Math.floor(oi/15)*24};}
      cy.layout({name:'preset',positions:posMap,fit:true,padding:40}).run();
      if(userZoom!=null){cy.zoom(userZoom);cy.pan(userPan);}
      document.getElementById('off-label').style.display='block';
      document.getElementById('tlay').textContent='▦ 固定列';
    }else{
      document.getElementById('off-label').style.display='none';
      cy.nodes().forEach(function(n){n.style('display','element');n.style('opacity','1');n.style('background-color','');n.style('border-color','');n.style('width','');n.style('height','');n.style('text-opacity','');n.style('font-size','');n.removeClass('offpath');});
      cy.layout({name:'cose',animate:true,animationDuration:800,nodeRepulsion:function(n){return n.degree()>3?12000:6000},idealEdgeLength:function(e){return 80},gravity:20,numIter:2000}).run();
      document.getElementById('tlay').textContent='🔄 力导';
    }
  }

  function highlightNode(aid){
    cy.elements().forEach(function(el){el.removeClass('highlight').removeClass('faded');});
    var target=cy.getElementById(''+aid);
    if(!target) return;
    target.addClass('highlight');
    // 找到该节点所在的所有路径, 高亮这些路径上的全部边
    var pathEdges=cy.edges('[edge_type="route"]').filter(function(e){
      var d=e.data();
      // 该节点的邻域边 (1-hop), 或同一条路径上所有的边
      return d.source===''+aid || d.target===''+aid;
    });
    var pathEdgeIds={};
    pathEdges.forEach(function(e){pathEdgeIds[e.id()]=true;});
    // 如果该节点有路径边, 把同路径的其他跳也加入
    cy.edges('[edge_type="route"]').forEach(function(e){
      if(pathEdgeIds[e.id()]) return;
      var d=e.data();
      // 检查该边是否和已高亮的路径边共享同一path_idx
      for(var pid in pathEdgeIds){
        var pe=cy.getElementById(pid);
        if(pe&&pe.data('path_idx')===d.path_idx){
          pathEdgeIds[e.id()]=true;
          break;
        }
      }
    });
    // 收集涉及的节点
    var keepNodes={}; keepNodes[''+aid]=true;
    for(var eid in pathEdgeIds){
      var pe=cy.getElementById(eid);
      if(pe){ keepNodes[pe.data('source')]=true; keepNodes[pe.data('target')]=true; }
    }
    // 应用
    var keepEdges={};
    for(var eid in pathEdgeIds) keepEdges[eid]=true;
    cy.nodes().forEach(function(n){if(!keepNodes[n.id()]) n.addClass('faded');else n.addClass('highlight');});
    cy.edges().forEach(function(e){if(!keepEdges[e.id()]) e.addClass('faded');else e.addClass('highlight');});
  }

  function clearHighlight(){
    hlNode=null;
    cy.elements().forEach(function(el){el.removeClass('highlight').removeClass('faded');});
  }

  // ═══ 路由路径链 ═══
  function renderRoutePaths(d){
    var panel=document.getElementById('bp-routes');
    var paths=d.route_paths||[];
    var probes=d.route_probes||[];
    var failures=d.route_failures||[];

    if(paths.length===0 && probes.length===0 && failures.length===0){
      panel.innerHTML='<p style=\"color:#94a3b8;font-size:11px;text-align:center;padding:12px\">未发现路由事件 (该网络无 Route Record/Request/Status 帧)</p>';return;
    }

    // 样式
    var sep='<div style=\"border-top:1px solid #e2e8f0;margin:8px 0\"></div>';
    var h='';

    // ── 上行路径 (Route Record) ──
    if(paths.length>0){
      var srcPaths={}; for(var i=0;i<paths.length;i++){var s=paths[i].src;if(!srcPaths[s])srcPaths[s]=[];srcPaths[s].push(paths[i]);}
      var changed=0; for(var k in srcPaths){if(srcPaths[k].length>1)changed++;}
      h+='<div style=\"font-size:11px;color:#64748b;margin-bottom:4px\">'
        +'<span style=\"color:#7c3aed;font-weight:600\">↑ 上行路径 (Route Record)</span> '
        +paths.length+'条 | '+Object.keys(srcPaths).length+'个设备'
        +(changed>0?' | <b style=\"color:#d97706\">'+changed+'个发生过路由变更</b>':'')
        +'</div>'
        +'<div style=\"font-size:10px;color:#94a3b8;margin-bottom:6px\">●实线=当前路由 · ◌虚线=历史路由</div>';
      var maxShow=Math.min(paths.length,20);
      for(var i=0;i<maxShow;i++){
        var p=paths[i];
        var icon=p.is_current?'●':'◌';
        var color=p.is_current?'#7c3aed':'#94a3b8';
        var style=p.is_current?'font-weight:600':'';
        var ts0=new Date(p.first_ts*1000).toISOString().substr(11,8);
        var ts1=new Date(p.last_ts*1000).toISOString().substr(11,8);
        var dur=p.first_ts===p.last_ts?'':(' ~ '+ts1);
        h+='<div style=\"display:flex;align-items:center;gap:4px;padding:3px 0;border-bottom:1px solid #f1f5f9;font-family:monospace;font-size:11px;'+style+'\" title=\"首帧:'+ts0+' 末帧:'+ts1+' 共'+p.frame_count+'帧\">'
          +'<span style=\"color:'+color+';min-width:14px;text-align:center\">'+icon+'</span>'
          +'<span style=\"color:'+color+'\"'+'>'+p.path_str+'</span>'
          +'<span style=\"color:#94a3b8;font-size:9px;white-space:nowrap\">'+p.hop_count+'跳 ×'+p.frame_count+'帧</span>'
          +'<span style=\"color:#94a3b8;font-size:9px;white-space:nowrap\">'+ts0+dur+'</span>'
          +(p.is_current?'<span style=\"color:#16a34a;font-size:9px;font-weight:600\">当前</span>':'<span style=\"color:#94a3b8;font-size:9px\">历史</span>')
          +'</div>';
      }
      if(paths.length>maxShow) h+='<p style=\"color:#94a3b8;font-size:10px;text-align:center\">...还有'+(paths.length-maxShow)+'条路径</p>';
    }

    // ── 下行探测 (Route Request) ──
    if(probes.length>0){
      h+=sep+'<div style=\"font-size:11px;color:#64748b;margin-bottom:6px\">'
        +'<span style=\"color:#3b82f6;font-weight:600\">↓ 下行探测 (Route Request)</span> '
        +probes.length+'对</div>';
      var maxP=Math.min(probes.length,10);
      for(var i=0;i<maxP;i++){
        var pp=probes[i];
        var ts0=new Date(pp.first_ts*1000).toISOString().substr(11,8);
        h+='<div style=\"display:flex;align-items:center;gap:4px;padding:2px 0;font-family:monospace;font-size:11px\" title=\"radius='+pp.radius+' 共'+pp.count+'次\">'
          +'<span style=\"color:#3b82f6;min-width:14px;text-align:center\">→</span>'
          +'<span style=\"color:#3b82f6\">'+pp.path_str+'</span>'
          +'<span style=\"color:#94a3b8;font-size:9px\">×'+pp.count+'次</span>'
          +'<span style=\"color:#94a3b8;font-size:9px\">'+ts0+'</span>'
          +'</div>';
      }
    }

    // ── 下行失败 (Network Status) ──
    if(failures.length>0){
      h+=sep+'<div style=\"font-size:11px;color:#64748b;margin-bottom:6px\">'
        +'<span style=\"color:#ef4444;font-weight:600\">✕ 下行失败 (Network Status)</span> '
        +failures.length+'处</div>';
      for(var i=0;i<failures.length;i++){
        var f=failures[i];
        var ts=new Date(f.timestamp*1000).toISOString().substr(11,8);
        h+='<div style=\"display:flex;align-items:center;gap:4px;padding:2px 0;font-family:monospace;font-size:11px\">'
          +'<span style=\"color:#ef4444;min-width:14px;text-align:center\">✕</span>'
          +'<span style=\"color:#ef4444\">'+f.path_str+'</span>'
          +'<span style=\"color:#ef4444;font-size:9px\">'+f.status_name+'</span>'
          +'<span style=\"color:#94a3b8;font-size:9px\">'+ts+'</span>'
          +'</div>';
      }
    }

    panel.innerHTML=h;
  }

  // ═══ 层级树 (保留, 移到底部面板) ═══
  function renderTree(){
    var d=topoData;if(!d) return;
    var ns=d.nodes||[], es=d.edges||[];
    var treeCoord=d.coord;
    var nmap={};for(var i=0;i<ns.length;i++){nmap[ns[i].aid]=ns[i]}
    var edgeMap={};for(var i=0;i<es.length;i++){edgeMap[es[i].src+'-'+es[i].dst]=es[i];edgeMap[es[i].dst+'-'+es[i].src]=es[i]}

    function renderNode(aid, ul){
      var n=nmap[aid];if(!n)return;
      var li=document.createElement('li');
      var isRouter=n.children&&n.children.length>0;
      var cls=n.is_coord?'coord':isRouter?'router':n.seen>100?'leaf':'low';
      var kids=n.children||[];
      kids.sort(function(a,b){return (nmap[b]?nmap[b].coord_traffic||0:0)-(nmap[a]?nmap[a].coord_traffic||0:0)});
      if(kids.length>0){
        var tog=document.createElement('span');tog.className='toggle';tog.textContent='▼';
        tog.addEventListener('click',function(e){e.stopPropagation();var p=this.parentElement;p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'▶':'▼'});
        li.appendChild(tog);
      }
      var nd=document.createElement('span');nd.className='node '+cls;
      nd.innerHTML='0x'+n.aid.toString(16).toUpperCase().padStart(4,'0');
      if(isRouter)nd.innerHTML+=' ['+kids.length+']';
      nd.title='seen:'+n.seen+' depth:'+n.depth;
      nd.addEventListener('click',function(){S.topoAddr='0x'+aid.toString(16).toUpperCase().padStart(4,'0');S.topoT0=null;S.topoT1=null;location.hash='tl'});
      li.appendChild(nd);
      if(n.parent!=null){
        var ek=n.parent+'-'+aid;var edge=edgeMap[ek];
        if(edge){
          var el=document.createElement('span');el.className='edge-label';
          el.textContent='← '+edge.count+'pkts';
          li.appendChild(el);
        }
      }
      if(kids.length>0){
        var childUl=document.createElement('ul');
        var MAX=15;var show=kids.slice(0,MAX);
        for(var i=0;i<show.length;i++)renderNode(show[i], childUl);
        if(kids.length>MAX){
          var foldLi=document.createElement('li');
          var foldSpan=document.createElement('span');foldSpan.className='fold';
          foldSpan.textContent='...'+(kids.length-MAX)+' more';
          foldSpan.addEventListener('click',function(e){e.stopPropagation();var pli=this.parentElement;pli.style.display='none';var rest=kids.slice(MAX);for(var i=0;i<rest.length;i++)renderNode(rest[i], childUl);});
          foldLi.appendChild(foldSpan);childUl.appendChild(foldLi);
        }
        li.appendChild(childUl);
      }
      ul.appendChild(li);
    }

    var root=document.getElementById('tree-root');root.innerHTML='';
    if(treeCoord!=null&&nmap[treeCoord]) renderNode(treeCoord, root);
    var orphans=[];for(var i=0;i<ns.length;i++){if(ns[i].parent==null&&ns[i].aid!==treeCoord)orphans.push(ns[i])}
    if(orphans.length>0){
      var oli=document.createElement('li');oli.classList.add('collapsed');
      var otog=document.createElement('span');otog.className='toggle';otog.textContent='▶';
      otog.addEventListener('click',function(e){e.stopPropagation();var p=this.parentElement;p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'▶':'▼'});
      oli.appendChild(otog);
      var ospan=document.createElement('span');ospan.className='node low';ospan.style.fontWeight='bold';ospan.style.background='#fef2f2';ospan.textContent='❓ 未归类节点 ('+orphans.length+')';
      oli.appendChild(ospan);
      var oul=document.createElement('ul');
      for(var i=0;i<Math.min(orphans.length,20);i++) renderNode(orphans[i].aid, oul);
      oli.appendChild(oul);root.appendChild(oli);
    }
  }

  // ═══ 底部面板 Tab 切换 ═══
  window.togBpTab=function(bp,btn){
    document.querySelectorAll('.bp-tab').forEach(function(b){b.classList.remove('on');b.style.borderBottomColor='transparent'});
    if(btn){btn.classList.add('on');btn.style.borderBottomColor='#3b82f6';}
    document.getElementById('bp-routes').style.display=bp==='routes'?'block':'none';
    document.getElementById('bp-neighbors').style.display=bp==='neighbors'?'block':'none';
    document.getElementById('bp-tree').style.display=bp==='tree'?'block':'none';
    if(bp==='neighbors') renderNeighborPanel();
    if(bp==='tree') renderTree();
  };

  // ═══ 邻居关系面板 ═══
  function renderNeighborPanel(){
    var panel=document.getElementById('bp-neighbors');
    var d=S.topo; if(!d){panel.innerHTML='<p style="color:#94a3b8">无拓扑数据</p>';return;}
    var nbt=d.neighbor_tables||{};
    if(Object.keys(nbt).length===0){panel.innerHTML='<p style="color:#94a3b8;text-align:center;padding:12px">无 Link Status 数据</p>';return;}
    // Build device dropdown sorted by neighbor count
    var devList=[]; for(var devStr in nbt){devList.push({aid:parseInt(devStr), count:Object.keys(nbt[devStr]).length});}
    devList.sort(function(a,b){return b.count-a.count;});
    var h='<div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">'
      +'<span style="font-size:11px;font-weight:600">设备:</span>'
      +'<select id="nb-dev-sel" style="font-family:monospace;font-size:11px;max-width:180px" onchange="showNbTable()">'
      +'<option value="">-- 选择设备 ('+devList.length+' 个有LS) --</option>';
    for(var i=0;i<devList.length;i++){
      h+='<option value="'+devList[i].aid+'">0x'+devList[i].aid.toString(16).toUpperCase().padStart(4,'0')+' ('+devList[i].count+' 邻居)</option>';
    }
    h+='</select><span style="font-size:10px;color:#64748b">共 '+devList.length+' 设备有Link Status数据</span></div>';
    h+='<div id="nb-detail" style="font-size:11px;max-height:140px;overflow-y:auto"></div>';
    panel.innerHTML=h;
    // Global function to show neighbor detail
    window.showNbTable=function(){
      var aid=parseInt(document.getElementById('nb-dev-sel').value);
      var detail=document.getElementById('nb-detail');
      if(!aid||!nbt[aid]){detail.innerHTML='';return;}
      var nbs=nbt[aid]; var nbKeys=Object.keys(nbs);
      if(nbKeys.length===0){detail.innerHTML='<p style="color:#94a3b8">该设备无邻居记录</p>';return;}
      var th='<table class="tbl"><tr><th>邻居</th><th>In Cost</th><th>Out Cost</th><th>最后更新</th><th>次数</th></tr>';
      nbKeys.sort(function(a,b){return (nbs[b].out_cost||0)-(nbs[a].out_cost||0);});
      for(var i=0;i<nbKeys.length;i++){
        var nb=nbs[nbKeys[i]]; var addr=parseInt(nbKeys[i]);
        var ic=nb.in_cost||0; var oc=nb.out_cost||0;
        var icColor=ic<=1?'#16a34a':ic<=3?'#d97706':'#dc2626';
        var ocColor=oc<=1?'#16a34a':oc<=3?'#d97706':'#dc2626';
        var ts=new Date((nb.last_seen_ts||0)*1000).toISOString().substr(11,8);
        th+='<tr style="cursor:pointer" onclick="S.topoAddr=\'0x'+addr.toString(16).toUpperCase().padStart(4,'0')+'\';location.hash=\'tl\'">'
          +'<td>0x'+addr.toString(16).toUpperCase().padStart(4,'0')+'</td>'
          +'<td style="color:'+icColor+';font-weight:600">'+ic+'</td>'
          +'<td style="color:'+ocColor+';font-weight:600">'+oc+'</td>'
          +'<td style="font-size:10px;color:#94a3b8">'+ts+'</td>'
          +'<td style="font-size:10px">'+nb.count+'</td></tr>';
      }
      th+='</table>';
      detail.innerHTML=th;
    };
  }

  // ═══ 侧边栏折叠 ═══
  document.getElementById('tside-tog').addEventListener('click',function(){
    var side=document.getElementById('tside');
    if(side.style.width==='0px'){side.style.width='340px';side.style.overflow='';this.textContent='◀ 折叠';}
    else{side.style.width='0px';side.style.overflow='hidden';this.textContent='▶';}
  });

  // ═══ 按钮事件 ═══
  document.getElementById('tgo').addEventListener('click',function(){
    var pv=document.getElementById('tpan').value.trim();S.topoPan=pv||null;
    loadData(pv,function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){}});
  });
  document.getElementById('trst').addEventListener('click',function(){
    document.getElementById('tpan').value='';document.getElementById('taddr').value='';
    S.topoPan=null;S.topoAddr=null;hlNode=null;
    tCenter=null;
    document.getElementById('tsl').value=500;
    updateTimeLabel();
    loadData('',function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){} try{clearHighlight();}catch(e){}});
  });
  document.getElementById('tfit').addEventListener('click',function(){if(cy){cy.zoom(1);cy.pan({x:0,y:0});cy.fit(undefined,30);}});
  document.getElementById('tlay').addEventListener('click',function(){
    curLayout=(curLayout+1)%2; runLayout();
    if(curLayout===1) setTimeout(function(){cy.fit(undefined,30);},900);
  });
  document.getElementById('thl-clear').addEventListener('click',function(){clearHighlight();});

  // ═══ 时间滑块 (单滑块 = 窗口中心) ═══
  function fmtTs(ts){var d=new Date(ts*1000);return d.getUTCHours().toString().padStart(2,'0')+':'+d.getUTCMinutes().toString().padStart(2,'0')+':'+d.getUTCSeconds().toString().padStart(2,'0');}
  function sliderToTs(val){return tsStart+(tsEnd-tsStart)*(val/1000);}
  function tsToSlider(ts){return Math.round((ts-tsStart)/(tsEnd-tsStart)*1000);}

  function getWinSize(){var ws=parseInt(document.getElementById('twin-size').value);if(ws>=9000)return null;return ws;}

  function getTimeWindow(){
    var ws=getWinSize();
    if(ws==null||tCenter==null) return {t0:null,t1:null};  // 全部
    var half=ws/2;
    var t0=Math.max(tsStart,tCenter-half);
    var t1=Math.min(tsEnd,t0+ws);
    if(t1>=tsEnd){t1=tsEnd;t0=Math.max(tsStart,t1-ws);}
    return {t0:t0,t1:t1};
  }

  function updateTimeLabel(){
    var tw=getTimeWindow();
    if(tw.t0==null){document.getElementById('ttime-label').textContent=fmtTs(tsStart)+' ~ '+fmtTs(tsEnd)+' (全部)';return;}
    var dur=tw.t1-tw.t0;
    document.getElementById('ttime-label').textContent=fmtTs(tw.t0)+' ~ '+fmtTs(tw.t1)+' ('+Math.round(dur)+'s)';
  }

  function applyTimeFilter(){
    var tw=getTimeWindow();
    S.topoT0=tw.t0; S.topoT1=tw.t1;  // 存全局状态
    updateTimeLabel();
    clearTimeout(tSliderTO);
    tSliderTO=setTimeout(function(){
      var pan=S.topoPan||'';
      loadData(pan,function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){} if(S.topoAddr&&cy){try{var a=parseInt(S.topoAddr,16);highlightNode(a);}catch(e){}} },tw.t0,tw.t1);
    },300);
  }

  window.onTimeSlide=function(){
    var v=parseInt(document.getElementById('tsl').value);
    tCenter=sliderToTs(v);
    applyTimeFilter();
  };

  function stepWindow(dir){
    var ws=getWinSize();
    if(ws==null) ws=120;
    if(tCenter==null) tCenter=tsStart+ws/2;
    var shift=dir*Math.max(5,ws/4);
    tCenter=Math.max(tsStart+ws/2,Math.min(tsEnd-ws/2,tCenter+shift));
    document.getElementById('tsl').value=tsToSlider(tCenter);
    applyTimeFilter();
    // 边界指示
    document.getElementById('tstep-bwd').disabled=(tCenter<=tsStart+ws/2);
    document.getElementById('tstep-fwd').disabled=(tCenter>=tsEnd-ws/2);
    document.getElementById('tstep-bwd').style.opacity=document.getElementById('tstep-bwd').disabled?'0.3':'';
    document.getElementById('tstep-fwd').style.opacity=document.getElementById('tstep-fwd').disabled?'0.3':'';
  }

  function setWindowFromSize(){
    var ws=getWinSize();
    var sl=document.getElementById('tsl');
    if(ws==null){
      tCenter=null; sl.value=500; sl.disabled=true;
      updateTimeLabel();
      var pan=S.topoPan||'';
      loadData(pan,function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){} if(S.topoAddr&&cy){try{var a=parseInt(S.topoAddr,16);highlightNode(a);}catch(e){}} });
      return;
    }
    sl.disabled=false;
    if(tCenter==null) tCenter=tsStart+ws/2;
    tCenter=Math.max(tsStart+ws/2,Math.min(tsEnd-ws/2,tCenter));
    sl.value=tsToSlider(tCenter);
    applyTimeFilter();
  }

  document.getElementById('tstep-bwd').addEventListener('click',function(){stepWindow(-1);});
  document.getElementById('tstep-fwd').addEventListener('click',function(){stepWindow(1);});
  document.getElementById('twin-size').addEventListener('change',setWindowFromSize);

  // 获取抓包时间范围 + 时间线过滤约束
  var tlT0=null, tlT1=null;
  A.get('/api/import/status').then(function(s){
    tsStart=s.ts_start;tsEnd=s.ts_end;
    // 时间线过滤存在时, 以时间线范围为准
    if(S.topoT0!=null&&S.topoT1!=null){tlT0=S.topoT0;tlT1=S.topoT1;tsStart=S.topoT0;tsEnd=S.topoT1;}
    else if(S.topoT0!=null){tlT0=S.topoT0;tsStart=S.topoT0;}
    updateTimeLabel();
  });

  // ═══ 初始加载 ═══
  var initPan=S.topoPan||'';
  loadData(initPan,function(d){
    try{renderGraph(d);}catch(e){console.error(e);}
    try{renderRoutePaths(d);}catch(e){console.error(e);}
    try{if(S.topoAddr&&cy){var aid=parseInt(S.topoAddr,16);highlightNode(aid);}}catch(e){}
  });
