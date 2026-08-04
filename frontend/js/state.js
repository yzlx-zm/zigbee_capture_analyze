// state.js — 全局共享模块 (所有页面 import 此模块)
// ES module: <script type="module"> 加载, import/export 原生隔离
export const A={get:u=>fetch(u).then(r=>r.json()),post:(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json())};
export const S={pkts:0,nodes:0,topo:null,topoPan:null,topoAddr:null,topoT0:null,topoT1:null};
export function sb(m){document.getElementById('sb').textContent=m||'就绪'}
export function setProg(msg,pct){var el=document.getElementById('prog');if(el){el.style.display=msg?'flex':'none';if(msg)el.classList.remove('prog-err');}var im=document.getElementById('imsg');if(im)im.textContent=msg||'';var bar=document.getElementById('pbar');if(bar){bar.style.display=(msg&&pct!=null)?'block':'none';}var fill=document.getElementById('pfill');if(fill){fill.style.width=(pct==null?0:pct)+'%';}var mc=document.getElementById('mc');if(mc)mc.classList.toggle('busy',!!msg);}
export function setErr(msg){var el=document.getElementById('prog');if(el){el.style.display='flex';el.classList.add('prog-err');}var im=document.getElementById('imsg');if(im)im.textContent='❌ '+(msg||'导入失败');var mc=document.getElementById('mc');if(mc)mc.classList.remove('busy');}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
export function sr(d,fname){var el=document.getElementById('sout');if(!el)return;
  if(!d||d.ok===false){setErr((d&&d.error)||'导入失败');return;}
  el.style.display='block';
  var h='';
  if(fname)h+='<p class=\"text-muted t-11\">📂 '+esc(fname)+'</p>';
  h+='<div class=\"stats\"><span>总包:'+(d.packets||0)+'</span><span>节点:'+(d.nodes||0)+'</span>';
  if(d.file_type)h+='<span>类型:'+d.file_type+'</span>';
  var bt=d.by_type||{};
  var btArr=Object.keys(bt).map(function(k){return k+':'+bt[k];});
  h+='</div><p class=\"t-11\">'+(btArr.join(', ')||'(无类型分布)').substr(0,300)+'</p>';
  if(d.decrypt_stats){h+='<p class=\"t-11 text-success\">解密: '+d.decrypt_stats.decrypted+'/'+d.decrypt_stats.total_data_frames+' 帧 ('+(d.decrypt_stats.decrypt_rate*100).toFixed(0)+'%) | Clusters: '+JSON.stringify(d.decrypt_stats.by_cluster)+'</p>';}
  if(d.verify){
    var v=d.verify;
    var vState=v.passed===true?'alert-ok':v.passed===false?'alert-bad':'';
    h+='<div class=\"alert '+vState+'\">';
    h+='<div class=\"alert-title\">'+(v.passed===true?'✅ 数据校验通过':v.passed===false?'❌ 数据校验失败 (拓扑/时间线已锁定)':'⏳ 校验中...')+'</div>';
    if(v.checks){for(var ck in v.checks){var c=v.checks[ck];var icon=c.passed?'✅':'❌';h+='<div class=\"t-10 '+(c.passed?'text-success':'text-danger')+'\">'+icon+' '+esc(c.label)+': 预期='+esc(c.expected==null?'-':c.expected)+' 实际='+esc(c.actual==null?'-':c.actual)+'</div>';}}
    if(v.detail&&Object.keys(v.detail).length>0){h+='<details class=\"verify-detail\"><summary>⚠️ 差异明细 ('+Object.keys(v.detail).length+' 项)</summary><pre class=\"text-danger\">'+esc(JSON.stringify(v.detail))+'</pre></details>';}
    h+='</div>';S.verifyPassed=v.passed;
  }
  document.getElementById('sdiv').innerHTML=h;
  S.pkts=d.packets||0;S.nodes=d.nodes||0;sb(S.pkts+'包 | '+S.nodes+'节点');
  A.get('/api/topology/graph').then(function(td){S.topo=td});}
export function doI(file){setProg('上传中...',2);
  var fd=new FormData();fd.append('files',file);
  fetch('/api/import/files',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
    if(d&&d.ok&&d.task_id){pollImport(d.task_id,file.name||'');}
    else{setProg('');setErr((d&&d.error)||'导入失败');}
  }).catch(function(e){setErr('网络错误: '+e.message);});}
export function doPI(files){setProg('上传中...',2);
  var fd=new FormData(); var cubx=0; var fnames=[];
  for(var i=0;i<files.length;i++){fd.append('files',files[i]);
    var n=files[i].name||'';fnames.push(n);if(n.toLowerCase().endsWith('.cubx'))cubx=1;}
  var url=cubx?'/api/import/cubx':'/api/import/pcap';
  fetch(url,{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
    if(d&&d.ok&&d.task_id){pollImport(d.task_id,fnames.join(', '),function(){if(!cubx&&window._loadKeyPanel)window._loadKeyPanel();});}
    else{setProg('');setErr((d&&d.error)||'导入失败');}
  }).catch(function(e){setErr('网络错误: '+e.message);});}
export function pollImport(tid,fname,onDone){
  var tries=0;
  var timer=setInterval(function(){
    tries++;
    if(tries>750){clearInterval(timer);setErr('导入超时 (5 分钟), 请重试');return;}  // 750×400ms
    A.get('/api/import/progress?task_id='+tid).then(function(p){
      if(p&&p.status==='done'){clearInterval(timer);if(p.result){setProg('');sr(p.result,fname);if(onDone)onDone();}else{setErr('导入完成但结果缺失, 请刷新页面');}}
      else if(p&&p.status==='error'){clearInterval(timer);setErr(p.error||'导入失败');}
      else if(p&&p.status==='running'){setProg((p.stage||'解析中')+' ('+p.percent+'%)',p.percent);}
    }).catch(function(){});
  },400);
}
export function fmtTs(ts){var d=new Date(ts*1000);return d.getUTCHours().toString().padStart(2,'0')+':'+d.getUTCMinutes().toString().padStart(2,'0')+':'+d.getUTCSeconds().toString().padStart(2,'0');}