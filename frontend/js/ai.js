// ai.js — 全局 AI 侧边栏助手 (U17)
// ⚠️ 模块级单例: 页面切换 (#mc 重建) 不销毁本模块 — 对话状态保留 (类 U6 顶栏三态理念)
// ⚠️ localStorage 持久化: 刷新/重启后对话保留, 多会话历史列表
// 阶段一 (2026-08-26): ①知识检索 (芯科 MCP, 无需 LLM key) + 统一对话入口意图分流;
//   分析意图 → 引导文案 (阶段二: 范围解析 → 取数摘要 → LLM 对话, key 自备)
import { A } from './state.js';

const LS_KEY = 'zc_ai_sessions_v1';
const MAX_SESSIONS = 20;
const PROVIDERS = { anthropic: 'Anthropic (Claude)', openai: 'OpenAI', deepseek: 'DeepSeek' };

// ── 状态 (模块级单例; localStorage 镜像) ──
let st = { sessions: [], cur: null, tab: 'chat', open: false, pos: null };

function load() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const d = JSON.parse(raw);
      if (d && Array.isArray(d.sessions)) {
        st.sessions = d.sessions;
        st.cur = d.sessions.some(s => s.id === d.cur) ? d.cur : (d.sessions[0] ? d.sessions[0].id : null);
        st.tab = d.tab || 'chat';
        st.open = !!d.open;
      }
    }
  } catch (e) { /* 损坏数据静默重置 */ }
}
function save() { try { localStorage.setItem(LS_KEY, JSON.stringify(st)); } catch (e) { /* 容量超限忽略 */ } }
function curSession() { return st.sessions.find(s => s.id === st.cur) || null; }

// ── DOM (挂 body, 与页面模块平行) ──
let fab, panel, msgsEl, inputEl, tabBtns, histEl, selEl, cfgEl = null;

function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

