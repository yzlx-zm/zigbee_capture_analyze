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

function l1Card(scenario, title, verdict, confidence, bodyHtml, conclusion, evidence, evTotal) {
  return '<div class="l1-card">'
    + '<h4>' + scenario + ' ' + title + ': '
    + '<span class="' + vClass(verdict, scenario) + '">' + (verdict || '—') + '</span> '
    + '<span class="conf" title="' + CONF_TITLE + '">置信度:' + (confidence || '—') + '</span></h4>'
    + (conclusion ? '<div class="conclusion" style="font-size:12px;font-weight:600;color:#1e293b;background:#f1f5f9;border-radius:4px;padding:6px 8px;margin:6px 0">💬 ' + conclusion + '</div>' : '')
    + '<div class="body">' + bodyHtml + '</div>'
    + evTable(evidence, evTotal)
    + '</div>';
}

// 证据表 (人工复核: 帧号/时间/类型/关键字段), 可折叠
function evTable(evidence, evTotal) {
  if (!evidence || !evidence.length) return '';
  var rows = (evidence || []).map(function (e) {
    return '<tr><td class="mono" style="font-family:monospace;font-size:10px">' + (e.ts != null ? e.ts.toFixed(3) : '—') + '</td>'
      + '<td class="mono" style="font-family:monospace;font-size:10px">' + (e.packet_id != null ? e.packet_id : '—') + '</td>'
      + '<td style="font-size:10px">' + (e.type || '') + '</td>'
      + '<td class="text-dim" style="font-size:10px;color:#64748b">' + (e.detail || '') + '</td></tr>';
  }).join('');
  var total = evTotal || (evidence || []).length;
  var note = total > evidence.length ? ('共 ' + total + ' 条, 展示前 ' + evidence.length + ' 条') : ('共 ' + total + ' 条');
  return '<details class="ev-table" style="margin-top:6px;border-top:1px dashed #e2e8f0;padding-top:4px">'
    + '<summary style="font-size:10px;color:#3b82f6;cursor:pointer">📋 证据帧 (' + note + ')</summary>'
    + '<table style="width:100%;border-collapse:collapse;margin-top:4px">'
    + '<thead><tr style="font-size:10px;color:#94a3b8;text-align:left">'
    + '<th style="padding:2px 4px">时间(s)</th><th style="padding:2px 4px">帧号</th>'
    + '<th style="padding:2px 4px">类型</th><th style="padding:2px 4px">关键字段</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></details>';
}

function devLine(dev, verdict, subRule, statsHtml, summary, hitPrefix) {
  var dc = vClass(verdict, hitPrefix || 'L1');
  return '<div class="dev"><b>0x' + dev.toString(16).toUpperCase().padStart(4, '0') + '</b>: '
    + '<span class="' + dc + '">' + (verdict || '—') + (subRule ? ' (' + subRule + ')' : '') + '</span> '
    + '<span class="text-dim">' + statsHtml + '</span>'
    + (summary ? '<div class="sum">' + summary + '</div>' : '')
    + '</div>';
}

// ── 顶部诊断摘要 (通俗结论, 2026-08-05 需求) ──
var PLAIN_TITLES = {
  'L1-1': '设备找不到网络',
  'L1-2': '设备入网失败或被拒',
  'L1-3': '密钥分发或验证出问题',
  'L1-4': '设备被网关拒绝或踢出',
  'L2-1': '终端频繁离线',
  'L3-5': '设备收不到网关下发',
  'L6-3': 'SED 消息收不到',
  'OFF': '设备离网',
};
var PLAIN_VERDICT = { 'L1-1': 'L1-1', 'L1-2': 'L1-2', 'L1-3': 'L1-3', 'L1-4': 'L1-4', 'L3-5': 'L3-5', 'OFF': 'OFF' };

function summaryCard(checks) {
  // checks: [{scenario, verdict, conclusion}]
  var probs = (checks || []).filter(function (c) {
    return c.verdict && c.verdict.indexOf('_HIT') !== -1;
  });
  var unknown = (checks || []).filter(function (c) {
    return c.verdict === 'INCONCLUSIVE';
  });
  var h = '<div class="card" style="margin-bottom:12px;border-left:4px solid '
    + (probs.length ? '#dc2626' : '#16a34a') + '">'
    + '<h3 style="font-size:14px;margin-bottom:6px">'
    + (probs.length ? '⚠️ 诊断结论: 发现问题 ' + probs.length + ' 项' : '✅ 诊断结论: 未发现明显问题')
    + '</h3>';
  if (probs.length) {
    h += '<ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.8">';
    (probs || []).forEach(function (p) {
      var title = PLAIN_TITLES[p.scenario] || p.scenario;
      h += '<li><b>' + title + '</b>：' + (p.conclusion || '') + '</li>';
    });
    h += '</ul>';
  } else if (unknown.length) {
    h += '<p style="font-size:12px;color:#b45309;margin:4px 0 0">⚠️ 部分检测因数据不足无法判定 ('
      + unknown.map(function (u) { return PLAIN_TITLES[u.scenario] || u.scenario; }).join('、')
      + ')，未排除问题的存在。</p>';
  }
  h += '</div>';
  return h;
}

