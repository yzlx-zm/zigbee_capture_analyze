// import.js — 导入页面模块 (ES module)
import { S, A, sb, sr, setProg, setErr, doI, doPI } from './state.js';

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
    +'<div id="prog" class="prog hidden"><span class="spin"></span><span id="imsg" class="t-11"></span></div></div>';
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

  // ── 本地路径导入 (统一错误处理; 失败内联显示, 不弹 alert) ──
  function importPath(url, paramName, p, fname){
    setProg('导入中...');
    var fd=new FormData();fd.append(paramName,p);
    fetch(url,{method:'POST',body:fd}).then(r=>r.json()).then(function(d){setProg('');if(d&&d.ok){sr(d,fname);}else{setErr((d&&d.error)||'导入失败');}})
      .catch(function(e){setErr('网络错误: '+e.message);});
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
    importPath(isCubx?'/api/import/local-cubx':'/api/import/local-pcap',isCubx?'path':'paths',p,p.split(/[\\\\/]/).pop());
  });

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
      S.topo=null;S.pkts=0;S.nodes=0;sb('就绪');setProg('');
      try{document.getElementById('sout').classList.add('hidden');}catch(e){}
      btn.dataset.confirming='';btn.textContent='清除数据';btn.disabled=false;btn.classList.remove('btn-r');
    });
  });
  // 校验状态兜底 (刷新后导航锁定用) — 渲染已由 sr() 统一负责, 避免重复
  A.get('/api/import/verify').then(function(v){S.verifyPassed=v&&v.passed;}).catch(function(){});
  if(S.impTab==='pcap'){setTimeout(function(){loadKeyPanel();},200);}
});