function buildDOM() {
  if (panel) return;
  fab = document.createElement('button');
  fab.id = 'zc-ai-fab'; fab.className = 'ai-fab'; fab.title = 'AI 助手';
  fab.textContent = '🤖';
  document.body.appendChild(fab);

  panel = document.createElement('div');
  panel.id = 'zc-ai-panel'; panel.className = 'ai-panel';
  panel.innerHTML = `
    <div class="ai-head">
      <span class="ai-title">🤖 AI 助手</span>
      <select class="ai-sel" title="切换会话"></select>
      <button class="btn btn-o btn-sm" id="zc-ai-new" title="新会话">＋</button>
      <button class="btn btn-sm ai-close" id="zc-ai-fold" title="折叠">─</button>
    </div>
    <div class="ai-tabs">
      <button class="ai-tab on" data-t="chat">对话</button>
      <button class="ai-tab" data-t="hist">历史</button>
      <button class="ai-tab" data-t="cfg">设置</button>
    </div>
    <div class="ai-body" id="zc-ai-chat">
      <div class="ai-msgs" id="zc-ai-msgs"></div>
      <div class="ai-input">
        <textarea id="zc-ai-in" rows="2" placeholder="问知识问题，或描述抓包分析需求（如“分析 10:00-10:30 的 0x838D”）。Enter 发送，Shift+Enter 换行"></textarea>
        <button class="btn btn-p btn-sm" id="zc-ai-send">发送</button>
      </div>
    </div>
    <div class="ai-body" id="zc-ai-hist" style="display:none">
      <div class="ai-msgs" id="zc-ai-hist-list"></div>
    </div>
    <div class="ai-body" id="zc-ai-cfg" style="display:none">
      <div class="ai-cfg">
        <p class="ai-cfg-hint">💡 知识检索无需配置即可使用（自动使用本机已授权的芯科访问凭证）。</p>
        <label class="ai-lbl">LLM 提供商 (阶段二对话分析用)</label>
        <select id="zc-ai-prov" class="ai-in">
          ${Object.entries(PROVIDERS).map(([k, v]) => `<option value="${k}">${v}</option>`).join('')}
        </select>
        <label class="ai-lbl">API Key <span class="ai-dim">（仅存本地，不入 git/分发包）</span></label>
        <input id="zc-ai-key" class="ai-in" type="password" placeholder="粘贴你的 API Key">
        <p id="zc-ai-key-state" class="ai-dim"></p>
        <label class="ai-lbl">API 端点 base_url <span class="ai-dim">（可选，如 DeepSeek Anthropic 兼容端点 https://api.deepseek.com/anthropic）</span></label>
        <input id="zc-ai-base" class="ai-in" placeholder="留空用默认端点">
        <label class="ai-lbl">模型 <span class="ai-dim">（可选，如 deepseek-v4-flash）</span></label>
        <input id="zc-ai-model" class="ai-in" placeholder="留空用默认模型">
        <label class="ai-lbl">API 风格 <span class="ai-dim">（端点兼容风格）</span></label>
        <select id="zc-ai-style" class="ai-in">
          <option value="">自动（按提供商）</option>
          <option value="anthropic">Anthropic 风格</option>
          <option value="openai">OpenAI 风格</option>
        </select>
        <label class="ai-lbl">芯科访问 token <span class="ai-dim">（可选，留空自动使用本机授权凭证）</span></label>
        <input id="zc-ai-tok" class="ai-in" type="password" placeholder="粘贴 MCP Bearer token">
        <button class="btn btn-p btn-sm" id="zc-ai-savecfg">保存配置</button>
        <p id="zc-ai-cfg-msg" class="ai-dim"></p>
      </div>
    </div>
    <div class="ai-resize-handle" title="拖动调整大小">⤡</div>`;
  document.body.appendChild(panel);

  msgsEl = panel.querySelector('#zc-ai-msgs');
  inputEl = panel.querySelector('#zc-ai-in');
  tabBtns = panel.querySelectorAll('.ai-tab');
  histEl = panel.querySelector('#zc-ai-hist-list');
  selEl = panel.querySelector('.ai-sel');
  cfgEl = panel.querySelector('#zc-ai-cfg');

  fab.addEventListener('click', toggle);
  // 面板拖拽移动 (08-26 用户反馈: 窗口可移动; 位置持久化)
  const head = panel.querySelector('.ai-head');
  let dragging = null;
  head.addEventListener('mousedown', e => {
    if (e.target.closest('select,button')) return;
    const r = panel.getBoundingClientRect();
    dragging = { dx: e.clientX - r.left, dy: e.clientY - r.top };
    e.preventDefault();
  });
  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const x = Math.max(0, Math.min(e.clientX - dragging.dx, window.innerWidth - 60));
    const y = Math.max(0, Math.min(e.clientY - dragging.dy, window.innerHeight - 40));
    panel.style.left = x + 'px';
    panel.style.top = y + 'px';
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
  });
  document.addEventListener('mouseup', () => {
    if (dragging) {
      st.pos = { left: panel.style.left, top: panel.style.top };
      save();
    }
    dragging = null;
  });
  if (st.pos) {
    panel.style.left = st.pos.left;
    panel.style.top = st.pos.top;
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
  }
  // 右下角 resize 手柄 (08-26 用户反馈: CSS resize 手柄看不见 → 自定义可见手柄)
  const rsz = panel.querySelector('.ai-resize-handle');
  let resizing = null;
  rsz.addEventListener('mousedown', e => {
    const r = panel.getBoundingClientRect();
    resizing = { w: r.width, h: r.height, x: e.clientX, y: e.clientY };
    e.preventDefault();
    e.stopPropagation();
  });
  document.addEventListener('mousemove', e => {
    if (!resizing) return;
    const w = Math.max(320, resizing.w + e.clientX - resizing.x);
    const h = Math.max(300, resizing.h + e.clientY - resizing.y);
    panel.style.width = w + 'px';
    panel.style.height = h + 'px';
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
  });
  document.addEventListener('mouseup', () => { resizing = null; });
  panel.querySelector('#zc-ai-fold').addEventListener('click', toggle);
  panel.querySelector('#zc-ai-new').addEventListener('click', newSession);
  panel.querySelector('#zc-ai-send').addEventListener('click', send);
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  tabBtns.forEach(b => b.addEventListener('click', () => { st.tab = b.dataset.t; save(); renderTabs(); }));
  selEl.addEventListener('change', () => { st.cur = selEl.value; save(); render(); });
  panel.querySelector('#zc-ai-savecfg').addEventListener('click', saveCfg);

  window.addEventListener('zc:imported', onImported);
  initCfg();
}

