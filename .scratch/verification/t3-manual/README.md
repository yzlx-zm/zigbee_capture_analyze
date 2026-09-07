# 工具截图与手册构建流程 (T3 沉淀, 可复用)

> 用途: 给 Web 工具页面抓「真实运行截图」(UI 手册/验证用), 以及配套的无视觉验证法。
> 本目录脚本由 T3 会话 (2026-09-07) 实机跑通, 后续会话 (UI 改版复抓/新手册) 直接复用。
> 主流程: 后端起服务 → Edge CDP 起浏览器 → 导素材 → 截图脚本 (DOM 断言+截图同帧) →
> PIL 压缩 → 模板构建 → 双层验证。

## 0. 能力边界 (先读)

本工程会话模型可能**无视觉** (读不了图片内容)。截图交付的验证闭环是:
**每次截图前/后在同一页面跑 DOM 断言** (元素数/文本/可见性/计数), 断言通过 = 截图内容可信;
「截图与 UI 一致」以 DOM 级验证为据, 并在交付中如实标注「未逐像素目视, 建议人工抽验」。

## 1. 前置: 后端 + 浏览器

```bash
# 后端 (开发模式; 全局单实例锁 → 只能有一个, 先查 netstat -ano | grep 8720 有无遗留)
python -m backend --port 8720 --no-browser     # --no-browser: 不弹用户浏览器

# Edge CDP (Node ≥22: fetch + 原生 WebSocket)
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --remote-debugging-port=9222 --user-data-dir="<独立目录, 如 %TEMP%\edge-cdp>" \
  --headless=new about:blank &
curl -s http://127.0.0.1:9222/json/version   # DevTools listening → OK
```

坑:
- 关测试 Edge 要**按 PID** (taskkill //PID <pid> //F)。`taskkill //IM msedge.exe` 会杀用户正在用的全部 Edge。
- 若 9222 已有实例 (前会话遗留) 直接复用, 别重复开。
- 单实例锁 (Local\ZigbeeAnalyzerInstance 互斥) 不分端口 — 后端不能双开。

## 2. 截图管线 (shot_lib.mjs 已封装)

```js
import { openTab, sleep } from './shot_lib.mjs';   // CDP='http://127.0.0.1:9222'
let p = await openTab('http://localhost:8720/#diag'); // 路由: #import #topo #tl #nodes #diag
await sleep(15000);   // 诊断/拓扑等要等检测端点 + 渲染 (6-16s 视页面)
const info = await p.ev(`(function(){ /* DOM 断言: 返回 {计数, 文本, 可见性} */ })()`);
await p.shot('shots/xxx.jpg');   // jpeg q88, 视口 1440×940 (Emulation 已设)
await p.close();                  // 关 tab (不关浏览器)
```

要点:
- 开 tab = `PUT /json/new?about:blank` → WebSocket 连 webSocketDebuggerUrl → `{id,method,params}` 收发, 等 `m.id` 匹配。
- `Page.captureScreenshot` 的 `captureBeyondViewport` **实测不生效** (仍是视口尺寸) → 长页面用
  `scrollIntoView({block:'start'})` 分屏截。
- 页面交互 (点 tab/行/滑块) 全走 `Runtime.evaluate`; 每步后 sleep 等渲染, 断言看结果。

## 3. 数据准备 (导素材)

```bash
# 后端无数据时: 本地路径导入 (Form 不是 JSON!)
curl -s -X POST http://127.0.0.1:8720/api/import/local-cubx \
  -F "path=D:/.../<ascii 名>.cubx"    # 中文名会经 curl 编码乱码 → 先复制成 ASCII 名
curl -s "http://127.0.0.1:8720/api/import/progress?task_id=<返回的 id>"   # 轮询
curl -s http://127.0.0.1:8720/api/import/status    # total/nodes 确认
```

坑:
- 素材路径**盘符大写 + 正斜杠** (`D:/ai_agent/...`) — 小写盘符曾报"路径不存在"。
- 遗留后端数据可能损坏 (实例曾见 pkts 8435 / nodes=0) → kill PID 后重启重导。
- 大包拆分面板触发 (真实 UI 路径): `DOM.getDocument` → `DOM.querySelector('#pfinp')` →
  `DOM.setFileInputFiles` (注入 >1MB 的 .cubx) → dispatch change 事件 → 面板弹出;
  拆分流**不污染**当前内存数据 (只拆不导, 关面板即还原)。

## 4. 截图 → 压缩 → 手册构建

```bash
python .scratch/verification/t3-manual/compress.py     # 选图宽≤1240 q82 → final/*.jpg
python docs/manual/build_manual.py                     # 模板+base64 → docs/user-manual.html (自包含)
```

模板: `docs/manual/user-manual.template.html`, 插图占位 `{IMG:name}`;
产物自包含 (无 CDN), 截图 base64 内嵌 (17 张 ≈ 2.4MB)。

## 5. 双层验证 (无视觉模型的兜底)

1. **结构断言** (python): 章节 id 齐全 / 无残占位符 / img 数与 data-uri 数 = 期望 / 0 外链 / 标签平衡。
2. **浏览器真实渲染** (verify_manual.mjs): `file://` 打开 → img `complete && naturalWidth>0` 全过、
   关键文字存在、0 运行时异常。
3. 交付时诚实标注: DOM 级验证已过, 建议用户侧目视抽验。

## 6. 本会话踩过的坑速查

| 坑 | 表现 | 解法 |
|----|------|------|
| 表格行文本是 **tab 分隔** | 正则 `/\|Data\|/` 永不匹配 | 用 `includes('Data')` + 确认首屏行的真实内容 (首屏多为 Beacon/MAC Ack) |
| 节点页「展开」= 点 **tr 本身** | 点行内第一个 button 无反应甚至跳页 | 🎯 是定位跳转按钮; 展开绑在 `.nd-row` click |
| 报文详情是**右侧固定面板** `#tl-detail` | 找行下展开容器永远找不到 | 点行后查 `#tl-detail` innerText (ZCL 帧 ~940 字符) |
| 可见性判断 | `.hidden` class 恒在 (组件用 style.display 控制) | 用 `offsetParent!==null` 或 `style.display` |
| 顶栏版本号开发模式为 null | 截图无 `v1.0.2` | 临时建根 `version.json` → 刷新截图 → **删掉再提交** (不入 git) |
| 中文文件名经 curl 乱码 | "路径不存在: ÖÐ¼Ì…" | 素材复制 ASCII 名; 路径盘符大写 |
| Edge 全家被杀 | 用户浏览器也被关 | 按 PID taskkill |
| 断言与截图错帧 | 截了空态 | 截图前先断言目标状态 (可见/计数), 失败则修步骤重截 |

## 7. 文件清单

- `shot_lib.mjs` — CDP 共用库 (openTab/ev/shot/close)
- `s1_diag.mjs` ~ `s8_extra.mjs` — 各页面截图 (可作新抓取范例)
- `compress.py` / `compress.mjs`(弃用) — 截图压缩
- `verify_manual.mjs` — 手册 file:// 渲染验证
- 截图原图 (jpg/png) 与 `final/` 压缩图在本目录, 不入 git (产物 HTML 已内嵌)
- 构建链: 模板 `docs/manual/user-manual.template.html` + `docs/manual/build_manual.py`
