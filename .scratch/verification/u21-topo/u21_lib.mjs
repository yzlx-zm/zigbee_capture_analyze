// U21 验证共用库 — 在 t3-manual/shot_lib.mjs 基础上加:
// addScriptToEvaluateOnNewDocument 钩住 cytoscape 工厂 → window.__cy (测试专用, 产品代码零改动)
export const CDP = 'http://127.0.0.1:9222';
const fs = await import('fs');
const fsp = await import('fs/promises');

// ⚠️ 必须用 defineProperty 拦截赋值: document-start 时 cytoscape.min.js 还没加载
// (曾直接读 window.cytoscape → undefined → 钩子静默失效)
const HOOK = `(function(){
  var _v;
  Object.defineProperty(window,'cytoscape',{configurable:true,get:function(){return _v;},
    set:function(v){
      if(typeof v!=='function'){_v=v;return;}
      var w=function(){var inst=v.apply(this,arguments);
        try{window.__cy=inst;
          // 计时钩子: 包住 layout().run() → 记录布局应用耗时 (大网络性能实测用)
          var ol=inst.layout;
          inst.layout=function(){var lo=ol.apply(this,arguments);
            if(lo&&typeof lo.run==='function'&&!lo.__u21w){
              var orun=lo.run;
              lo.run=function(){var t0=performance.now();var r=orun.apply(this,arguments);
                var ms=performance.now()-t0;
                window.__u21_lastMs=Math.round(ms*10)/10;
                window.__u21_sumMs=Math.round(((window.__u21_sumMs||0)+ms)*10)/10;
                window.__u21_n=(window.__u21_n||0)+1;
                return r;};
              lo.__u21w=1;}
            return lo;};
        }catch(e){}
        return inst;};
      for(var k in v){try{w[k]=v[k];}catch(e){}}
      _v=w;
    }});
})();`;

export async function openTab(url, { width = 1440, height = 940 } = {}) {
  const t = await (await fetch(`${CDP}/json/new?about:blank`, { method: 'PUT' })).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(); const exceptions = [];
  ws.onmessage = e => { const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
    if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails?.exception?.description || 'x'); };
  // ⚠️ 超时保护: 页面死循环 (主线程阻塞) 时 Runtime.evaluate 永不返回 → 卡死验证脚本
  const send = (method, params = {}, ms = 25000) => new Promise(res => {
    const i = ++id; const to = setTimeout(() => { pending.delete(i); res({ timeout: true }); }, ms);
    pending.set(i, m => { clearTimeout(to); res(m); }); ws.send(JSON.stringify({ id: i, method, params })); });
  const evf = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.timeout) { exceptions.push('TIMEOUT(页面主线程阻塞?): ' + expr.slice(0, 80)); return { err: 'timeout' }; }
    if (r.result?.exceptionDetails) exceptions.push('eval: ' + (r.result.exceptionDetails.exception?.description || '').slice(0, 200));
    return r.result?.result?.value; };
  await send('Page.enable'); await send('Runtime.enable');
  // ⚠️ 必须禁用缓存: 同一版本号下改了 js → 浏览器命中旧缓存 (第 2 轮验证踩到: 修复版未生效)
  await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Page.addScriptToEvaluateOnNewDocument', { source: HOOK });
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url });
  return {
    id: t.id, ws, send, ev: evf, exceptions,
    shot: async (path) => {
      const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 88 });
      const dir = path.substring(0, path.lastIndexOf('/'));   // ⚠️ 无目录部分时 mkdir('') → ENOENT
      if (dir) await fsp.mkdir(dir, { recursive: true });
      await fs.promises.writeFile(path, Buffer.from(r.result.data, 'base64'));
      console.log('📷', path);
    },
    close: () => fetch(`${CDP}/json/close/${t.id}`),
  };
}
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export const CHECKS = [];
export function check(name, ok, extra = '') {
  CHECKS.push({ name, ok: !!ok });
  console.log(`${ok ? '✅' : '❌'} ${name}${extra ? ' — ' + extra : ''}`);
}
export function summary(extraLines = []) {
  const ok = CHECKS.filter(c => c.ok).length;
  console.log(`\n===== 汇总: ${ok}/${CHECKS.length} =====`);
  extraLines.forEach(l => console.log(l));
  return ok === CHECKS.length;
}