function toggle() {
  st.open = !st.open; save();
  panel.classList.toggle('on', st.open);
  fab.classList.toggle('on', st.open);
  if (st.open && st.tab === 'chat') render();
}

function newSession() {
  const s = { id: 's' + Date.now(), title: '新会话', created: Date.now(), messages: [] };
  st.sessions.unshift(s);
  if (st.sessions.length > MAX_SESSIONS) st.sessions.length = MAX_SESSIONS;
  st.cur = s.id; st.tab = 'chat'; save();
  render(); renderTabs();
}

function pushMsg(m) {
  const s = curSession();
  if (!s) newSession();
  const cs = curSession();
  cs.messages.push(Object.assign({ ts: Date.now() }, m));
  if (cs.messages.length === 1 && m.role === 'user') cs.title = (m.content || '新会话').slice(0, 24);
}

// ── 会话上下文辅助 (U17 阶段二) ──
function lastScopeOf(s) {
  // 最近一个 scope 消息的范围 (追问继承: 无新范围信号时沿用)
  for (let i = s.messages.length - 1; i >= 0; i--) {
    if (s.messages[i].kind === 'scope' && s.messages[i].scope) return s.messages[i].scope;
  }
  return null;
}
function lastHistory(s, excludeScopeId) {
  // 对话历史 (user/assistant 文本, 最后 10 条; 不含范围确认卡)
  const out = [];
  for (let i = s.messages.length - 1; i >= 0 && out.length < 10; i--) {
    const m = s.messages[i];
    if (m.role === 'user' && m.kind === 'text') out.unshift({ role: 'user', content: m.content });
    else if (m.role === 'assistant' && m.kind === 'text' && m.content) out.unshift({ role: 'assistant', content: m.content });
  }
  return out;
}

// ── 发送: 统一对话入口 → 意图分流 ──
function send() {
  const text = inputEl.value.trim();
  if (!text) return;
  const s = curSession();
  pushMsg({ role: 'user', kind: 'text', content: text });
  const tIdx = s.messages.length;   // thinking 占位索引 (响应到达时替换)
  pushMsg({ role: 'assistant', kind: 'thinking', content: '' });
  inputEl.value = '';
  save(); render();
  A.post('/api/ai/chat', { message: text, prev_scope: lastScopeOf(s) }).then(resp => {
    s.messages.splice(tIdx, 1);   // 移除 thinking 占位
    if (resp && resp.error) {
      pushMsg({ role: 'assistant', kind: 'error', content: resp.error });
    } else if (resp && resp.type === 'kb') {
      if (resp.ok) pushMsg({ role: 'assistant', kind: 'kb', content: resp.query, results: resp.results || [] });
      else pushMsg({ role: 'assistant', kind: 'error', content: resp.error || '检索失败' });
    } else if (resp && resp.type === 'scope') {
      // 范围确认卡: 展示解析范围 + 摘要预览, 用户确认后流式分析
      pushMsg({ role: 'assistant', kind: 'scope', scope: resp.scope, summary: resp.summary, message: resp.message || '' });
    } else if (resp && resp.type === 'analyze') {
      pushMsg({ role: 'assistant', kind: 'analyze', content: resp.message || '' });
    } else if (resp && resp.detail) {
      // 后端 FastAPI 错误结构 (如 404 旧后端无此接口): 显示实际原因, 不显示"未知响应"
      pushMsg({ role: 'assistant', kind: 'error', content: '后端接口异常: ' + String(resp.detail).slice(0, 100) });
    } else {
      pushMsg({ role: 'assistant', kind: 'error', content: '未知响应' });
    }
    save(); render();
  }).catch(e => {
    s.messages.splice(tIdx, 1);
    pushMsg({ role: 'assistant', kind: 'error', content: '网络错误: ' + (e.message || '无法连接后端') });
    save(); render();
  });
}

