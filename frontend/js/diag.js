// diag.js — 诊断页面模块 (ES module)
// UI 对齐 (2026-08-04): L1-1/2/3/4 卡片统一模板 + None 防御 + 视觉规范 (.l1-card)
import { S, A } from './state.js';

// ── L1 卡片统一渲染工具 ──
var CONF_TITLE = '置信度: 高=直接证据/中=帧模式/低=推断/不可判定=数据不足';

function vClass(verdict, hitPrefix) {
  // verdict: HEALTHY → 绿; <hitPrefix>_HIT → 红; 其他 → 琥珀
  if (verdict === 'HEALTHY') return 'v-ok';
  if (hitPrefix && verdict.indexOf(hitPrefix + '_HIT') === 0) return 'v-bad';
  return 'v-warn';
}

function l1Card(scenario, title, verdict, confidence, bodyHtml) {
  return '<div class="l1-card">'
    + '<h4>' + scenario + ' ' + title + ': '
    + '<span class="' + vClass(verdict, scenario) + '">' + (verdict || '—') + '</span> '
    + '<span class="conf" title="' + CONF_TITLE + '">置信度:' + (confidence || '—') + '</span></h4>'
    + '<div class="body">' + bodyHtml + '</div></div>';
}

function devLine(dev, verdict, subRule, statsHtml, summary) {
  var dc = vClass(verdict, 'L1');
  return '<div class="dev"><b>0x' + dev.toString(16).toUpperCase().padStart(4, '0') + '</b>: '
    + '<span class="' + dc + '">' + (verdict || '—') + (subRule ? ' (' + subRule + ')' : '') + '</span> '
    + '<span class="text-dim">' + statsHtml + '</span>'
    + (summary ? '<div class="sum">' + summary + '</div>' : '')
    + '</div>';
}

