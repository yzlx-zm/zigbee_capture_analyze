// topo.js — 拓扑页面模块 (ES module)
// reg('topo',...) 回调体 + 全部拓扑渲染/布局/事件逻辑
import { S, A, sb, fmtTs } from './state.js';

// ── 模块私有变量 (不可被其他模块 import) ──
let cy = null, topoData = null, hlNode = null;
let tCenter = null, tSliderTO = null, curLayout = 0;
let tsStart = 0, tsEnd = 0;
let topoNbt = null;   // 当前邻居表 (事件闭包引用, 实例复用时保持最新)
let silentHidden = false, focusAid = null;
let slideMode = false;  // S3-重构: 时刻模式 (拖动游标, 30s 证据窗) vs 全貌模式 (最近证据)
let curT = null;   // U13 时刻游标 (当前时刻, 边按此过滤)   // U13-B 聚焦模式   // 静默/邻居边 状态 (模块级, 跨页面保留)
let dataTotal = 0;    // 导入数据总帧数 (空态引导判断用)
const PATH_COLORS = ['#e74c3c','#3498db','#2ecc71','#e67e22','#9b59b6','#1abc9c','#f39c12','#e91e63'];

reg('topo', function(){
  // 页面重建清理: 旧 cy 实例绑定已移除的容器, 必须销毁; 播放/防抖定时器同步停
  if(cy){cy.destroy();cy=null;}
  focusAid=null;  // U13-B: 页面重建退出聚焦
  clearTimeout(tSliderTO);
  var h='<div class="page">'
    // ── 左侧边栏 ──
    +'<div id="tside">'
    +'<div class="tside-head">'
    +'<button class="btn btn-o btn-s" id="tside-tog" title="折叠侧边栏">◀ 折叠</button>'
    +'<span id="tinfo"></span></div>'
    +'<div class="card card-tight"><h3>📊 拓扑统计</h3><div id="tstat"></div></div>'
    +'<div class="card card-tight"><h3>🔍 节点搜索</h3><input id="tsearch" class="mono t-11" placeholder="地址 / 型号 / 厂商" style="width:100%">'
    +'<div id="tsearch-list" class="scroll-y" style="max-height:180px;margin-top:4px"></div></div>'
    +'<div class="card card-tight"><h3>📡 PAN 列表</h3><div id="pan-list" class="scroll-y"></div></div>'
    +'<div class="card card-tight"><h3>📋 不对称链路</h3><div id="tasym"></div></div>'
    +'</div>'
    // ── 主区域 ──
    +'<div class="col grow oh">'
    // 工具栏
    +'<div class="toolbar">'
    +'<input id="tpan" placeholder="PAN (16B6)" class="mono w-100 t-11">'
    +'<input id="taddr" placeholder="地址" class="mono w-90 t-11">'
    // S3 (2026-08-28 用户反馈): 节点过滤手段 — 🎯 聚焦按钮 (输入地址 → 聚焦链路变化)
    +'<button class="btn btn-o btn-s" id="tfocus" title="输入地址后聚焦该节点链路变化">🎯 聚焦</button>'
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
      +'<div class="lp-row"><span class="edge-demo parent"></span> 父链路 (poll/入网/下行证据)</div>'
      +'<div class="lp-title mt-1">状态</div>'
      +'<div class="lp-row"><span class="lp-q">⏳</span> 链路遗失 (历史残影, 悬停看最后时间)</div>'
      +'<div class="lp-row"><span class="dot silent"></span> 静默节点 (可隐藏)</div>'
      +'<div class="lp-row"><span class="dot hl"></span> 高亮节点</div>'
    +'</div>'
    +'</div>'
    // ── 时间控制条: 单滑块(窗口中心) + 窗口大小 ──
    +'<div class="timebar">'
    +'<span class="t-label">⏱ 时刻:</span>'
    +'<input type="range" id="tsl" min="0" max="1000" value="500" oninput="onTimeSlide()" onchange="onTimeSlideEnd()">'
    +'<span id="ttime-label">--:--:--</span>'
    +'<span class="t-10 text-muted" style="margin-left:8px">拖动游标观察该时刻的链路</span>'
    +'<div class="time-scale">'
      +'<span class="ts-label" id="ts-t0"></span>'
      +'<div class="ts-track"><div class="ts-window" id="ts-window"></div></div>'
      +'<span class="ts-label" id="ts-t1"></span>'
    +'</div>'
    +'</div>'
    // Cytoscape 图
    +'<div id="cy-graph">'
    +'<div id="off-frame"></div>'
    +'<div id="focus-bar" style="display:none"></div>'
    +'<div id="off-label">◌ 未关联 (无链路证据)</div>'
    +'</div>'
    // 底部面板 (路由路径链 + 层级树)
    +'<div id="bottom-panels">'
    +'<div class="bp-head">'
    +'<button class="btn bp-tab on" onclick="togBpTab(\'routes\',this)">🛤️ 路由路径链</button>'
    +'<button class="btn bp-tab" onclick="togBpTab(\'history\',this)">🕐 链路历史</button>'
    +'<button class="btn bp-tab" onclick="togBpTab(\'neighbors\',this)">📡 邻居关系</button>'
    +'</div>'
    +'<div id="bp-routes" class="bp-body"></div>'
    +'<div id="bp-history" class="bp-body hidden"></div>'
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

  // ═══ U13-B: 聚焦模式 (选节点看链路变化, 其他隐藏) ═══
  function reloadTopo(){
    // U13 时刻游标: 数据已全量加载, 聚焦切换本地重渲染
    if(S.topo) renderGraph(S.topo);
  }
  function enterFocus(aid){
    focusAid=aid;
    var bar=document.getElementById('focus-bar');
    // ⚠️ S3 (2026-08-28, 用户反馈布局): 聚焦横幅结构化 4 行 —
    // 标题行(地址+按钮) / 提示行 / 链路历史时间轴 / 当前段信息
    bar.innerHTML='<div class="fhist-title">'
      +'<b class="fhist-aid">🔍 聚焦 0x'+aid.toString(16).toUpperCase().padStart(4,'0')+'</b>'
      +'<span class="fhist-hint">拖动时间滑块观察链路变化</span>'
      +'<span class="fhist-btns">'
      +'<button class="btn btn-o btn-s" id="focus-tl" style="color:#fff">🔍 报文</button>'
      +'<button class="btn btn-s" id="focus-exit">✕ 退出</button>'
      +'</span></div>'
      // S3-C (2026-08-28, 用户选择 A+B): 链路历史时间轴 (分段色块 + 游标指针)
      +'<div id="focus-hist" class="fhist"></div>';
    bar.style.display='flex';
    document.getElementById('focus-tl').addEventListener('click',function(){
      S.topoAddr='0x'+aid.toString(16).toUpperCase().padStart(4,'0');S.topoT0=null;S.topoT1=null;location.hash='tl';
    });
    document.getElementById('focus-exit').addEventListener('click',exitFocus);
    renderFocusHist();
    reloadTopo();
  }

  // ═══ S3-C: 聚焦链路历史时间轴 (方案 B) — 该节点链路分段色块 + 游标指针 ═══
  // S3 (2026-08-28, 用户反馈): 切换点橙色标记 — 相邻段链路签名变化处
  function segSig(s){
    if(s.kind==='parent')return 'p:'+s.parent;
    if(s.kind==='route')return 'r:'+String(s.dst)+':'+(s.relays||[]).join(',');
    return s.kind;
  }
  function segChangeDesc(prev,cur){
    var hx=function(a){return '0x'+a.toString(16).toUpperCase().padStart(4,'0');};
    if(prev.kind==='parent'&&cur.kind==='parent')
      return '父链路切换 '+hx(prev.parent)+' → '+hx(cur.parent)+' @ '+fmtTsH(cur.t0);
    if(prev.kind==='route'&&cur.kind==='route')
      return '路径切换 @ '+fmtTsH(cur.t0);
    return '链路变更 ('+(prev.kind==='parent'?'父':'路径')+'→'+(cur.kind==='parent'?'父':'路径')+') @ '+fmtTsH(cur.t0);
  }
  function renderFocusHist(){
    var el=document.getElementById('focus-hist');
    if(!el)return;
    var segs=(S.topo&&S.topo.link_snapshots)?S.topo.link_snapshots[''+focusAid]:null;
    if(!segs||!segs.length){el.innerHTML='<div class="fhist-empty">该节点无链路证据帧</div>';return;}
    var t0=segs[0].t0,t1=segs[segs.length-1].t1;
    var span=Math.max(t1-t0,1);
    var h='<div class="fhist-bar">';
    for(var i=0;i<segs.length;i++){
      var s=segs[i];
      var color=s.kind==='parent'?'#0ea5e9':'#e74c3c';
      var w=Math.max(6,Math.round((s.t1-s.t0)/span*100));
      h+='<div class="fhist-seg" data-i="'+i+'" title="'+fmtTsH(s.t0)+'~'+fmtTsH(s.t1)+' '+s.path_str
        +'" style="width:'+w+'%;background:'+color+'"></div>';
    }
    // 切换点: 相邻段链路签名变化 → 橙色竖线 (悬停看切换内容)
    for(var i=1;i<segs.length;i++){
      if(segSig(segs[i-1])!==segSig(segs[i])){
        var left=Math.min(99,Math.max(1,((segs[i].t0-t0)/span*100)));
        h+='<div class="fhist-switch" style="left:'+left+'%"'
          +' title="'+segChangeDesc(segs[i-1],segs[i])+'"></div>';
      }
    }
    h+='<div id="fhist-cur" class="fhist-cur"></div></div>'
      +'<div class="fhist-legend"><span style="color:#0ea5e9">▮</span> 父链路 · '
      +'<span style="color:#e74c3c">▮</span> 路由路径 · '
      +'<span style="color:#f59e0b">▮</span> 链路切换点</div>'
      +'<div id="fhist-info" class="fhist-info"></div>';
    el.innerHTML=h;
    updateFocusHist();
  }
  function updateFocusHist(){
    var el=document.getElementById('focus-hist');
    if(!el||focusAid==null)return;
    var segs=(S.topo&&S.topo.link_snapshots)?S.topo.link_snapshots[''+focusAid]:null;
    if(!segs||!segs.length)return;
    var t0=segs[0].t0,t1=segs[segs.length-1].t1;
    var span=Math.max(t1-t0,1);
    var cur=document.getElementById('fhist-cur');
    if(cur)cur.style.left=Math.min(100,Math.max(0,(curT-t0)/span*100))+'%';
    var info=document.getElementById('fhist-info');
    if(info){
      var best=null;
      for(var i=0;i<segs.length;i++){
        var s=segs[i];
        if(s.t0>curT)break;
        if(slideMode&&curT-s.t1>60)continue;  // 与 snapAt 同语义 (30s 窗+顺延)
        best=s;
      }
      if(best){
        // S3 修复: link_snapshots 段无 path_str 字段 (那是 link-history 端点拼的),
        // 这里从段数据拼路径文本
        var evL={poll:'poll轮询',assoc:'入网关联',rr:'路由下一跳',down:'下行源路由'}[best.evidence]||'';
        var ps;
        if(best.kind==='parent'){
          ps='父: 0x'+best.parent.toString(16).toUpperCase().padStart(4,'0');
        }else{
          var chain=[focusAid].concat(best.relays||[]).concat([best.dst]);
          ps=chain.map(function(a){return '0x'+a.toString(16).toUpperCase().padStart(4,'0');}).join(' → ');
        }
        info.innerHTML='<span class="mono">'+ps+'</span>'
          +' <span class="t-10 text-dim">'+fmtTsH(best.t0)+'~'+fmtTsH(best.t1)
          +(evL?' · '+evL:'')+'</span>'
          +(slideMode&&curT-best.t1>60?' <span style="color:#d97706">⏳ 历史残影</span>':'');
      }else{
        info.innerHTML='<span class="t-10 text-dim">当前时刻无链路证据</span>';
      }
    }
  }
  function exitFocus(){
    focusAid=null;
    var bar=document.getElementById('focus-bar');
    if(bar)bar.style.display='none';
    // ⚠️ 2026-08-25 用户反馈: 退出后"还在过滤界面" — 曾保留当前时间窗
    // (S.topoT0/T1 不清) → 图仍是窗内视图; 退出 = 恢复全量视图
    var slEl=document.getElementById('tsl'); if(slEl)slEl.value=500;
    curT=sliderToTs(500);
    slideMode=false;  // S3-重构: 退出聚焦恢复全貌模式
    updateTimeLabel();
    reloadTopo();
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
    // ⚠️ S3 修复 (2026-08-28, test2 实锤): on_path 扩展 — 有父链路证据
    // (poll/assoc/rr/down 四来源) 的节点也是"链路上"节点。曾只认 RR 路径 →
    // test2 401 个下行源路由父节点被染黄 (用户反馈"有些节点还是黄色的")
    for(var i=0;i<ns.length;i++){
      if(ns[i].parent!=null&&!pathNodes[ns[i].aid])pathNodes[ns[i].aid]=[];
    }

    // ── 节点 ──
    var cyNodes=[];
    var hasPaths=rps.length>0;  // 无 Route Record 路径时全部按"在路径上"渲染, 否则 offpath 会让整图隐形
    // ⚠️ U13-B 聚焦模式: focusAid 非空时只渲染 协调器+聚焦节点+链路链 (downlink+parent 链)
    // ⚠️ S3-C (2026-08-28, 用户选择 A+B): focusCore=当前链路链 (实线);
    // focusGhost=历史段节点 (该节点历史链路的父/中继, 灰淡对比显示)
    var focusSet=null, focusCore=null;
    if(focusAid!=null&&ns.length){
      focusSet={}; focusCore={};
      focusSet[0]=1;focusCore[0]=1; focusSet[focusAid]=1;focusCore[focusAid]=1;
      var fnd=null; for(var fi=0;fi<ns.length;fi++){if(ns[fi].aid===focusAid){fnd=ns[fi];break;}}
      if(fnd){
        if(fnd.downlink)fnd.downlink.forEach(function(a){focusSet[a]=1;focusCore[a]=1;});
        var fcur=focusAid, fguard=0;
        while(fcur!=null&&fcur!==0&&fguard++<20){
          var fpn=null; for(var pi2=0;pi2<ns.length;pi2++){if(ns[pi2].aid===fcur){fpn=ns[pi2];break;}}
          if(fpn&&fpn.parent!=null){focusSet[fpn.parent]=1;focusCore[fpn.parent]=1;fcur=fpn.parent;}else break;
        }
      }
      // S3-C: 聚焦节点所有历史段的父/中继/dst 节点 → ghost 对比 (仅 focusSet, 非 core)
      var fsSegs=d.link_snapshots?d.link_snapshots[''+focusAid]:null;
      if(fsSegs){
        for(var gi=0;gi<fsSegs.length;gi++){
          var gs=fsSegs[gi];
          if(gs.kind==='parent'&&gs.parent!=null){focusSet[gs.parent]=1;}
          else if(gs.kind==='route'){
            if(gs.dst!=null)focusSet[gs.dst]=1;
            for(var gj=0;gj<(gs.relays||[]).length;gj++)focusSet[gs.relays[gj]]=1;
          }
        }
      }
    }
    for(var i=0;i<ns.length;i++){
      var n=ns[i]; var aid=n.aid;
      if(focusSet&&!focusSet[aid])continue;  // 聚焦: 非链路链节点不渲染
      var dt=n.device_type||'unknown';
      // S3-C: ghost 节点 = 聚焦时历史链路段的父/中继 (灰淡, 对比显示)
      var isGhost=focusCore!=null&&!focusCore[aid]&&aid!==focusAid;
      var onPath=(!hasPaths)||!!pathNodes[aid]||aid===0;  // 无路径全可见; 协调器永远可见
      // U14-2: label 双行 — 第二行型号 (model_id 非空时; 小节点放不下由 tooltip 兜底)
      // U14-3: behavior 类 (rejoining/sleeping/offline) — 仅 onpath 节点应用
      //   (offpath 仅 LS 可见节点是辅助渲染, 行为状态无意义)
      var model=n.model_id||'';
      // ⚠️ U13-B (2026-08-25): 密集模式 (>40 节点) 单行 label — 双行 (地址+型号)
      // 高度超过列间距, 文字压到下方节点; 型号移入 tooltip (已有)
      var dense=ns.length>40;
      // S3-重构: online=false = 窗内无在线证据 (终端无 poll / 路由无帧) → 灰显
      var online=n.online!==false;
      cyNodes.push({
        data:{id:''+aid,
          label:'0x'+aid.toString(16).toUpperCase().padStart(4,'0')+(model&&!dense?'\n'+model:''),
          aid:aid, device_type:dt, seen:n.seen, on_path:onPath,
          model_id:model, manufacturer_name:n.manufacturer_name||'',
          behavior:n.behavior||'', poll_interval:n.poll_interval,
          eui64:n.eui64||'', tx_count:n.tx_count, rx_count:n.rx_count,
          // U13: 协议级父链路 + 下行 source-route (芯科规范 relay 反转)
          // ⚠️ 字段名不能用 parent — Cytoscape data.parent 是复合节点保留字段
          // (2026-08-25 自审: 曾导致网关框住全部子设备), 改名 link_parent/link_ev
          link_parent:n.parent, link_ev:n.parent_evidence||'',
          downlink:n.downlink||null,
          inactive:!online},
        classes:onPath?(dt+' onpath'+(n.behavior?' '+n.behavior:'')+(dense?' dense':'')+(online?'':' inactive')+(isGhost?' ghost-node':'')):(online?'offpath':'offpath inactive')
      });
    }
    // ⚠️ S3-重构 (2026-08-27, 用户对齐): 节点全量返回 (后端 nodes 含所有出现过节点),
    // 在线状态协议判定 (online 字段) — 窗内无在线证据的节点灰显, 不消失不跳变
    // (曾 U13-A3 inactive_nodes: 基于事件集粗判, 终端持续 poll 却被灰显 — 用户反馈问题大)

    // ── 边: 数据流量 → 灰色细线背景 ──
    var cyEdges=[];
    var trafficSeen={};
    // ⚠️ S3 修复 (2026-08-28): cyNodeIds 提前构建 — 曾定义在链路快照段 (traffic 边
    // 之后), var 提升但值为 undefined → 聚焦检查 src/dst 时 TypeError → renderGraph
    // 崩溃 → canvas 0 (92 节点但图空白, 用户"无效果"另一根源)
    var cyNodeIds={}; for(var ni=0;ni<cyNodes.length;ni++)cyNodeIds[cyNodes[ni].data.id]=true;
    for(var i=0;i<es.length;i++){
      var e=es[i];
      // ⚠️ S3 修复 (2026-08-28, 聚焦无效果根因): 聚焦模式节点被过滤后,
      // 未检查 src/dst 是否在渲染集 → Cytoscape 创建边异常 → renderGraph 中断
      // → 链路边不画 → 拖动游标"完全没有效果" (t-0-28762 异常实锤)
      if(!cyNodeIds[''+e.src]||!cyNodeIds[''+e.dst])continue;
      var ek=Math.min(e.src,e.dst)+'-'+Math.max(e.src,e.dst);
      if(trafficSeen[ek]) continue;
      trafficSeen[ek]=true;
      cyEdges.push({
        data:{id:'t-'+ek, source:''+e.src, target:''+e.dst, count:e.count||0, edge_type:'traffic'},
        classes:'traffic-bg'
      });
    }

    // ── 边: U13 时刻游标 (2026-08-25 重构) — curT 时刻链路快照 ──
    // 每节点 T 时刻状态 = link_snapshots 分段中 t0<=curT 的最近一段:
    //   route 段 → 该时刻路径全链边; parent 段 → 该时刻 poll 父边
    // (曾用窗过滤 route_paths + 全程 parent — 时刻语义不精确, 用户反馈重做)
    // ⚠️ S3: cyNodeIds 已在 traffic 边段前构建 (曾定义于此导致 traffic 检查 TypeError)
    var snaps=d.link_snapshots||{};
    var lsKeys={};
    // ⚠️ S3-重构 (2026-08-27, 用户对齐: 默认全貌 + 游标时刻):
    //   全貌模式 (slideMode=false) = 每节点最近证据, 无窗限制 (链路现状图)
    //   时刻模式 (拖动游标) = 30s 证据窗 + 顺延前 30s:
    //     分段末帧距 curT 超过 60s (30 窗 + 30 顺延) → 证据过旧不算
    // ⚠️ S3-方案A (2026-08-27, 用户选择: 原位+残影): 三态链路 —
    //   cur   = 时刻窗内证据 → 正常链路边 (实线)
    //   stale = 无窗内证据但历史有 → 灰色虚线残影边 (节点留最后链路位置,
    //           不丢右上堆叠; 残影边参与 BFS 布局 = 位置 = 最后已知链路)
    //   none  = 从未有链路证据 → 待定区 (现状 off-path)
    function snapState(segs){
      if(!segs||!segs.length)return {state:'none'};
      var best=null, stale=null;
      for(var si=0;si<segs.length;si++){
        var s=segs[si];
        if(s.t0>curT)break;
        if(slideMode&&curT-s.t1>60){stale=s;continue;}
        best=s;
      }
      if(best)return {state:'cur',seg:best,staleSeg:stale};
      if(stale)return {state:'stale',seg:stale};
      return {state:'none'};
    }
    // ⚠️ S3 修复 (2026-08-28, 60A4 右上角实锤): cur 段边不可达 (父/链节点不在
    // 渲染集, 如 down 父被过滤) → 降级画 stale 历史段残影边, 避免节点孤立
    function segDrawable(s, aidN){
      if(!s)return false;
      if(s.kind==='parent')return !!cyNodeIds[''+s.parent];
      if(s.kind==='route'){
        var _ch=[aidN].concat(s.relays||[]).concat([s.dst]);
        for(var _ci=0;_ci<_ch.length-1;_ci++){
          if(!cyNodeIds[''+_ch[_ci]]||!cyNodeIds[''+_ch[_ci+1]])return false;
        }
        return true;
      }
      return false;
    }
    for(var aidS in snaps){
      var st=snapState(snaps[aidS]);
      if(st.state==='none')continue;
      var seg=st.seg;
      var aidN=parseInt(aidS);
      if(!cyNodeIds[''+aidN])continue;
      var isStale=st.state==='stale';
      if(!isStale&&!segDrawable(seg,aidN)&&segDrawable(st.staleSeg,aidN)){
        seg=st.staleSeg; isStale=true;  // 回退历史段 (残影边)
      }
      if(seg.kind==='route'){
        var chain=[aidN].concat(seg.relays||[]).concat([seg.dst]);
        for(var jj=0;jj<chain.length-1;jj++){
          var s3=''+chain[jj],t3=''+chain[jj+1];
          if(!cyNodeIds[s3]||!cyNodeIds[t3])continue;
          var ek3=Math.min(chain[jj],chain[jj+1])+'-'+Math.max(chain[jj],chain[jj+1]);
          if(lsKeys[ek3])continue;
          lsKeys[ek3]=true;
          if(isStale){  // 残影: 灰虚线 + 最后证据时间
            cyEdges.push({data:{id:'ls-'+ek3,source:s3,target:t3,edge_type:'route',cur:false,stale:true,last_ts:seg.t1},
              classes:'route-path stale-path'});
          }else{
            // 按节点分配路径色 (曾全部 path-c0 全红 — 用户反馈)
            cyEdges.push({data:{id:'ls-'+ek3,source:s3,target:t3,edge_type:'route',cur:true},classes:'route-path path-c'+(aidN%PATH_COLORS.length)});
          }
        }
      }else if(seg.kind==='parent'&&cyNodeIds[''+seg.parent]){
        var ek4=Math.min(aidN,seg.parent)+'-'+Math.max(aidN,seg.parent);
        if(!lsKeys[ek4]){lsKeys[ek4]=true;
          if(isStale){
            cyEdges.push({data:{id:'ls-'+ek4,source:''+aidN,target:''+seg.parent,edge_type:'parent',evidence:seg.evidence||'poll',stale:true,last_ts:seg.t1},classes:'parent-edge stale-path'});
          }else{
            cyEdges.push({data:{id:'ls-'+ek4,source:''+aidN,target:''+seg.parent,edge_type:'parent',evidence:seg.evidence||'poll'},classes:'parent-edge'});
          }
        }
      }
      // ⚠️ S3-C (2026-08-28, 用户选择 A+B): 聚焦节点历史链路段 ghost 叠加 —
      // 拖动游标时"从哪变到哪"一目了然 (旧父/旧路径灰淡虚线)
      if(focusAid!=null&&aidN===focusAid){
        var segsAll=snaps[aidS];
        for(var gi=0;gi<segsAll.length;gi++){
          var gs=segsAll[gi];
          if(gs===seg)continue;  // 当前段 (已画实线/残影)
          if(gs.kind==='parent'&&gs.parent!=null&&cyNodeIds[''+gs.parent]){
            var ek5=Math.min(aidN,gs.parent)+'-'+Math.max(aidN,gs.parent);
            if(!lsKeys[ek5]){lsKeys[ek5]=true;
              cyEdges.push({data:{id:'gh-'+ek5,source:''+aidN,target:''+gs.parent,edge_type:'parent',evidence:gs.evidence||'poll',ghost:true},classes:'parent-edge ghost-edge'});
            }
          }else if(gs.kind==='route'){
            var gchain=[aidN].concat(gs.relays||[]).concat([gs.dst]);
            for(var gj=0;gj<gchain.length-1;gj++){
              var gs3=''+gchain[gj],gt3=''+gchain[gj+1];
              if(!cyNodeIds[gs3]||!cyNodeIds[gt3])continue;
              var gk=Math.min(gchain[gj],gchain[gj+1])+'-'+Math.max(gchain[gj],gchain[gj+1]);
              if(lsKeys[gk])continue;
              lsKeys[gk]=true;
              cyEdges.push({data:{id:'gh-'+gk,source:gs3,target:gt3,edge_type:'route',ghost:true},classes:'route-path ghost-edge'});
            }
          }
        }
      }
    }
    // 节点 stale 标记 (tooltip 显示最后链路时间; 视觉: 淡化+灰虚线边框+label ⏳)
    // S3-方案A (2026-08-28 用户选择): "?" → ⏳ 沙漏 (链路等待中语义), 节点 opacity 0.65
    for(var sni=0;sni<cyNodes.length;sni++){
      var ndata=cyNodes[sni].data;
      var nst=snaps[ndata.aid]?snapState(snaps[ndata.aid]):{state:'none'};
      if(nst.state==='stale'){
        ndata.stale=true; ndata.last_link_ts=nst.seg.t1;
        ndata.label=String(ndata.label).replace(/[\s?⏳]+$/, '')+' ⏳';  // 去重防连加
        if(cyNodes[sni].classes.indexOf('inactive')<0)cyNodes[sni].classes+=' stale-node';
      }
    }

    // ⚠️ S3-重构 (2026-08-27, 用户对齐): Link Status 邻居关系不再画在拓扑图 —
    // 节点多时混乱; 邻居信息保留底部 📡 邻居面板 + 节点 tooltip LS 邻居数

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
        {selector:'node', style:{'background-color':'#3b82f6','shape':'ellipse','label':'data(label)','font-size':'9px','color':'#1e293b','text-valign':'bottom','text-halign':'center','text-margin-y':4,'border-width':1,'border-color':'#fff','width':28,'height':28,'text-wrap':'wrap'}},
        // 设备类型形状分类 (U7): 协调器=大六边形 / 路由器=菱形 / 终端=圆 / 未知=三角
        {selector:'node.coordinator', style:{'background-color':'#f59e0b','shape':'hexagon','border-color':'#d97706','border-width':3,'font-weight':'bold','width':60,'height':60,'text-margin-y':8}},
        {selector:'node.router', style:{'background-color':'#3b82f6','shape':'diamond','width':32,'height':32}},
        {selector:'node.end_device', style:{'background-color':'#16a34a','shape':'ellipse','width':22,'height':22}},
        {selector:'node.unknown', style:{'background-color':'#94a3b8','shape':'triangle','width':22,'height':22}},
        // U13-B2 (2026-08-25): 密集模式 — label 移入节点内部 (不依赖列间距)
        // + 节点缩小 (曾双行/单行 label 在节点下方, 间距 34px 只比节点 32px 多 2px → 文字必被压)
        // B3 (用户反馈样式丑): 深色字 + 白色描边 — 白字在亮色节点 (蓝/绿/橙) 对比差
        {selector:'node.dense', style:{'font-size':'8px','color':'#0f172a','text-outline-color':'#fff','text-outline-width':1.5,'text-valign':'center','text-halign':'center','text-margin-y':0,'font-weight':'bold'}},
        {selector:'node.dense.router', style:{'width':28,'height':28}},
        {selector:'node.dense.end_device', style:{'width':22,'height':22}},
        {selector:'node.dense.unknown', style:{'width':22,'height':22}},
        {selector:'node.dense.coordinator', style:{'width':54,'height':54,'font-size':'10px'}},
        // U14-3: 行为状态样式 — 重连橙虚线边框 / 休眠灰半透明 / 离线暗红边框
        // (角标 canvas 难实现, 用粗红边框 + tooltip 状态文字表达)
        {selector:'node.rejoining', style:{'border-color':'#f59e0b','border-style':'dashed','border-width':3}},
        {selector:'node.sleeping', style:{'opacity':0.55}},
        {selector:'node.offline', style:{'border-color':'#b91c1c','border-width':3}},
        // 路径节点: 紫框
        {selector:'node.onpath', style:{'border-width':3,'border-color':'#7c3aed'}},
        // 路径外节点: 半透明缩小
        {selector:'node.offpath', style:{'background-color':'#e2e8f0','opacity':0.3,'width':10,'height':10,'font-size':'7px','color':'#94a3b8','text-opacity':0}},
        // U13-A3: 窗外节点灰度保留 (窗口切换不跳变, 15% 透明灰点 + 小灰字)
        {selector:'node.inactive', style:{'background-color':'#cbd5e1','opacity':0.15,'width':14,'height':14,
          'font-size':'6px','color':'#64748b','text-opacity':0.6,'text-valign':'bottom','text-halign':'center','text-margin-y':2}},
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
        // ⚠️ S3-重构: 邻居边 CSS 移除 (Link Status 不上图)
        // U13: 协议级父链路 — 天蓝点线 + 箭头指向父 (poll/Assoc/RR/下行 证据, tooltip 标注类型)
        {selector:'edge.parent-edge', style:{'line-style':'dotted','line-color':'#0ea5e9','width':2,
          'target-arrow-shape':'triangle','target-arrow-color':'#0ea5e9','arrow-scale':0.7,'opacity':0.9}},
        // 路径行 hover 高亮 (路由路径链联动)
        {selector:'edge.path-hl', style:{'width':5,'opacity':1,'line-color':'#e11d48','target-arrow-color':'#e11d48'}},
        // S3-方案A (2026-08-27, 用户选择): 历史残影 — 时刻窗内无证据但有历史:
        //   灰虚线弱化边 (节点留最后链路位置) + 节点淡化 0.65 + 细灰虚线边框
        // (双类选择器压过 path-cX 单类颜色; 2026-08-28 用户选择: 加淡化)
        {selector:'edge.route-path.stale-path', style:{'line-style':'dashed','opacity':0.3,'width':1.5,'line-color':'#94a3b8','target-arrow-color':'#94a3b8'}},
        {selector:'edge.parent-edge.stale-path', style:{'line-style':'dashed','opacity':0.3,'width':1.5,'line-color':'#94a3b8','target-arrow-color':'#94a3b8'}},
        {selector:'node.stale-node', style:{'border-color':'#94a3b8','border-style':'dashed','border-width':1.5,'opacity':0.65}},
        // S3-C: 聚焦历史叠加 — ghost 节点 (历史链路段的父/中继, 灰淡) + ghost 边 (z 低于当前边)
        {selector:'node.ghost-node', style:{'opacity':0.35,'background-color':'#94a3b8','border-color':'#cbd5e1','border-width':1,'width':16,'height':16,'text-opacity':0.5}},
        {selector:'edge.ghost-edge', style:{'z-index':-1,'opacity':0.18,'line-style':'dashed','width':2,'line-color':'#94a3b8','target-arrow-color':'#94a3b8','target-arrow-shape':'none'}},
        // U13-C: 窗内非当前路径弱化 (同源多路径主次分明)
        {selector:'edge.route-alt', style:{'opacity':0.22,'line-style':'dashed','width':1.5}},
        {selector:'edge.hist-hl', style:{'width':6,'opacity':1,'line-color':'#e11d48','target-arrow-color':'#e11d48','z-index':999}},
      ],
        wheelSensitivity:0.3,
      });

      // ── 交互事件 (只绑定一次, 实例复用时保留) ──
      var tooltip=document.createElement('div');tooltip.id='cy-tt';tooltip.style.cssText='position:absolute;display:none;background:#1e293b;color:#fff;padding:6px 10px;border-radius:6px;font-size:11px;pointer-events:none;z-index:999;max-width:280px;white-space:pre-line';
      document.getElementById('cy-graph').appendChild(tooltip);

      cy.on('mouseover','node',function(e){var n=e.target;var d=n.data();var nbtEntry=topoNbt[d.aid];var nbCount=nbtEntry?Object.keys(nbtEntry).length:0;
        // S3-重构: 无在线证据节点 tooltip (终端窗内无 poll / 路由窗内无帧)
        if(d.inactive){tooltip.innerHTML='<b>'+d.label+'</b>\n当前时间窗无在线证据 (终端无 poll / 路由无帧)';tooltip.style.display='block';updateTooltipPos(e);return;}
        // U14-4: tooltip 增强 — EUI64/厂商型号/行为状态/poll 间隔/帧量收/发/LS 邻居数
        var tName={coordinator:'协调器',router:'路由器',end_device:'终端设备',unknown:'未知'}[d.device_type]||d.device_type;
        var bName={active:'活跃',sleeping:'休眠',rejoining:'重连中',offline:'离线',unknown:'未知'}[d.behavior]||'未知';
        var h='<b>'+String(d.label).replace(/\n/g,' ')+'</b> ('+tName+')';
        if(d.manufacturer_name)h+='\n厂商: '+d.manufacturer_name;
        if(d.model_id)h+='\n型号: '+d.model_id;
        if(d.eui64)h+='\nEUI64: '+d.eui64;
        h+='\n状态: '+bName;
        // S3-方案A: 时刻窗内无链路证据但有历史 → 标注最后链路时间
        if(d.stale&&d.last_link_ts)h+='\n⏳ 最后链路: '+fmtTs(d.last_link_ts);
        if(d.poll_interval)h+='\npoll 间隔: '+Math.round(d.poll_interval*10)/10+'s';
        if(d.tx_count!=null||d.rx_count!=null)h+='\n帧量: 发'+d.tx_count+'/收'+d.rx_count;
        // U13: 父链路 (协议级证据) + 下行 source-route
        // ⚠️ S3 修复 (2026-08-28): data 存的是 link_ev (parent 是 Cytoscape 保留字段),
        // 曾用 d.parent_evidence → undefined → tooltip "(undefined)"
        if(d.link_parent!=null){
          var evN={poll:'poll轮询',assoc:'入网关联',rr:'路由下一跳',down:'下行源路由'}[d.link_ev]||d.link_ev;
          h+='\n父链路: 0x'+Number(d.link_parent).toString(16).toUpperCase().padStart(4,'0')+' ('+evN+')';
        }
        if(d.downlink&&d.downlink.length){
          h+='\n下行: '+d.downlink.map(function(a){return '0x'+a.toString(16).toUpperCase().padStart(4,'0');}).join('→');
        }
        h+='\n'+(d.on_path?'在路径上':'不在路径上')+'\nLS邻居:'+nbCount;
        tooltip.innerHTML=h;tooltip.style.display='block';updateTooltipPos(e);});
    cy.on('mouseout','node',function(){tooltip.style.display='none';});
    cy.on('mouseover','edge',function(e){var ed=e.target;var d=ed.data();
      if(d.edge_type==='parent'){var evN={poll:'poll轮询',assoc:'入网关联',rr:'路由下一跳',down:'下行源路由'}[d.evidence]||d.evidence||'?';tooltip.innerHTML='<b>父链路 (协议级)</b>\n0x'+d.source.toString(16).toUpperCase()+' → 0x'+d.target.toString(16).toUpperCase()+'\n证据: '+evN+(d.stale&&d.last_ts?'\n⏳ 历史残影 (最后链路 '+fmtTs(d.last_ts)+')':'');}
      else if(d.edge_type==='traffic'){tooltip.innerHTML='<b>数据流</b>\n0x'+d.source.toString(16).toUpperCase()+' ↔ 0x'+d.target.toString(16).toUpperCase()+'\n'+d.count+' 包';}
      // ⚠️ S3 修复 (2026-08-27): U13 时刻游标重构后 route 边不再带 path_idx/hop
      // (边来自 link_snapshots 分段, 非 route_paths 行), 原 else 分支渲染 #NaN — 独立分支
      else if(d.edge_type==='route'){tooltip.innerHTML='<b>路由路径 (时刻链路)</b>\n0x'+d.source.toString(16).toUpperCase()+' → 0x'+d.target.toString(16).toUpperCase()+(d.stale&&d.last_ts?'\n⏳ 历史残影 (最后链路 '+fmtTs(d.last_ts)+')':'')+'\n当前时刻该设备的上行路径跳';}
      else{var hf=S.topoT0!=null||S.topoT1!=null;var st=hf?(d.active!==false?'● 活跃':'◌ 窗口外'):(d.is_current?'● 当前':'◌ 历史');tooltip.innerHTML='<b>路径 #'+(d.path_idx+1)+' 第'+(d.hop+1)+'跳</b>\n'+st+'\n'+d.path_str;};
      tooltip.style.display='block';updateTooltipPos(e);});
    cy.on('mouseout','edge',function(){tooltip.style.display='none';});

    function updateTooltipPos(e){
      // ⚠️ 修复 (2026-08-24 用户反馈): tooltip 是 #cy-graph 子元素 (absolute 相对容器),
      // 必须用 DOM 鼠标真实坐标 (clientX/Y) **减容器偏移**再定位 —
      // 曾用 Cytoscape 图坐标+容器偏移 (双重偏移更远) / clientX 不加容器偏移
      // (多算容器偏移, 实证 744=容器左缘340+404) 两版都错;
      // 正解: (页面坐标 - 容器偏移) + 14px 右侧
      var oe=(e&&e.originalEvent)||e||{};
      var x=oe.clientX!=null?oe.clientX:window.innerWidth/2;
      var y=oe.clientY!=null?oe.clientY:window.innerHeight/2;
      var gb=document.getElementById('cy-graph').getBoundingClientRect();
      tooltip.style.left=(x-gb.left+14)+'px';
      tooltip.style.top=(y-gb.top-8)+'px';
    }
    cy.on('mousemove',function(e){ if(tooltip.style.display==='block') updateTooltipPos(e); });  // tooltip 跟随鼠标移动

    // Click → 跳转时间线
    // ⚠️ U13-B (2026-08-25): 单击进入聚焦模式 (曾直接跳时间线) — 选节点看链路变化,
    // 时间线跳转移到聚焦横幅按钮; 再单击同节点退出聚焦
    cy.on('tap','node',function(e){var n=e.target;var d=n.data();
      if(d.inactive)return;
      if(focusAid===d.aid){exitFocus();return;}
      enterFocus(d.aid);
    });

      // 双击 → 高亮/淡出
      cy.on('dbltap','node',function(e){var n=e.target;var aid=n.data('aid');if(hlNode===aid){clearHighlight();return;}hlNode=aid;highlightNode(aid);});
    }else{
      cy.json({elements: cyNodes.concat(cyEdges)});   // 实例复用: 只替换元素, 保留样式表/事件/视图
    }

    // 默认固定列 — 深度+布局+fit一体化
    (function(){
      // ⚠️ U13 步骤 A (2026-08-25): 层级只基于**协议链路证据** (route 边 = RR 路径,
      // parent 边 = poll/Assoc 父链路) BFS — 曾混入 LS 邻居扩展 (物理 1-hop 可达 ≠
      // 转发层级, 用户反馈: A-B-C 中 C 被 LS 拉到深度 1 与 B 同列, 线交错);
      // LS 邻居仅作辅助边显示, 不参与深度; 无链路证据节点 → offpath 区
      var nd={};nd[0]=0;var chg=true;
      while(chg){chg=false;cy.edges().forEach(function(e){
        var et=e.data('edge_type');
        if(et!=='route'&&et!=='parent')return;
        var s=parseInt(e.data('source')),t=parseInt(e.data('target'));
        if(nd[s]!=null){var nd2=nd[s]+1;if(nd[t]==null||nd2<nd[t]){nd[t]=nd2;chg=true;}}
        if(nd[t]!=null){var nd2=nd[t]+1;if(nd[s]==null||nd2<nd[s]){nd[s]=nd2;chg=true;}}
      });}
      var pathMax=0;for(var k in nd)if(nd[k]>pathMax)pathMax=nd[k];
      cy.nodes().forEach(function(n){if(n.data('inactive'))return;var aid=n.data('aid');if(nd[aid]==null)nd[aid]=99;n.style('display','element');var d=nd[aid];if(d==null)d=99;var isOnPath2=n.data('on_path')===true;if(!isOnPath2){n.style('background-color','#f59e0b');n.style('border-color','#d97706');n.style('opacity','0.9');n.connectedEdges().forEach(function(e){if(e.data('edge_type')==='traffic'){e.style('line-color','#f59e0b');e.style('target-arrow-color','#f59e0b');e.style('opacity','0.6');}});}else{if(!n.hasClass('sleeping')){n.style('opacity','1');}}});
      var cols={};cy.nodes().forEach(function(n){var d=nd[n.data('aid')];if(d==null)d=99;if(!cols[d])cols[d]=[];cols[d].push(n);});
      var pos={},offAll=[];cy.nodes().forEach(function(n){var d=nd[n.data('aid')];if(d==null)d=99;if(d<99&&!n.data('on_path'))offAll.push(n);});
      // U13 密度自适应 (用户反馈 08-25: 大网络节点多 → 列超长/重叠不友好):
      // >40 节点: 同深度列拆子列 (每列 ≤18, 间距≥34 保证不重叠) + 列宽/offpath 区压缩
      var totalN=cy.nodes().length;
      var dense=totalN>40;
      var colGap=dense?34:48, perColMax=dense?18:1e9, colW=dense?150:200;
      var offGap=dense?24:36, offRowN=dense?20:15, offSep=dense?20:28;
      var offCols=Math.max(3,Math.ceil(offAll.length/12));if(offCols<1)offCols=1;var offPerCol=Math.ceil(offAll.length/offCols),offStartX=-(offCols+2)*colW;
      for(var c=0;c<offCols;c++){var chunk=offAll.slice(c*offPerCol,(c+1)*offPerCol),ch=Math.max(300,chunk.length*offGap);chunk.forEach(function(n,i){pos[n.id()]={x:offStartX+c*colW,y:-(ch/2)+(ch/(chunk.length+1))*(i+1)};});}
      pos['0']={x:-200,y:0};
      var rColX=0;for(var d2=1;d2<=pathMax;d2++){var nds3=cols[d2];if(!nds3)continue;nds3=nds3.filter(function(n){return nd[n.data('aid')]!=null&&nd[n.data('aid')]<99;});var pNodes=nds3.filter(function(n){return n.data('on_path');});if(pNodes.length===0){rColX+=colW;continue;}
        var subCols=Math.max(1,Math.ceil(pNodes.length/perColMax));
        for(var si=0;si<subCols;si++){
          var sub=pNodes.slice(si*perColMax,(si+1)*perColMax);
          if(!sub.length)continue;
          var ch3=Math.max(300,sub.length*colGap);
          sub.forEach(function(n,i){pos[n.id()]={x:rColX+si*colW,y:-(ch3/2)+(ch3/(sub.length+1))*(i+1)};});
        }
        rColX+=subCols*colW;
      }
      var d99=cols[99]||[];for(var oi=0;oi<d99.length;oi++){pos[d99[oi].id()]={x:rColX+100+(oi%offRowN)*offSep,y:-200+Math.floor(oi/offRowN)*24};}
      cy.layout({name:'preset',positions:pos,fit:true,padding:40}).run();
      if(userZoom!=null){cy.zoom(userZoom);cy.pan(userPan);}  // 恢复用户缩放
      document.getElementById('off-label').style.display='block';
      // ⚠️ S3 修复: 按实际布局状态显示按钮文本 (小网络 <10 节点默认力导,
      // 曾无条件写 '▦ 固定列' → 显示与实际布局不一致)
      document.getElementById('tlay').textContent=curLayout===1?'🔄 力导':'▦ 固定列';
    })();
    applySilentHidden();   // 数据刷新后恢复静默节点隐藏状态
  }

  // ═══ 布局引擎 ═══
  function runLayout(){
    if(!cy) return;
    // BFS深度: 协议链路证据 (route 边 = RR 路径 / parent 边 = poll/Assoc 父链路)
    // ⚠️ U13 步骤 A: 曾混入 LS 邻居扩展 (物理可达 ≠ 转发层级) — 已移除;
    // LS 仅作辅助边显示, 不参与层级
    var nodeDepth={}; nodeDepth[0]=0;
    var chg=true;while(chg){chg=false;
      cy.edges().forEach(function(e){
        var et=e.data('edge_type');
        if(et!=='route'&&et!=='parent')return;
        var s=parseInt(e.data('source'));var t=parseInt(e.data('target'));
        if(nodeDepth[s]!=null){var nd=nodeDepth[s]+1;if(nodeDepth[t]==null||nd<nodeDepth[t]){nodeDepth[t]=nd;chg=true;}}
        if(nodeDepth[t]!=null){var nd=nodeDepth[t]+1;if(nodeDepth[s]==null||nd<nodeDepth[s]){nodeDepth[s]=nd;chg=true;}}
      });
    }
    var pathMax=0; for(var k in nodeDepth)if(nodeDepth[k]>pathMax)pathMax=nodeDepth[k];
    cy.nodes().forEach(function(n){var aid=n.data('aid');if(nodeDepth[aid]==null)nodeDepth[aid]=99;});

    if(curLayout===0){  // fixed column
      // off-path节点换琥珀色+连线换可见色 (inactive 窗外节点跳过, 保持灰度)
      cy.nodes().forEach(function(n){if(n.data('inactive'))return;n.style('display','element');var d=nodeDepth[n.data('aid')];if(d==null)d=99;
        var isOnPath=n.data('on_path')===true; // 严格true才算路径节点
        if(!isOnPath){n.style('background-color','#f59e0b');n.style('border-color','#d97706');n.style('opacity','0.9');
          n.connectedEdges().forEach(function(e){if(e.data('edge_type')==='traffic'){e.style('line-color','#f59e0b');e.style('target-arrow-color','#f59e0b');e.style('opacity','0.6');}});
        }
        else{if(!n.hasClass('sleeping')){n.style('opacity','1');}}
      });

      var cols={}; cy.nodes().forEach(function(n){var d=nodeDepth[n.data('aid')];if(d==null)d=99;if(!cols[d])cols[d]=[];cols[d].push(n);});
      var posMap={};
      // left: off-path均分多列(~12节点/列)
      var offAll=[]; cy.nodes().forEach(function(n){var d=nodeDepth[n.data('aid')];if(d==null)d=99;if(d<99&&!n.data('on_path'))offAll.push(n);});
      // C3: off-path 节点按邻居连通分量分组 (物理层聚类), 组内连续排布
      // ⚠️ S3 修复 (2026-08-27): nbt 是 renderGraph 局部变量, runLayout 作用域无定义
      // (4688 小包 offAll 空未触发; 中继 78 节点切换布局 ReferenceError 实测)
      var nbt=topoNbt||{};
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
      // ⚠️ S3 修复: 删除引用 renderGraph 局部变量 userZoom/userPan 的失效行
      // (切换布局后 fit 全图, 无需保留缩放)
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
  // U13 (08-26): 4 个 section 头部点击折叠/展开 + 超长列表尾部"展开全部"按钮
  // 折叠状态模块级保存, 数据刷新重绘后保留
  var MAX_ROWS=20;                       // 超长列表截断阈值
  var foldSec={down:false,up:false,probe:false,fail:false};    // false=展开
  var expandAll={down:false,up:false,probe:false,fail:false};  // false=截断前20条
  function renderRoutePaths(d){
    var panel=document.getElementById('bp-routes');
    var paths=d.route_paths||[];
    var probes=d.route_probes||[];
    var failures=d.route_failures||[];

    if(paths.length===0 && probes.length===0 && failures.length===0){
      panel.innerHTML='<p class="empty">未发现路由事件 (该网络无 Route Record/Request/Status 帧)</p>';return;
    }

    var sep='<div class="sep"></div>';
    var h='';

    // ── section 辅助: 可点击折叠头 + 明细容器 (超长自动截断 + 展开全部按钮) ──
    function secHead(sec,titleHtml){
      return '<div class="path-head fold-head" data-sec="'+sec+'" title="点击折叠/展开">'
        +'<span class="fold-arrow">'+(foldSec[sec]?'▸':'▾')+'</span>'+titleHtml+'</div>';
    }
    function secBody(sec,rows,rowsLen){
      var body;
      if(rowsLen>MAX_ROWS&&!expandAll[sec]){
        body=rows.slice(0,MAX_ROWS).join('')
          +'<div class="expand-all" data-sec="'+sec+'">... 展开全部 '+rowsLen+' 条 ▾</div>';
      }else if(rowsLen>MAX_ROWS){
        body=rows.join('')+'<div class="expand-all" data-sec="'+sec+'">▲ 收起至前 '+MAX_ROWS+' 条</div>';
      }else{
        body=rows.join('');
      }
      return '<div class="path-body" data-body="'+sec+'"'+(foldSec[sec]?' style="display:none"':'')+'>'+body+'</div>';
    }

    // ── 下行路径 (Source Route, U13: 芯科规范 relay 反转) ──
    if(paths.length>0){
      var downRows=[];
      for(var di=0;di<paths.length;di++){
        var dp=paths[di];
        var dl=[dp.dst].concat((dp.relays||[]).slice().reverse()).concat([dp.src]);
        var dlStr=dl.map(function(a){return '0x'+a.toString(16).toUpperCase().padStart(4,'0');}).join(' → ');
        downRows.push('<div class="path-row" data-pidx="'+di+'"><span class="path-idx">#'+(di+1)+'</span> '
          +'<span class="mono">'+dlStr+'</span> <span class="t-10 text-dim">(源路由 '+dp.hop_count+' 跳)</span></div>');
      }
      h+=secHead('down','<span class="text-info text-strong">↓ 下行 (Source Route)</span> '
        +'<span class="t-10 text-dim">协调器→设备, Route Record relay 反转 (芯科: concentrator 存反转列表)</span> '
        +'<b>'+downRows.length+'条</b>')
        +secBody('down',downRows,downRows.length);
    }
    // ── 上行路径 (Route Record) ──
    if(paths.length>0){
      var srcPaths={}; for(var i=0;i<paths.length;i++){var s=paths[i].src;if(!srcPaths[s])srcPaths[s]=[];srcPaths[s].push(paths[i]);}
      var changed=0; for(var k in srcPaths){if(srcPaths[k].length>1)changed++;}
      var upRows=[];
      for(var i=0;i<paths.length;i++){
        var p=paths[i];
        var icon=p.is_current?'●':'◌';
        var color=p.is_current?'#7c3aed':'#94a3b8';
        var ts0=new Date(p.first_ts*1000);ts0=String(ts0.getHours()).padStart(2,'0')+':'+String(ts0.getMinutes()).padStart(2,'0')+':'+String(ts0.getSeconds()).padStart(2,'0');
        var ts1=new Date(p.last_ts*1000);ts1=String(ts1.getHours()).padStart(2,'0')+':'+String(ts1.getMinutes()).padStart(2,'0')+':'+String(ts1.getSeconds()).padStart(2,'0');
        var dur=p.first_ts===p.last_ts?'':(' ~ '+ts1);
        upRows.push('<div class="path-row'+(p.is_current?' text-strong':'')+'" data-pidx="'+i+'" title=\"首帧:'+ts0+' 末帧:'+ts1+' 共'+p.frame_count+'帧\">'
          +'<span class="p-icon" style="color:'+color+'">'+icon+'</span>'
          +'<span style="color:'+color+'">'+p.path_str+'</span>'
          +'<span class="p-tag text-dim">'+p.hop_count+'跳 ×'+p.frame_count+'帧</span>'
          +'<span class="p-tag text-dim">'+ts0+dur+'</span>'
          +(p.is_current?'<span class="p-tag text-success text-strong">当前</span>':'<span class="p-tag text-dim">历史</span>')
          +'</div>');
      }
      h+=secHead('up','<span class="text-route text-strong">↑ 上行路径 (Route Record)</span> '
        +paths.length+'条 | '+Object.keys(srcPaths).length+'个设备'
        +(changed>0?' | <b class="text-amber">'+changed+'个发生过路由变更</b>':''))
        +'<div class="path-tip">●实线=当前路由 · ◌虚线=历史路由</div>'
        +secBody('up',upRows,upRows.length);
    }

    // ── 下行探测 (Route Request) ──
    if(probes.length>0){
      var probeRows=[];
      for(var i=0;i<probes.length;i++){
        var pp=probes[i];
        var ts0=new Date(pp.first_ts*1000);ts0=String(ts0.getHours()).padStart(2,'0')+':'+String(ts0.getMinutes()).padStart(2,'0')+':'+String(ts0.getSeconds()).padStart(2,'0');
        probeRows.push('<div class="path-row" title=\"radius='+pp.radius+' 共'+pp.count+'次\">'
          +'<span class="p-icon text-info">→</span>'
          +'<span class="text-info">'+pp.path_str+'</span>'
          +'<span class="p-tag text-dim">×'+pp.count+'次</span>'
          +'<span class="p-tag text-dim">'+ts0+'</span>'
          +'</div>');
      }
      h+=sep+secHead('probe','<span class="text-info text-strong">↓ 下行探测 (Route Request)</span> '
        +probes.length+'对')
        +secBody('probe',probeRows,probeRows.length);
    }

    // ── 下行失败 (Network Status) ──
    if(failures.length>0){
      var failRows=[];
      for(var i=0;i<failures.length;i++){
        var f=failures[i];
        var ts=new Date(f.timestamp*1000);ts=String(ts.getHours()).padStart(2,'0')+':'+String(ts.getMinutes()).padStart(2,'0')+':'+String(ts.getSeconds()).padStart(2,'0');
        failRows.push('<div class="path-row">'
          +'<span class="p-icon text-danger">✕</span>'
          +'<span class="text-danger">'+f.path_str+'</span>'
          +'<span class="p-tag text-danger">'+f.status_name+'</span>'
          +'<span class="p-tag text-dim">'+ts+'</span>'
          +'</div>');
      }
      h+=sep+secHead('fail','<span class="text-danger text-strong">✕ 下行失败 (Network Status)</span> '
        +failures.length+'处')
        +secBody('fail',failRows,failRows.length);
    }

    panel.innerHTML=h;

    // ── 折叠交互: 点击 section 头折叠/展开 (DOM 操作, 不重绘) ──
    panel.querySelectorAll('.fold-head').forEach(function(hd){
      hd.addEventListener('click',function(){
        var sec=hd.dataset.sec;
        foldSec[sec]=!foldSec[sec];
        hd.querySelector('.fold-arrow').textContent=foldSec[sec]?'▸':'▾';
        var body=panel.querySelector('[data-body="'+sec+'"]');
        if(body) body.style.display=foldSec[sec]?'none':'block';
      });
    });
    // ── 展开全部/收起: 重绘 (状态在模块变量, 保留折叠状态) ──
    panel.querySelectorAll('.expand-all').forEach(function(btn){
      btn.addEventListener('click',function(){
        expandAll[btn.dataset.sec]=!expandAll[btn.dataset.sec];
        renderRoutePaths(S.topo||topoData);
      });
    });

    // ── 路径行 ↔ 图联动: hover 高亮图上对应路径 (U7 优化) ──
    // ⚠️ S3 修复 (2026-08-27): U13 时刻游标重构后 route 边来自 link_snapshots 分段,
    // 不再带 path_idx (按 path_idx 匹配永不命中) — 改为按路径链节点对匹配
    function highlightPathOnGraph(idx){
      if(!cy) return;
      cy.elements().removeClass('path-hl');
      var rp=(S.topo||topoData).route_paths&&(S.topo||topoData).route_paths[idx];
      if(!rp) return;
      var chain=[rp.src].concat(rp.relays||[]).concat([rp.dst]);
      cy.edges('[edge_type="route"]').forEach(function(e){
        var a=parseInt(e.data('source')),b=parseInt(e.data('target'));
        for(var j=0;j<chain.length-1;j++){
          if((a===chain[j]&&b===chain[j+1])||(a===chain[j+1]&&b===chain[j])){e.addClass('path-hl');break;}
        }
      });
    }
    function clearPathHighlight(){ if(cy) cy.elements().removeClass('path-hl'); }
    document.querySelectorAll('#bp-routes .path-row[data-pidx]').forEach(function(row){
      var idx=parseInt(row.dataset.pidx);
      row.addEventListener('mouseenter',function(){highlightPathOnGraph(idx);});
      row.addEventListener('mouseleave',function(){clearPathHighlight();});
    });
  }

  // ═══ 底部面板 Tab 切换 (层级树已移除 2026-08-05) ═══
  window.togBpTab=function(bp,btn){
    document.querySelectorAll('.bp-tab').forEach(function(b){b.classList.remove('on');b.style.borderBottomColor='transparent'});
    if(btn){btn.classList.add('on');btn.style.borderBottomColor='#3b82f6';}
    document.getElementById('bp-routes').style.display=bp==='routes'?'block':'none';
    document.getElementById('bp-history').style.display=bp==='history'?'block':'none';
    document.getElementById('bp-neighbors').style.display=bp==='neighbors'?'block':'none';
    if(bp==='history') renderHistoryPanel();
    if(bp==='neighbors') renderNeighborPanel();
  };

  // ═══ 链路历史面板 (U13: 选节点 → 链路变化时间轴 → 点段看当时链路) ═══
  var histAid=null, histSegs=null;
  function fmtTsH(ts){
    var d=new Date(ts*1000);
    return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')+':'+d.getSeconds().toString().padStart(2,'0');
  }
  function renderHistoryPanel(){
    var panel=document.getElementById('bp-history');
    var ns=S.topo?S.topo.nodes:[];
    // 有链路证据的节点 (parent 或 downlink 或 RR 源)
    var candidates=ns.filter(function(n){
      return (n.parent!=null)||(n.downlink&&n.downlink.length)||(n.aid===0);
    });
    var h='<div class="t-11 mb-1">选择节点查看链路变化时间轴 (RR 路径切换 / poll 父变更):</div>'
      +'<select id="hist-sel" class="mono t-11">';
    candidates.forEach(function(n){
      h+='<option value="'+n.aid+'">0x'+n.aid.toString(16).toUpperCase().padStart(4,'0')+(n.model_id?' '+n.model_id:'')+'</option>';
    });
    h+='</select><span id="hist-info" class="t-10 text-muted" style="margin-left:8px"></span>';
    h+='<div id="hist-timeline" class="mt-1"></div>';
    panel.innerHTML=h;
    var sel=document.getElementById('hist-sel');
    if(histAid!=null&&candidates.some(function(n){return n.aid===histAid;}))sel.value=''+histAid;
    sel.addEventListener('change',function(){histAid=parseInt(this.value);loadHist();});
    // ⚠️ S3 修复: 首次打开 histAid=null → 请求 aid=null → 422 假象 "0 段链路证据"
    if(histAid==null)histAid=parseInt(sel.value);
    if(sel.value)loadHist();
  }
  function loadHist(){
    var info=document.getElementById('hist-info');
    var tl=document.getElementById('hist-timeline');
    if(!info||!tl)return;
    info.textContent='加载中...';
    var params=[];
    if(S.topoPan)params.push('pan='+S.topoPan);
    if(S.topoT0!=null)params.push('time_start='+S.topoT0);
    if(S.topoT1!=null)params.push('time_end='+S.topoT1);
    A.get('/api/topology/link-history?aid='+histAid+(params.length?'&'+params.join('&'):'')).then(function(d){
      histSegs=d.segments||[];
      info.textContent=d.error||(histSegs.length+' 段链路证据');
      if(!histSegs.length){tl.innerHTML='<p class="empty">无链路证据帧</p>';return;}
      var t0=histSegs[0].t0,t1=histSegs[histSegs.length-1].t1;
      var span=Math.max(t1-t0,1);
      var h='<div class="hist-bar">';
      for(var i=0;i<histSegs.length;i++){
        var s=histSegs[i];
        var color=s.kind==='parent'?'#0ea5e9':PATH_COLORS[i%PATH_COLORS.length];
        var w=Math.max(8,Math.round((s.t1-s.t0)/span*100));
        h+='<div class="hist-seg" data-i="'+i+'" title="'+fmtTsH(s.t0)+'~'+fmtTsH(s.t1)+' '+s.path_str
          +'" style="width:'+w+'%;background:'+color+'"></div>';
      }
      h+='</div><div class="hist-legend t-10 text-muted">色块=链路稳定段 · 悬停看路径 · 点击高亮当时链路</div>'
        +'<div id="hist-detail" class="t-11 mt-1"></div>';
      tl.innerHTML=h;
      tl.querySelectorAll('.hist-seg').forEach(function(b){
        b.addEventListener('click',function(){
          var i=parseInt(this.dataset.i);var s=histSegs[i];
          // 高亮该段路径边
          cy.edges().removeClass('hist-hl');
          if(s.kind==='route'&&s.relays){
            var chain=[histAid].concat(s.relays).concat([s.dst]);
            cy.edges().forEach(function(e){
              var a=parseInt(e.data('source')),b=parseInt(e.data('target'));
              for(var j=0;j<chain.length-1;j++){
                if((a===chain[j]&&b===chain[j+1])||(a===chain[j+1]&&b===chain[j])){e.addClass('hist-hl');break;}
              }
            });
          }
          // S3-重构: parent 段标注证据类型 (poll/assoc/down/rr)
          var evLabel=s.kind==='parent'
            ?('父链路 ('+({poll:'poll轮询',assoc:'入网关联',down:'下行源路由'}[s.evidence]||'路由下一跳')+'):')
            :'上行路径: ';
          document.getElementById('hist-detail').innerHTML='<b>'+fmtTsH(s.t0)+' ~ '+fmtTsH(s.t1)+'</b> '
            +evLabel+'<span class="mono">'+s.path_str+'</span>'
            +(s.kind==='route'&&s.relays.length?' <span class="t-10 text-dim">'+((s.t1-s.t0)+'s 稳定')+'</span>':'');
        });
      });
    }).catch(function(e){
      info.textContent='加载失败';
      tl.innerHTML='<p class="text-danger">'+e.message+'</p>';
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
        var ts=new Date((nb.last_seen_ts||0)*1000);ts=String(ts.getHours()).padStart(2,'0')+':'+String(ts.getMinutes()).padStart(2,'0')+':'+String(ts.getSeconds()).padStart(2,'0');
        th+='<tr onclick="S.topoAddr=\'0x'+addr.toString(16).toUpperCase().padStart(4,'0')+'\';S.topoT0=null;S.topoT1=null;location.hash=\'tl\'">'
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

  // ═══ S3 (2026-08-28, 用户反馈): 节点过滤手段 — 侧栏节点搜索 + 🎯 聚焦按钮 ═══
  var tsearchInput=document.getElementById('tsearch');
  function renderSearchList(){
    var list=document.getElementById('tsearch-list');
    if(!list)return;
    var q=(tsearchInput.value||'').trim().toLowerCase();
    var ns=(S.topo&&S.topo.nodes)||[];
    if(!q){list.innerHTML='<div class="t-10 text-dim">输入地址/型号/厂商过滤 (点击聚焦)</div>';return;}
    var hits=[];
    for(var i=0;i<ns.length;i++){
      var n=ns[i];
      var lbl='0x'+n.aid.toString(16).toUpperCase().padStart(4,'0');
      var model=n.model_id||'', mf=n.manufacturer_name||'';
      if(lbl.toLowerCase().indexOf(q)>=0||model.toLowerCase().indexOf(q)>=0
         ||(mf&&mf.toLowerCase().indexOf(q)>=0))hits.push(n);
    }
    if(!hits.length){list.innerHTML='<div class="t-10 text-dim">无匹配节点</div>';return;}
    var h='';
    for(var i=0;i<Math.min(hits.length,30);i++){
      var n=hits[i];
      var lbl='0x'+n.aid.toString(16).toUpperCase().padStart(4,'0');
      h+='<div class="tsearch-item" data-aid="'+n.aid+'">'
        +'<span class="mono t-11">'+lbl+'</span>'
        +(n.model_id?' <span class="t-10 text-dim">'+n.model_id+'</span>':'')
        +(n.manufacturer_name?' <span class="t-10 text-dim">'+n.manufacturer_name+'</span>':'')
        +'</div>';
    }
    list.innerHTML=h;
    list.querySelectorAll('.tsearch-item').forEach(function(it){
      it.addEventListener('click',function(){enterFocus(parseInt(this.dataset.aid));});
    });
  }
  if(tsearchInput){tsearchInput.addEventListener('input',renderSearchList);renderSearchList();}
  document.getElementById('tfocus').addEventListener('click',function(){
    var av=document.getElementById('taddr').value.trim();
    if(!av){document.getElementById('taddr').title='先输入节点地址 (hex)';return;}
    var aid=parseInt(av.replace(/^0x/i,''),16);
    if(isNaN(aid)){document.getElementById('taddr').title='无效地址 (hex)';return;}
    var ns=(S.topo&&S.topo.nodes)||[];
    var found=false;
    for(var i=0;i<ns.length;i++){if(ns[i].aid===aid){found=true;break;}}
    if(!found){document.getElementById('taddr').title='节点不在当前图';return;}
    enterFocus(aid);
  });

  // ═══ 按钮事件 ═══
  document.getElementById('tgo').addEventListener('click',function(){
    var av=document.getElementById('taddr').value.trim();
    if(av){locateAddr();return;}   // 有地址 → 定位 (nodes 页跳转也走这里)
    var pv=document.getElementById('tpan').value.trim();S.topoPan=pv||null;
    loadData(pv,function(d){try{renderGraph(d);}catch(e){} try{renderRoutePaths(d);}catch(e){}});
  });
  document.getElementById('trst').addEventListener('click',function(){
    document.getElementById('tpan').value='';document.getElementById('taddr').value='';
    S.topoPan=null;S.topoAddr=null;S.topoT0=null;S.topoT1=null;hlNode=null;  // ⚠️ S3: 时间窗状态一并清 (残留影响后续跳时间线带旧窗)
    // ⚠️ U13-B 修复 (用户反馈 08-25): 重置必须退出聚焦模式 + 恢复全部时间窗,
    // 否则 focusAid 残留 → 重置后仍只显示聚焦链路链节点
    focusAid=null;
    var fb=document.getElementById('focus-bar');if(fb)fb.style.display='none';
    var slR=document.getElementById('tsl');if(slR)slR.value=500;
    curT=sliderToTs(500);
    slideMode=false;  // S3-重构: 重置恢复全貌模式
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

  // ═══ 时间滑块 (时刻游标, U13 2026-08-25 重构: 单滑块 = 时刻, 无窗口档位) ═══
  // ⚠️ S3 清理 (2026-08-27): 删除 twin-size 档位时代死代码
  // (getWinSize/getTimeWindow/updateTimeScale/applyTimeFilter/showPreviewMask/
  //  hidePreviewMask/stepWindow/setWindowFromSize — twin-size 元素已删, 调用即 TypeError)
  function fmtTs(ts){var d=new Date(ts*1000);return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')+':'+d.getSeconds().toString().padStart(2,'0');}
  function sliderToTs(val){return tsStart+(tsEnd-tsStart)*(val/1000);}
  function tsToSlider(ts){return Math.round((ts-tsStart)/(tsEnd-tsStart)*1000);}

  function updateTimeLabel(){
    // U13 时刻游标: 显示当前时刻
    var el=document.getElementById('ttime-label');
    if(el&&curT!=null) el.textContent=fmtTs(curT);
  }

  // ⚠️ U13 时刻游标 (2026-08-25 重构): 滑块 = 时刻, 拖动实时本地重渲染 (不请求后端)
  window.onTimeSlide=function(){
    slideMode=true;  // S3-重构: 用户拖动 = 时刻视图 (30s 证据窗, 默认恢复全貌)
    var v=parseInt(document.getElementById('tsl').value);
    curT=sliderToTs(v);
    updateTimeLabel();
    updateFocusHist();  // S3-C: 聚焦时间轴指针跟随
    clearTimeout(tSliderTO);
    tSliderTO=setTimeout(function(){ if(S.topo) renderGraph(S.topo); },120);
  };
  window.onTimeSlideEnd=function(){
    clearTimeout(tSliderTO);
    updateFocusHist();
    if(S.topo) renderGraph(S.topo);
  };


  // S.topoT0/T1 → 绝对时间戳: 兼容数字 (拓扑滑块) / "HH:MM:SS" 字符串 (时间线保存)
  // ⚠️ P2 修复: 此前字符串直接赋给 tsStart → 数值运算 NaN, 且 tsStart/tsEnd 被覆盖破坏滑块比例
  function topoTs(v, baseTs){
    if(v==null)return null;
    if(typeof v==='number')return v;
    var parts=String(v).split(':');
    if(parts.length<2||!baseTs)return null;
    var h=parseInt(parts[0]),m=parseInt(parts[1]),s=parseInt(parts[2])||0;
    if(isNaN(h)||isNaN(m))return null;
    var d=new Date(baseTs*1000);
    // 时区修复 (08-13): 输入为本地时间 → 本地 Date 构建 (曾 Date.UTC 偏 8h)
    return new Date(d.getFullYear(),d.getMonth(),d.getDate(),h,m,s).getTime()/1000;
  }

  // 时间线时间窗口 → 拓扑窗口 UI (档位 + 滑块中心 + 标签)
  function syncWinFromTimeline(){
    if(tlT0==null||tlT1==null)return;
    var ws=tlT1-tlT0;
    if(ws<=0)return;
    var sel=document.getElementById('twin-size');
    if(sel){
      var opts=[30,60,120,300];
      var best=opts[0];
      for(var oi=1;oi<opts.length;oi++){if(Math.abs(opts[oi]-ws)<Math.abs(best-ws))best=opts[oi];}
      sel.value=String(best);
    }
    tCenter=(tlT0+tlT1)/2;
    var sl=document.getElementById('tsl');
    if(sl)sl.value=tsToSlider(tCenter);
    updateTimeLabel();
  }

  // 获取抓包时间范围 + 时间线过滤窗口同步 (P2)
  var tlT0=null, tlT1=null;
  A.get('/api/import/status').then(function(s){
    dataTotal=s.total||0;
    tsStart=s.ts_start;tsEnd=s.ts_end;  // tsStart/tsEnd 始终 = 抓包范围 (滑块比例/刻度条基准)
    if(curT==null)curT=tsStart+(tsEnd-tsStart)/2;  // U13 时刻游标初始 = 中点
    var t0n=topoTs(S.topoT0, tsStart), t1n=topoTs(S.topoT1, tsStart);
    if(t0n!=null&&t1n!=null&&t1n>t0n){tlT0=t0n;tlT1=t1n;}
    else if(t0n!=null){tlT0=t0n;}
    syncWinFromTimeline();
    updateTimeLabel();

    // ═══ 初始加载 (U13 时刻游标: 全量加载含 link_snapshots, 拖动游标本地过滤) ═══
    var initPan=S.topoPan||'';
    loadData(initPan,function(d){
      try{renderGraph(d);}catch(e){console.error(e);}
      try{renderRoutePaths(d);}catch(e){console.error(e);}
      try{if(S.topoAddr&&cy){var aid=parseInt(S.topoAddr,16);highlightNode(aid);}}catch(e){}
    });
  });
});