// ── 范围确认 → 流式对话分析 (SSE) ──
function analyzeScope(scope, s) {
  const history = lastHistory(s);
  // 占位消息 (流式填充)
  const sm = { role: 'assistant', kind: 'stream', content: '…', refs: [] };
  s.messages.push(Object.assign({ ts: Date.now() }, sm));
  save(); render();
  const idx = s.messages.length - 1;
  fetch('/api/ai/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope, history }),
  }).then(resp => {
    if (!resp.ok || !resp.body) { throw new Error('HTTP ' + resp.status); }
    const ct = resp.headers.get('content-type') || '';
    if (!ct.includes('event-stream')) {
      // 非流式 (如无 key → no_key JSON): 替换占位消息
      return resp.json().then(d => {
        if (d && d.type === 'no_key') {
          s.messages[idx] = { role: 'assistant', kind: 'no_key', content: d.message || '未配置 LLM Key' };
        } else {
          s.messages[idx].content = '❌ ' + ((d && (d.message || d.error)) || '分析失败');
          s.messages[idx].kind = 'error';
        }
        save(); render();
      });
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    const pump = () => reader.read().then(({ done, value }) => {
      if (done) return;
      buf += decoder.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, i); buf = buf.slice(i + 2);
        const m = /^data:\s*(.*)$/m.exec(block.trim());
        if (!m) continue;
        let d; try { d = JSON.parse(m[1]); } catch (e) { continue; }
        if (d.delta) {
          s.messages[idx].content = (s.messages[idx].content === '…' ? '' : s.messages[idx].content) + d.delta;
          updateStreamMsg(s, idx);
        } else if (d.refs) {
          s.messages[idx].refs = d.refs || [];
          s.messages[idx].kind = 'text';
          finalizeRefs(s, idx);
          save();
        } else if (d.error) {
          s.messages[idx].content = '❌ ' + d.error;
          s.messages[idx].kind = 'error';
          save(); render();
        }
      }
      pump();
    }).catch(e => {
      if (s.messages[idx]) { s.messages[idx].content = '❌ 流式中断: ' + (e.message || ''); s.messages[idx].kind = 'error'; }
      save(); render();
    });
    pump();
  }).catch(e => {
    if (s.messages[idx]) { s.messages[idx].content = '❌ 分析失败: ' + (e.message || ''); s.messages[idx].kind = 'error'; }
    save(); render();
  });
}

function updateStreamMsg(s, idx) {
  // 流式增量更新 (仅改最后一个消息气泡, 避免全量重渲染)
  const msgs = msgsEl.querySelectorAll('.ai-msg');
  const el = msgs[msgs.length - 1];
  if (el) {
    const b = el.querySelector('.ai-bubble');
    if (b) b.textContent = s.messages[idx].content + (s.messages[idx].kind === 'stream' ? '▌' : '');
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }
}

function finalizeRefs(s, idx) {
  // 回答完成: 帧引用 "第 N 帧" → 可点击链接 (点击跳时间线定位)
  const m = s.messages[idx];
  if (!m.refs || !m.refs.length) { render(); return; }
  let text = m.content;
  const sorted = m.refs.slice().sort((a, b) => (b.packet_id || 0) - (a.packet_id || 0));
  sorted.forEach(r => {
    if (!r.packet_id) return;
    const link = `<a class="ai-ref" data-id="${r.id}" href="#tl">第 ${r.packet_id} 帧</a>`;
    text = text.split('第 ' + r.packet_id + ' 帧').join(link);
    text = text.split('帧#' + r.packet_id).join(link);
  });
  m.content = text; m.kind = 'text';
  render();
}
// 帧引用点击 → 报文页定位 (timeline.js 暴露 window.tlJumpFrame)
document.addEventListener('click', e => {
  const t = e.target;
  if (t && t.classList && t.classList.contains('ai-ref')) {
    e.preventDefault();
    location.hash = 'tl';
    setTimeout(() => { if (window.tlJumpFrame) window.tlJumpFrame(parseInt(t.dataset.id, 10)); }, 300);
  }
});

// ── 渲染 ──
function renderTabs() {
  tabBtns.forEach(b => b.classList.toggle('on', b.dataset.t === st.tab));
  const chat = panel.querySelector('#zc-ai-chat'), hist = panel.querySelector('#zc-ai-hist');
  chat.style.display = st.tab === 'chat' ? '' : 'none';
  hist.style.display = st.tab === 'hist' ? '' : 'none';
  cfgEl.style.display = st.tab === 'cfg' ? '' : 'none';
  if (st.tab === 'hist') renderHist();
  if (st.tab === 'chat') { render(); inputEl.focus(); }
}

