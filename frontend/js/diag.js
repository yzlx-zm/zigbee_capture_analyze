// diag.js — 诊断页面模块 (ES module)
// UI 对齐 (2026-08-04): L1-1/2/3/4 卡片统一模板 + None 防御 + 视觉规范 (.l1-card)
// 2026-08-10 (U8-1): 四层 then 嵌套 → 检测器注册表 (数据驱动) —
//   新增检测只需注册表加条目 + 一个 render 函数, 主流程 (Promise.all + renderH) 不动。
import { S, A, fmtTs } from './state.js';

// ── L1 卡片统一渲染工具 ──
var CONF_TITLE = '置信度: 高=直接证据/中=帧模式/低=推断/不可判定=数据不足';

function vClass(verdict, hitPrefix) {
  // verdict: HEALTHY → 绿; <hitPrefix>_HIT → 红; 其他 → 琥珀
  if (verdict === 'HEALTHY') return 'v-ok';
  if (hitPrefix && verdict.indexOf(hitPrefix + '_HIT') === 0) return 'v-bad';
  return 'v-warn';
}

function l1Card(scenario, title, verdict, confidence, bodyHtml, conclusion, evidence, evTotal) {
  // 白话化 (08-10): 编号降级小角标, 标题/verdict 用 PLAIN_TITLES 白话; vClass 用 hitPrefixOf (修 L6-S3 前缀)
  var displayTitle = PLAIN_TITLES[scenario] || title;
  var scTag = '<span class="sc-tag" title="场景编号 ' + scenario + '">' + scenario + '</span> ';
  return '<div class="l1-card">'
    + '<h4>' + scTag + displayTitle + ': '
    + '<span class="' + vClass(verdict, hitPrefixOf(scenario)) + '" title="' + (verdict || '—') + '">' + verdictText(scenario, verdict) + '</span> '
    + '<span class="conf" title="' + CONF_TITLE + '">置信度:' + (confidence || '—') + '</span></h4>'
    + (conclusion ? '<div class="conclusion" style="font-size:12px;font-weight:600;color:#1e293b;background:#f1f5f9;border-radius:4px;padding:6px 8px;margin:6px 0">💬 ' + conclusion + '</div>' : '')
    + '<div class="body">' + bodyHtml + '</div>'
    + evTable(evidence, evTotal)
    + '</div>';
}

