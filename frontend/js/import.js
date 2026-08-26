// import.js — 导入页面模块 (ES module)
// S1 自审 (2026-08-26, 用户需求): CSV 导入已删除, 只保留抓包导入 (pcap/cubx)
import { S, A, sb, sbTask, sr, setProg, setErr, doPI, pollImport } from './state.js';

reg('import',function(){
  var h='<div class="card"><h3>📂 数据导入</h3>'
    +'<div class="file-drop" id="pdrop"><p>拖拽 .pcap / .cubx 文件到此处 (支持多选)</p><input type="file" id="pfinp" accept=".pcap,.pcapng,.cubx" multiple class="hidden"></div>'
    +'<button class="btn btn-o" id="plpath">或输入本地路径 (逗号分隔多个)...</button>'
    +'<div id="pkey-panel" class="card key-panel">'
      +'<h4 id="pkey-toggle">🔑 密钥管理 ▸</h4>'
      +'<div id="pkey-body" class="t-11 hidden"></div>'
    +'</div>'
    +'<div id="cubx-prescan" class="card hidden">'
      +'<h4>⏱ 大包时间窗拆分导入 (U11)</h4>'
      +'<p id="cs-info" class="t-11"></p>'
      +'<div id="cs-hist" class="cs-hist"></div>'
      +'<div class="cs-sliders">'
        +'<input type="range" id="cs-s1" class="cs-range">'
        +'<input type="range" id="cs-s2" class="cs-range">'
      +'</div>'
      +'<div class="cs-time-inputs">'
        +'<span class="t-11">精确时间 (月-日 时:分):</span>'
        +'<input id="cs-t1m" class="mono w-40" maxlength="2" placeholder="08">'
        +'<span class="t-11">-</span>'
        +'<input id="cs-t1d" class="mono w-40" maxlength="2" placeholder="13">'
        +'<span class="t-11">&nbsp;</span>'
        +'<input id="cs-t1h" class="mono w-40" maxlength="2" placeholder="04">'
        +'<span class="t-11">:</span>'
        +'<input id="cs-t1n" class="mono w-40" maxlength="2" placeholder="49">'
        +'<span class="t-11">→</span>'
        +'<input id="cs-t2m" class="mono w-40" maxlength="2" placeholder="08">'
        +'<span class="t-11">-</span>'
        +'<input id="cs-t2d" class="mono w-40" maxlength="2" placeholder="13">'
        +'<span class="t-11">&nbsp;</span>'
        +'<input id="cs-t2h" class="mono w-40" maxlength="2" placeholder="05">'
        +'<span class="t-11">:</span>'
        +'<input id="cs-t2n" class="mono w-40" maxlength="2" placeholder="03">'
        +'<button class="btn btn-o btn-sm" id="cs-tapply">应用</button>'
      +'</div>'
      +'<p id="cs-win" class="t-11 text-strong"></p>'
      +'<div class="mt-1">'
        +'<button class="btn btn-p" id="cs-go">拆分子包</button> '
        +'<button class="btn btn-o" id="cs-cancel">取消 (整包导入)</button> '
        +'<button class="btn btn-r btn-sm" id="cs-close">关闭面板 (换别的包)</button>'
      +'</div>'
      +'<div id="cs-subs" class="cs-subs mt-1"></div>'
    +'</div>'
    +'<div id="prog" class="prog hidden"><span class="spin"></span><span id="imsg" class="t-11"></span><div class="bar" id="pbar"><div class="bar-fill" id="pfill"></div></div></div></div>';
  h+='<div class="card hidden" id="sout"><h3>📊 导入结果</h3><div id="sdiv"></div>'
    +'<button class="btn btn-p mt-2" id="gotopo">查看拓扑 →</button> '
    +'<button class="btn btn-r mt-2" id="clr">清除数据</button></div>';
  document.getElementById('mc').innerHTML=h;
  A.get('/api/import/last').then(function(d){if(d&&d.ok){sr(d,d.filename||'');}}).catch(function(){});
  setTimeout(function(){loadKeyPanel();},200);

  // ── 本地路径导入 (后台任务 + 轮询真实进度; 失败内联显示, 不弹 alert) ──
  function importPath(url, paramName, p, fname){
    setProg('提交中...', 1);
    var fd=new FormData();fd.append(paramName,p);
    fetch(url,{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
      if(d&&d.ok&&d.task_id){pollImport(d.task_id,fname);}
      else{setProg('');setErr((d&&d.error)||'导入失败');}
    }).catch(function(e){setErr('网络错误: '+e.message);});
  }

  // ── 抓包导入 (拖拽 / 文件选择 / 本地路径) ──
  var pdrop=document.getElementById('pdrop'),pinp=document.getElementById('pfinp');
  pdrop.addEventListener('click',function(){pinp.click()});
  pdrop.addEventListener('dragover',function(e){e.preventDefault()});
  pdrop.addEventListener('drop',function(e){e.preventDefault();if(e.dataTransfer.files.length)doPI(e.dataTransfer.files)});
  pinp.addEventListener('change',function(){if(pinp.files.length)doPI(pinp.files)});
  document.getElementById('plpath').addEventListener('click',function(){
    var p=prompt('pcap/cubx 文件路径 (逗号分隔多个):');if(!p)return;
    var isCubx=p.toLowerCase().endsWith('.cubx');
    if(isCubx){
      // U11: cubx 先预扫 — >30MB 进时间窗拆分面板, 小文件直接导入
      importLocalCubx(p,p.split(/[\\\\/]/).pop());
    }else{
      importPath('/api/import/local-pcap','paths',p,p.split(/[\\\\/]/).pop());
    }
  });

  // ── U11: 大 cubx 时间窗拆分导入 (预扫 → 选窗 → 拆分 → 自动导入) ──
  // 拖拽/文件选择大包入口 (state.js doPI 调用): 上传暂存 + 预扫 → 面板
  window._stageCubx=function(file, fname){
    setProg('上传大包暂存中 ('+Math.round(file.size/1048576)+'MB)...', 5);
    var fd=new FormData();fd.append('file',file);
    fetch('/api/cubx/upload-stage',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
      if(d&&d.path&&d.prescan){
        setProg('',0);
        showPrescanPanel(d.prescan,d.path,fname);
      }else{setProg('');setErr((d&&d.error)||'暂存失败');}
    }).catch(function(e){setErr('暂存失败: '+e.message);});
  };
  function fmtTsWin(ts){ var d=new Date(ts*1000);
    return (d.getMonth()+1)+'-'+d.getDate()+' '+d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0'); }
  function importLocalCubx(path, fname){
    setProg('预扫描中...', 5);
    var fd=new FormData();fd.append('path',path);
    fetch('/api/cubx/prescan',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
      setProg('',0);
      if(d.error){setErr(d.error);return;}
      // 大包阈值 1MB (用户定义 08-13: 大于 1M 即大包可拆)
      if(d.file_mb>1){showPrescanPanel(d,path,fname);}
      else{importPath('/api/import/local-cubx','path',path,fname);}
    }).catch(function(e){setErr('预扫失败: '+e.message);});
  }
  function showPrescanPanel(d, path, fname){
    // U11: 面板状态持久化 (S.cubxPrescan) — 切页回来 reg() 重建时恢复
    var prev = S.cubxPrescan;
    S.cubxPrescan={prescan:d, path:path, fname:fname};
    var panel=document.getElementById('cubx-prescan');
    // 概览
    document.getElementById('cs-info').innerHTML='文件 '+d.file_mb+'MB · 物理帧 '+d.total_frames.toLocaleString()
      +' · 时长 '+Math.round(d.duration_s/60)+' 分钟 · 信道 '+Object.keys(d.channels).join('/')
      +(d.lqi?(' · LQI '+d.lqi.avg):'')+(d.rssi?(' · RSSI '+d.rssi.avg+'dBm'):'');
    // 直方图 (60 桶 div)
    var maxC=1;d.histogram.forEach(function(h){if(h.count>maxC)maxC=h.count;});
    document.getElementById('cs-hist').innerHTML='<div class="cs-hist-wrap">'+d.histogram.map(function(h){
      var hgt=Math.max(2,Math.round(h.count/maxC*70));
      return '<div class="cs-bar" style="height:'+hgt+'px" title="'+fmtTsWin(h.ts_start)+': '+h.count.toLocaleString()+' 帧"></div>';
    }).join('')+'</div>';
    // 双滑块 (ts_start/ts_end ∈ [ts_first, ts_last])
    var s1=document.getElementById('cs-s1'),s2=document.getElementById('cs-s2');
    s1.min=s2.min=d.ts_first; s1.max=s2.max=d.ts_last;
    s1.value=d.ts_first; s2.value=d.ts_last;
    // S1 (用户反馈 08-13: 拆分面板状态保持): 同素材重建时恢复上次窗口选择
    if(prev && prev.winStart!=null && prev.prescan && prev.prescan.ts_first===d.ts_first){
      s1.value=Math.max(+d.ts_first, +prev.winStart);
      s2.value=Math.min(+d.ts_last, +prev.winEnd);
    }
    var lbl=document.getElementById('cs-win');
    function updWin(){ lbl.textContent='窗口: '+fmtTsWin(+s1.value)+' → '+fmtTsWin(+s2.value)
      +' ('+Math.round((+s2.value-+s1.value)/60)+' 分钟)'; }
    s1.oninput=s2.oninput=updWin; updWin();
    // 精确时间输入框重置 (数字框: 月-日 时:分, 解析/应用逻辑在 reg 一次性绑定区)
    ['cs-t1m','cs-t1d','cs-t1h','cs-t1n','cs-t2m','cs-t2d','cs-t2h','cs-t2n']
      .forEach(function(i){document.getElementById(i).value='';});
    panel.classList.remove('hidden');
    panel.dataset.path=path; panel.dataset.fname=fname;
    panel.dataset.tsFirst=d.ts_first; panel.dataset.tsLast=d.ts_last;
  }
  var csPanel=document.getElementById('cubx-prescan');
  if(csPanel){
    document.getElementById('cs-go').addEventListener('click',function(){
      var path=csPanel.dataset.path;
      var tsStart=+document.getElementById('cs-s1').value,tsEnd=+document.getElementById('cs-s2').value;
      if(tsEnd<=tsStart){setErr('窗口无效: 结束时间必须大于开始时间');return;}
      // S1: 保存窗口选择 (切页回来恢复用, 用户反馈 08-13)
      if(S.cubxPrescan){S.cubxPrescan.winStart=tsStart;S.cubxPrescan.winEnd=tsEnd;}
      // 只拆不导 (定义核对 08-13): 轮询拆分任务 → 追加子包清单, 手动导入
      setProg('拆分中...',1);
      var fd=new FormData();fd.append('path',path);
      fd.append('ts_start',tsStart);fd.append('ts_end',tsEnd);
      fetch('/api/cubx/split',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
        if(!(d&&d.ok&&d.task_id)){setProg('');setErr((d&&d.error)||'拆分失败');return;}
        var tries=0;
        var timer=setInterval(function(){
          A.get('/api/import/progress?task_id='+d.task_id).then(function(p){
            if(!p||p.status==='running'){
              var lbl=(p?p.stage||'拆分中':'拆分中')+' '+(p&&p.percent!=null?p.percent+'%':'');
              sbTask('⟳ '+lbl,'run');
              // S1: 页内进度条同步 (此前只更新顶栏, 页内条停在 1% "拆分中...")
              setProg(lbl+'',p&&p.percent!=null?p.percent:0);
              if(++tries>1000){clearInterval(timer);setProg('');setErr('拆分超时 (5 分钟)');}
              return;
            }
            clearInterval(timer);
            if(p.status==='done'&&p.result){
              setProg('',0);
              // S1: 完成清理顶栏 (此前 done 分支不清 → 顶栏残留 "⟳ 时间窗拆分 N%")
              sb(S.pkts+'包 | '+S.nodes+'节点');
              S.cubxSubs=S.cubxSubs||[];
              S.cubxSubs.push({winStart:tsStart, winEnd:tsEnd,
                               frames:p.result.out_frames, path:p.result.out_path});
              renderSubs();
            }else{setProg('');setErr((p&&p.error)||'拆分失败');}
          }).catch(function(){if(++tries>1000){clearInterval(timer);setProg('');setErr('拆分超时');}});
        },300);
      }).catch(function(e){setErr('网络错误: '+e.message);});
    });
    document.getElementById('cs-cancel').addEventListener('click',function(){
      csPanel.classList.add('hidden');
      S.cubxPrescan=null;
      importPath('/api/import/local-cubx','path',csPanel.dataset.path,csPanel.dataset.fname);
    });
    // 关闭面板 (换别的包): 清面板状态 + 子包清单, 不导入 — 用户反馈 08-13
    document.getElementById('cs-close').addEventListener('click',function(){
      csPanel.classList.add('hidden');
      S.cubxPrescan=null;
      S.cubxSubs=null;
      renderSubs();
      setProg('',0);
    });
  }
  // U11: 精确时间输入应用 (一次性绑定; MM-DD HH:MM:SS, 素材年份) → 同步滑块
  document.getElementById('cs-tapply').addEventListener('click',function(){
    var panel=csPanel;
    var tsFirst=+panel.dataset.tsFirst, tsLast=+panel.dataset.tsLast;
    if(!tsFirst||!tsLast){setErr('先预扫素材再输入时间');return;}
    // 数字框组解析: [月, 日, 时, 分] 各 1-2 位数字, 缺失/非法返回 null
    function parseBoxes(ids){
      var vals=[];
      for(var i=0;i<ids.length;i++){
        var v=(document.getElementById(ids[i]).value||'').trim();
        if(!/^\d{1,2}$/.test(v))return null;
        vals.push(+v);
      }
      if(vals[0]<1||vals[0]>12||vals[1]<1||vals[1]>31
         ||vals[2]<0||vals[2]>23||vals[3]<0||vals[3]>59)return null;
      return vals;
    }
    var year=new Date(tsFirst*1000).getFullYear();
    var t1v=parseBoxes(['cs-t1m','cs-t1d','cs-t1h','cs-t1n']);
    var t2v=parseBoxes(['cs-t2m','cs-t2d','cs-t2h','cs-t2n']);
    if(!t1v||!t2v){setErr('时间无效: 月 1-12 / 日 1-31 / 时 0-23 / 分 0-59');return;}
    var t1=new Date(year, t1v[0]-1, t1v[1], t1v[2], t1v[3], 0).getTime()/1000;
    var t2=new Date(year, t2v[0]-1, t2v[1], t2v[2], t2v[3], 0).getTime()/1000;
    // S1 修复 (2026-08-26): 输入粒度是分钟, 素材 ts_first/ts_last 带秒/小数秒 —
    // 用户输入面板显示的起始分钟 (如 04:49) 会因 t1 < ts_first(04:49:38) 被拒 (P1)。
    // 放宽到 ±60s 并 clamp 回素材范围 (窗口仍保证在素材内)。
    if(!(t1>=tsFirst-60&&t1<=tsLast&&t2>=tsFirst&&t2<=tsLast+60)){
      setErr('时间超出素材范围: '+fmtTsWin(tsFirst)+' → '+fmtTsWin(tsLast));return;}
    t1=Math.max(t1,tsFirst); t2=Math.min(t2,tsLast);
    if(t2<=t1){setErr('结束时间必须大于开始时间');return;}
    document.getElementById('cs-s1').value=t1;
    document.getElementById('cs-s2').value=t2;
    document.getElementById('cs-s1').oninput();
  });
  // U11: 子包清单渲染 (连续拆多子包 — 定义核对 08-13: 只拆不导, 手动导入)
  function renderSubs(){
    var el=document.getElementById('cs-subs');
    if(!el)return;
    var subs=S.cubxSubs||[];
    if(!subs.length){el.innerHTML='';return;}
    var h='<p class="t-11 text-strong mt-1">已拆子包 ('+subs.length+') — 下载复验或手动导入</p>';
    subs.forEach(function(s){
      h+='<div class="cs-sub-row">'
        +'<span class="t-11 mono">'+fmtTsWin(s.winStart)+' → '+fmtTsWin(s.winEnd)
        +' · '+s.frames.toLocaleString()+' 帧</span> '
        +'<a class="btn btn-o btn-sm" href="/api/cubx/download?path='+encodeURIComponent(s.path)+'" download title="下载子包 (Ubiqua 复验)">⬇ 下载</a> '
        +'<button class="btn btn-p btn-sm cs-sub-import" data-path="'+s.path+'">导入此子包</button>'
        +'</div>';
    });
    el.innerHTML=h;
    el.querySelectorAll('.cs-sub-import').forEach(function(b){
      b.addEventListener('click',function(){
        var p=b.dataset.path;
        importPath('/api/import/local-cubx','path',p,p.split(/[\\\\/]/).pop());
      });
    });
  }
  // U11: 切页回来恢复拆分面板 (reg 重建 DOM 后)
  if(S.cubxPrescan){
    showPrescanPanel(S.cubxPrescan.prescan, S.cubxPrescan.path, S.cubxPrescan.fname);
  }
  if(S.cubxSubs&&S.cubxSubs.length)renderSubs();

  // Key panel toggle
  // S1 (2026-08-26): 初始 body 带 class hidden (CSS display:none) 而 inline style 为空 —
  // 原判断 body.style.display==='none' 首次点击误判为"已展开"→ 点一次无效 (P2)。改为
  // class 或 inline 任一隐藏即视为收起。
  document.getElementById('pkey-toggle').addEventListener('click',function(){
    var body=document.getElementById('pkey-body');
    var show=body.classList.contains('hidden')||body.style.display==='none';
    body.classList.toggle('hidden',!show);
    body.style.display=show?'block':'none';
    this.textContent=show?'🔑 密钥管理 ▾':'🔑 密钥管理 ▸';
    if(show)loadKeyPanel();
  });

  // ── 密钥面板 ──
  function normHex(raw){return (raw||'').replace(/[:\s-]/g,'').replace(/^0x/i,'').toUpperCase();}
  // S1 (2026-08-26): key 标签为用户输入, 渲染进 innerHTML 必须转义 (P2 XSS)
  function escHtml(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function showKeyErr(msg){var el=document.getElementById('pk-err');if(el){el.textContent=msg;el.classList.remove('hidden');}}
  function clearKeyErr(){var el=document.getElementById('pk-err');if(el){el.textContent='';el.classList.add('hidden');}}
  function loadKeyPanel(){
    A.get('/api/keys').then(function(d){
      var keys=d.keys||[],stats=d.stats;
      var h='';
      if(stats){var mt=stats.matched_keys||[];
        h+='<div class="text-muted">📊 解密: '+stats.decrypted+'/'+stats.total_data_frames+' 帧 ('+(stats.decrypt_rate*100).toFixed(0)+'%)'
          +(mt.length?' <span class="badge badge-decrypted">'+mt.length+' 个 Key 命中</span>':'')
          +'</div>';}
      h+='<table class="tbl"><tr><th>Key</th><th>标签</th><th>状态</th><th></th></tr>';
      for(var i=0;i<keys.length;i++){
        var k=keys[i];
        var mk=stats&&stats.matched_keys&&stats.matched_keys.filter(function(m){return m.label===k.label})[0];
        var status=mk?'<span class="text-success">✓ 命中'+(mk.frame_count?' ('+mk.frame_count+'帧)':'')+'</span>':'<span class="text-dim">✗ 未命中</span>';
        var del=k.is_preset?'':'<button class="btn btn-o btn-s text-danger-strong" data-kl="'+escHtml(k.label)+'">✕</button>';
        var full=k.hex;
        var disp=full.length>16?full.substring(0,16)+'…':full;
        h+='<tr><td class="mono t-10 key-hex" title="点击展开/收起" data-full="'+escHtml(full)+'" data-short="'+escHtml(disp)+'">'+escHtml(disp)+'</td>'
          +'<td>'+escHtml(k.label)+(k.is_preset?' <span class="badge">预设</span>':'')+'</td>'
          +'<td>'+status+'</td><td>'+del+'</td></tr>';
      }
      h+='</table>';
      h+='<div class="key-add-row"><input id="pk-hex" placeholder="粘贴 hex Key (FC:90:D2:...)" class="grow t-10 mono"><input id="pk-label" placeholder="标签" class="w-80 t-10"><button class="btn btn-p btn-s" id="pk-add">添加</button></div>';
      h+='<div id="pk-err" class="t-11 text-danger hidden"></div>';
      document.getElementById('pkey-body').innerHTML=h;
      document.getElementById('pk-add').addEventListener('click',addKey);
      ['pk-hex','pk-label'].forEach(function(id){
        document.getElementById(id).addEventListener('keydown',function(e){if(e.key==='Enter')addKey();});
      });
      document.querySelectorAll('#pkey-body .key-hex').forEach(function(td){
        td.addEventListener('click',function(){
          var short=this.dataset.short;
          this.textContent=(this.textContent===short)?this.dataset.full:short;
        });
      });
      document.querySelectorAll('[data-kl]').forEach(function(btn){
        btn.addEventListener('click',function(){
          var kl=this.dataset.kl;
          // S1: label 是用户输入, URL 必须编码 (含 #/? 等字符会截断/歧义, P2)
          fetch('/api/keys/'+encodeURIComponent(kl),{method:'DELETE'}).then(r=>r.json()).then(function(d){
            if(d&&d.ok){loadKeyPanel();}else{showKeyErr((d&&d.error)||'删除失败');}
          }).catch(function(e){showKeyErr('网络错误: '+e.message)});
        });
      });
    });
  }
  function addKey(){
    clearKeyErr();
    var hex=document.getElementById('pk-hex').value.trim();
    var label=document.getElementById('pk-label').value.trim()||('Key'+Date.now());
    var clean=normHex(hex);
    if(!/^[0-9A-F]{32}$/.test(clean)){showKeyErr('Key 必须是 16 字节 (32 位 hex), 当前: '+clean.length+' 位');return;}
    A.post('/api/keys',{key:clean,label:label}).then(function(r){
      if(r.ok){document.getElementById('pk-hex').value='';document.getElementById('pk-label').value='';loadKeyPanel();}
      else{showKeyErr(r.error||'添加失败');}
    }).catch(function(e){showKeyErr('网络错误: '+e.message);});
  }
  window._loadKeyPanel=loadKeyPanel;

  // ── Common ──
  document.getElementById('gotopo').addEventListener('click',function(){location.hash='topo'});
  document.getElementById('clr').addEventListener('click',function(){
    var btn=this;
    if(btn.dataset.confirming!=='1'){
      btn.dataset.confirming='1';
      btn.classList.add('btn-r');
      btn.textContent='再次点击确认清除 (3s)';
      var n=2;
      var t=setInterval(function(){
        btn.textContent='再次点击确认清除 ('+n+'s)';
        n--;
        if(n<0){clearInterval(t);btn.dataset.confirming='';btn.textContent='清除数据';btn.classList.remove('btn-r');}
      },1000);
      return;
    }
    btn.textContent='清除中...';btn.disabled=true;setProg('清除中...');
    fetch('/api/import/clear',{method:'DELETE'}).then(r=>r.json()).then(function(){
      S.topo=null;S.pkts=0;S.nodes=0;S.verifyPassed=null;sb('就绪');setProg('');
      // sr() 曾设置 style.display='block' (inline), 类无法覆盖 — 必须用 style 隐藏
      try{document.getElementById('sout').style.display='none';}catch(e){}
      if(window._loadKeyPanel)window._loadKeyPanel();  // 密钥命中统计清零
      btn.dataset.confirming='';btn.textContent='清除数据';btn.disabled=false;btn.classList.remove('btn-r');
    });
  });
  // 校验状态兜底 (刷新后导航锁定用) — 渲染已由 sr() 统一负责, 避免重复
  A.get('/api/import/verify').then(function(v){S.verifyPassed=v&&v.passed;}).catch(function(){});
  // S1 (2026-08-26): P6 解析正确性卡渲染移入 sr() (导入结果自带 parser_verify),
  // 删除此处独立 fetch — fresh import 后卡缺失的竞态修复
});