function render() {
  if (!panel) return;
  // 会话下拉
  selEl.innerHTML = st.sessions.map(s => `<option value="${s.id}">${esc(s.title)}</option>`).join('');
  if (st.cur) selEl.value = st.cur;
  const s = curSession();
  msgsEl.innerHTML = '';
  if (!s || s.messages.length === 0) {
    msgsEl.innerHTML = '<div class="ai-empty">👋 有什么可以帮你？<br>· 知识：<span class="ai-dim">"什么是 parent end device"</span><br>· 分析（阶段二）：<span class="ai-dim">"分析 10:00-10:30 的 0x838D"</span></div>';
    return;
  }
  s.messages.forEach(m => msgsEl.appendChild(msgNode(m, s)));
  msgsEl.scrollTop = msgsEl.scrollHeight;
}

function msgNode(m, s) {
  const wrap = document.createElement('div');
  // role → ai-user/ai-assistant/ai-system; error 消息附加 ai-error (样式用)
  wrap.className = 'ai-msg ai-' + m.role + (m.kind === 'error' ? ' ai-error' : '');
  if (m.kind === 'kb' && m.results) {
    wrap.innerHTML = '<div class="ai-kb-q">🔎 知识检索: ' + esc(m.content) + '</div>';
    const list = document.createElement('div'); list.className = 'ai-kb-list';
    m.results.forEach(r => {
      const c = document.createElement('div'); c.className = 'ai-kb-item';
      c.innerHTML = '<div class="ai-kb-title">' + esc(r.title) + '</div>' +
        '<div class="ai-kb-snippet">' + esc(r.snippet) + '</div>' +
        (r.url ? '<a class="ai-kb-link" href="' + esc(r.url) + '" target="_blank" rel="noopener">🔗 打开官方文档</a>' : '');
      list.appendChild(c);
    });
    wrap.appendChild(list);
    return wrap;
  }
  if (m.kind === 'thinking') {
    // 处理中动画: spinner + 提示 (08-26 用户反馈)
    wrap.innerHTML = '<div class="ai-bubble ai-thinking"><span class="ai-spin"></span>正在处理…</div>';
    return wrap;
  }
  if (m.kind === 'scope' && m.scope) {
    // 范围确认卡 (阶段二): 解析范围 + 摘要预览 + 确认/重述
    wrap.innerHTML = '<div class="ai-bubble ai-scope-head">📐 ' + esc(m.message || '') + '</div>' +
      '<div class="ai-scope-summary">' + esc(m.summary || '') + '</div>' +
      '<div class="ai-scope-actions">' +
      '<button class="btn btn-p btn-sm" data-act="confirm">✅ 确认并分析</button>' +
      '<button class="btn btn-o btn-sm" data-act="redo">✏️ 换种说法</button>' +
      '</div>';
    wrap.querySelector('[data-act="confirm"]').addEventListener('click', () => {
      const btn = wrap.querySelector('[data-act="confirm"]');
      btn.disabled = true;
      btn.textContent = '⏳ 分析中…';   // 处理动画 (08-26 用户反馈)
      analyzeScope(m.scope, s);
    });
    wrap.querySelector('[data-act="redo"]').addEventListener('click', () => {
      inputEl.value = '分析 ' + (m.scope.text || '');
      inputEl.focus();
      inputEl.select();
    });
    return wrap;
  }
  if (m.kind === 'no_key') {
    wrap.innerHTML = '<div class="ai-bubble">⚠️ ' + esc(m.content) +
      '</div><div class="ai-scope-actions"><button class="btn btn-o btn-sm" data-act="gocfg">🔑 去设置配置 Key</button></div>';
    wrap.querySelector('[data-act="gocfg"]').addEventListener('click', () => {
      st.tab = 'cfg'; save(); renderTabs();
    });
    return wrap;
  }
  wrap.innerHTML = '<div class="ai-bubble">' + esc(m.content) + '</div>';
  return wrap;
}

