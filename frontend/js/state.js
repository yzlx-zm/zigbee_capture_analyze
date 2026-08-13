// state.js — 全局共享模块 (所有页面 import 此模块)
// ES module: <script type="module"> 加载, import/export 原生隔离
export const A={get:u=>fetch(u).then(r=>r.json()),post:(u,b)=>fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json())};
export const S={pkts:0,nodes:0,topo:null,topoPan:null,topoAddr:null,topoT0:null,topoT1:null};
export function sb(m){var el=document.getElementById('sb');if(!el)return;el.textContent=m||'就绪';delete el.dataset.task;}
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
  // U11: 拆分产物下载 (人工复验, 如 Ubiqua 打开) — 按钮样式明显
  if(d.split_out_path){
    h+='<p class="mt-1"><a class="btn btn-p btn-sm" href="/api/cubx/download?path='+encodeURIComponent(d.split_out_path)+'" download>⬇ 下载拆分产物 ('+((d.split_out_frames||0).toLocaleString())+' 帧)</a> <span class="t-10 text-dim">Ubiqua 打开复验用</span></p>';
  }
  document.getElementById('sdiv').innerHTML=h;
  S.pkts=d.packets||0;S.nodes=d.nodes||0;sb(S.pkts+'包 | '+S.nodes+'节点');
  A.get('/api/topology/graph').then(function(td){S.topo=td});}
// XHR 上传 (可上报真实上传进度 0-10%), 完成后转任务轮询
function uploadXHR(url, fd, fname, onDone){
  var xhr=new XMLHttpRequest();
  xhr.open('POST',url);
  xhr.upload.onprogress=function(e){
    if(e.lengthComputable){
      var up=Math.round(e.loaded/e.total*100);
      setProg('上传中 ('+up+'%)',Math.round(up*0.1));  // 上传占 0-10%
    }
  };
  xhr.onload=function(){
    var d;
    try{d=JSON.parse(xhr.responseText);}catch(e){setErr('响应解析失败');return;}
    if(d&&d.ok&&d.task_id){setProg('解析中...',10);pollImport(d.task_id,fname,onDone);}
    else{setProg('');setErr((d&&d.error)||'导入失败');}
  };
  xhr.onerror=function(){setErr('网络错误: 上传失败');};
  xhr.send(fd);
}
export function doI(file){setProg('上传中...',1);
  var fd=new FormData();fd.append('files',file);
  uploadXHR('/api/import/files',fd,file.name||'');}
export function doPI(files){setProg('上传中...',1);
  var fd=new FormData(); var cubx=0; var fnames=[];
  for(var i=0;i<files.length;i++){fd.append('files',files[i]);
    var n=files[i].name||'';fnames.push(n);if(n.toLowerCase().endsWith('.cubx'))cubx=1;}
  // U11: 大 cubx (>1MB, 用户定义 08-13) 走暂存+预扫拆分面板 (免整包解析卡死)
  if(cubx && files.length===1 && files[0].size > 1*1048576 && window._stageCubx){
    window._stageCubx(files[0], fnames[0]); return;
  }
  var url=cubx?'/api/import/cubx':'/api/import/pcap';
  uploadXHR(url,fd,fnames.join(', '),function(){if(!cubx&&window._loadKeyPanel)window._loadKeyPanel();});}
// ── 全局导入任务监视器 (2026-08-05, grilling 确认方案) ──
// 轮询与页面 DOM 解耦: 模块级单例, 页面切换 (#mc 重建) 不销毁轮询。
// 顶栏 #sb 显示任务状态: ⟳ 阶段 45% (run) / ✅ 完成·点击查看 (done) / ❌ 失败·点击查看 (err);
// done/err 且不在导入页时, 点击 #sb 跳回导入页 (import/last 自动恢复结果, err 用延迟 setErr 恢复详情)。
// 在导入页时仍驱动页内进度条/busy/结果渲染 (与 U6 行为一致)。
var _ptid=null,_pfname='',_ponDone=null,_pdone=false,_ptimer=null,_plastErr='',_ptries=0;
function onImportPage(){var h=location.hash.slice(1)||'import';return h==='import';}
function stopPoll(){if(_ptimer){clearInterval(_ptimer);_ptimer=null;}}
export function sbTask(label,cls){sb(label);var el=document.getElementById('sb');if(el)el.dataset.task=cls;}
export function pollImport(tid,fname,onDone){
  stopPoll();                    // 新任务顶掉旧轮询 (后端并发防护下不会同时有两个)
  _ptid=tid;_pfname=fname;_ponDone=onDone;_pdone=false;_plastErr='';_ptries=0;
  tick();                        // 立即首查 (任务快时也能抓到解析阶段)
  _ptimer=setInterval(tick,300);
}
function tick(){
  if(_pdone||!_ptid)return;
  if(++_ptries>1000){            // 5 分钟超时兜底 (任务表容量清理后 progress=unknown 时防无限轮询)
    _pdone=true;stopPoll();
    if(onImportPage())setErr('导入超时 (5 分钟), 请重试');
    else sbTask('❌ 导入超时, 请重试','err');
    return;
  }
  A.get('/api/import/progress?task_id='+_ptid).then(function(p){
    if(_pdone||!_ptid)return;
    if(p&&p.status==='done'){
      _pdone=true;stopPoll();
      if(p.result){
        if(onImportPage()){setProg('');sr(p.result,_pfname);if(_ponDone)_ponDone();}  // sr 内 sb() 覆盖为统计
        else sbTask('✅ 完成 · 点击查看','done');                                       // 非导入页仅提示, 不刷新
      }else{
        if(onImportPage())setErr('导入完成但结果缺失, 请刷新页面');
        else sbTask('❌ 完成但结果缺失','err');
      }
    }else if(p&&p.status==='error'){
      _pdone=true;stopPoll();
      if(onImportPage())setErr(p.error||'导入失败');
      else{_plastErr=p.error||'导入失败';sbTask('❌ 失败 · 点击查看','err');}
    }else if(p&&p.status==='running'){
      var st=p.stage||'解析中',pct=p.percent||0;
      sbTask('⟳ '+st+' '+(pct!=null?pct+'%':''),'run');
      if(onImportPage())setProg(st+' ('+pct+'%)',pct);   // 切回导入页时进度条由 tick 恢复
    }
  }).catch(function(){});       // 网络抖动静默, 下个 tick 重试
}
// 顶栏 #sb 点击 → 跳回导入页 (仅任务已终态且不在导入页时)
document.addEventListener('click',function(e){
  var t=e.target;
  if(t&&t.id==='sb'&&_pdone&&!onImportPage()){
    var err=_plastErr;
    if(err)setTimeout(function(){setErr(err);},120);     // 等 rt() 重建导入页 DOM 后恢复错误详情
    location.hash='import';
  }
});
// ⚠️ 时区修复 (08-13): 曾 getUTCHours (UTC 偏 8h); 抓包/导入页为本地时间 → 统一本地
export function fmtTs(ts){var d=new Date(ts*1000);return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')+':'+d.getSeconds().toString().padStart(2,'0');}