reg('diag', function () {
  document.getElementById('mc').style.padding = '16px';
  var h = '<div class="card"><h3>🩺 网络诊断</h3>'
    + '<p class="hint mt-1">基于协议数据 (Leave/Rejoin/Announce/Network Status) 的离线诊断</p></div>';

  // ── L1 入网检测区 (文档→测试→工具工作流验证) ──
  A.get('/api/diag/l1').then(function (l1d) {
    if (l1d && l1d.error) {
      h += '<div class="card card-danger">'
        + '<h3 class="text-danger">L1 入网检测</h3>'
        + '<p class="hint">' + l1d.error + ' (L1 检测需要 .cubx 或含 MAC 帧的 pcap)</p></div>';
      document.getElementById('mc').innerHTML = h;
      renderOffline();
      return;
    }
    var l1 = l1d ? (l1d.l1_1 || {}) : {};
    var l2 = l1d ? (l1d.l1_2 || {}) : {};
    var l3 = l1d ? (l1d.l1_3 || {}) : {};
    var l4 = l1d ? (l1d.l1_4 || {}) : {};

    // ── L1-1 卡片 ──
    var b1 = 'Beacon Request: <b>' + (l1.beacon_request_count || 0) + '</b> 个 | 命中 <b class="' + vClass(l1.verdict, 'L1-1') + '">'
      + (l1.hit_count || 0) + '/' + (l1.beacon_request_count || 0) + '</b> '
      + '(' + Math.round((l1.hit_rate || 0) * 100) + '%)<br>'
      + '最大连续MISS: <b>' + (l1.max_consecutive_miss || 0) + '</b> (判定阈值≥2)<br>'
      + (l1.delay_summary_ms ? '响应延迟: <b>' + l1.delay_summary_ms.min + '~' + l1.delay_summary_ms.max + '</b>ms (median ' + l1.delay_summary_ms.median + ')' : '');

    // ── L1-2 卡片 ──
    var b2 = 'AssocReq: <b>' + (l2.assoc_req_count || 0) + '</b> | 成功 <b class="v-ok">' + (l2.success_count || 0)
      + '</b> | 无响应 <b class="v-warn">' + (l2.no_response_count || 0)
      + '</b> | 拒绝 <b class="v-bad">' + (l2.rejected_count || 0) + '</b><br>'
      + '<span class="text-muted">' + (l2.summary || '') + '</span>';

    // ── L1-3 卡片 ──
    var b3 = '入网设备: <b>' + (l3.joined_device_count || 0) + '</b> 台<br>'
      + '<span class="text-muted">' + (l3.summary || '') + '</span>'
      + ((l3.devices || []).length ? '<div class="divider">'
        + (l3.devices || []).map(function (d) {
            return devLine(d.device, d.verdict, d.sub_rule,
              'T' + (d.transport_nwk || 0) + '/RQ' + (d.request_key || 0)
              + '/Tclk' + (d.transport_tclk || 0) + '/V' + (d.verify || 0)
              + '/C' + (d.confirm || 0) + '/L' + (d.leave || 0)
              + (d.route_error ? '/R' + d.route_error : ''),
              d.summary);
          }).join('')
        + '</div>' : '');

    // ── L1-4 卡片 ──
    var b4 = 'Remove Device(0x07): <b>' + (l4.remove_event_count || 0) + '</b> 帧 | 入网设备: <b>' + (l4.joined_device_count || 0) + '</b> 台<br>'
      + '<span class="text-muted">' + (l4.summary || '') + '</span>'
      + ((l4.remove_events || []).length ? '<div class="divider">'
        + (l4.remove_events || []).map(function (r) {
            var d = r.nwk_dst != null ? '0x' + r.nwk_dst.toString(16).toUpperCase().padStart(4, '0') : '0x?';
            var s = r.nwk_src != null ? '0x' + r.nwk_src.toString(16).toUpperCase().padStart(4, '0') : '0x?';
            return '<div class="dev mono">' + d + ' ← ' + s
              + (r.target_eui64 ? ' → ' + r.target_eui64 : '') + '</div>';
          }).join('')
        + '</div>' : '')
      + ((l4.devices || []).length ? '<div class="divider">'
        + (l4.devices || []).map(function (d) {
            return devLine(d.device, d.verdict, d.sub_rule,
              'Rm' + (d.remove_device || 0) + '/Ann' + (d.announce || 0) + '/Lv' + (d.leave || 0),
              d.summary);
          }).join('')
        + '</div>' : '');

    h += '<div class="card l1-sec">'
      + '<h3>🔍 L1 入网检测 <span class="conf">(文档→测试→工具)</span></h3>'
      + '<div class="l1-cards">'
      + l1Card('L1-1', '发现失败', l1.verdict, l1.confidence, b1)
      + l1Card('L1-2', 'Association', l2.verdict, l2.confidence, b2)
      + l1Card('L1-3', '密钥分发', l3.verdict, l3.confidence, b3)
      + l1Card('L1-4', 'TC 拒绝/踢人', l4.verdict, l4.confidence, b4)
      + '</div></div>';

    document.getElementById('mc').innerHTML = h;
    renderOffline();
  }).catch(function () {
    // L1 失败不阻塞离线诊断
    document.getElementById('mc').innerHTML = h;
    renderOffline();
  });

  function renderOffline() {
    A.get('/api/diag/offline').then(function (d) {
      var devs = d.devices || [];
      if (!devs.length) {
        h += '<div class="card empty">'
          + '<p>✅ 未发现设备离网事件</p>'
          + '<p class="sub">当前抓包中没有 NWK Leave 或 Device Announce 帧</p></div>';
      } else {
        var s = d.summary || {};
        h += '<div class="card card-info">'
          + '<div class="text-strong t-13">📊 设备离线总览</div>'
          + '<div class="stats t-12">'
          + '<span>离网设备: <b class="text-danger-strong">' + s.total_devices_left + '</b></span>'
          + '<span>被踢: <b>' + s.kicked + '</b></span>'
          + '<span>主动: <b>' + s.voluntary + '</b></span>'
          + '<span>有重入网尝试: <b class="text-info">' + s.with_rejoin + '</b></span>'
          + '</div></div>';
        for (var i = 0; i < devs.length; i++) {
          var dev = devs[i];
          var typeLabel = dev.device_type === 'coordinator' ? '协调器' : dev.device_type === 'router' ? '路由器' : '终端设备';
          var eui = dev.eui64 || '未知';
          if (eui.length === 16) { eui = eui.slice(0, 2) + ':' + eui.slice(2, 4) + ':' + eui.slice(4, 6) + ':' + eui.slice(6, 8) + ':' + eui.slice(8, 10) + ':' + eui.slice(10, 12) + ':' + eui.slice(12, 14) + ':' + eui.slice(14, 16); }

          h += '<div class="card diag-card">'
            + '<div class="diag-header">'
            + '<span class="dev-label">' + dev.label + '</span>'
            + '<span class="dev-eui">' + eui + '</span>'
            + '<span class="badge">' + typeLabel + '</span>'
            + '</div>';

          var pe = dev.pre_events || {};
          h += '<div class="diag-timeline">';
          h += '<div class="diag-ev"><span class="diag-ic diag-ic-com">▸</span> 正常通信 (Link Status, Route Record, Data)</div>';
          if (pe.network_status_count > 0) { h += '<div class="diag-ev"><span class="diag-ic diag-ic-warn">⚠</span> Network Status ×' + pe.network_status_count + ' (路由层异常前置信号)</div>'; }
          if (pe.ieee_addr_req_count > 0) { h += '<div class="diag-ev"><span class="diag-ic diag-ic-info">🔍</span> IEEE Addr Req ×' + pe.ieee_addr_req_count + ' (协调器查询设备身份)</div>'; }
          var bursts = dev.leave_bursts || [];
          for (var b = 0; b < bursts.length; b++) {
            var burst = bursts[b];
            var bt = burst.burst_index === 1 ? '第一波' : burst.burst_index === 2 ? '第二波' : ('第' + burst.burst_index + '波');
            var bc = burst.count > 1 ? (' ×' + burst.count) : '';
            var typeName = burst.type === 'kicked' ? '[被踢]' : burst.type === 'voluntary_permanent' ? '[主动永久]' : burst.type === 'voluntary_rejoin' ? '[主动暂离]' : '[被踢·可重入]';
            h += '<div class="diag-ev"><span class="diag-ic diag-ic-leave">✕</span> ' + bt + ' Leave' + bc + ' ' + typeName + '</div>';
          }
          var rej = dev.rejoin_attempts || [];
          for (var r = 0; r < rej.length; r++) {
            var rj = rej[r];
            h += '<div class="diag-ev"><span class="diag-ic diag-ic-join">📢</span> Device Announce ×' + rj.announce_count + ' (第' + rj.after_burst + '波Leave后 ' + rj.delay_seconds + 's) ← 重入网尝试</div>';
          }
          h += '</div>';
          var diag = dev.diagnosis || {};
          h += '<div class="diag-conclusion">'
            + '<b>诊断: </b>' + diag.summary
            + '</div>';
          h += '</div>';
        }
      }
      document.getElementById('mc').innerHTML = h;
    }).catch(function (e) {
      document.getElementById('mc').innerHTML = h + '<div class="card text-danger">诊断数据加载失败: ' + e.message + '</div>';
    });
  }
});