function renderHist() {
  histEl.innerHTML = '';
  // 清空全部 (用户需求 08-26: 重启后测试残留无法一键清)
  const bar = document.createElement('div');
  bar.className = 'ai-hist-bar';
  const clearBtn = document.createElement('button');
  clearBtn.className = 'btn btn-r btn-sm';
  clearBtn.textContent = '🗑 清空全部会话';
  clearBtn.addEventListener('click', () => {
    if (!confirm('清空全部会话历史？此操作不可恢复。')) return;
    st.sessions = [];
    st.cur = null;
    save();
    renderHist(); render(); renderTabs();
  });
  bar.appendChild(clearBtn);
  histEl.appendChild(bar);
  if (!st.sessions.length) {
    histEl.innerHTML += '<div class="ai-empty">暂无历史会话</div>';
    return;
  }
  st.sessions.forEach(s => {
    const d = document.createElement('div'); d.className = 'ai-hist-item';
    d.innerHTML = '<span class="ai-hist-t">' + esc(s.title) + '</span>' +
      '<span class="ai-hist-meta">' + new Date(s.created).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) + ' · ' + s.messages.length + ' 条</span>';
    d.addEventListener('click', () => { st.cur = s.id; st.tab = 'chat'; save(); renderTabs(); });
    const del = document.createElement('button'); del.className = 'btn btn-r btn-sm ai-hist-del'; del.textContent = '删';
    del.addEventListener('click', e => { e.stopPropagation(); st.sessions = st.sessions.filter(x => x.id !== s.id); if (st.cur === s.id) st.cur = st.sessions[0] ? st.sessions[0].id : null; save(); renderHist(); render(); });
    d.appendChild(del);
    histEl.appendChild(d);
  });
}

// ── 设置区 ──
function initCfg() {
  A.get('/api/ai/config').then(c => {
    if (!c) return;
    panel.querySelector('#zc-ai-prov').value = c.provider || 'anthropic';
    const ks = panel.querySelector('#zc-ai-key-state');
    ks.textContent = c.key_set ? '✅ Key 已配置（本地）' : '⚠️ 未配置 Key — 阶段二对话分析需要；知识检索不受影响';
    panel.querySelector('#zc-ai-base').value = c.base_url || '';
    panel.querySelector('#zc-ai-model').value = c.model || '';
    panel.querySelector('#zc-ai-style').value = c.api_style || '';
    if (c.kb_token_ok) panel.querySelector('#zc-ai-tok').placeholder = '✅ 已自动使用本机芯科授权凭证';
    else panel.querySelector('#zc-ai-tok').placeholder = '❌ 未找到凭证，粘贴 token 或检查网络';
  }).catch(() => {});
}

function saveCfg() {
  const prov = panel.querySelector('#zc-ai-prov').value;
  const key = panel.querySelector('#zc-ai-key').value.trim();
  const tok = panel.querySelector('#zc-ai-tok').value.trim();
  const base = panel.querySelector('#zc-ai-base').value.trim();
  const model = panel.querySelector('#zc-ai-model').value.trim();
  const style = panel.querySelector('#zc-ai-style').value;
  const msg = panel.querySelector('#zc-ai-cfg-msg');
  const body = { provider: prov };
  if (key) body.api_key = key;
  if (tok) body.mcp_token = tok;
  body.base_url = base;   // 显式空串 = 清除回默认
  body.model = model;
  body.api_style = style;
  fetch('/api/ai/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    .then(r => r.json()).then(d => {
      if (d && d.ok) {
        msg.textContent = '✅ 已保存（仅存本地）';
        panel.querySelector('#zc-ai-key').value = '';
        panel.querySelector('#zc-ai-tok').value = '';
        initCfg();
      } else msg.textContent = '❌ ' + ((d && d.error) || '保存失败');
    }).catch(() => { msg.textContent = '❌ 网络错误'; });
}

// ── 导入新包 → 上下文切换提示 (U17 对齐决策: 导入新包时对话提示) ──
function onImported(e) {
  const d = e.detail || {};
  const s = curSession();
  if (s && s.messages.length) {
    pushMsg({ role: 'system', kind: 'text', content: '📂 已导入新包' + (d.filename ? '「' + d.filename + '」' : '') + '（' + (d.packets || 0) + ' 帧）— 对话上下文已切换' });
    save(); render();
  }
}

// ── 挂载 (先恢复 localStorage 持久化状态, 再建 DOM — 刷新后对话/面板状态还原) ──
load();
buildDOM();
panel.classList.toggle('on', st.open);
fab.classList.toggle('on', st.open);
renderTabs();
