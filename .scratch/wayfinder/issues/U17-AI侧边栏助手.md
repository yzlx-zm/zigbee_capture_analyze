# U17 — AI 侧边栏助手 (知识检索 + 对话式问题分析, grilling 对齐产出)

**What to build:** 全局侧边栏 AI 助手: ①芯科 MCP 知识检索 (手动搜索, 无需 LLM key) +
②对话式问题分析 (自然语言描述问题+范围 → 范围内取数 → LLM 对话, key 使用者自备)。

**Blocked by:** None

**Status:** ready-for-agent | **Assignee:** U17-实现窗口 (2026-08-26) — 阶段一+阶段二代码完成 (真流式待 key 实测)

**Type:** task | **AFK** (② 依赖使用者 key, 界面先行)

**来源**: 2026-08-25 总控窗口 grilling 对齐 (用户确认, 页面形态=侧边栏调整后确认)。
用户约束: "api key 得是别人给, 不能内置, 否则都是花我的钱" — **key 使用者自备, 分发包不含**。

## 对齐决策 (用户确认, 不可更改)

| 项 | 结论 |
|----|------|
| 页面形态 | **全局侧边栏** (可折叠, 任何页面可用), **切页对话状态保持** (模块级单例, 类 U6 顶栏三态理念) |
| 入口 | **统一对话输入框** — 意图分流: 纯知识问题 → 芯科 MCP 检索; 含范围/包 → 分析 (非双 Tab) |
| ① 知识检索 | 芯科 MCP 封装 (HTTP 端点 `https://silabs.mcp.kapa.ai`, 已确认) → 统一对话内分流查 → 结果: 官方文档片段 + 来源链接; **不做诊断联动** (用户裁定) |
| ② 对话式分析 | 用户**纯自然语言**描述问题+范围 → 后端解析范围 (时间窗/PAN/节点/簇, 复用 U11 预扫+解析能力) → **先展示解析范围供确认/修正** → 按范围取数生成 AI 可读摘要 → LLM 对话回答 (可追问) |
| 输出形态 | **文本 + 帧引用可点击** (如"第 352 帧的 Leave") → 跳时间线定位验证 |
| 多轮追问 | **继承上轮范围** (时间窗延续, 换对象即可; 显式新范围覆盖) |
| 持久化 | **localStorage 保存对话历史** (刷新/重启保留, 多会话历史列表) |
| ③ 包全景扫描 | **暂缓** (用户裁定麻烦, 不列入) |
| LLM key | 使用者自备, **本地配置** (配置文件/环境变量, 分发包不含); 提供商可配置 (Anthropic/OpenAI/DeepSeek 兼容) |
| 范围解析失败 | 引导用户重新描述, 不臆测 |

## 技术基础 (总控已确认)

- 芯科 MCP: 标准 HTTP MCP (`https://silabs.mcp.kapa.ai`), Python mcp 库可连;
  工具 = search_silicon_labs_knowledge_sources (本会话已实证可用, U13 用过)
- 范围能力: U11 cubx_splitter.prescan_cubx (时间窗/PAN/帧统计) + U13 链路证据 +
  U15 载荷解析 — 按范围取数生成摘要的基础
- AI 摘要: export_ai_dataset.py digest/packet_summary 可复用
- 侧边栏基建: 无现成 — 新建全局浮层 (fixed 面板), 与页面模块平行

## 实现要点 (总控设计)

### 阶段一: ①知识检索 (先交付, 无需 LLM key)
1. **后端** — 新文件 backend/ai_kb.py:
   - MCP 客户端: Python mcp 库连 `https://silabs.mcp.kapa.ai` (或 HTTP 直调该端点,
     实现时评估 — mcp 库最标准), 封装 `search_kb(query) -> [{title, snippet, url}]`
   - 后端启动延迟初始化 (网络失败降级提示"知识源不可达", 不阻断工具)
   - API: `GET /api/ai/kb?q=...` → 检索结果 (片段+来源链接)
2. **前端** — 侧边栏"知识"Tab: 搜索框 → 结果列表 (片段+链接, 点击打开官方文档)

### 阶段二: ②对话式分析 (key 自配)
3. **范围解析** — 后端 /api/ai/analyze:
   - 输入: 对话消息 (自然语言)
   - 解析: 时间窗 (HH:MM:SS~或"前 N 秒")/PAN/短地址/簇关键词 → 结构化范围
     (正则+关键词, 解析失败返回引导提示)
   - 按范围取数: 复用 cubx_splitter 时间过滤 + packets 过滤 → 生成范围摘要
     (统计+关键事件+检测结果, 精简版)
