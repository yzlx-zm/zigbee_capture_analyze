// topo.js — 拓扑页面模块 (ES module)
// reg('topo',...) 回调体 + 全部拓扑渲染/布局/事件逻辑
import { S, A, sb, fmtTs } from './state.js';

// ── 模块私有变量 (不可被其他模块 import) ──
let cy = null, topoData = null, hlNode = null;
let tCenter = null, tSliderTO = null, curLayout = 0;
let tsStart = 0, tsEnd = 0;
let topoNbt = null;   // 当前邻居表 (事件闭包引用, 实例复用时保持最新)
let playTO = null, silentHidden = false;   // 播放定时器 / 静默节点隐藏态 (模块级, 跨页面切换保留)
let dataTotal = 0;    // 导入数据总帧数 (空态引导判断用)
const PATH_COLORS = ['#e74c3c','#3498db','#2ecc71','#e67e22','#9b59b6','#1abc9c','#f39c12','#e91e63'];

reg('topo', function(){
  // 页面重建清理: 旧 cy 实例绑定已移除的容器, 必须销毁; 播放/防抖定时器同步停
  if(cy){cy.destroy();cy=null;}
  if(playTO){clearInterval(playTO);playTO=null;}
  clearTimeout(tSliderTO);
  var h='<div class="page">'
    // ── 左侧边栏 ──
    +'<div id="tside">'
    +'<div class="tside-head">'
    +'<button class="btn btn-o btn-s" id="tside-tog" title="折叠侧边栏">◀ 折叠</button>'
    +'<span id="tinfo"></span></div>'
    +'<div class="card card-tight"><h3>📊 拓扑统计</h3><div id="tstat"></div></div>'
    +'<div class="card card-tight"><h3>📡 PAN 列表</h3><div id="pan-list" class="scroll-y"></div></div>'
    +'<div class="card card-tight"><h3>📋 不对称链路</h3><div id="tasym"></div></div>'
    +'</div>'
    // ── 主区域 ──
    +'<div class="col grow oh">'
    // 工具栏
    +'<div class="toolbar">'
    +'<input id="tpan" placeholder="PAN (16B6)" class="mono w-100 t-11">'
    +'<input id="taddr" placeholder="地址" class="mono w-90 t-11">'
    +'<button class="btn btn-p btn-s" id="tgo">🔍 筛选</button><button class="btn btn-o btn-s" id="trst">重置</button>'
    +'<span class="toolbar-sep">|</span>'
    +'<button class="btn btn-o btn-s" id="tfit">⊞ 适应</button>'
    +'<button class="btn btn-o btn-s" id="tlay" title="切换布局">📐 层次</button>'
    +'<button class="btn btn-o btn-s" id="tshow-all" title="显示/隐藏静默节点">👁 静默节点</button>'
    +'<button class="btn btn-o btn-s" id="thl-clear" title="清除高亮">🔆 清除高亮</button>'
    +'<span class="toolbar-sep">|</span>'
    +'<button class="btn btn-o btn-s" id="tlegend" title="显示/隐藏图例">📖 图例</button>'
    // 图例浮层 (C1: 折叠收纳, 点击切换)
    +'<div class="legend-pop hidden" id="legend-pop">'
      +'<div class="lp-title">节点形状</div>'
      +'<div class="lp-row"><span class="dot coord"></span> 协调器</div>'
      +'<div class="lp-row"><span class="dot router"></span> 路由器</div>'
      +'<div class="lp-row"><span class="dot enddev"></span> 终端设备</div>'
      +'<div class="lp-row"><span class="dot unknown square"></span> 未知设备</div>'
      +'<div class="lp-title mt-1">链路</div>'
      +'<div class="lp-row"><span class="edge-demo traffic"></span> 数据流 (通信)</div>'
      +'<div class="lp-row"><span class="edge-demo route"></span> 路由路径 (当前实线 / 历史虚线)</div>'
      +'<div class="lp-row"><span class="edge-demo neighbor"></span> 邻居关系 (Link Status)</div>'
      +'<div class="lp-title mt-1">状态</div>'
      +'<div class="lp-row"><span class="dot silent"></span> 静默节点 (可隐藏)</div>'
      +'<div class="lp-row"><span class="dot hl"></span> 高亮节点</div>'
    +'</div>'
    +'</div>'
    // ── 时间控制条: 单滑块(窗口中心) + 窗口大小 ──
    +'<div class="timebar">'
    +'<span class="t-label">⏱ 窗口:</span>'
    +'<select id="twin-size">'
    +'<option value="30">30s</option><option value="60">60s</option><option value="120">120s</option><option value="300">300s</option><option value="9999" selected>全部</option></select>'
    +'<button class="btn btn-o btn-s" id="tstep-bwd" title="前移">◀</button>'
    +'<button class="btn btn-o btn-s" id="tplay" title="播放/暂停 (自动推进窗口)">▶</button>'
    +'<input type="range" id="tsl" min="0" max="1000" value="500" oninput="onTimeSlide()" onchange="onTimeSlideEnd()">'
    +'<button class="btn btn-o btn-s" id="tstep-fwd" title="后移">▶</button>'
    +'<span id="ttime-label">--:--:-- ~ --:--:--</span>'
    +'<div class="time-scale">'
      +'<span class="ts-label" id="ts-t0"></span>'
      +'<div class="ts-track"><div class="ts-window" id="ts-window"></div></div>'
      +'<span class="ts-label" id="ts-t1"></span>'
    +'</div>'
    +'</div>'
    // Cytoscape 图
    +'<div id="cy-graph">'
    +'<div id="off-frame"></div>'
    +'<div id="off-label">📡 仅LS可见</div>'
    +'</div>'
    // 底部面板 (路由路径链 + 层级树)
    +'<div id="bottom-panels">'
    +'<div class="bp-head">'
    +'<button class="btn bp-tab on" onclick="togBpTab(\'routes\',this)">🛤️ 路由路径链</button>'
    +'<button class="btn bp-tab" onclick="togBpTab(\'neighbors\',this)">📡 邻居关系</button>'
    +'</div>'
    +'<div id="bp-routes" class="bp-body"></div>'
    +'<div id="bp-neighbors" class="bp-body hidden"></div>'
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
      +'<span>图节点: <b class="text-success">'+activeCount+'</b>活跃</span><span class="text-dim">'+(ns.length-activeCount)+'静默</span>'
      +'<span>图边: <b>'+es.length+'</b>数据流</span>'
      +'<span class="text-route">'+rps.length+'路径↑</span>'
      +(probes.length>0?'<span class="text-info">'+probes.length+'探测↓</span>':'')
      +(failures.length>0?'<span class="text-danger-strong">'+failures.length+'失败✕</span>':'')
      +'<span>📡 LS邻居:<b>'+nbTotal+'</b></span><span>LS设备:'+nbDevCount+'</span>'
      +'</div>';
    // PAN list
    var pl=d.pan_list||[];
    var ph='<table class="tbl"><tr><th>PAN</th><th>包数</th></tr>';
    for(var i=0;i<pl.length;i++){ph+='<tr class="pan-row" data-pan="'+pl[i].pan+'"><td>'+pl[i].label+'</td><td>'+pl[i].count+'</td><td><button class="btn btn-o btn-s pan-tl-btn" data-pan="'+pl[i].pan+'">→TL</button></td></tr>';}
    document.getElementById('pan-list').innerHTML=ph+'</table>';
    document.querySelectorAll('.pan-row').forEach(function(r){r.addEventListener('click',function(e){if(e.target.classList.contains('pan-tl-btn'))return;var pv=parseInt(this.dataset.pan);var ps=pv.toString(16).toUpperCase();document.getElementById('tpan').value=ps;S.topoPan=ps;loadData(ps,function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){} })})});
    document.querySelectorAll('.pan-tl-btn').forEach(function(b){b.addEventListener('click',function(e){e.stopPropagation();S.topoPan=parseInt(this.dataset.pan).toString(16).toUpperCase();S.topoT0=null;S.topoT1=null;location.hash='tl'})});
    // Asymmetric links — 只显示WEAK和ASYMM级别, 点击可高亮图中节点
    var al=d.asymmetric_links||[];
    var alFiltered=[]; for(var i=0;i<al.length;i++){if(al[i].level!=='OK') alFiltered.push(al[i]);}
    var ah='';
    var alTitle='📋 不对称链路 ('+alFiltered.length+'条, 不含OK)';
    document.querySelector('#tasym').parentElement.querySelector('h3').textContent=alTitle;
    if(alFiltered.length===0){ah='<p class="t-10 text-success">✅ 未发现不对称链路</p>';}
    else{
      ah='<table class="tbl"><tr><th>A</th><th>B</th><th>A→B</th><th>B→A</th><th>差</th></tr>';
      var maxShow=Math.min(alFiltered.length,15);
      for(var i=0;i<maxShow;i++){
        var a=alFiltered[i];var lc=a.level==='WEAK'?'#d97706':'#dc2626';
        ah+='<tr class="asym-row" data-a="'+a.a+'" data-b="'+a.b+'">'
          +'<td>0x'+a.a.toString(16).toUpperCase().padStart(4,'0')+'</td><td>0x'+a.b.toString(16).toUpperCase().padStart(4,'0')+'</td>'
          +'<td>'+a.a_to_b_cost+'</td><td>'+a.b_to_a_cost+'</td><td class="text-strong" style="color:'+lc+'">'+a.diff+'</td></tr>';
      }
      if(alFiltered.length>maxShow) ah+='<tr><td colspan="5" class="text-dim text-center">...还有'+(alFiltered.length-maxShow)+'条</td></tr>';
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

  // ═══ 空态引导 (A1): 按原因区分三层, 带操作按钮 ═══
  function showEmptyGuide(){
    var g=document.getElementById('cy-graph'); if(!g) return;
    // 保留 off-frame/off-label (后续 renderGraph 依赖)
    var off=document.getElementById('off-frame'), ol=document.getElementById('off-label');
    g.innerHTML='';
    if(off) g.appendChild(off);
    if(ol) g.appendChild(ol);
    var reason='', btn='';
    if(!dataTotal){
      reason='还没有导入抓包数据 — 拓扑图需要先导入 .cubx/.pcap 素材';
      btn='<button class="btn btn-p btn-s" onclick="location.hash=\'import\'">去导入 →</button>';
    }else if(S.topoPan||S.topoT0!=null||S.topoT1!=null){
      reason='当前被过滤条件筛空 — PAN: '+(S.topoPan||'全部')+' | 时间窗口: '+(S.topoT0!=null?'过滤中':'全部');
      btn='<button class="btn btn-o btn-s" onclick="document.getElementById(\'trst\').click()">重置过滤</button>';
    }else{
      reason='素材存在 ('+dataTotal+' 帧), 但未推导出拓扑节点 — 拓扑依赖 Route Record / Link Status 等路由事件帧';
    }
    var div=document.createElement('div');div.className='empty-guide';
    div.innerHTML='<div class="empty-guide-icon">📭</div><div>'+reason+'</div><div class="mt-2">'+btn+'</div>';
    g.appendChild(div);
  }

  // ═══ Cytoscape 力导向图 (路径着色 + 流量背景) ═══

  function renderGraph(d){
    if(!d) return;
    var nbt=d.neighbor_tables||{};
    var ns=d.nodes||[];
    if(ns.length===0){if(cy){cy.destroy();cy=null;}document.getElementById('tinfo').textContent='无拓扑数据';showEmptyGuide();return;}
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
      var ci=i % PATH_COLORS.length;
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

    // ── 边: 邻居关系 (Link Status) — 物理层 (C2) ──
    // 只画无 traffic 边的邻居对; two-way (out_cost>0) 点线, one-way 虚线+箭头; 密度保护 (>8 邻居不画, tooltip 显示数量)
    var denseNbs={};
    for(var nai in nbt){ if(Object.keys(nbt[nai]||{}).length>8) denseNbs[nai]=true; }
    var nbPairs={};
    for(var nai in nbt){
      for(var nbi in (nbt[nai]||{})){
        if(denseNbs[nai]||denseNbs[nbi]) continue;
        var na2=parseInt(nai), nb2=parseInt(nbi);
        if(!cyNodeIds[''+na2]||!cyNodeIds[''+nb2]) continue;
        var pk2=Math.min(na2,nb2)+'-'+Math.max(na2,nb2);
        if(nbPairs[pk2]||trafficSeen[pk2]) continue;   // 与 traffic 边去重
        nbPairs[pk2]=true;
        var ninfo=nbt[nai][nbi];
        var twoWay=(ninfo.out_cost||0)>0;   // MCP: two-way = 非零出站成本
        cyEdges.push({
          data:{id:'nb-'+pk2, source:''+na2, target:''+nb2, edge_type:'neighbor',
                in_cost:ninfo.in_cost, out_cost:ninfo.out_cost, last_seen:ninfo.last_seen_ts, count:ninfo.count},
          classes:'neighbor-edge'+(twoWay?'':' one-way')
        });
      }
    }

    // 保存用户缩放状态
    var userZoom=null, userPan=null;
    if(cy){userZoom=cy.zoom();userPan=cy.pan();}

    // ── 初始化 Cytoscape (U7: 实例复用 — 时间过滤只换元素不销毁重建) ──
    topoNbt=nbt;
    if(!cy){
      cy=cytoscape({
        container: document.getElementById('cy-graph'),
      elements: cyNodes.concat(cyEdges),
      style: [
        // 节点基础
        {selector:'node', style:{'background-color':'#3b82f6','shape':'ellipse','label':'data(label)','font-size':'9px','color':'#1e293b','text-valign':'bottom','text-halign':'center','text-margin-y':4,'border-width':1,'border-color':'#fff','width':28,'height':28}},
        // 设备类型形状分类 (U7): 协调器=大六边形 / 路由器=菱形 / 终端=圆 / 未知=三角
        {selector:'node.coordinator', style:{'background-color':'#f59e0b','shape':'hexagon','border-color':'#d97706','border-width':3,'font-weight':'bold','width':60,'height':60,'text-margin-y':8}},
        {selector:'node.router', style:{'background-color':'#3b82f6','shape':'diamond','width':32,'height':32}},
        {selector:'node.end_device', style:{'background-color':'#16a34a','shape':'ellipse','width':22,'height':22}},
        {selector:'node.unknown', style:{'background-color':'#94a3b8','shape':'triangle','width':22,'height':22}},
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
        // 邻居边 (C2): 物理层 — two-way 点线 / one-way 虚线+箭头 (方向=有出站成本侧)
        {selector:'edge.neighbor-edge', style:{'line-style':'dotted','line-color':'#94a3b8','width':1,'opacity':0.35}},
        {selector:'edge.neighbor-edge.one-way', style:{'line-style':'dashed','target-arrow-shape':'triangle','target-arrow-color':'#94a3b8','arrow-scale':0.5,'opacity':0.25}},
        // 路径行 hover 高亮 (路由路径链联动)
        {selector:'edge.path-hl', style:{'width':5,'opacity':1,'line-color':'#e11d48','target-arrow-color':'#e11d48'}},
      ],
        wheelSensitivity:0.3,
      });

      // ── 交互事件 (只绑定一次, 实例复用时保留) ──
      var tooltip=document.createElement('div');tooltip.id='cy-tt';tooltip.style.cssText='position:absolute;display:none;background:#1e293b;color:#fff;padding:6px 10px;border-radius:6px;font-size:11px;pointer-events:none;z-index:999;max-width:280px;white-space:pre-line';
      document.getElementById('cy-graph').appendChild(tooltip);

      cy.on('mouseover','node',function(e){var n=e.target;var d=n.data();var nbtEntry=topoNbt[d.aid];var nbCount=nbtEntry?Object.keys(nbtEntry).length:0;tooltip.innerHTML='<b>'+d.label+'</b>\n类型:'+(d.device_type==='coordinator'?'协调器':d.device_type==='router'?'路由器':d.device_type==='end_device'?'终端设备':'未知')+'\n'+(d.on_path?'在路径上':'不在路径上')+'\nLS邻居:'+nbCount;tooltip.style.display='block';updateTooltipPos(e);});
    cy.on('mouseout','node',function(){tooltip.style.display='none';});
    cy.on('mouseover','edge',function(e){var ed=e.target;var d=ed.data();if(d.edge_type==='neighbor'){tooltip.innerHTML='<b>邻居关系</b>\n0x'+d.source.toString(16).toUpperCase()+' ↔ 0x'+d.target.toString(16).toUpperCase()+'\n入向cost:'+d.in_cost+' 出向cost:'+(d.out_cost||'未知')+(d.last_seen?'\n最近:'+fmtTs(d.last_seen)+' · '+d.count+'帧':'');}else if(d.edge_type==='traffic'){tooltip.innerHTML='<b>数据流</b>\n0x'+d.source.toString(16).toUpperCase()+' ↔ 0x'+d.target.toString(16).toUpperCase()+'\n'+d.count+' 包';}else{var hf=S.topoT0!=null||S.topoT1!=null;var st=hf?(d.active!==false?'● 活跃':'◌ 窗口外'):(d.is_current?'● 当前':'◌ 历史');tooltip.innerHTML='<b>路径 #'+(d.path_idx+1)+' 第'+(d.hop+1)+'跳</b>\n'+st+'\n'+d.path_str;};tooltip.style.display='block';updateTooltipPos(e);});
    cy.on('mouseout','edge',function(){tooltip.style.display='none';});

    function updateTooltipPos(e){var r=e.renderedPosition||e.position;var gb=document.getElementById('cy-graph').getBoundingClientRect();tooltip.style.left=(gb.left+r.x+12)+'px';tooltip.style.top=(gb.top+r.y-10)+'px';}

    // Click → 跳转时间线
    cy.on('tap','node',function(e){var n=e.target;var aid=n.data('aid');S.topoAddr='0x'+aid.toString(16).toUpperCase().padStart(4,'0');S.topoT0=null;S.topoT1=null;location.hash='tl';});

      // 双击 → 高亮/淡出
      cy.on('dbltap','node',function(e){var n=e.target;var aid=n.data('aid');if(hlNode===aid){clearHighlight();return;}hlNode=aid;highlightNode(aid);});
    }else{
      cy.json({elements: cyNodes.concat(cyEdges)});   // 实例复用: 只替换元素, 保留样式表/事件/视图
    }

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
    applySilentHidden();   // 数据刷新后恢复静默节点隐藏状态
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
      // C3: off-path 节点按邻居连通分量分组 (物理层聚类), 组内连续排布
      var offGroups=[], offSeen={};
      for(var oi=0;oi<offAll.length;oi++){
        var on=offAll[oi]; if(offSeen[on.id()]) continue;
        var comp=[], q=[on.id()]; offSeen[on.id()]=true;
        while(q.length){
          var cid=q.shift(), cn=cy.getElementById(cid); if(!cn||!cn.nonempty()) continue;
          comp.push(cn);
          var nbInfo=nbt[cid]||{};
          for(var nbi in nbInfo){var nid=''+nbi; if(!offSeen[nid]){var nn=cy.getElementById(nid);if(nn.nonempty()&&!nn.data('on_path')){offSeen[nid]=true;q.push(nid);}}}
          cn.connectedEdges('[edge_type="traffic"]').forEach(function(e){var oid=(e.source().id()===cid)?e.target().id():e.source().id();if(!offSeen[oid]){var nn2=cy.getElementById(oid);if(nn2.nonempty()&&!nn2.data('on_path')){offSeen[oid]=true;q.push(oid);}}});
        }
        if(comp.length) offGroups.push(comp);
      }
      var offOrdered=[]; for(var ogi=0;ogi<offGroups.length;ogi++){for(var ogj=0;ogj<offGroups[ogi].length;ogj++)offOrdered.push(offGroups[ogi][ogj]);}
      var offCols=Math.max(3,Math.ceil(offOrdered.length/12)); if(offCols<1)offCols=1;
      var offPerCol=Math.ceil(offOrdered.length/offCols);
      var offStartX=-(offCols+2)*200;
      for(var c=0;c<offCols;c++){var chunk=offOrdered.slice(c*offPerCol,(c+1)*offPerCol);var ch=Math.max(300,chunk.length*36);chunk.forEach(function(n,i){posMap[n.id()]={x:offStartX+c*200,y:-(ch/2)+(ch/(chunk.length+1))*(i+1)};});}
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
    applySilentHidden();   // 布局切换后恢复静默节点隐藏状态
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
      panel.innerHTML='<p class="empty">未发现路由事件 (该网络无 Route Record/Request/Status 帧)</p>';return;
    }

    // 样式
    var sep='<div class="sep"></div>';
    var h='';

    // ── 上行路径 (Route Record) ──
    if(paths.length>0){
      var srcPaths={}; for(var i=0;i<paths.length;i++){var s=paths[i].src;if(!srcPaths[s])srcPaths[s]=[];srcPaths[s].push(paths[i]);}
      var changed=0; for(var k in srcPaths){if(srcPaths[k].length>1)changed++;}
      h+='<div class="path-head">'
        +'<span class="text-route text-strong">↑ 上行路径 (Route Record)</span> '
        +paths.length+'条 | '+Object.keys(srcPaths).length+'个设备'
        +(changed>0?' | <b class="text-amber">'+changed+'个发生过路由变更</b>':'')
        +'</div>'
        +'<div class="path-tip">●实线=当前路由 · ◌虚线=历史路由</div>';
      var maxShow=Math.min(paths.length,20);
      for(var i=0;i<maxShow;i++){
        var p=paths[i];
        var icon=p.is_current?'●':'◌';
        var color=p.is_current?'#7c3aed':'#94a3b8';
        var ts0=new Date(p.first_ts*1000).toISOString().substr(11,8);
        var ts1=new Date(p.last_ts*1000).toISOString().substr(11,8);
        var dur=p.first_ts===p.last_ts?'':(' ~ '+ts1);
        h+='<div class="path-row'+(p.is_current?' text-strong':'')+'" data-pidx="'+i+'" title=\"首帧:'+ts0+' 末帧:'+ts1+' 共'+p.frame_count+'帧\">'
          +'<span class="p-icon" style="color:'+color+'">'+icon+'</span>'
          +'<span style="color:'+color+'">'+p.path_str+'</span>'
          +'<span class="p-tag text-dim">'+p.hop_count+'跳 ×'+p.frame_count+'帧</span>'
          +'<span class="p-tag text-dim">'+ts0+dur+'</span>'
          +(p.is_current?'<span class="p-tag text-success text-strong">当前</span>':'<span class="p-tag text-dim">历史</span>')
          +'</div>';
      }
      if(paths.length>maxShow) h+='<p class="text-dim t-10 text-center">...还有'+(paths.length-maxShow)+'条路径</p>';
    }

    // ── 下行探测 (Route Request) ──
    if(probes.length>0){
      h+=sep+'<div class="path-head">'
        +'<span class="text-info text-strong">↓ 下行探测 (Route Request)</span> '
        +probes.length+'对</div>';
      var maxP=Math.min(probes.length,10);
      for(var i=0;i<maxP;i++){
        var pp=probes[i];
        var ts0=new Date(pp.first_ts*1000).toISOString().substr(11,8);
        h+='<div class="path-row" title=\"radius='+pp.radius+' 共'+pp.count+'次\">'
          +'<span class="p-icon text-info">→</span>'
          +'<span class="text-info">'+pp.path_str+'</span>'
          +'<span class="p-tag text-dim">×'+pp.count+'次</span>'
          +'<span class="p-tag text-dim">'+ts0+'</span>'
          +'</div>';
      }
    }

    // ── 下行失败 (Network Status) ──
    if(failures.length>0){
      h+=sep+'<div class="path-head">'
        +'<span class="text-danger text-strong">✕ 下行失败 (Network Status)</span> '
        +failures.length+'处</div>';
      for(var i=0;i<failures.length;i++){
        var f=failures[i];
        var ts=new Date(f.timestamp*1000).toISOString().substr(11,8);
        h+='<div class="path-row">'
          +'<span class="p-icon text-danger">✕</span>'
          +'<span class="text-danger">'+f.path_str+'</span>'
          +'<span class="p-tag text-danger">'+f.status_name+'</span>'
          +'<span class="p-tag text-dim">'+ts+'</span>'
          +'</div>';
      }
    }

    panel.innerHTML=h;

    // ── 路径行 ↔ 图联动: hover 高亮图上对应路径 (U7 优化) ──
    function highlightPathOnGraph(idx){
      if(!cy) return;
      cy.elements().removeClass('path-hl');
      cy.edges('[edge_type="route"]').forEach(function(e){ if(e.data('path_idx')===idx) e.addClass('path-hl'); });
    }
    function clearPathHighlight(){ if(cy) cy.elements().removeClass('path-hl'); }
    document.querySelectorAll('#bp-routes .path-row[data-pidx]').forEach(function(row){
      var idx=parseInt(row.dataset.pidx);
      row.addEventListener('mouseenter',function(){highlightPathOnGraph(idx);});
      row.addEventListener('mouseleave',function(){clearPathHighlight();});
    });
  }

  // ═══ 邻居关系面板 ═══
  function renderNeighborPanel(){
    var panel=document.getElementById('bp-neighbors');
    var d=S.topo; if(!d){panel.innerHTML='<p class="text-dim">无拓扑数据</p>';return;}
    var nbt=d.neighbor_tables||{};
    if(Object.keys(nbt).length===0){panel.innerHTML='<p class="empty">无 Link Status 数据</p>';return;}
    // Build device dropdown sorted by neighbor count
    var devList=[]; for(var devStr in nbt){devList.push({aid:parseInt(devStr), count:Object.keys(nbt[devStr]).length});}
    devList.sort(function(a,b){return b.count-a.count;});
    var h='<div class="row">'
      +'<span class="t-11 text-strong">设备:</span>'
      +'<select id="nb-dev-sel" class="mono t-11 w-180" onchange="showNbTable()">'
      +'<option value="">-- 选择设备 ('+devList.length+' 个有LS) --</option>';
    for(var i=0;i<devList.length;i++){
      h+='<option value="'+devList[i].aid+'">0x'+devList[i].aid.toString(16).toUpperCase().padStart(4,'0')+' ('+devList[i].count+' 邻居)</option>';
    }
    h+='</select><span class="t-10 text-muted">共 '+devList.length+' 设备有Link Status数据</span></div>';
    h+='<div id="nb-detail" class="t-11 scroll-y"></div>';
    panel.innerHTML=h;
    // Global function to show neighbor detail
    window.showNbTable=function(){
      var v=document.getElementById('nb-dev-sel').value;
      var detail=document.getElementById('nb-detail');
      if(v===''){detail.innerHTML='';return;}   // 未选择; 注意不能用 !aid (协调器 aid=0 会被误过滤)
      var aid=parseInt(v);
      if(!nbt[aid]){detail.innerHTML='';return;}
      var nbs=nbt[aid]; var nbKeys=Object.keys(nbs);
      if(nbKeys.length===0){detail.innerHTML='<p class="text-dim">该设备无邻居记录</p>';return;}
      var th='<table class="tbl"><tr><th>邻居</th><th>In Cost</th><th>Out Cost</th><th>最后更新</th><th>次数</th></tr>';
      nbKeys.sort(function(a,b){return (nbs[b].out_cost||0)-(nbs[a].out_cost||0);});
      for(var i=0;i<nbKeys.length;i++){
        var nb=nbs[nbKeys[i]]; var addr=parseInt(nbKeys[i]);
        var ic=nb.in_cost||0; var oc=nb.out_cost||0;
        var icColor=ic<=1?'#16a34a':ic<=3?'#d97706':'#dc2626';
        var ocColor=oc<=1?'#16a34a':oc<=3?'#d97706':'#dc2626';
        var ts=new Date((nb.last_seen_ts||0)*1000).toISOString().substr(11,8);
        th+='<tr onclick="S.topoAddr=\'0x'+addr.toString(16).toUpperCase().padStart(4,'0')+'\';location.hash=\'tl\'">'
          +'<td>0x'+addr.toString(16).toUpperCase().padStart(4,'0')+'</td>'
          +'<td class="text-strong" style="color:'+icColor+'">'+ic+'</td>'
          +'<td class="text-strong" style="color:'+ocColor+'">'+oc+'</td>'
          +'<td class="t-10 text-dim">'+ts+'</td>'
          +'<td class="t-10">'+nb.count+'</td></tr>';
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

  // ═══ 地址定位 (taddr): 输入地址 → 图上定位高亮 (U7 修复死控件) ═══
  function locateAddr(){
    var av=document.getElementById('taddr').value.trim();
    if(!av||!cy) return;
    var aid=parseInt(av,16);
    if(isNaN(aid)){document.getElementById('taddr').title='无效地址 (hex)';return;}
    var n=cy.getElementById(''+aid);
    if(n&&n.nonempty()){
      S.topoAddr='0x'+aid.toString(16).toUpperCase().padStart(4,'0');
      clearHighlight();
      highlightNode(aid);
      cy.animate({center:{eles:n},zoom:Math.max(cy.zoom(),1.5)},{duration:300});
      document.getElementById('taddr').title='';
    }else{
      document.getElementById('taddr').title='节点不在当前图 (可能被 PAN 过滤)';
    }
  }
  document.getElementById('taddr').addEventListener('keydown',function(e){if(e.key==='Enter')locateAddr();});

  // ═══ 按钮事件 ═══
  document.getElementById('tgo').addEventListener('click',function(){
    var av=document.getElementById('taddr').value.trim();
    if(av){locateAddr();return;}   // 有地址 → 定位 (nodes 页跳转也走这里)
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
  // ═══ 图例浮层 (C1) ═══
  document.getElementById('tlegend').addEventListener('click',function(e){
    e.stopPropagation();
    document.getElementById('legend-pop').classList.toggle('hidden');
  });
  document.addEventListener('click',function(){var p=document.getElementById('legend-pop');if(p&&!p.classList.contains('hidden'))p.classList.add('hidden');});

  document.getElementById('tfit').addEventListener('click',function(){if(cy){cy.zoom(1);cy.pan({x:0,y:0});cy.fit(undefined,30);}});
  document.getElementById('tlay').addEventListener('click',function(){
    curLayout=(curLayout+1)%2; runLayout();
    if(curLayout===1) setTimeout(function(){cy.fit(undefined,30);},900);
  });
  document.getElementById('thl-clear').addEventListener('click',function(){clearHighlight();});

  // ═══ 静默节点显示/隐藏 (tshow-all, U7 修复死控件) — 静默 = 孤立节点 (degree 0, 非路径) ═══
  function applySilentHidden(){
    if(!cy) return;
    cy.nodes().forEach(function(n){
      if(n.degree()===0&&n.data('on_path')!==true) n.style('display',silentHidden?'none':'element');
    });
  }
  document.getElementById('tshow-all').addEventListener('click',function(){
    if(!cy) return;
    silentHidden=!silentHidden;
    applySilentHidden();
    this.classList.toggle('on',silentHidden);
    this.title=silentHidden?'显示静默节点':'隐藏静默节点';
  });

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
    if(tw.t0==null){document.getElementById('ttime-label').textContent=fmtTs(tsStart)+' ~ '+fmtTs(tsEnd)+' (全部)';}
    else{
      var dur=tw.t1-tw.t0;
      document.getElementById('ttime-label').textContent=fmtTs(tw.t0)+' ~ '+fmtTs(tw.t1)+' ('+Math.round(dur)+'s)';
    }
    updateTimeScale(tw);
  }

  // ── 时间刻度条: 总时长 + 当前窗口位置 (U7) ──
  function updateTimeScale(tw){
    var win=document.getElementById('ts-window'); if(!win) return;
    var t0=document.getElementById('ts-t0'), t1=document.getElementById('ts-t1');
    if(t0&&tsStart!=null){t0.textContent=fmtTs(tsStart);t1.textContent=fmtTs(tsEnd);}
    var total=(tsEnd-tsStart)||1;
    if(!tw) tw=getTimeWindow();
    if(tw.t0==null){win.style.left='0%';win.style.width='100%';}
    else{
      win.style.left=Math.max(0,((tw.t0-tsStart)/total*100))+'%';
      win.style.width=Math.min(100,((tw.t1-tw.t0)/total*100))+'%';
    }
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

  // ── 滑块预览遮罩 (D1) ──
  function showPreviewMask(){
    var g=document.getElementById('cy-graph'); if(!g) return;
    var m=document.getElementById('time-mask');
    if(!m){m=document.createElement('div');m.id='time-mask';m.className='time-mask';g.appendChild(m);}
    var tw=getTimeWindow();
    if(tw.t0==null){m.style.display='none';return;}
    m.style.display='block';
    m.textContent='⏱ 预览: '+fmtTs(tw.t0)+' ~ '+fmtTs(tw.t1);
  }
  function hidePreviewMask(){var m=document.getElementById('time-mask');if(m)m.style.display='none';}

  window.onTimeSlide=function(){   // oninput: 拖动中 — 标签/刻度条/预览遮罩实时, 图不刷新
    var v=parseInt(document.getElementById('tsl').value);
    tCenter=sliderToTs(v);
    updateTimeLabel();
    showPreviewMask();
  };
  window.onTimeSlideEnd=function(){  // change: 松手 — 触发图刷新
    applyTimeFilter();
    hidePreviewMask();
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

  // ═══ 播放/暂停: 自动推进时间窗口 (U7) ═══
  window.togglePlay=function(){
    var btn=document.getElementById('tplay');
    if(playTO){clearInterval(playTO);playTO=null;btn.textContent='▶';btn.classList.remove('btn-p');return;}
    var ws=getWinSize();
    if(ws==null){document.getElementById('twin-size').value='120';setWindowFromSize();ws=120;}
    if(tCenter==null){tCenter=tsStart+ws/2;document.getElementById('tsl').value=tsToSlider(tCenter);}
    btn.textContent='⏸';btn.classList.add('btn-p');
    playTO=setInterval(function(){
      var w2=getWinSize()||120;
      var step=Math.max(5,w2/4);
      tCenter=Math.min(tsEnd-w2/2,tCenter+step);
      document.getElementById('tsl').value=tsToSlider(tCenter);
      applyTimeFilter();
      if(tCenter>=tsEnd-w2/2) togglePlay();  // 到尾自动停
    },600);
  };
  document.getElementById('tplay').addEventListener('click',togglePlay);

  // 获取抓包时间范围 + 时间线过滤约束
  var tlT0=null, tlT1=null;
  A.get('/api/import/status').then(function(s){
    dataTotal=s.total||0;
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
});