// 页面内取值辅助 (统一在 __cy 上做数值断言)
export const P = {
  state: `(function(){var c=window.__cy;if(!c)return {err:'no cy'};
    return {nodes:c.nodes().length,edges:c.edges().length,
      badges:c.nodes('[is_badge]').length,
      tinfo:(document.getElementById('tinfo')||{}).textContent,
      layout:(document.getElementById('tlaymode')||{}).value};})()`,
  positions: `(function(){var c=window.__cy;if(!c)return null;var o={};
    c.nodes().forEach(function(n){var p=n.position();o[n.id()]=[Math.round(p.x*100)/100,Math.round(p.y*100)/100];});return o;})()`,
  // 几何断言: 分环/交叉/重叠/标签 (返回纯数值, 由调用方判定)
  geo: `(function(){
  var c=window.__cy;
  var ns=c.nodes().filter(function(n){return !n.data('is_badge');});
  var bd=c.nodes('[is_badge]');
  var par={};
  ns.forEach(function(n){par[n.data('aid')]=n.data('link_parent');});
  // 深度: 沿父链走到根 (0x0000); 走不到根 (无父证据/父不在集) → -1 = 孤儿 (最外环, 单独成组)
  function dep(a){var d=0,cur=a,g=0;
    while(cur!=null&&g++<30){var pp=par[cur];if(pp==null||pp===cur)break;cur=pp;d++;}
    return (cur===0||a===0)?d:-1;}
  var rings={}, rows=[];
  ns.forEach(function(n){var a=n.data('aid');var p=n.position();
    var R=Math.round(Math.hypot(p.x,p.y));var d=dep(a);
    (rings[d]=rings[d]||[]).push(R);
    rows.push({aid:a,dep:d,R:R,dt:n.data('device_type'),x:Math.round(p.x),y:Math.round(p.y)});});
  var ringBad=[], ringR={};
  for(var k in rings){var arr=rings[k],mn=Math.min.apply(null,arr),mx=Math.max.apply(null,arr);
    ringR[k]=mn; if(mx-mn>1)ringBad.push(k+':'+mn+'~'+mx);}
  var ds=Object.keys(ringR).map(Number).sort(function(a,b){return a-b;});
  var incOk=true,prev=-1;ds.forEach(function(d){if(ringR[d]<prev)incOk=false;prev=ringR[d];});
  var segs=[];
  ns.forEach(function(n){var lp=n.data('link_parent');if(lp==null)return;
    var pp=c.getElementById(''+lp); if(!pp.nonempty())return;
    segs.push({a:n.position(),b:pp.position(),ids:[n.id(),''+lp]});});
  function ccw(A,B,C){return (C.y-A.y)*(B.x-A.x)>(B.y-A.y)*(C.x-A.x);}
  function inter(A,B,C,D){return (ccw(A,C,D)!==ccw(B,C,D))&&(ccw(A,B,C)!==ccw(A,B,D));}
  var cross=0,cps=[];
  for(var i=0;i<segs.length;i++)for(var j=i+1;j<segs.length;j++){
    var s=segs[i],t=segs[j];
    if(s.ids[0]===t.ids[0]||s.ids[0]===t.ids[1]||s.ids[1]===t.ids[0]||s.ids[1]===t.ids[1])continue;
    if(inter(s.a,s.b,t.a,t.b)){cross++;if(cps.length<4)cps.push(s.ids.join('+')+' x '+t.ids.join('+'));}}
  var ov=0,ovp=[];
  for(var i=0;i<ns.length;i++)for(var j=i+1;j<ns.length;j++){
    var A=ns[i],B=ns[j],pa=A.position(),pb=B.position();
    var dd=Math.hypot(pa.x-pb.x,pa.y-pb.y),rr=(A.width()+B.width())/2;
    if(dd<rr-1){ov++;if(ovp.length<4)ovp.push(A.id()+'-'+B.id());}}
  var vis=[],hid=0;
  ns.forEach(function(n){var to=n.style('text-opacity');var num=parseFloat(to);if(isNaN(num))num=1;
    if(num<0.5){hid++;return;}
    vis.push({id:n.id(),bb:n.renderedBoundingBox(),dt:n.data('device_type'),lbl:String(n.data('label')).replace(/\\n/g,'|')});});
  var lbOv=0,lbp=[];
  for(var i=0;i<vis.length;i++)for(var j=i+1;j<vis.length;j++){
    var A=vis[i].bb,B=vis[j].bb;
    var ox=Math.min(A.x2,B.x2)-Math.max(A.x1,B.x1),oy=Math.min(A.y2,B.y2)-Math.max(A.y1,B.y1);
    if(ox>1&&oy>1){lbOv++;if(lbp.length<4)lbp.push(vis[i].id+'/'+vis[i].lbl+' x '+vis[j].id+'/'+vis[j].lbl+' ('+Math.round(ox)+'x'+Math.round(oy)+')');}}
  var bb=c.nodes().boundingBox();
  var bh=[]; bd.forEach(function(n){bh.push({id:n.id(),lbl:String(n.data('label')).replace(/\\n/g,'|'),cnt:n.data('count'),pa:n.data('parent_aid'),open:n.hasClass('agg-open'),stats:n.data('stats')});});
  // 徽章与所属父节点的距离 (贴父节点)
  var bd2=[]; bd.forEach(function(n){var pp=c.getElementById(''+n.data('parent_aid'));
    bd2.push({id:n.id(),dist:pp.nonempty()?Math.round(Math.hypot(pp.position().x-n.position().x,pp.position().y-n.position().y)):-1});});
  return {n:ns.length,badge:bd.length,badges:bh,badgeDist:bd2,rings:ringR,ringBad:ringBad,ringInc:incOk,
    segs:segs.length,cross:cross,cps:cps,nodeOv:ov,ovp:ovp,lblVis:vis.length,lblHid:hid,lblOv:lbOv,lbp:lbp,
    w:Math.round(bb.w),h:Math.round(bb.h),rows:rows};})()`,
};
