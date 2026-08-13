// import.js — 导入页面模块 (ES module)
import { S, A, sb, sr, setProg, setErr, doI, doPI, pollImport } from './state.js';

reg('import',function(){
  if(!S.impTab)S.impTab='csv';
  var h='<div class="card"><h3>📂 数据导入</h3>'
    +'<div class="tabs">'
    +'<button class="btn imp-tab'+(S.impTab==='csv'?' on':'')+'" data-tab="csv">📊 CSV 快速预览</button>'
    +'<button class="btn imp-tab'+(S.impTab==='pcap'?' on':'')+'" data-tab="pcap">📡 抓包导入</button>'
    +'</div>'
    +'<div id="imp-csv" class="'+(S.impTab==='csv'?'':'hidden')+'">'
      +'<p class="hint">Ubiqua File → Export → CSV</p>'
      +'<div class="file-drop" id="drop"><p>拖拽 .csv 文件到此处</p><input type="file" id="finp" accept=".csv" class="hidden"></div>'
      +'<button class="btn btn-o" id="lpath">或输入本地路径...</button>'
    +'</div>'
    +'<div id="imp-pcap" class="'+(S.impTab==='pcap'?'':'hidden')+'">'
      +'<p class="hint">Ubiqua File → Export → pcap</p>'
      +'<div class="file-drop" id="pdrop"><p>拖拽 .pcap / .cubx 文件到此处 (支持多选)</p><input type="file" id="pfinp" accept=".pcap,.pcapng,.cubx" multiple class="hidden"></div>'
      +'<button class="btn btn-o" id="plpath">或输入本地路径 (逗号分隔多个)...</button>'
      +'<div id="pkey-panel" class="card key-panel">'
        +'<h4 id="pkey-toggle">🔑 密钥管理 ▸</h4>'
        +'<div id="pkey-body" class="t-11 hidden"></div>'
      +'</div>'
    +'</div>'
    +'<div id="cubx-prescan" class="card hidden">'
      +'<h4>⏱ 大包时间窗拆分导入 (U11)</h4>'
      +'<p id="cs-info" class="t-11"></p>'
      +'<div id="cs-hist" class="cs-hist"></div>'
      +'<div class="cs-sliders">'
        +'<input type="range" id="cs-s1" class="cs-range">'
        +'<input type="range" id="cs-s2" class="cs-range">'
      +'</div>'
      +'<p id="cs-win" class="t-11 text-strong"></p>'
      +'<div class="mt-1">'
        +'<button class="btn btn-p" id="cs-go">拆分并导入</button> '
        +'<button class="btn btn-o" id="cs-cancel">取消 (整包导入)</button>'
      +'</div>'
    +'</div>'
    +'<div id="prog" class="prog hidden"><span class="spin"></span><span id="imsg" class="t-11"></span><div class="bar" id="pbar"><div class="bar-fill" id="pfill"></div></div></div></div>';
  h+='<div class="card hidden" id="sout"><h3>📊 导入结果</h3><div id="sdiv"></div>'
    +'<button class="btn btn-p mt-2" id="gotopo">查看拓扑 →</button> '
    +'<button class="btn btn-r mt-2" id="clr">清除数据</button></div>';
  document.getElementById('mc').innerHTML=h;
  A.get('/api/import/last').then(function(d){if(d&&d.ok){sr(d,d.filename||'');}}).catch(function(){});

  // Tab switch
  document.querySelectorAll('.imp-tab').forEach(function(btn){
    btn.addEventListener('click',function(){
      S.impTab=this.dataset.tab;
      document.getElementById('imp-csv').style.display=S.impTab==='csv'?'block':'none';
      document.getElementById('imp-pcap').style.display=S.impTab==='pcap'?'block':'none';
      document.querySelectorAll('.imp-tab').forEach(function(b){
        b.classList.toggle('on',S.impTab===b.dataset.tab);
      });
      if(S.impTab==='pcap')loadKeyPanel();
    });
  });

  // ── 本地路径导入 (后台任务 + 轮询真实进度; 失败内联显示, 不弹 alert) ──
  function importPath(url, paramName, p, fname){
    setProg('提交中...', 1);
    var fd=new FormData();fd.append(paramName,p);
    fetch(url,{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
      if(d&&d.ok&&d.task_id){pollImport(d.task_id,fname);}
      else{setProg('');setErr((d&&d.error)||'导入失败');}
    }).catch(function(e){setErr('网络错误: '+e.message);});
  }

  // ── CSV tab ──
  var drop=document.getElementById('drop'),inp=document.getElementById('finp');
  drop.addEventListener('click',function(){inp.click()});
  drop.addEventListener('dragover',function(e){e.preventDefault()});
  drop.addEventListener('drop',function(e){e.preventDefault();if(e.dataTransfer.files.length)doI(e.dataTransfer.files[0])});
  inp.addEventListener('change',function(){if(inp.files.length)doI(inp.files[0])});
  document.getElementById('lpath').addEventListener('click',function(){
    var p=prompt('CSV 文件路径:');if(!p)return;
    importPath('/api/import/local','path',p,p.split(/[\\\\/]/).pop());
  });

  // ── pcap tab ──
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
      if(d.file_mb>30){showPrescanPanel(d,path,fname);}
      else{importPath('/api/import/local-cubx','path',path,fname);}
    }).catch(function(e){setErr('预扫失败: '+e.message);});
  }
  function showPrescanPanel(d, path, fname){
    // U11: 面板状态持久化 (S.cubxPrescan) — 切页回来 reg() 重建时恢复
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
    var lbl=document.getElementById('cs-win');
    function updWin(){ lbl.textContent='窗口: '+fmtTsWin(+s1.value)+' → '+fmtTsWin(+s2.value)
      +' ('+Math.round((+s2.value-+s1.value)/60)+' 分钟)'; }
    s1.oninput=s2.oninput=updWin; updWin();
    panel.classList.remove('hidden');
    panel.dataset.path=path; panel.dataset.fname=fname;
  }
  var csPanel=document.getElementById('cubx-prescan');
  if(csPanel){
    document.getElementById('cs-go').addEventListener('click',function(){
      var path=csPanel.dataset.path,fname=csPanel.dataset.fname;
      var tsStart=+document.getElementById('cs-s1').value,tsEnd=+document.getElementById('cs-s2').value;
      if(tsEnd<=tsStart){setErr('窗口无效: 结束时间必须大于开始时间');return;}
      S.cubxPrescan=null;   // 开始拆分后清状态 (面板使命完成, 结果区提供下载)
      setProg('提交拆分...',1);
      var fd=new FormData();fd.append('path',path);
      fd.append('ts_start',tsStart);fd.append('ts_end',tsEnd);
      fetch('/api/cubx/split',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
        if(d&&d.ok&&d.task_id){pollImport(d.task_id,fname);}
        else{setProg('');setErr((d&&d.error)||'拆分失败');}
      }).catch(function(e){setErr('网络错误: '+e.message);});
    });
    document.getElementById('cs-cancel').addEventListener('click',function(){
      csPanel.classList.add('hidden');
      S.cubxPrescan=null;
      importPath('/api/import/local-cubx','path',csPanel.dataset.path,csPanel.dataset.fname);
    });
  }
  // U11: 切页回来恢复拆分面板 (reg 重建 DOM 后)
  if(S.cubxPrescan){
    showPrescanPanel(S.cubxPrescan.prescan, S.cubxPrescan.path, S.cubxPrescan.fname);
  }

  // Key panel toggle
  document.getElementById('pkey-toggle').addEventListener('click',function(){
    var body=document.getElementById('pkey-body');
    var show=body.style.display==='none';
    body.style.display=show?'block':'none';
    this.textContent=show?'🔑 密钥管理 ▾':'🔑 密钥管理 ▸';
    if(show)loadKeyPanel();
  });

  // ── 密钥面板 ──
  function normHex(raw){return (raw||'').replace(/[:\s-]/g,'').replace(/^0x/i,'').toUpperCase();}
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
        var del=k.is_preset?'':'<button class="btn btn-o btn-s text-danger-strong" data-kl="'+k.label+'">✕</button>';
        var full=k.hex;
        var disp=full.length>16?full.substring(0,16)+'…':full;
        h+='<tr><td class="mono t-10 key-hex" title="点击展开/收起" data-full="'+full+'" data-short="'+disp+'">'+disp+'</td>'
          +'<td>'+k.label+(k.is_preset?' <span class="badge">预设</span>':'')+'</td>'
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
          fetch('/api/keys/'+kl,{method:'DELETE'}).then(r=>r.json()).then(function(d){
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
  // 解析正确性校验 (P6) — 导入后后台自动跑, 此处在导入结果区渲染结果卡片
  A.get('/api/import/parser-verify').then(function(pv){
    if(!pv||pv.passed===null||!document.getElementById('sout'))return;
    S.parserPassed = (pv.failure_type!=='parse_mismatch');  // 解析错位 → 锁定导航
    var ok = pv.passed===true;
    var vc = ok?'#16a34a':'#dc2626';
    var ph='<div style="margin-top:8px;padding:8px;border-radius:4px;background:'+(ok?'#f0fdf4':'#fef2f2')+';border:1px solid '+vc+';font-size:11px">';
    ph+='<b style="color:'+vc+'">'+(ok?'✅ 解析正确性校验通过':'❌ 解析正确性校验异常')+'</b>';
    if(pv.failure_type){ph+=' <span style="color:#94a3b8">('+(pv.failure_type==='parse_mismatch'?'解析错位, 已锁定拓扑/时间线/节点页':pv.failure_type==='missing_key'?'缺 key, 仅警告':'警告')+')</span>';}
    if(pv.checks){for(var ck in pv.checks){var c=pv.checks[ck];
      ph+='<br>'+(c.passed?'✅':'⚠️')+' '+c.label+': <span style="color:#64748b">'+(c.actual||'')+'</span>';
    }}
    if(pv.detail){for(var dk in pv.detail){var dd=pv.detail[dk];
      ph+='<div style="color:#b45309;margin-top:4px">'+dk+': '+(Array.isArray(dd)?dd.slice(0,3).join(' | '):dd)+'</div>';
    }}
    ph+='</div>';
    var el=document.getElementById('sdiv');
    if(el){el.innerHTML+=ph;}
  }).catch(function(){});
  if(S.impTab==='pcap'){setTimeout(function(){loadKeyPanel();},200);}
});
