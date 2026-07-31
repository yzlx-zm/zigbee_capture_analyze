// import.js — 导入页面模块 (ES module)
import { S, A, sb, sr, setProg, doI, doPI } from './state.js';

reg('import',function(){
  if(!S.impTab)S.impTab='csv';
  var h='<div class="card"><h3>📂 数据导入</h3>'
    +'<div style="display:flex;gap:2px;margin-bottom:12px;border-bottom:2px solid #e2e8f0">'
    +'<button class="btn imp-tab'+(S.impTab==='csv'?' on':'')+'" data-tab="csv" style="border-radius:4px 4px 0 0;font-size:12px;padding:6px 14px;border:none;background:'+(S.impTab==='csv'?'#3b82f6;color:#fff':'#f1f5f9')+'">📊 CSV 快速预览</button>'
    +'<button class="btn imp-tab'+(S.impTab==='pcap'?' on':'')+'" data-tab="pcap" style="border-radius:4px 4px 0 0;font-size:12px;padding:6px 14px;border:none;background:'+(S.impTab==='pcap'?'#3b82f6;color:#fff':'#f1f5f9')+'">📡 抓包导入</button>'
    +'</div>'
    +'<div id="imp-csv" style="display:'+(S.impTab==='csv'?'block':'none')+'">'
      +'<p style="font-size:11px;color:#94a3b8;margin-bottom:8px">Ubiqua File → Export → CSV</p>'
      +'<div class="file-drop" id="drop"><p>拖拽 .csv 文件到此处</p><input type="file" id="finp" accept=".csv" style="display:none"></div>'
      +'<button class="btn btn-o" id="lpath" style="font-size:11px">或输入本地路径...</button>'
    +'</div>'
    +'<div id="imp-pcap" style="display:'+(S.impTab==='pcap'?'block':'none')+'">'
      +'<p style="font-size:11px;color:#94a3b8;margin-bottom:8px">Ubiqua File → Export → pcap</p>'
      +'<div class="file-drop" id="pdrop"><p>拖拽 .pcap / .cubx 文件到此处 (支持多选)</p><input type="file" id="pfinp" accept=".pcap,.pcapng,.cubx" multiple style="display:none"></div>'
      +'<button class="btn btn-o" id="plpath" style="font-size:11px">或输入本地路径 (逗号分隔多个)...</button>'
      +'<div id="pkey-panel" class="card" style="margin-top:8px;background:#f8fafc">'
        +'<h4 style="font-size:12px;cursor:pointer" id="pkey-toggle">🔑 密钥管理 ▸</h4>'
        +'<div id="pkey-body" style="display:none;font-size:11px"></div>'
      +'</div>'
    +'</div>'
    +'<div id="prog" style="display:none;margin-top:8px"><p id="imsg" style="font-size:11px"></p></div></div>';
  h+='<div class="card" id="sout" style="display:none"><h3>📊 导入结果</h3><div id="sdiv"></div>'
    +'<button class="btn btn-p" id="gotopo" style="margin-top:8px">查看拓扑 →</button> '
    +'<button class="btn btn-r" id="clr" style="margin-top:8px">清除数据</button></div>';
  document.getElementById('mc').innerHTML=h;
  A.get('/api/import/last').then(function(d){if(d&&d.ok){sr(d,d.filename||'');}}).catch(function(){});

  // Tab switch
  document.querySelectorAll('.imp-tab').forEach(function(btn){
    btn.addEventListener('click',function(){
      S.impTab=this.dataset.tab;
      document.getElementById('imp-csv').style.display=S.impTab==='csv'?'block':'none';
      document.getElementById('imp-pcap').style.display=S.impTab==='pcap'?'block':'none';
      document.querySelectorAll('.imp-tab').forEach(function(b){
        b.style.background=S.impTab===b.dataset.tab?'#3b82f6':'#f1f5f9';
        b.style.color=S.impTab===b.dataset.tab?'#fff':'#374151';
      });
      if(S.impTab==='pcap')loadKeyPanel();
    });
  });

  // ── CSV tab ──
  var drop=document.getElementById('drop'),inp=document.getElementById('finp');
  drop.addEventListener('click',function(){inp.click()});
  drop.addEventListener('dragover',function(e){e.preventDefault()});
  drop.addEventListener('drop',function(e){e.preventDefault();if(e.dataTransfer.files.length)doI(e.dataTransfer.files[0])});
  inp.addEventListener('change',function(){if(inp.files.length)doI(inp.files[0])});
  document.getElementById('lpath').addEventListener('click',function(){
    var p=prompt('CSV 文件路径:');if(!p)return;
    setProg('导入 CSV...');
    var fd=new FormData();fd.append('path',p);
    fetch('/api/import/local',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){setProg('');sr(d,p.split(/[\\\\/]/).pop())})
      .catch(function(e){alert('错误: '+e.message);setProg('')});
  });

  // ── pcap tab ──
  var pdrop=document.getElementById('pdrop'),pinp=document.getElementById('pfinp');
  pdrop.addEventListener('click',function(){pinp.click()});
  pdrop.addEventListener('dragover',function(e){e.preventDefault()});
  pdrop.addEventListener('drop',function(e){e.preventDefault();if(e.dataTransfer.files.length)doPI(e.dataTransfer.files)});
  pinp.addEventListener('change',function(){if(pinp.files.length)doPI(pinp.files)});
  document.getElementById('plpath').addEventListener('click',function(){
    var p=prompt('pcap/cubx 文件路径 (逗号分隔多个):');if(!p)return;
    setProg('导入中...');
    var isCubx=p.toLowerCase().endsWith('.cubx');
    var fd=new FormData();
    if(isCubx){fd.append('path',p);fetch('/api/import/local-cubx',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){setProg('');sr(d,p.split(/[\\\\/]/).pop());}).catch(function(e){alert('错误: '+e.message);setProg('')});}
    else{fd.append('paths',p);fetch('/api/import/local-pcap',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){setProg('');sr(d,p.split(/[\\\\/]/).pop());}).catch(function(e){alert('错误: '+e.message);setProg('')});}
  });

  // Key panel toggle
  document.getElementById('pkey-toggle').addEventListener('click',function(){
    var body=document.getElementById('pkey-body');
    var show=body.style.display==='none';
    body.style.display=show?'block':'none';
    this.textContent=show?'🔑 密钥管理 ▾':'🔑 密钥管理 ▸';
    if(show)loadKeyPanel();
  });

  // loadKeyPanel (模块私有, 通过 window._loadKeyPanel 暴露)
  function loadKeyPanel(){
    A.get('/api/keys').then(function(d){
      var keys=d.keys||[],stats=d.stats;
      var h='';
      if(stats){h+='<div style="margin-bottom:8px;color:#64748b">📊 解密: '+stats.decrypted+'/'+stats.total_data_frames+' 帧 ('+(stats.decrypt_rate*100).toFixed(0)+'%)</div>';}
      h+='<table class="tbl"><tr><th>Key</th><th>标签</th><th>状态</th><th></th></tr>';
      for(var i=0;i<keys.length;i++){
        var k=keys[i];
        var matched=stats&&stats.matched_keys&&stats.matched_keys.some(function(m){return m.label===k.label});
        var status=matched?'<span style="color:#16a34a">✓ 命中</span>':'<span style="color:#94a3b8">✗ 未命中</span>';
        var del=k.is_preset?'':'<button class="btn btn-o" data-kl="'+k.label+'" style="font-size:9px;color:#ef4444">✕</button>';
        h+='<tr><td style="font-family:monospace;font-size:10px">'+k.hex.substring(0,16)+'...</td><td>'+k.label+(k.is_preset?' (预设)':'')+'</td><td>'+status+'</td><td>'+del+'</td></tr>';
      }
      h+='</table>';
      h+='<div style="margin-top:8px;display:flex;gap:4px"><input id="pk-hex" placeholder="粘贴 hex Key (FC:90:D2:...)" style="flex:1;font-size:10px;font-family:monospace"><input id="pk-label" placeholder="标签" style="width:80px;font-size:10px"><button class="btn btn-p" id="pk-add" style="font-size:10px">添加</button></div>';
      document.getElementById('pkey-body').innerHTML=h;
      document.getElementById('pk-add').addEventListener('click',function(){
        var hex=document.getElementById('pk-hex').value.trim();
        var label=document.getElementById('pk-label').value.trim()||('Key'+Date.now());
        if(!hex)return;
        A.post('/api/keys',{key:hex,label:label}).then(function(r){
          if(r.ok){loadKeyPanel();}else{alert(r.error||'添加失败');}
        });
      });
      document.querySelectorAll('[data-kl]').forEach(function(btn){
        btn.addEventListener('click',function(){
          var kl=this.dataset.kl;
          fetch('/api/keys/'+kl,{method:'DELETE'}).then(function(){loadKeyPanel();});
        });
      });
    });
  }
  window._loadKeyPanel=loadKeyPanel;

  // ── Common ──
  document.getElementById('gotopo').addEventListener('click',function(){location.hash='topo'});
  document.getElementById('clr').addEventListener('click',function(){
    var btn=this;
    if(btn.dataset.confirming!=='1'){
      btn.dataset.confirming='1';
      btn.textContent='再次点击确认清除';
      btn.style.background='#dc2626';btn.style.color='#fff';
      setTimeout(function(){btn.dataset.confirming='';btn.textContent='清除数据';btn.style.background='';btn.style.color='';},3000);
      return;
    }
    btn.textContent='清除中...';btn.disabled=true;
    fetch('/api/import/clear',{method:'DELETE'}).then(r=>r.json()).then(function(){
      S.topo=null;S.pkts=0;S.nodes=0;sb('就绪');
      try{document.getElementById('sout').style.display='none';}catch(e){}
      btn.dataset.confirming='';btn.textContent='清除数据';btn.disabled=false;btn.style.background='';btn.style.color='';
    });
  });
  A.get('/api/import/verify').then(function(v){S.verifyPassed=v.passed;
    if(v.passed!==null&&document.getElementById('sout')){
      var vc=v.passed===true?'#16a34a':'#dc2626';
      var vh='<div style="margin-top:8px;padding:8px;border-radius:4px;background:'+(v.passed?'#f0fdf4':'#fef2f2')+';border:1px solid '+vc+';font-size:11px">';
      vh+='<b style="color:'+vc+'">'+(v.passed?'✅ 数据校验通过':'❌ 数据校验失败')+'</b>';
      if(v.checks){for(var ck in v.checks){var c=v.checks[ck];vh+='<br>'+ (c.passed?'✅':'❌')+' '+c.label;}}
      vh+='</div>';
      document.getElementById('sdiv').innerHTML+=vh;
    }
  });
  if(S.impTab==='pcap'){setTimeout(function(){loadKeyPanel();},200);}
});
