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
let st = { sessions: [], cur: null, tab: 'chat', open: false };

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
        <label class="ai-lbl">芯科访问 token <span class="ai-dim">（可选，留空自动使用本机授权凭证）</span></label>
        <input id="zc-ai-tok" class="ai-in" type="password" placeholder="粘贴 MCP Bearer token">
        <button class="btn btn-p btn-sm" id="zc-ai-savecfg">保存配置</button>
        <p id="zc-ai-cfg-msg" class="ai-dim"></p>
      </div>
    </div>`;
  document.body.appendChild(panel);

  msgsEl = panel.querySelector('#zc-ai-msgs');
  inputEl = panel.querySelector('#zc-ai-in');
  tabBtns = panel.querySelectorAll('.ai-tab');
  histEl = panel.querySelector('#zc-ai-hist-list');
  selEl = panel.querySelector('.ai-sel');
  cfgEl = panel.querySelector('#zc-ai-cfg');

  fab.addEventListener('click', toggle);
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

// ── 发送: 统一对话入口 → 意图分流 ──
function send() {
  const text = inputEl.value.trim();
  if (!text) return;
  pushMsg({ role: 'user', kind: 'text', content: text });
  inputEl.value = '';
  save(); render();
  A.post('/api/ai/chat', { message: text }).then(resp => {
    if (resp && resp.error) {
      pushMsg({ role: 'assistant', kind: 'error', content: resp.error });
    } else if (resp && resp.type === 'kb') {
      if (resp.ok) pushMsg({ role: 'assistant', kind: 'kb', content: resp.query, results: resp.results || [] });
      else pushMsg({ role: 'assistant', kind: 'error', content: resp.error || '检索失败' });
    } else if (resp && resp.type === 'analyze') {
      pushMsg({ role: 'assistant', kind: 'analyze', content: resp.message || '该问题属于抓包分析，将在阶段二支持。' });
    } else {
      pushMsg({ role: 'assistant', kind: 'error', content: '未知响应' });
    }
    save(); render();
  }).catch(e => {
    pushMsg({ role: 'assistant', kind: 'error', content: '网络错误: ' + (e.message || '无法连接后端') });
    save(); render();
  });
}

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
  s.messages.forEach(m => msgsEl.appendChild(msgNode(m)));
  msgsEl.scrollTop = msgsEl.scrollHeight;
}

function msgNode(m) {
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
  wrap.innerHTML = '<div class="ai-bubble">' + esc(m.content) + '</div>';
  return wrap;
}

function renderHist() {
  histEl.innerHTML = '';
  if (!st.sessions.length) { histEl.innerHTML = '<div class="ai-empty">暂无历史会话</div>'; return; }
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
    if (c.kb_token_ok) panel.querySelector('#zc-ai-tok').placeholder = '✅ 已自动使用本机芯科授权凭证';
    else panel.querySelector('#zc-ai-tok').placeholder = '❌ 未找到凭证，粘贴 token 或检查网络';
  }).catch(() => {});
}

function saveCfg() {
  const prov = panel.querySelector('#zc-ai-prov').value;
  const key = panel.querySelector('#zc-ai-key').value.trim();
  const tok = panel.querySelector('#zc-ai-tok').value.trim();
  const msg = panel.querySelector('#zc-ai-cfg-msg');
  const body = { provider: prov };
  if (key) body.api_key = key;
  if (tok) body.mcp_token = tok;
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
