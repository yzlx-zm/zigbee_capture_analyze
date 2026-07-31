// state.js — 全局共享模块 (所有页面 import 此模块)
// ES module: <script type="module"> 加载, import/export 原生隔离
export const A={get:u=>fetch(u).then(r=>r.json()),post:(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json())};
export const S={pkts:0,nodes:0,topo:null,topoPan:null,topoAddr:null,topoT0:null,topoT1:null};
export function sb(m){document.getElementById('sb').textContent=m||'就绪'}
export function setProg(msg){var el=document.getElementById('prog');if(el){el.style.display=msg?'block':'none';}var im=document.getElementById('imsg');if(im)im.textContent=msg||'';}
export function sr(d,fname){var el=document.getElementById('sout');if(!el)return;el.style.display='block';
  var h='';
  if(fname)h+='<p style=\"font-size:11px;color:#64748b;margin-bottom:4px\">📂 '+fname+'</p>';
  h+='<div class=\"stats\"><span>总包:'+(d.packets||0)+'</span><span>节点:'+(d.nodes||0)+'</span>';
  if(d.file_type)h+='<span>类型:'+d.file_type+'</span>';
  var bt=d.by_type||{};
  var btArr=Object.keys(bt).map(function(k){return k+':'+bt[k];});
  h+='</div><p style=\"font-size:11px;margin-top:4px\">'+(btArr.join(', ')||'(无类型分布)').substr(0,300)+'</p>';
  if(d.decrypt_stats){h+='<p style=\"font-size:11px;margin-top:2px;color:#16a34a\">解密: '+d.decrypt_stats.decrypted+'/'+d.decrypt_stats.total_data_frames+' 帧 ('+(d.decrypt_stats.decrypt_rate*100).toFixed(0)+'%) | Clusters: '+JSON.stringify(d.decrypt_stats.by_cluster)+'</p>';}
  if(d.verify){
    var v=d.verify;var vc=v.passed===true?'#16a34a':(v.passed===false?'#dc2626':'#94a3b8');
    h+='<div style=\"margin-top:8px;padding:8px;border-radius:4px;background:'+(v.passed===true?'#f0fdf4':v.passed===false?'#fef2f2':'#f8fafc')+';border:1px solid '+vc+'\">';
    h+='<div style=\"font-weight:600;color:'+vc+';margin-bottom:4px\">'+(v.passed===true?'✅ 数据校验通过':v.passed===false?'❌ 数据校验失败 (拓扑/时间线已锁定)':'⏳ 校验中...')+'</div>';
    if(v.checks){for(var ck in v.checks){var c=v.checks[ck];var icon=c.passed?'✅':'❌';h+='<div style=\"font-size:10px;margin:2px 0;color:'+(c.passed?'#16a34a':'#dc2626')+'\">'+icon+' '+c.label+': 预期='+c.expected+' 实际='+c.actual+'</div>';}}
    if(v.detail&&Object.keys(v.detail).length>0){h+='<div style=\"font-size:10px;color:#dc2626;margin-top:4px\">差异: '+JSON.stringify(v.detail).substr(0,300)+'</div>';}
    h+='</div>';S.verifyPassed=v.passed;
  }
  document.getElementById('sdiv').innerHTML=h;
  S.pkts=d.packets||0;S.nodes=d.nodes||0;sb(S.pkts+'包 | '+S.nodes+'节点');
  A.get('/api/topology/graph').then(function(td){S.topo=td});}
export function doI(file){setProg('上传解析中...');
  var fd=new FormData();fd.append('files',file);
  fetch('/api/import/files',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){setProg('');sr(d,file.name||'')})
    .catch(function(e){alert('错误: '+e.message);setProg('')});}
export function doPI(files){setProg('上传解析中...');
  var fd=new FormData(); var cubx=0; var fnames=[];
  for(var i=0;i<files.length;i++){fd.append('files',files[i]);
    var n=files[i].name||'';fnames.push(n);if(n.toLowerCase().endsWith('.cubx'))cubx=1;}
  var url=cubx?'/api/import/cubx':'/api/import/pcap';
  fetch(url,{method:'POST',body:fd}).then(r=>r.json()).then(function(d){setProg('');sr(d,fnames.join(', '));if(!cubx&&window._loadKeyPanel)window._loadKeyPanel();})
    .catch(function(e){alert('错误: '+e.message);setProg('')});}
export function fmtTs(ts){var d=new Date(ts*1000);return d.getUTCHours().toString().padStart(2,'0')+':'+d.getUTCMinutes().toString().padStart(2,'0')+':'+d.getUTCSeconds().toString().padStart(2,'0');}