// 证据表 (人工复核: 帧号/时间/类型/关键字段), 可折叠
// S2 (2026-08-28): 帧号可点击 → 报文页定位 (tlJumpFrame 契约, 与 AI 侧边栏帧引用同机制)
function evJumpHtml(e) {
  var txt = (e.packet_id != null ? e.packet_id : '—');
  if (e.id == null) return '<span class="mono" style="font-family:monospace;font-size:10px">' + txt + '</span>';
  return '<a class="ev-jump mono" href="#tl" title="报文页查看该帧" '
    + 'onclick="event.stopPropagation();setTimeout(function(){window.tlJumpFrame&&window.tlJumpFrame(' + e.id + ')},300)">'
    + txt + '</a>';
}
function evTable(evidence, evTotal) {
  if (!evidence || !evidence.length) return '';
  var rows = (evidence || []).map(function (e) {
    // 2026-08-12 用户反馈: 绝对时间戳 13 位挤在一起 — 改时钟时间 (fmtTs, 与时间线一致)
    return '<tr><td class="mono" style="font-family:monospace;font-size:10px">' + (e.ts != null ? fmtTs(e.ts) : '—') + '</td>'
      + '<td>' + evJumpHtml(e) + '</td>'
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

function devLine(dev, verdict, subRule, statsHtml, summary, scenario) {
  // 2026-08-10 (U8-2): 设备地址跳转 (U4 联动落地) — 时间线过滤该设备
  // 复用 S.topoAddr 跨页契约 (U5 topoAddr→tlNode 同步); inline onclick 需 window.S (app.js 已暴露)
  // ⚠️ 08-10 用户反馈: 拓扑跳转无意义已移除, 仅保留时间线; emoji 用项目已验证的 🔍
  // 白话化 (08-10): verdict 显示白话 (修 L1-3 传 'L1' 前缀不匹配显示琥珀 bug), 规则码进 title
  var sc = scenario || 'L1';
  var dc = vClass(verdict, hitPrefixOf(sc));
  var addrTxt = '0x' + dev.toString(16).toUpperCase().padStart(4, '0');
  var jump = '<a class="dev-jump" href="#tl" title="报文页查看该设备" '
    + 'onclick="event.stopPropagation();S.topoAddr=\'' + addrTxt + '\';S.topoT0=null;S.topoT1=null;">🔍报文</a>';
  return '<div class="dev"><b>' + addrTxt + '</b> ' + jump + ': '
    + '<span class="' + dc + '" title="' + (verdict || '—') + (subRule ? ' (' + subRule + ')' : '') + '">'
    + verdictText(sc, verdict) + '</span> '
    + '<span class="text-dim">' + statsHtml + '</span>'
    + (summary ? '<div class="sum">' + summary + '</div>' : '')
    + '</div>';
}

// ── 跨卡片事件链 (2026-08-10 U8-2): 同设备多检测命中 → 提示可能是同一问题链 ──
// 各模块 render 命中时调 collectHit 登记; renderH 生成事件链卡 (≥2 项命中触发)
var hitDevices = {};
function collectHit(device, scenario, rule, summary) {
  if (device == null) return;
  (hitDevices[device] = hitDevices[device] || []).push({
    scenario: scenario, rule: rule, summary: summary,
  });
}

// ── 顶部诊断摘要 (通俗结论, 2026-08-05 需求) ──
var PLAIN_TITLES = {
  'L1-1': '设备找不到网络',
  'L1-2': '设备入网失败或被拒',
  'L1-3': '密钥分发或验证出问题',
  'L1-4': '设备被网关拒绝或踢出',
  'L2-1': '终端频繁离线',
  'L2-6': '设备静默失联',
  'L3-5': '设备收不到网关下发',
  'L3-1': '命令收不到确认',
  'L3-2': '命令送达但未执行',
  'L3-3': '状态上报滞后',
  'L3-11': '命令反复重发',
  'L3-9': '链路质量不对称',
  'L6-3': 'SED 消息收不到',
  'L6-S3': 'SED 消息收不到',  // S2: 事件链卡用检测器场景号 L6-S3 (曾显示原文编号)
  'OFF': '设备离网',
};
// ── 白话化 (2026-08-10, 用户反馈: "L1-3" 等编号对外人难懂) ──
// 编号保留为小角标 (研发/文档追溯), 主表述用 PLAIN_TITLES 白话;
// verdict 也显示白话 ("密钥分发或验证出问题" 而非 "L1-3_HIT"), 规则码进 title 提示。
var VERDICT_PREFIX = { 'L6-3': 'L6-S3' };  // 卡片名 → 检测器 verdict 前缀 (仅不一致的; ⚠️ L6 场景号)
function hitPrefixOf(scenario) { return VERDICT_PREFIX[scenario] || scenario; }
function verdictText(scenario, verdict) {
  if (verdict === 'HEALTHY') return '正常';
  if (verdict === 'INCONCLUSIVE') return '无法判定';
  if (verdict && verdict.indexOf(hitPrefixOf(scenario) + '_HIT') === 0) {
    return PLAIN_TITLES[scenario] || verdict;
  }
  // S2 兜底 (2026-08-28): 非标准 verdict 变体 (L1-2_POSSIBLE_NO_RESPONSE) →
  // 白话前缀 "疑似" — 曾直接显示原始英文串 (白话化原则违反, 用户可读性 bug)
  if (verdict && verdict.indexOf('_POSSIBLE_') !== -1) {
    return '疑似' + (PLAIN_TITLES[scenario] || scenario);
  }
  return verdict || '—';
}

// 覆盖范围提示 (2026-08-10 U8-3): 防"未发现明显问题"误信 —
// 检测体系 8 大类 55 场景; ⚠️ S2 (2026-08-28): 写死 "8/55" 已过时 (检测器增至 13 场景),
// 改为按实际完成检测数动态统计 (渐进渲染时数字如实增长)
// U12 (2026-09-07): 场景总数以 /api/cases/scenarios 为准 (54 — taxonomy 逐条计数,
// 文档标题 "~55" 为约数); 学习进度 "已学 X/N" 同端点
var SCENARIO_TOTAL = 55;  // 兜底值 (端点失败时); ADR-0001: 框架只允许增量扩展

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
  } else {
    if (unknown.length) {
      h += '<p style="font-size:12px;color:#b45309;margin:4px 0 0">⚠️ 部分检测因数据不足无法判定 ('
        + unknown.map(function (u) { return PLAIN_TITLES[u.scenario] || u.scenario; }).join('、')
        + ')，未排除问题的存在。</p>';
    }
    // 无 HIT 时显示覆盖提示 (有问题时页面已醒目, 提示冗余)
    var covered = Object.keys(checks).length;
    h += '<p class="text-dim" style="font-size:11px;color:#64748b;margin:6px 0 0">'
      + '⚠️ 覆盖范围: 本页已检测 ' + covered + '/' + SCENARIO_TOTAL + ' 场景, 其余 '
      + (SCENARIO_TOTAL - covered) + ' 个未检测 — "未发现明显问题"≠"网络没问题"</p>'
    // U12: 相似历史案例区 (新包诊断时; 案例库非空且当前检测有命中场景时提示入口)
    if (window.__similarHint) h += window.__similarHint;
  }
  h += '</div>';
  return h;
}

reg('diag', function () {
  document.getElementById('mc').style.padding = '16px';
  // ⚠️ 2026-08-05 修复: 摘要区被 innerHTML 重建覆盖 (先填旧 DOM 再整体重渲)
  // 改用注释占位 + 统一渲染; 2026-08-06 摘要独立渲染:
  // 各检测完成即写入 checks, renderH() 动态生成 — 不再依赖最内层回调 (L6 失败曾致摘要丢失)
  // 2026-08-10 修复 (用户反馈: L2/L3 被移动到最下方): 模块完成存 sections slot,
  // renderH 按注册表顺序拼接 — 渐进渲染保留, 但顺序固定, 不再受响应完成顺序影响
  // S2 (2026-08-28): 网络(PAN)选择器 + 重新诊断按钮 — 多 PAN 素材串网修复的交互端;
  // 加载逻辑抽为 loadDiag() 供切换 PAN/重跑复用
  // U12 (2026-09-07): 诊断页 = 学习容器 — 双视图: 「检测结果」(现有全部卡) +
  // 「场景学习」(54 场景 tab, 案例列表/学习进度/差距报告/案例导入导出);
  // 无案例库时「检测结果」行为与现状一致 (回归要求)
  var sections = {};       // 模块 key → section html (完成即存)
  var offlineHtml = '';    // 离线区 (独立请求)
  var checks = {};
  var diagPan = '';        // 当前 PAN 选择 ('' = 全部)
  var panOptions = '<option value="">加载中...</option>';  // PAN 选项 (renderH 重建 select 复用)

  // ── U12: 视图切换 (检测结果 / 场景学习) ──
  var diagView = S.diagView || 'detect';   // 'detect' | 'learn'
  S.diagView = diagView;
  var learnHtml = '';                      // 场景学习区 (惰性加载后缓存)

  function viewTabs() {
    return '<div class="sc-view-tabs">'
      + '<button class="sc-view-tab' + (diagView === 'detect' ? ' on' : '') + '" data-v="detect">🩺 检测结果</button>'
      + '<button class="sc-view-tab' + (diagView === 'learn' ? ' on' : '') + '" data-v="learn">📚 场景学习</button>'
      + '</div>';
  }

  function renderH() {
    var summaryHtml = Object.keys(checks).length ? summaryCard(Object.keys(checks).map(function (k) { return checks[k]; })) : '';
    // 跨卡片事件链 (2026-08-10 U8-2): 同设备 ≥2 项检测命中 → 提示可能同一问题链
    var chainDevs = Object.keys(hitDevices).filter(function (dev) { return hitDevices[dev].length >= 2; });
    if (chainDevs.length) {
      summaryHtml += '<div class="card" style="margin-bottom:12px;border-left:4px solid #7c3aed">'
        + '<h3 style="font-size:13px;margin-bottom:6px">🔗 事件链提示: 同设备多检测命中, 可能是同一问题链</h3>'
        + '<ul style="margin:0;padding-left:18px;font-size:12px;line-height:1.8">';
      chainDevs.forEach(function (dev) {
        var hits = hitDevices[dev];
        summaryHtml += '<li><b>0x' + parseInt(dev).toString(16).toUpperCase().padStart(4, '0') + '</b>: '
          + hits.map(function (hit) {
              return '<span class="v-bad" title="' + hit.scenario + (hit.rule ? ' (' + hit.rule + ')' : '') + '">'
                + (PLAIN_TITLES[hit.scenario] || hit.scenario) + '</span>';
            }).join(' × ')
          + ' <span class="text-dim">' + (hits[0].summary || '') + '</span></li>';
      });
      summaryHtml += '</ul></div>';
    }
    // 按注册表顺序拼接 section (未完成模块留空, 完成即渐进出现)
    var bodyHtml = MODULES.map(function (m) { return sections[m.key] || ''; }).join('');
    var headerHtml = '<div class="card"><h3>🩺 网络诊断</h3>'
      + '<p class="hint mt-1">基于协议数据 (Leave/Rejoin/Announce/Network Status) 的离线诊断</p>'
      + viewTabs()
      + '<div class="mt-1" id="detect-ctrl">网络(PAN): <select id="diag-pan" class="mono" style="font-size:12px" '
      + 'onchange="window.__diagPanChange(this.value)">'
      + panOptions + '</select> '
      + '<button id="diag-rerun" class="btn-s" onclick="window.__diagRerun()">⟳ 重新诊断</button>'
      + '<span class="text-dim" style="font-size:11px;margin-left:8px">默认当前网络 (主 PAN), 可切换其他网络</span>'
      + '</div></div>';
    // ⚠️ S2: renderH 重建 innerHTML 会重置 select — 保存/恢复当前选择
    var prevPan = document.getElementById('diag-pan') ? document.getElementById('diag-pan').value : diagPan;
    var detectBody = summaryHtml + bodyHtml + offlineHtml;
    document.getElementById('mc').innerHTML = headerHtml
      + (diagView === 'detect'
        ? '<div id="diag-detect">' + detectBody + '</div>'
        : '<div id="diag-detect" style="display:none">' + detectBody + '</div>'
          + '<div id="diag-learn">' + learnHtml + '</div>');
    var sel = document.getElementById('diag-pan');
    if (sel && sel.options.length) { sel.value = prevPan || diagPan; }
    // U12: 视图 tab 点击
    var tabs = document.querySelectorAll('.sc-view-tab');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function () { switchView(this.dataset.v); });
    }
  }

  function switchView(v) {
    if (v === diagView) return;
    diagView = v; S.diagView = v;
    renderH();
    if (v === 'learn' && !learnHtml) loadLearn();  // 惰性首载
  }

  // ── 检测器注册表 (2026-08-10 U8-1: 四层嵌套 → 数据驱动) ──
  // 每模块 = {api, render(d, checks) -> section html}; render 内部更新 checks 并返回该区 html。
  // 单模块失败不阻塞整页 (catch 保留原嵌套链行为); 全部完成统一 renderH + 离线诊断。
  var MODULES = [
    {
      key: 'l1',
      api: '/api/diag/l1',
      render: function (d, checks) {
        if (d && d.error) {
          return '<div class="card card-danger">'
            + '<h3 class="text-danger">L1 入网检测</h3>'
            + '<p class="hint">' + d.error + ' (L1 检测需要 .cubx 或含 MAC 帧的 pcap)</p></div>';
        }
        var l1 = d ? (d.l1_1 || {}) : {};
        var l2 = d ? (d.l1_2 || {}) : {};
        var l3 = d ? (d.l1_3 || {}) : {};
        var l4 = d ? (d.l1_4 || {}) : {};

        checks['L1-1'] = { scenario: 'L1-1', verdict: l1.verdict, conclusion: l1.conclusion };
        checks['L1-2'] = { scenario: 'L1-2', verdict: l2.verdict, conclusion: l2.conclusion };
        checks['L1-3'] = { scenario: 'L1-3', verdict: l3.verdict, conclusion: l3.conclusion };
        checks['L1-4'] = { scenario: 'L1-4', verdict: l4.verdict, conclusion: l4.conclusion };
        // 事件链登记: L1-3/L1-4 命中设备 (2026-08-10 U8-2)
        (l3.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L1-3_HIT') === 0) collectHit(h.device, 'L1-3', h.sub_rule, h.summary);
        });
        (l4.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L1-4_HIT') === 0) collectHit(h.device, 'L1-4', h.sub_rule, h.summary);
        });

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
                  d.summary, 'L1-3');
              }).join('')
            + '</div>' : '');

        // ── L1-4 卡片 ──
        var b4 = 'Remove Device(0x07): <b>' + (l4.remove_event_count || 0) + '</b> 帧 | 入网设备: <b>' + (l4.joined_device_count || 0) + '</b> 台<br>'
          + '<span class="text-muted">' + (l4.summary || '') + '</span>'
          + ((l4.remove_events || []).length ? '<div class="divider">'
            + (l4.remove_events || []).map(function (r) {
                var dd = r.nwk_dst != null ? '0x' + r.nwk_dst.toString(16).toUpperCase().padStart(4, '0') : '0x?';
                var ss = r.nwk_src != null ? '0x' + r.nwk_src.toString(16).toUpperCase().padStart(4, '0') : '0x?';
                // S2: 时间 + 帧号可跳报文页 (人工复核定位)
                return '<div class="dev mono" style="font-size:11px">' + fmtTs(r.ts) + ' '
                  + evJumpHtml(r) + ' ' + dd + ' ← ' + ss
                  + (r.target_eui64 ? ' → ' + r.target_eui64 : '') + '</div>';
              }).join('')
            + '</div>' : '')
          + ((l4.devices || []).length ? '<div class="divider">'
            + (l4.devices || []).map(function (d) {
                return devLine(d.device, d.verdict, d.sub_rule,
                  'Rm' + (d.remove_device || 0) + '/Ann' + (d.announce || 0) + '/Lv' + (d.leave || 0),
                  d.summary, 'L1-4');
              }).join('')
            + '</div>' : '');

        return '<div class="card l1-sec">'
          + '<h3>🔍 L1 入网检测</h3>'  // S2: 去内部流程术语 (白话化原则)
          + '<div class="l1-cards">'
          + l1Card('L1-1', '发现失败', l1.verdict, l1.confidence, b1, l1.conclusion, l1.evidence, l1.evidence_total)
          + l1Card('L1-2', 'Association', l2.verdict, l2.confidence, b2, l2.conclusion, l2.evidence, l2.evidence_total)
          + l1Card('L1-3', '密钥分发', l3.verdict, l3.confidence, b3, l3.conclusion, l3.evidence, l3.evidence_total)
          + l1Card('L1-4', 'TC 拒绝/踢人', l4.verdict, l4.confidence, b4, l4.conclusion, l4.evidence, l4.evidence_total)
          + '</div></div>';
      },
    },
    {
      key: 'l2',
      api: '/api/diag/l2',
      render: function (d, checks) {
        var l21 = d && !d.error ? (d.l2_1 || {}) : {};
        var l26 = d && !d.error ? (d.l2_6 || {}) : {};
        checks['L2-1'] = { scenario: 'L2-1', verdict: l21.verdict, conclusion: l21.conclusion };
        checks['L2-6'] = { scenario: 'L2-6', verdict: l26.verdict, conclusion: l26.conclusion };
        (l21.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L2-1_HIT') === 0) collectHit(h.device, 'L2-1', h.sub_rule, h.summary);
        });
        (l26.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L2-6_HIT') === 0) collectHit(h.device, 'L2-6', h.sub_rule, h.summary);
        });
        var b2x = 'poll 设备: <b>' + (l21.poll_device_count || 0) + '</b> 台 | poll 帧: <b>' + (l21.poll_total || 0) + '</b> | rejoin=1 Leave: <b>' + (l21.leave_rejoin_total || 0) + '</b><br>'
          + '<span class="text-muted">' + (l21.summary || '') + '</span>'
          + ((l21.devices || []).length ? '<div class="divider">'
            + (l21.devices || []).map(function (d) {
                return devLine(d.device, d.verdict, d.sub_rule,
                  'poll' + (d.poll_count || 0), d.summary, 'L2-1');
              }).join('')
            + '</div>' : '');
        // ── L2-6 卡片 (2026-08-11: 设备静默失联 — poll 停止 / LS 邻居消失) ──
        var b26 = '<span class="text-muted">' + (l26.summary || '') + '</span>'
          + ((l26.devices || []).length ? '<div class="divider">'
            + (l26.devices || []).map(function (d) {
                var stats = d.sub_rule === 'R1'
                  ? ('poll' + (d.poll_count || 0) + '/沉默' + (d.silent_s || 0) + 's')
                  : ('LS消失×' + (d.ls_gone || 0));
                return devLine(d.device, d.verdict, d.sub_rule,
                  stats + (d.left_leave ? ' Lv' : '') + (d.edge_uncertain ? ' ⚠️边缘' : ''),
                  d.summary, 'L2-6');
              }).join('')
            + '</div>' : '');
        return '<div class="card l1-sec">'
          + '<h3>📡 L2 在线维持检测</h3>'  // S2: 去内部流程术语 (白话化原则)
          + '<div class="l1-cards">'
          + l1Card('L2-1', '终端频繁离线', l21.verdict, l21.confidence, b2x, l21.conclusion, l21.evidence, l21.evidence_total)
          + l1Card('L2-6', '设备静默失联', l26.verdict, l26.confidence, b26, l26.conclusion, l26.evidence, l26.evidence_total)
          + '</div></div>';
      },
    },
    {
      key: 'l3',
      api: '/api/diag/l3',
      render: function (d, checks) {
        var l35 = d && !d.error ? (d.l3_5 || {}) : {};
        var l31 = d && !d.error ? (d.l3_1 || {}) : {};
        var l32 = d && !d.error ? (d.l3_2 || {}) : {};
        var l33 = d && !d.error ? (d.l3_3 || {}) : {};
        var l311 = d && !d.error ? (d.l3_11 || {}) : {};
        var l39 = d && !d.error ? (d.l3_9 || {}) : {};
        checks['L3-5'] = { scenario: 'L3-5', verdict: l35.verdict, conclusion: l35.conclusion };
        checks['L3-1'] = { scenario: 'L3-1', verdict: l31.verdict, conclusion: l31.conclusion };
        checks['L3-2'] = { scenario: 'L3-2', verdict: l32.verdict, conclusion: l32.conclusion };
        checks['L3-3'] = { scenario: 'L3-3', verdict: l33.verdict, conclusion: l33.conclusion };
        checks['L3-11'] = { scenario: 'L3-11', verdict: l311.verdict, conclusion: l311.conclusion };
        checks['L3-9'] = { scenario: 'L3-9', verdict: l39.verdict, conclusion: l39.conclusion };
        (l35.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L3-5_HIT') === 0) collectHit(h.device, 'L3-5', h.sub_rule, h.summary);
        });
        (l31.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L3-1_HIT') === 0) collectHit(h.device, 'L3-1', h.sub_rule, h.summary);
        });
        (l32.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L3-2_HIT') === 0) collectHit(h.device, 'L3-2', h.sub_rule, h.summary);
        });
        (l33.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L3-3_HIT') === 0) collectHit(h.device, 'L3-3', h.sub_rule, h.summary);
        });
        (l311.devices || []).forEach(function (h) {
          if ((h.verdict || '').indexOf('L3-11_HIT') === 0) collectHit(h.device, 'L3-11', h.sub_rule, h.summary);
        });
        // L3-9 事件链登记: 链路两端设备 (2026-08-10)
        (l39.asymmetric_links || []).forEach(function (ln) {
          collectHit(ln.a, 'L3-9', 'R1', '链路质量不对称');
          collectHit(ln.b, 'L3-9', 'R1', '链路质量不对称');
        });
        (l39.oneway_links || []).forEach(function (ln) {
          collectHit(ln.a, 'L3-9', 'R2', '持续 one-way');
          collectHit(ln.b, 'L3-9', 'R2', '持续 one-way');
        });
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
        // ── L3-1 卡片 (2026-08-06: 发送命令无 APS Ack, APS 配对能力支撑) ──
        var b31 = '无 ack 事务: <b class="' + vClass(l31.verdict, 'L3-1') + '">' + (l31.no_ack_total || 0) + '</b>'
          + '<br><span class="text-muted">' + (l31.summary || '') + '</span>'
          + ((l31.devices || []).length ? '<div class="divider">'
            + (l31.devices || []).map(function (d) {
                var cross = '';
                if (d.cross && (d.cross.route_error || d.cross.indirect_expiry || d.cross.leave)) {
                  cross = '<span class="text-dim"> ' + (d.cross.route_error ? 'L3-5×' + d.cross.route_error : '')
                    + (d.cross.indirect_expiry ? ' L6-S3×' + d.cross.indirect_expiry : '')
                    + (d.cross.leave ? ' Lv×' + d.cross.leave : '') + '</span>';
                }
                return devLine(d.device, d.verdict, d.sub_rule,
                  (d.direction === 'downlink' ? '↓下行' : '↑上行') + '×' + (d.no_ack_count || 0)
                  + '/重发' + (d.retry_max || 0) + cross,
                  d.summary, 'L3-1');
              }).join('')
            + '</div>' : '');
        // ── L3-2 卡片 (2026-08-12: 命令送达但设备未执行, ZCL 错误 status) ──
        var b32 = '错误响应: <b>' + (l32.devices || []).reduce(function (n, d) { return n + (d.error_count || 0); }, 0) + '</b>'
          + '<br><span class="text-muted">' + (l32.summary || '') + '</span>'
          + ((l32.devices || []).length ? '<div class="divider">'
            + (l32.devices || []).map(function (d) {
                var dirTxt = d.direction === 'coordinator_reject' ? '协调器拒绝'
                  : (d.direction === 'downlink' ? '↓下行' : '↑上行');
                return devLine(d.device, d.verdict, d.sub_rule,
                  dirTxt + '×' + (d.error_count || 0),
                  d.summary, 'L3-2');
              }).join('')
            + '</div>' : '');
        // ── L3-11 卡片 (2026-08-12: 应用层重传频繁 — 新 counter 轮次 ≥3) ──
        var b311 = '重传设备: <b>' + (l311.devices || []).length + '</b> 台'
          + '<br><span class="text-muted">' + (l311.summary || '') + '</span>'
          + ((l311.devices || []).length ? '<div class="divider">'
            + (l311.devices || []).map(function (d) {
                return devLine(d.device, d.verdict, d.sub_rule,
                  (d.cmd_name || ('0x' + (d.cmd_id || 0).toString(16))) + '×' + (d.rounds || 0) + '轮/' + (d.interval_s || 0) + 's',
                  d.summary, 'L3-11');
              }).join('')
            + '</div>' : '');
        // ── L3-3 卡片 (2026-08-12: 状态上报滞后 — Write 成功后设备无上报) ──
        var b33 = '滞后设备: <b>' + (l33.devices || []).length + '</b> 台'
          + '<br><span class="text-muted">' + (l33.summary || '') + '</span>'
          + ((l33.devices || []).length ? '<div class="divider">'
            + (l33.devices || []).map(function (d) {
                return devLine(d.device, d.verdict, d.sub_rule,
                  '滞后×' + (d.lag_count || 0) + '/最大' + (d.max_gap_s || 0) + 's',
                  d.summary, 'L3-3');
              }).join('')
            + '</div>' : '');
        // ── L3-9 卡片 (2026-08-10: 非对称链路, LS 双向成本) ──
        var b39 = '不对称链路: <b>' + (l39.asymmetric_links || []).length + '</b> | one-way: <b>' + (l39.oneway_links || []).length + '</b>'
          + '<br><span class="text-muted">' + (l39.summary || '') + '</span>'
          + (((l39.asymmetric_links || []).length || (l39.oneway_links || []).length) ? '<div class="divider">'
            + (l39.asymmetric_links || []).map(function (ln) {
                return '<div class="dev">0x' + ln.a.toString(16).toUpperCase().padStart(4, '0')
                  + ' ↔ 0x' + ln.b.toString(16).toUpperCase().padStart(4, '0')
                  + ': <span class="v-warn">不对称</span> <span class="text-dim">in '
                  + ln.a_in + ' vs ' + ln.b_in + ' (差' + ln.diff + ')</span></div>';
              }).join('')
            + (l39.oneway_links || []).map(function (ln) {
                return '<div class="dev">0x' + ln.a.toString(16).toUpperCase().padStart(4, '0')
                  + ' → 0x' + ln.b.toString(16).toUpperCase().padStart(4, '0')
                  + ': <span class="v-warn">one-way</span> <span class="text-dim">in=' + ln.in_cost
                  + ' out=0 (×' + ln.reports + ' 报告)</span></div>';
              }).join('')
            + '</div>' : '');
        return '<div class="card l1-sec">'
          + '<h3>🔧 L3 运营期检测</h3>'  // S2: 去内部流程术语 (白话化原则)
          + '<div class="l1-cards">'
          + l1Card('L3-1', '发送命令无 APS Ack', l31.verdict, l31.confidence, b31, l31.conclusion, l31.evidence, l31.evidence_total)
          + l1Card('L3-2', '命令送达但未执行', l32.verdict, l32.confidence, b32, l32.conclusion, l32.evidence, l32.evidence_total)
          + l1Card('L3-3', '状态上报滞后', l33.verdict, l33.confidence, b33, l33.conclusion, l33.evidence, l33.evidence_total)
          + l1Card('L3-5', '源路由/MTORR 失效', l35.verdict, l35.confidence, b5, l35.conclusion, l35.evidence, l35.evidence_total)
          + l1Card('L3-9', '链路质量不对称', l39.verdict, l39.confidence, b39, l39.conclusion, l39.evidence, l39.evidence_total)
          + l1Card('L3-11', '命令反复重发', l311.verdict, l311.confidence, b311, l311.conclusion, l311.evidence, l311.evidence_total)
          + '</div></div>';
      },
    },
    {
      key: 'l6',
      api: '/api/diag/l6',
      render: function (d, checks) {
        var l63 = d && !d.error ? (d.l6_3 || {}) : {};
        checks['L6-3'] = { scenario: 'L6-3', verdict: l63.verdict, conclusion: l63.conclusion };
        (l63.devices || []).forEach(function (h) {
          // ⚠️ 检测器 verdict 为 L6-S3_HIT (场景编号 L6-S3, 非卡片名 L6-3)
          if ((h.verdict || '').indexOf('L6-S3_HIT') === 0) collectHit(h.device, 'L6-S3', h.sub_rule, h.summary);
        });
        var b6x = '0x06 间接过期: <b>' + (l63.expiry_count || 0) + '</b> 帧 | 0x05 队列满: <b>' + (l63.no_indirect_capacity_count || 0) + '</b><br>'
          + '<span class="text-muted">' + (l63.summary || '') + '</span>'
          + ((l63.devices || []).length ? '<div class="divider">'
            + (l63.devices || []).map(function (d) {
                return devLine(d.device, d.verdict, d.sub_rule,
                  '0x06×' + (d.expiry_count || 0), d.summary, 'L6-3');
              }).join('')
            + '</div>' : '');
        return '<div class="card l1-sec">'
          + '<h3>🌙 L6 SED 专项检测</h3>'  // S2: 去内部流程术语 (白话化原则)
          + '<div class="l1-cards">'
          + l1Card('L6-3', '间接事务过期', l63.verdict, l63.confidence, b6x, l63.conclusion, l63.evidence, l63.evidence_total)
          + '</div></div>';
      },
    },
  ];

  // 主流程 (2026-08-10 U8-1 自审修正): 每模块完成即渲染 (渐进, 恢复原嵌套行为) —
  // ⚠️ 初版用 Promise.all 统一渲染: 单模块请求挂起 (无超时) 会整页空白 (实测复现);
  // 改为独立超时 (15s 兜底) + 完成即 renderH, 挂起模块最终超时不阻塞其余模块。
  function withTimeout(promise, ms) {
    return Promise.race([promise, new Promise(function (_, reject) {
      setTimeout(function () { reject(new Error('请求超时')); }, ms);
    })]);
  }
  // S2: 加载逻辑抽为 loadDiag(pan) — 切换 PAN / 重新诊断复用;
  // 顺序修复 (08-10 用户反馈: L2/L3 被移动到最下方): 完成即存 sections[key],
  // renderH 按注册表顺序拼接 — 渐进渲染保留, 顺序固定, 不受响应完成顺序影响
  function loadDiag() {
    hitDevices = {};          // 重置事件链登记 (页面可重复进入 / 切 PAN)
    sections = {}; checks = {}; offlineHtml = '';
    var sel = document.getElementById('diag-pan');
    diagPan = (sel && sel.options.length) ? sel.value : diagPan;
    var q = diagPan ? ('?pan=' + diagPan) : '';
    MODULES.forEach(function (m) {
      withTimeout(A.get(m.api + q), 15000).then(function (d) {
        var html = m.render(d, checks);
        if (html) sections[m.key] = html;   // 存 slot 而非追加
      }).catch(function () { /* 单模块失败/超时不阻塞 (原嵌套 catch 链行为) */ })
        .then(function () { renderH(); });  // 每模块 settle 后即渲染 (渐进)
    });
    renderOffline(diagPan);
  }
  window.__diagPanChange = function (v) {
    diagPan = v;
    var sel = document.getElementById('diag-pan');
    if (sel) sel.value = v;  // ⚠️ 同步 select (loadDiag 会从 select 读值, 曾覆盖回旧 PAN)
    loadDiag();
  };
  window.__diagRerun = function () { loadDiag(); };
  // PAN 列表初始化 — 2026-08-29 用户反馈改版: 用 /api/diag/pans (全量包统计,
  // 含 beacon-only 网络; events.pans 只含路由事件网络, 曾导致下拉只有 2 个选项)
  // ⚠️ 修复 (2026-08-28 CDP 实测): 首次进入 rt() 已清空 mc, select 尚不存在 —
  // 曾直接 return 导致 loadDiag 永不执行, 页面恒空白; 先 renderH 渲染 header 再填选项
  A.get('/api/diag/pans').then(function (d) {
    var sel = document.getElementById('diag-pan');
    if (!sel) { renderH(); sel = document.getElementById('diag-pan'); }
    if (!sel) { loadDiag(); return; }
    var pans = (d.pans || []).map(function (p) { return p.pan; });
    var main = d.main_pan;
    var html = '<option value="">全部 PAN</option>';
    if (main != null && pans.indexOf(main) !== -1) {
      html += '<option value="' + main.toString(16).toUpperCase() + '">主网络 0x'
        + main.toString(16).toUpperCase().padStart(4, '0') + '</option>';
    }
    (d.pans || []).forEach(function (p) {
      if (main != null && p.pan === main) return;
      html += '<option value="' + p.pan.toString(16).toUpperCase() + '">0x'
        + p.pan.toString(16).toUpperCase().padStart(4, '0')
        + ' <span class="text-dim">(' + p.count + ' 帧)</span></option>';
    });
    panOptions = html;  // ⚠️ 存模块变量: renderH 重建 select 时复用 (曾重置为加载中)
    sel.innerHTML = html;
    // 默认主 PAN (与拓扑页一致: 每 PAN 独立网络, 数据不混入; 全部 PAN 为显式选项)
    sel.value = diagPan || (main != null ? main.toString(16).toUpperCase() : '');
    diagPan = sel.value;
    loadDiag();
  }).catch(function () {
    var sel = document.getElementById('diag-pan');
    if (sel) sel.innerHTML = '<option value="">全部 PAN</option>';
    loadDiag();
  });

  // U12: 进入页面时若上次停在学习视图, 惰性加载案例库 (无案例库不影响检测视图)
  if (diagView === 'learn') loadLearn();
  if (!S.lastImportPath) {
    // 素材原路径 (案例素材副本用; 本地路径导入时有值 — /api/import/last 不带路径,
    // 由 import.js 导入时写入 S.lastImportPath)
    S.lastImportPath = '';
  }

  function renderOffline(pan) {
    A.get('/api/diag/offline' + (pan ? ('?pan=' + pan) : '')).then(function (d) {
      var devs = d.devices || [];
      if (!devs.length) {
        offlineHtml += '<div class="card empty">'
          + '<p>✅ ' + (d.conclusion || '未发现设备离网事件') + '</p>'
          + '<p class="sub">当前抓包中没有 NWK Leave 或 Device Announce 帧</p></div>';
      } else {
        var s = d.summary || {};
        offlineHtml += '<div class="card card-info">'
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
          // 事件链登记: 离网设备 (OFF) — 与 L1-4 被踢 / L1-3 密钥循环等跨卡关联 (2026-08-10 U8-2)
          collectHit(dev.aid, 'OFF', null, (dev.diagnosis || {}).summary);
          var typeLabel = dev.device_type === 'coordinator' ? '协调器' : dev.device_type === 'router' ? '路由器' : '终端设备';
          var eui = dev.eui64 || '未知';
          if (eui.length === 16) { eui = eui.slice(0, 2) + ':' + eui.slice(2, 4) + ':' + eui.slice(4, 6) + ':' + eui.slice(6, 8) + ':' + eui.slice(8, 10) + ':' + eui.slice(10, 12) + ':' + eui.slice(12, 14) + ':' + eui.slice(14, 16); }

          offlineHtml += '<div class="card diag-card">'
            + '<div class="diag-header">'
            + '<span class="dev-label">' + dev.label + '</span>'
            + '<span class="dev-eui">' + eui + '</span>'
            + '<span class="badge">' + typeLabel + '</span>'
            + '</div>';

          var pe = dev.pre_events || {};
          offlineHtml += '<div class="diag-timeline">';
          offlineHtml += '<div class="diag-ev"><span class="diag-ic diag-ic-com">▸</span> 正常通信 (Link Status, Route Record, Data)</div>';
          if (pe.network_status_count > 0) { offlineHtml += '<div class="diag-ev"><span class="diag-ic diag-ic-warn">⚠</span> Network Status ×' + pe.network_status_count + ' (路由层异常前置信号)</div>'; }
          if (pe.ieee_addr_req_count > 0) { offlineHtml += '<div class="diag-ev"><span class="diag-ic diag-ic-info">🔍</span> IEEE Addr Req ×' + pe.ieee_addr_req_count + ' (协调器查询设备身份)</div>'; }
          var bursts = dev.leave_bursts || [];
          for (var b = 0; b < bursts.length; b++) {
            var burst = bursts[b];
            var bt = burst.burst_index === 1 ? '第一波' : burst.burst_index === 2 ? '第二波' : ('第' + burst.burst_index + '波');
            var bc = burst.count > 1 ? (' ×' + burst.count) : '';
            var typeName = burst.type === 'kicked' ? '[被踢]' : burst.type === 'voluntary_permanent' ? '[主动永久]' : burst.type === 'voluntary_rejoin' ? '[主动暂离]' : '[被踢·可重入]';
            // S2: 补波次时间 (fmtTs 时钟时间, 与时间线一致)
            offlineHtml += '<div class="diag-ev"><span class="diag-ic diag-ic-leave">✕</span> ' + bt + ' Leave' + bc + ' ' + typeName
              + ' <span class="text-dim" style="font-size:10px">' + fmtTs(burst.first_ts) + '</span></div>';
          }
          var rej = dev.rejoin_attempts || [];
          for (var r = 0; r < rej.length; r++) {
            var rj = rej[r];
            offlineHtml += '<div class="diag-ev"><span class="diag-ic diag-ic-join">📢</span> Device Announce ×' + rj.announce_count + ' (第' + rj.after_burst + '波Leave后 ' + rj.delay_seconds + 's) ← 重入网尝试'
              + ' <span class="text-dim" style="font-size:10px">' + fmtTs(rj.first_ts) + '</span></div>';
          }
          offlineHtml += '</div>';
          var diag = dev.diagnosis || {};
          offlineHtml += '<div class="diag-conclusion">'
            + '<b>诊断: </b>' + diag.summary
            + '</div>';
          offlineHtml += '</div>';
        }
      }
      renderH();
    }).catch(function (e) {
      renderH(); document.getElementById('mc').innerHTML += '<div class="card text-danger">诊断数据加载失败: ' + e.message + '</div>';
    });
  }

  // ══════════ U12: 场景学习视图 (学习容器) ══════════
  // 数据源: /api/cases/scenarios (学习进度 + 54 场景) + /api/cases (案例列表)
  // + /api/cases/gaps (差距报告); tab 惰性渲染 (仅激活场景渲染案例, 性能)
  var learnData = null;      // scenarios 端点缓存
  var learnCases = [];       // 全部案例摘要 (tab 过滤在渲染层)
  var learnGaps = null;      // 差距报告
  var activeScenario = null; // 当前激活场景 tab (null = 总览)

  function escHtml(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function fmtDate(ts) {
    if (!ts) return '—';
    var d = new Date(ts * 1000);
    return (d.getMonth() + 1) + '-' + d.getDate() + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  function fmtPan(pan) { return pan != null ? '0x' + pan.toString(16).toUpperCase().padStart(4, '0') : '—'; }
  function fmtAddr(a) { return a != null ? '0x' + a.toString(16).toUpperCase().padStart(4, '0') : '—'; }
  var SEV_TXT = { high: '严重', medium: '中等', low: '轻微' };

  function loadLearn(force) {
    if (learnData && !force) { renderLearn(); return; }
    A.get('/api/cases/scenarios').then(function (s) {
      learnData = s;
      SCENARIO_TOTAL = s.total || SCENARIO_TOTAL;
      return A.get('/api/cases');
    }).then(function (c) {
      learnCases = c.cases || [];
      learnRootCauses = c.root_cause_suggestions || [];
      return A.get('/api/cases/gaps');
    }).then(function (g) {
      learnGaps = g;
      renderLearn();
    }).catch(function (e) {
      learnHtml = '<div class="card text-danger">案例库加载失败: ' + escHtml(e.message || e) + '</div>';
      renderH();
    });
  }
  var learnRootCauses = [];

  // 场景 tab 分组 (8 大类; 已学/有检测器的排前, 大类内保持编号序)
  var GROUPS = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8'];
  var GROUP_NAMES = { L1: '入网', L2: '在线维持', L3: '运营期', L4: '网络维护', L5: '应用层', L6: 'SED 专项', L7: 'MAC/物理', L8: '硬件固件' };

  function renderLearn() {
    var s = learnData;
    if (!s) { loadLearn(); return; }
    var scen = s.scenarios || {};
    // ── 头部: 学习进度 + 操作按钮 ──
    var h = '<div class="card">'
      + '<h3>📚 场景学习 <span class="text-dim" style="font-size:11px;font-weight:400">(问题包+标注 → 案例入库 → 结论由案例支撑)</span></h3>'
      + '<div class="sc-progress">已学 <b>' + s.learned + '</b>/' + s.total + ' 场景 · 案例库 ' + (s.case_total || 0) + ' 条 '
      + '<button class="btn-s" onclick="window.__caseAnnotate()">➕ 把当前包标为案例</button> '
      + '<button class="btn-s" onclick="window.__caseExport()">⬇ 导出案例库</button> '
      + '<button class="btn-s" onclick="window.__caseImportClick()">⬆ 导入案例库</button> '
      + '<input type="file" id="case-import-file" accept=".zip" style="display:none">'
      + '</div></div>';
    // ── 差距报告摘要 (检测 vs 标注未对齐 → 检测器改进优先级) ──
    if (learnGaps && learnGaps.gap_count > 0) {
      h += '<div class="card" style="border-left:4px solid #f59e0b">'
        + '<h3 style="font-size:13px">📋 待完善清单 (检测与标注不符 ' + learnGaps.gap_count + ' 项)</h3>'
        + '<table class="sc-mini-table"><thead><tr><th>场景</th><th>漏报线索</th><th>误报线索</th></tr></thead><tbody>';
      (learnGaps.by_scenario || []).forEach(function (a) {
        var info = scen[a.scenario] || {};
        h += '<tr><td><span class="sc-tag">' + a.scenario + '</span> ' + escHtml(info.name || '') + '</td>'
          + '<td>' + (a.missed ? '<b class="v-warn">' + a.missed + '</b>' : 0) + '</td>'
          + '<td>' + (a.false_positive ? '<b class="v-warn">' + a.false_positive + '</b>' : 0) + '</td></tr>';
      });
      h += '</tbody></table>'
        + '<p class="text-dim" style="font-size:11px;margin:6px 0 0">漏报 = 人工归属但检测未命中 (检测器规则待补) · 误报 = 检测命中但人工未归属 (规则待收紧) — 走 P5 工单流迭代检测器</p></div>';
    }
    // ── 场景 tab 条 (按大类分组; 徽章 = 案例数) ──
    h += '<div class="card"><div class="sc-tabs">';
    h += '<button class="sc-tab' + (activeScenario == null ? ' on' : '') + '" data-s="">📊 总览</button>';
    GROUPS.forEach(function (g) {
      var ids = Object.keys(scen).filter(function (sid) { return sid.indexOf(g + '-') === 0; });
      if (!ids.length) return;
      h += '<span class="sc-group">' + GROUP_NAMES[g] + '</span>';
      ids.forEach(function (sid) {
        var info = scen[sid];
        var n = info.case_count || 0;
        var cls = 'sc-tab' + (activeScenario === sid ? ' on' : '')
          + (n > 0 ? ' sc-learned' : '') + (info.covered ? ' sc-covered' : '');
        h += '<button class="' + cls + '" data-s="' + sid + '"'
          + ' title="' + escHtml(sid + ' ' + info.name + (info.covered ? ' (有检测器)' : ' (未覆盖)')) + '">'
          + '<span class="sc-tag">' + sid + '</span>' + escHtml(info.name)
          + (n ? ' <span class="sc-badge">' + n + '</span>' : '') + '</button>';
      });
    });
    h += '</div>';
    // ── tab 内容 (总览 or 单场景案例列表) ──
    h += '<div class="sc-tab-body">' + (activeScenario ? scenarioBody(activeScenario, scen) : overviewBody(scen)) + '</div>';
    h += '</div>';
    learnHtml = h;
    renderH();
    bindLearnEvents();
  }

  function overviewBody(scen) {
    // 总览: 学习进度说明 + 已学场景案例速览 (全部案例按时间倒序, 截 20)
    var h = '<p class="text-dim" style="font-size:12px;margin:4px 0 8px">点任意场景查看该场景已学案例; 灰色 tab = 该场景还没有案例 (待学习); 带 ✦ = 有检测器覆盖。</p>';
    if (!learnCases.length) {
      return h + '<div class="empty" style="padding:16px;color:#64748b">案例库为空 — 导入问题包后点「➕ 把当前包标为案例」开始学习。<br>场景案例越多, 诊断结论置信度越高; 未学场景结论显示"待学习"。</div>';
    }
    h += '<p class="text-dim" style="font-size:11px;margin:0 0 4px">最近案例 (前 20 条):</p>';
    return h + caseRows(learnCases.slice(0, 20));
  }

  function scenarioBody(sid, scen) {
    var info = scen[sid] || {};
    var cases = learnCases.filter(function (c) { return (c.scenarios || []).indexOf(sid) !== -1; });
    var h = '<h4 style="margin:2px 0 6px"><span class="sc-tag">' + sid + '</span> ' + escHtml(info.name) + ' '
      + (info.covered ? '<span class="badge" title="检测器已覆盖此场景">✦ 有检测器</span>' : '<span class="badge" style="background:#f1f5f9;color:#64748b" title="此场景暂无检测器, 靠案例标注积累">待开发检测器</span>')
      + ' · 案例数: <b>' + (info.case_count || 0) + '</b></h4>';
    // 结论置信度标注 (grilling 决策: ≥3 = 多案例支撑; 少 = 待更多案例)
    if (cases.length >= 3) {
      h += '<p style="font-size:12px;color:#16a34a;margin:4px 0">✅ 多案例支撑 (' + cases.length + ' 条) — 该场景结论置信度高</p>';
    } else if (cases.length > 0) {
      h += '<p style="font-size:12px;color:#b45309;margin:4px 0">⚠️ 案例尚少 (' + cases.length + ' 条) — 结论弱化, 待更多案例 (≥3 条为多案例支撑)</p>';
    } else {
      h += '<p style="font-size:12px;color:#64748b;margin:4px 0">⬜ 待学习: 该场景还没有案例。'
        + (info.covered ? '检测器已覆盖, 但结论还没有真实问题包核对。' : '需要导入对应问题包 + 标注建立案例。')
        + ' <button class="btn-s" onclick="window.__caseAnnotate(\'' + sid + '\')">➕ 用当前包学此场景</button></p>';
    }
    return h + (cases.length ? caseRows(cases) : '');
  }

  function caseRows(cases) {
    var h = '<table class="sc-mini-table"><thead><tr><th>时间</th><th>现象</th><th>根因</th><th>严重度</th><th>PAN/设备</th><th>归属场景</th><th>素材</th><th></th></tr></thead><tbody>';
    cases.forEach(function (c) {
      h += '<tr>'
        + '<td class="text-dim" style="white-space:nowrap">' + fmtDate(c.ts) + '</td>'
        + '<td style="max-width:260px">' + escHtml(c.phenomenon || '') + '</td>'
        + '<td style="max-width:200px">' + escHtml(c.root_cause || '—') + '</td>'
        + '<td>' + (SEV_TXT[c.severity] || c.severity || '—') + '</td>'
        + '<td class="mono" style="white-space:nowrap">' + fmtPan(c.pan) + (c.device_addr != null ? ' / ' + fmtAddr(c.device_addr) : '') + '</td>'
        + '<td>' + (c.scenarios || []).map(function (s) { return '<span class="sc-tag">' + s + '</span>'; }).join(' ') + '</td>'
        + '<td>' + (c.has_material
          ? '<a class="ev-jump" href="/api/cases/download?path=' + encodeURIComponent(c.material_path || '') + '" title="下载素材副本">📦</a>'
          : '<span class="text-dim">—</span>') + '</td>'
        + '<td><button class="btn-s text-danger" data-del-case="' + escHtml(c.id) + '" title="删除案例">✕</button></td>'
        + '</tr>';
    });
    return h + '</tbody></table>';
  }

  function bindLearnEvents() {
    var el = document.getElementById('diag-learn');
    if (!el) return;
    var tabs = el.querySelectorAll('.sc-tab');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener('click', function () {
        var v = this.dataset.s;
        activeScenario = v ? v : null;
        renderLearn();
      });
    }
    var dels = el.querySelectorAll('[data-del-case]');
    for (var j = 0; j < dels.length; j++) {
      dels[j].addEventListener('click', function () {
        var id = this.dataset.delCase;
        if (!confirm('删除案例 ' + id + '? (素材副本一并删除)')) return;
        fetch('/api/cases/' + id, { method: 'DELETE' }).then(function (r) { return r.json(); }).then(function (d) {
          if (d.ok) { learnData = null; loadLearn(); }  // 强刷
          else alert(d.error || '删除失败');
        });
      });
    }
    var imp = document.getElementById('case-import-file');
    if (imp) imp.addEventListener('change', function () {
      if (!imp.files || !imp.files.length) return;
      var fd = new FormData(); fd.append('file', imp.files[0]); fd.append('merge', '1');
      fetch('/api/cases/import', { method: 'POST', body: fd }).then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.ok) {
            var t = setInterval(function () {
              A.get('/api/import/progress?task_id=' + d.task_id).then(function (p) {
                if (p.status === 'done') {
                  clearInterval(t); alert('导入完成: 新增 ' + (p.result ? p.result.added.length : 0) + ' / 跳过 ' + (p.result ? p.result.skipped.length : 0));
                  learnData = null; loadLearn();
                } else if (p.status === 'error') { clearInterval(t); alert('导入失败: ' + p.error); }
              });
            }, 400);
          } else alert(d.error || '导入失败');
        });
    });
  }

  // ── U12: 案例标注表单 (当前包 + 标注 → 入库) ──
  // ⚠️ 存在性校验查后端 import/status (曾用前端 S.pkts 内存态 — CDP/API 直接
  // 导入时页面 S.pkts=0 误拒; 后端状态才反映真实数据)
  window.__caseAnnotate = function (presetScenario) {
    A.get('/api/import/status').then(function (st) {
      if (!st || !st.total) { alert('请先导入抓包 (当前无数据)'); return; }
      var sel = document.getElementById('diag-pan');
      var curPan = (sel && sel.options.length) ? sel.value : '';
      openAnnotate(presetScenario, curPan);
    }).catch(function () { alert('后端不可达, 无法标注'); });
  };
  function openAnnotate(presetScenario, curPan) {
    // 场景多选列表 (检测器覆盖的排前, 自动命中预勾选由后端算 — 表单先全展示)
    var scenList = learnData ? learnData.scenarios : {};
    var ids = Object.keys(scenList);
    if (!ids.length) { alert('场景表加载中, 稍后再试'); return; }
    var opts = '';
    // 已有案例的 + 有检测器的排前
    ids.sort(function (a, b) {
      var wa = (scenList[a].covered ? 0 : 1) + (scenList[a].case_count ? 0 : 2);
      var wb = (scenList[b].covered ? 0 : 1) + (scenList[b].case_count ? 0 : 2);
      return wa - wb || (a < b ? -1 : 1);
    });
    ids.forEach(function (sid) {
      var info = scenList[sid];
      opts += '<label class="sc-check"><input type="checkbox" name="ann-scen" value="' + sid + '"'
        + (sid === presetScenario ? ' checked' : '') + '> <span class="sc-tag">' + sid + '</span> '
        + escHtml(info.name) + (info.covered ? ' ✦' : '') + '</label>';
    });
    var rcOpts = '<option value="">(可选 — 选建议或手填)</option>';
    (learnRootCauses || []).forEach(function (rc) { rcOpts += '<option>' + escHtml(rc) + '</option>'; });
    rcOpts += '<option value="__custom__">✏️ 手动输入…</option>';

    var h = '<div class="sc-modal-mask" id="ann-modal">'
      + '<div class="sc-modal">'
      + '<h3>➕ 案例标注 <span class="text-dim" style="font-size:11px;font-weight:400">(当前导入包 → 案例库)</span></h3>'
      + '<div class="sc-form">'
      + '<label class="ai-lbl">现象 (必填) *</label>'
      + '<input class="ai-in" id="ann-phenomenon" placeholder="例: 中继 838D 入网后 2s 被踢, 下行不通">'
      + '<label class="ai-lbl">根因 (可选, 带建议列表)</label>'
      + '<select class="ai-in" id="ann-rc-sel">' + rcOpts + '</select>'
      + '<input class="ai-in" id="ann-rc-custom" placeholder="手填根因" style="display:none;margin-top:4px">'
      + '<label class="ai-lbl">严重度</label>'
      + '<select class="ai-in" id="ann-severity"><option value="high">严重</option><option value="medium" selected>中等</option><option value="low">轻微</option></select>'
      + '<label class="ai-lbl">环境说明 (可选)</label>'
      + '<input class="ai-in" id="ann-env" placeholder="例: 现场中继场景, DA13 网关">'
      + '<label class="ai-lbl">归属场景 (自动命中会一并入库, 这里勾选人工确认的归属)</label>'
      + '<div class="sc-check-grid">' + opts + '</div>'
      + '<label class="ai-lbl">PAN / 问题设备 (自动预填, 可改)</label>'
      + '<div style="display:flex;gap:6px">'
      + '<input class="ai-in mono" id="ann-pan" style="width:110px" value="' + (curPan || '') + '" placeholder="580C">'
      + '<input class="ai-in mono" id="ann-dev" style="width:130px" placeholder="838D">'
      + '</div>'
      + '<label class="sc-check" style="margin-top:8px"><input type="checkbox" id="ann-copy" checked> 复制素材副本 (导出传播时自带素材; 大包可取消)</label>'
      + '</div>'
      + '<div style="display:flex;gap:8px;margin-top:12px">'
      + '<button class="btn btn-p" id="ann-go">入库 (自动跑检测 + 场景归属)</button>'
      + '<button class="btn btn-o" id="ann-cancel">取消</button>'
      + '<span id="ann-msg" class="text-dim" style="font-size:11px;align-self:center"></span>'
      + '</div>'
      + '</div></div>';
    var div = document.createElement('div');
    div.innerHTML = h;
    document.body.appendChild(div.firstChild);
    document.getElementById('ann-rc-sel').addEventListener('change', function () {
      document.getElementById('ann-rc-custom').style.display = this.value === '__custom__' ? 'block' : 'none';
    });
    document.getElementById('ann-cancel').addEventListener('click', function () {
      var m = document.getElementById('ann-modal'); if (m) m.remove();
    });
    document.getElementById('ann-go').addEventListener('click', function () {
      var phenomenon = document.getElementById('ann-phenomenon').value.trim();
      if (!phenomenon) { document.getElementById('ann-msg').textContent = '现象必填'; return; }
      var rcSel = document.getElementById('ann-rc-sel').value;
      var rootCause = rcSel === '__custom__' ? document.getElementById('ann-rc-custom').value.trim()
        : (rcSel && rcSel !== '' ? rcSel : '');
      var manuals = [];
      var boxes = document.querySelectorAll('#ann-modal input[name="ann-scen"]:checked');
      for (var i = 0; i < boxes.length; i++) manuals.push(boxes[i].value);
      var body = {
        phenomenon: phenomenon,
        root_cause: rootCause,
        severity: document.getElementById('ann-severity').value,
        environment: document.getElementById('ann-env').value.trim(),
        manual_scenarios: manuals,
        pan: (document.getElementById('ann-pan').value || '').trim(),
        device_addr: (document.getElementById('ann-dev').value || '').trim(),
        copy_material: document.getElementById('ann-copy').checked,
        source_path: S.lastImportPath || '',
      };
      document.getElementById('ann-msg').textContent = '检测 + 入库中…';
      document.getElementById('ann-go').disabled = true;
      A.post('/api/cases/annotate', body).then(function (d) {
        var m = document.getElementById('ann-modal'); if (m) m.remove();
        if (d.ok) {
          var c = d.case;
          alert('案例入库 ✓ ' + c.id + '\n归属场景: ' + (c.scenarios || []).join(', ')
            + '\n差距报告: ' + (d.gap_report ? d.gap_report.gap_count + ' 项未对齐' : '—'));
          learnData = null; loadLearn();  // 强刷学习视图
        } else {
          alert('入库失败: ' + (d.error || '未知错误'));
        }
      }).catch(function (e) { alert('网络错误: ' + e.message); });
    });
  };

  // ── U12: 导出 (后台任务 + 下载) / 导入入口 ──
  window.__caseExport = function () {
    A.post('/api/cases/export', {}).then(function (d) {
      if (!d.ok) { alert('导出失败: ' + (d.error || '已有任务运行中')); return; }
      var t = setInterval(function () {
        A.get('/api/import/progress?task_id=' + d.task_id).then(function (p) {
          if (p.status === 'done') {
            clearInterval(t);
            var r = p.result || {};
            if (r.out_path) {
              // 直接触发下载 (cases/ 目录内白名单)
              location.href = '/api/cases/download?path=' + encodeURIComponent(r.out_path);
            }
          } else if (p.status === 'error') { clearInterval(t); alert('导出失败: ' + p.error); }
        });
      }, 400);
    });
  };
  window.__caseImportClick = function () {
    var imp = document.getElementById('case-import-file');
    if (imp) imp.click();
  };

});