reg('diag', function () {
  document.getElementById('mc').style.padding = '16px';
  var h = '<div class="card"><h3>🩺 网络诊断</h3>'
    + '<p class="hint mt-1">基于协议数据 (Leave/Rejoin/Announce/Network Status) 的离线诊断</p></div>'
    + '<!--DIAG-SUMMARY-->';
  // ⚠️ 2026-08-05 修复: 摘要区被 innerHTML 重建覆盖 (先填旧 DOM 再整体重渲)
  // 改用注释占位 + 统一渲染; 2026-08-06 摘要独立渲染:
  // 各检测完成即写入 checks, renderH() 动态生成 — 不再依赖最内层回调 (L6 失败曾致摘要丢失)
  var checks = {};
  function renderH() {
    var summaryHtml = Object.keys(checks).length ? summaryCard(Object.keys(checks).map(function (k) { return checks[k]; })) : '';
    document.getElementById('mc').innerHTML = h.replace('<!--DIAG-SUMMARY-->', summaryHtml);
  }

  // ── L1 入网检测区 (文档→测试→工具工作流验证) ──
  A.get('/api/diag/l1').then(function (l1d) {
    if (l1d && l1d.error) {
      h += '<div class="card card-danger">'
        + '<h3 class="text-danger">L1 入网检测</h3>'
        + '<p class="hint">' + l1d.error + ' (L1 检测需要 .cubx 或含 MAC 帧的 pcap)</p></div>';
      renderH();
      renderOffline();
      return;
    }
    var l1 = l1d ? (l1d.l1_1 || {}) : {};
    var l2 = l1d ? (l1d.l1_2 || {}) : {};
    var l3 = l1d ? (l1d.l1_3 || {}) : {};
    var l4 = l1d ? (l1d.l1_4 || {}) : {};

    // 摘要独立收集: 每层检测成功即写入, renderH() 动态渲染 (2026-08-06)
    checks['L1-1'] = { scenario: 'L1-1', verdict: l1.verdict, conclusion: l1.conclusion };
    checks['L1-2'] = { scenario: 'L1-2', verdict: l2.verdict, conclusion: l2.conclusion };
    checks['L1-3'] = { scenario: 'L1-3', verdict: l3.verdict, conclusion: l3.conclusion };
    checks['L1-4'] = { scenario: 'L1-4', verdict: l4.verdict, conclusion: l4.conclusion };

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
      + l1Card('L1-1', '发现失败', l1.verdict, l1.confidence, b1, l1.conclusion, l1.evidence, l1.evidence_total)
      + l1Card('L1-2', 'Association', l2.verdict, l2.confidence, b2, l2.conclusion, l2.evidence, l2.evidence_total)
      + l1Card('L1-3', '密钥分发', l3.verdict, l3.confidence, b3, l3.conclusion, l3.evidence, l3.evidence_total)
      + l1Card('L1-4', 'TC 拒绝/踢人', l4.verdict, l4.confidence, b4, l4.conclusion, l4.evidence, l4.evidence_total)
      + '</div></div>';

    // ── L2 在线维持检测区 (L2-1 终端频繁离线) ──
    A.get('/api/diag/l2').then(function (l2d) {
      var l21 = l2d && !l2d.error ? (l2d.l2_1 || {}) : {};
      checks['L2-1'] = { scenario: 'L2-1', verdict: l21.verdict, conclusion: l21.conclusion };
      var b2x = 'poll 设备: <b>' + (l21.poll_device_count || 0) + '</b> 台 | poll 帧: <b>' + (l21.poll_total || 0) + '</b> | rejoin=1 Leave: <b>' + (l21.leave_rejoin_total || 0) + '</b><br>'
        + '<span class="text-muted">' + (l21.summary || '') + '</span>'
        + ((l21.devices || []).length ? '<div class="divider">'
          + (l21.devices || []).map(function (d) {
              return devLine(d.device, d.verdict, d.sub_rule,
                'poll' + (d.poll_count || 0), d.summary, 'L2-1');
            }).join('')
          + '</div>' : '');
      h += '<div class="card l1-sec">'
        + '<h3>📡 L2 在线维持检测 <span class="conf">(文档→测试→工具)</span></h3>'
        + '<div class="l1-cards">'
        + l1Card('L2-1', '终端频繁离线', l21.verdict, l21.confidence, b2x, l21.conclusion, l21.evidence, l21.evidence_total)
        + '</div></div>';

    // ── L3 运营期检测区 (L3-5 源路由/MTORR 失效) ──
    A.get('/api/diag/l3').then(function (l3d) {
      var l35 = l3d && !l3d.error ? (l3d.l3_5 || {}) : {};
      checks['L3-5'] = { scenario: 'L3-5', verdict: l35.verdict, conclusion: l35.conclusion };
      var b5 = 'Network Status: <b>' + (l35.network_status_total || 0) + '</b> 帧'
        + ' | 0x0B 源路由: <b class="' + vClass(l35.verdict, 'L3-5') + '">' + (l35.source_route_failure_count || 0) + '</b>'
        + ' | 0x0C MTORR: <b>' + (l35.mto_route_failure_count || 0) + '</b><br>'
        + '<span class="text-muted">' + (l35.summary || '') + '</span>'
        + (l35.network_status_codes ? '<br><span class="text-dim">全码分布: ' + Object.keys(l35.network_status_codes).map(function (c) { return c + '×' + l35.network_status_codes[c]; }).join(' ') + '</span>' : '')
        + (l35.self_heal ? '<br><span class="text-dim">自愈: ' + l35.self_heal.note + '</span>' : '')
        + ((l35.devices || []).length ? '<div class="divider">'
          + (l35.devices || []).map(function (d) {
              return devLine(d.device, d.verdict, d.sub_rule,
                'NS' + (d.route_error_count || 0) + '/轮' + (d.rounds || 0), d.summary, 'L3-5');
            }).join('')
          + '</div>' : '');
      h += '<div class="card l1-sec">'
        + '<h3>🔧 L3 运营期检测 <span class="conf">(文档→测试→工具)</span></h3>'
        + '<div class="l1-cards">'
        + l1Card('L3-5', '源路由/MTORR 失效', l35.verdict, l35.confidence, b5, l35.conclusion, l35.evidence, l35.evidence_total)
        + '</div></div>';
      // ── L6 SED 专项检测区 (L6-S3 间接事务过期) ──
      A.get('/api/diag/l6').then(function (l6d) {
        var l63 = l6d && !l6d.error ? (l6d.l6_3 || {}) : {};
        checks['L6-3'] = { scenario: 'L6-3', verdict: l63.verdict, conclusion: l63.conclusion };
        var b6x = '0x06 间接过期: <b>' + (l63.expiry_count || 0) + '</b> 帧 | 0x05 队列满: <b>' + (l63.no_indirect_capacity_count || 0) + '</b><br>'
          + '<span class="text-muted">' + (l63.summary || '') + '</span>'
          + ((l63.devices || []).length ? '<div class="divider">'
            + (l63.devices || []).map(function (d) {
                return devLine(d.device, d.verdict, d.sub_rule,
                  '0x06×' + (d.expiry_count || 0), d.summary, 'L6-3');
              }).join('')
            + '</div>' : '');
        h += '<div class="card l1-sec">'
          + '<h3>🌙 L6 SED 专项检测 <span class="conf">(文档→测试→工具)</span></h3>'
          + '<div class="l1-cards">'
          + l1Card('L6-3', '间接事务过期', l63.verdict, l63.confidence, b6x, l63.conclusion, l63.evidence, l63.evidence_total)
          + '</div></div>';

        // 摘要已独立渲染 (checks 收集 + renderH 动态生成), 此处只需渲染卡片与离线区
        renderH();
        renderOffline();
      }).catch(function () {  // L6 失败不阻塞
        renderH();
        renderOffline();
      });
    }).catch(function () {
      renderH();
      renderOffline();
    });
    }).catch(function () {  // L2 失败不阻塞
      renderH();
      renderOffline();
    });
  }).catch(function () {
    // L1 失败不阻塞离线诊断
    renderH();
    renderOffline();
  });

  function renderOffline() {
    A.get('/api/diag/offline').then(function (d) {
      var devs = d.devices || [];
      if (!devs.length) {
        h += '<div class="card empty">'
          + '<p>✅ ' + (d.conclusion || '未发现设备离网事件') + '</p>'
          + '<p class="sub">当前抓包中没有 NWK Leave 或 Device Announce 帧</p></div>';
      } else {
        var s = d.summary || {};
        h += '<div class="card card-info">'
          + '<div class="text-strong t-13">📊 设备离线总览</div>'
          + (d.conclusion ? '<div class="conclusion" style="font-size:12px;font-weight:600;color:#1e293b;background:#f1f5f9;border-radius:4px;padding:6px 8px;margin:6px 0">💬 ' + d.conclusion + '</div>' : '')
          + '<div class="stats t-12">'
          + '<span>离网设备: <b class="text-danger-strong">' + s.total_devices_left + '</b></span>'
          + '<span>被踢: <b>' + s.kicked + '</b></span>'
          + '<span>主动: <b>' + s.voluntary + '</b></span>'
          + '<span>有重入网尝试: <b class="text-info">' + s.with_rejoin + '</b></span>'
          + '</div>'
          + evTable(d.evidence, d.evidence_total)
          + '</div>';
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
      renderH();
    }).catch(function (e) {
      renderH(); document.getElementById('mc').innerHTML += '<div class="card text-danger">诊断数据加载失败: ' + e.message + '</div>';
    });
  }
});