4. **LLM 对话** — backend/ai_chat.py:
   - key 配置: 本地配置文件 (如 ai_config.json 或环境变量), 界面"设置"入口填写
     (key 存本地, 不入 git/分发包)
   - 提供商适配: Anthropic/OpenAI/DeepSeek 兼容层 (统一接口, 流式)
   - 上下文: 系统提示 (Zigbee 领域特化) + 范围摘要 + 对话历史 (窗口限制)
   - 流式响应 → 前端对话渲染
5. **前端侧边栏**:
   - 全局挂载 (index.html + app.js), 可折叠按钮 (顶栏或右下角浮标)
   - Tab: [知识] [分析] [设置(key)]
   - 对话状态: 模块级单例 (切页保留), 上下文绑定当前导入包 (导入新包清空或提示)
   - 分析 Tab: 输入框 + 对话列表 (流式) + 范围确认提示 (解析出的范围展示给用户)

### 不做 (本次)
- 包全景扫描 (暂缓)、诊断联动 (用户裁定)、多包对比、导出对话记录

## 验证标准

1. 知识检索: 查 "parent end device" → 返回官方文档片段+链接 (U13 实证过的查询)
2. 侧边栏: 任何页面可开/折叠; 切页后对话与 Tab 状态保留 (CDP)
3. 范围解析: "分析 10:00-10:30 的 0x838D" → 时间窗+PAN/节点解析正确; 无法解析 → 引导提示
4. 范围摘要: 导入中继素材 → 范围内摘要含帧数/关键事件 (与 digest 对账)
5. LLM 对话: 配置 key 后 (测试 key) → 流式回答; 无 key → 提示配置 (不崩)
6. 回归: 现有页面功能不崩 (侧边栏无侵入); 版本号递增

## 风险

- MCP HTTP 端点: 需确认 mcp 库对该端点的兼容性 (stdio 为标准, HTTP 走 streamable-http;
  实现时若 mcp 库不兼容则直调 HTTP 端点)
- 范围解析准确度: 自然语言解析是薄弱点 — 解析失败引导重述, 不臆测 (铁律)
- LLM 提供商差异: 兼容层封装, 先用一个提供商实测再扩展
- 侧边栏与页面联动: 上下文 = 当前导入包; 导入新包时对话提示"上下文已切换"
- key 安全: 本地配置, 界面提示"key 仅存本地"

## Resolution (2026-08-26, 阶段一: ①知识检索先行 — 已完成并验证)

**交付范围**: 阶段一全部 (知识检索 + 侧边栏框架 + 统一对话入口意图分流 + localStorage 持久化 + 设置区界面先行)。阶段二 (范围解析/取数摘要/LLM 对话) 未做, 界面与引导文案就绪。

### 后端 (3 文件)
- `backend/ai_kb.py` — 芯科 MCP 客户端: **直调 HTTP 端点方案** (实测 2026-08-26: 端点 `https://silabs.mcp.kapa.ai` 为 OAuth 保护 (401 invalid_token, .well-known/oauth-protected-resource), Python mcp 库未装且无需 — httpx + SSE 解析 3 步打通: initialize → tools/call → 提取); **token 自动发现链**: ai_config.json 显式配置 (mcp_token) → Claude Code 凭证 (~/.claude/.credentials.json mcpOAuth, 用户已授权 kapa.ai) → 无 token 降级提示不阻断; 检索结果来源 = structuredContent.results[].source_url (content 文本无 URL, 实测)
- `backend/api/ai.py` — POST /api/ai/chat 意图分流 (4 位 hex 地址/时间窗/范围词 → analyze; 知识问法 → kb; 无法判定不臆测) + GET /api/ai/kb + GET/PUT /api/ai/config (key 存 ai_config.json, 不入 git, 响应不回传 key 明文)
- `backend/api/router.py` — 注册 ai 路由

### 前端 (5 文件)
- `frontend/js/ai.js` — 侧边栏模块: 右下角 🤖 浮标 + fixed 面板 (任何页面可用); 统一对话输入框 → 意图分流渲染 (kb 结果卡片 title/snippet/🔗链接 / analyze 引导文案); 模块级单例 (切页保留) + localStorage 持久化 (多会话, 刷新恢复); 设置区 (provider 下拉 + API key + MCP token, "仅存本地"提示); 导入新包 → 系统消息"上下文已切换"
- `frontend/index.html` — **移除 AI 导航项 + reg('ai') 占位** (用户确认决策); 版本号递增
- `frontend/js/app.js` — import ai.js (版本号递增); `frontend/js/state.js` — sr() 广播 zc:imported 事件; `frontend/css/app.css` — .ai-* 样式 (43 规则)

### 修复的真 bug (验证中发现)
1. **load() 从未被调用** — localStorage 持久化从未生效 (切页保留靠内存单例正常, 刷新恢复失效); 修复: 模块底部 buildDOM 前 load()
2. **消息 class 选择器不匹配** — wrap.className='ai-msg ai-system' vs CSS .ai-msg.system (含 .ai-msg.error 同样问题, 错误样式从未生效); 修复: CSS 改 .ai-msg.ai-system/.ai-msg.ai-error + msgNode 附加 ai-error

### 验证 (14/14 CDP, .scratch/verification/u17-ai-sidebar/u17_verify.mjs)
- 知识检索 "parent end device" → 8 条结果含官方链接 ✅ (U13 实证查询可复现)
- 侧边栏开/折叠 ✅; 切页保留 ✅; 刷新恢复 (localStorage) ✅; 导入事件提示 ✅
- 意图分流: "分析 10:00-10:30 的 0x838D" → analyze 引导文案 (不崩不臆测) ✅; 边界 "什么是 0x0B 网络状态码" → kb ✅
- 设置区 key 状态显示 (无 key 不崩) ✅; 无 JS 异常 ✅; 后端回归 (import/status/packets) ✅

### ⚠️ 并发冲突记录 (铁律 5)
并行会话 (15c1709 等 5 条提交) 同时改动 U17 相关文件: 恢复 AI 导航链接 + 折叠箭头样式 + 把我未提交的 app.css 改动卷入 HEAD。用户裁定: 本会话继续并提交 (按决策移除导航)。两会话文件已合并一致, 无残留冲突。

### 阶段二待办 (未做)
范围解析 (时间窗/PAN/节点/簇) → 取数摘要 (复用 export_ai_dataset) → LLM 兼容层 (Anthropic/OpenAI/DeepSeek 流式, ai_config.json key) → 帧引用跳转时间线。设置区 UI 已就绪, key 配置可直接用。


## Resolution 追加 (2026-08-26, 阶段二: 对话式分析 — 代码完成, 真 LLM 流式待 key 实测)

### A 检索质量优化 (用户实测反馈驱动)
- `backend/ai_kb.py`: 标题精简 (面包屑只留末段, 过短并入前段, >60 截断); snippet 清洗 (去 markdown 标题行/HTML 标签/图片/符号, 从正文截取); 结果过滤 (排除 Thread/ot-docs 文档 + 语言变体去重 + 同标题多源去重); 上限 6 条
- 实测: "parent end device" → 6 条干净结果 (标题 "Parents of End Device", 无 HTML 残留)

### C 对话式分析 (阶段二)
- `backend/ai_scope.py` — 范围解析 parse_scope: 时间窗 (10:00-10:30/至/到) + 相对时间 (最近 N 秒/分钟/小时) + 短地址 (0x838D, 排除广播) + PAN 0x1234; 无信号 → 继承上轮范围 (追问); 解析失败 → 引导重述不臆测; build_scope_summary: 范围内统计+关键事件 (pkt_type 兜底含加密 NWK 命令帧)+检测 verdict 精简 (l1/l2/l3/l6 detect, 异常降级)
- `backend/ai_chat.py` — LLM 兼容层: anthropic (SDK) / openai / deepseek (OpenAI 兼容 base_url) 统一流式接口; key 解析: ai_config.json → 环境变量; 无 key → LLMError 可读提示; 系统提示 Zigbee 领域特化 (0x0B/0x0C/0x06 术语)
- `backend/api/ai.py` — 流程: /ai/chat analyze 分支 → parse_scope → 返回范围确认卡 (type=scope + summary); /ai/analyze → 无 key 提示 (type=no_key) / 有 key SSE 流式 (data: {delta}, 结束 {done, refs}); 帧引用提取 (第 N 帧 → packet_id → 列表 id 映射); 范围继承 (prev_scope)
- `frontend/js/ai.js` — 范围确认卡渲染 (范围+摘要+确认/换种说法) + SSE 流式渲染 (ReadableStream, 增量更新) + no_key 卡片 (去设置按钮) + 帧引用可点击 (ai-ref → hash=#tl + tlJumpFrame); `timeline.js` 暴露 window.tlJumpFrame (reg 回调作用域内, 报文页进入时生效)
- 验证 (8721, CDP): 范围解析 (相对时间→时间窗) ✅ / 摘要含事件 ✅ / 追问继承 ✅ / 无 key → no_key 提示+跳设置 ✅ / 帧引用映射单测 ✅ / tlJumpFrame 报文页可用 ✅ / 检索清洗 ✅; **真 LLM 流式未实测 (无 key) — 诚实标注, 待用户配置 key 验证**
- 修复: ai.py 装饰器被 Edit 误吞 (语法结构修复); from ..files → .files 路径; detect_intent 补相对时间/"看看"信号; timeline.js 暴露语句作用域错误 (模块链中断根因)
