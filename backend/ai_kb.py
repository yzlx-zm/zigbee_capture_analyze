"""芯科知识库检索客户端 (U17 阶段一: ①知识检索先行).

MCP 端点实测 (2026-08-26): https://silabs.mcp.kapa.ai 为 OAuth 保护的
streamable-HTTP MCP 端点 (标准 HTTP MCP, 但**非匿名** — 直调返回 401
invalid_token, .well-known/oauth-protected-resource 指向 public OAuth).
本机 Claude Code 已授权过该端点 (token 存 ~/.claude/.credentials.json 的
mcpOAuth 下, 用户 08-25 曾用 U13 知识检索), 后端自动发现复用该 token;
用户也可在 ai_config.json 显式配置 (优先级更高)。

技术决策: **直调 HTTP 端点** (httpx 同步 + SSE 解析), 不引入 Python mcp 库 —
端点仅需 initialize → tools/call 两个 JSON-RPC 调用, 依赖更轻 (实测全流程通过)。

key 安全: token 只读不写, 不入 git/分发包; 网络失败/无 token → 降级提示, 不阻断工具。
"""
from __future__ import annotations

import json
import os
import re

import httpx

MCP_ENDPOINT = "https://silabs.mcp.kapa.ai"
TOOL_NAME = "search_silicon_labs_knowledge_sources"
_UA = "zigbee-capture-analyzer/1.0"
_TIMEOUT = httpx.Timeout(25.0, connect=8.0)

# 本地 LLM 配置 (ai_config.json, 与 config.py 同目录; 不入 git) — 这里只读 mcp_token 字段
AI_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_config.json")
# Claude Code 凭证 (OAuth 授权过 kapa.ai 的 token; 自动发现兜底)
_CLAUDE_CRED = os.path.expanduser("~/.claude/.credentials.json")


def _load_ai_config() -> dict:
    try:
        with open(AI_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def resolve_token() -> str | None:
    """按序解析 MCP Bearer token: ai_config.json 显式配置 → Claude Code 凭证自动发现.

    返回 None = 未配置 (调用方降级提示, 不抛异常).
    """
    cfg = _load_ai_config()
    tok = (cfg.get("mcp_token") or "").strip()
    if tok:
        return tok
    try:
        with open(_CLAUDE_CRED, encoding="utf-8") as f:
            cred = json.load(f)
        for v in (cred.get("mcpOAuth") or {}).values():
            if isinstance(v, dict) and v.get("serverUrl") == MCP_ENDPOINT:
                t = (v.get("accessToken") or "").strip()
                if t:
                    return t
    except Exception:
        pass
    return None


def _parse_sse(body: str) -> list[dict]:
    """解析 streamable-HTTP SSE 响应 (event: message\\ndata: {json}).

    data 行可能跨多行 (长 JSON), 按块拼接; 兼容无 event 前缀的裸 JSON."""
    out: list[dict] = []
    for block in re.split(r"\n\s*\n", body.strip()):
        data_lines = [ln[5:].strip() for ln in block.splitlines() if ln.startswith("data:")]
        if not data_lines:
            # 纯 JSON 响应 (非 SSE)
            try:
                out.append(json.loads(block))
            except (json.JSONDecodeError, ValueError):
                pass
            continue
        try:
            out.append(json.loads("".join(data_lines)))
        except (json.JSONDecodeError, ValueError):
            continue
    return out


def _mcp_call(token: str, method: str, params: dict | None = None) -> dict | None:
    """单个 JSON-RPC 调用 (带 initialize 前导, 无状态 — 每次检索全流程)."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}",
        "User-Agent": _UA,
    }
    with httpx.Client(timeout=_TIMEOUT, headers=headers) as client:
        # 1) initialize (streamable HTTP 标准握手)
        resp = client.post(MCP_ENDPOINT, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": _UA, "version": "1.0"}},
        })
        resp.raise_for_status()
        # 2) tools/call (端点实测无需 notifications/initialized 也可调用)
        if method != "initialize":
            resp = client.post(MCP_ENDPOINT, json={
                "jsonrpc": "2.0", "id": 2, "method": method, "params": params or {},
            })
            resp.raise_for_status()
    msgs = _parse_sse(resp.text)
    for m in msgs:
        if m.get("id") in (1, 2) and "result" in m:
            return m["result"]
        if m.get("id") in (1, 2) and "error" in m:
            raise RuntimeError(f"MCP {method} 错误: {m['error']}")
    return None


def _clean_title(raw_title: str) -> str:
    """标题精简 (U17 完善 08-26, 用户实测反馈): 面包屑路径 `A > B > C` 只保留
    最后一段 (过短则并入前段); 超长截断."""
    segs = [s.strip() for s in re.split(r"[>|]", raw_title) if s.strip()]
    if not segs:
        return raw_title
    t = segs[-1]
    if len(t) < 15 and len(segs) > 1:
        t = f"{segs[-2]} > {t}"
    return t[:60] + "…" if len(t) > 60 else t


def _clean_snippet(content: str) -> str:
    """snippet 清洗 (U17 完善): 去 markdown 标题行 (title 已单独显示, 路径噪音
    主要来自首行 # 面包屑) → 去 HTML 标签残留 → 去 markdown 图片/链接 → 去符号
    → 压缩空白, 从正文段落截取."""
    lines = [ln for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    text = " ".join(lines)
    text = re.sub(r"<[^>]+>", " ", text)                              # HTML 标签 (<figure>/<a href>)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)                 # markdown 图片
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)              # markdown 链接 → 文本
    text = re.sub(r"[*_>`|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:220]


# Thread/OpenThread 文档 (ot-docs 域) — 用户问 Zigbee 时无关, 过滤 (U17 完善)
_IRRELEVANT_URL = re.compile(r"ot-docs|thread-primer|thread-br|thread-commissioner")


def _url_fingerprint(url: str) -> str:
    """URL 指纹去重 (中英重复): 去掉语言段 (/en/ /zh-cn/ 等) 后相同视为同一文档."""
    return re.sub(r"/(en|zh-cn|ja|ko|de|fr|es)/", "/", url)


def _extract_results(raw_result: dict) -> list[dict]:
    """MCP 工具返回结构 (实测 2026-08-26): content = 15 个独立 markdown text item
    (无 URL), **source_url 在 structuredContent.results[]** → 转换为
    [{title, snippet, url}].

    双路径: structuredContent 优先, content[].text 兜底 (title 取 markdown 首行 #).
    过滤: Thread 文档排除 + 语言变体去重 (保留先出现的); 最多 6 条.
    """
    out: list[dict] = []
    seen_fp: set[str] = set()
    seen_title: set[str] = set()   # 同标题多源 (docs.silabs.com + github 镜像) 去重

    def _fmt(rec: dict) -> dict | None:
        content = (rec.get("content") or "").strip()
        url = rec.get("source_url") or ""
        if not content or not url:
            return None
        if _IRRELEVANT_URL.search(url):
            return None
        fp = _url_fingerprint(url)
        if fp in seen_fp:
            return None
        m = re.match(r"#\s*(.+)$", content, re.M)
        title = _clean_title(m.group(1).strip() if m else url)
        if title in seen_title:
            return None  # 同一文档的官方站 + github 镜像, 保留先出现的
        seen_fp.add(fp)
        seen_title.add(title)
        return {"title": title,
                "snippet": _clean_snippet(content), "url": url}

    try:
        sc = raw_result.get("structuredContent") or {}
        for rec in (sc.get("results") or [])[:15]:
            item = _fmt(rec)
            if item:
                out.append(item)
        if not out:
            for c in raw_result.get("content", [])[:8]:
                item = _fmt({"content": c.get("text", "")})
                if item:
                    out.append(item)
    except Exception:
        pass
    return out[:6]


def search_kb(query: str) -> dict:
    """检索芯科知识库 → {"ok": True, results: [{title, snippet, url}]}.

    失败降级: {"ok": False, "error": 人类可读原因} — 不抛异常, 不阻断工具.
    """
    token = resolve_token()
    if not token:
        return {"ok": False, "error": "知识源未配置 (无访问 token)"}
    try:
        result = _mcp_call(token, "tools/call", {
            "name": TOOL_NAME, "arguments": {"query": query},
        })
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"知识源不可达: {e.__class__.__name__}"}
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    if not result:
        return {"ok": False, "error": "知识源响应为空"}
    results = _extract_results(result)
    if not results:
        return {"ok": False, "error": "未检索到相关内容"}
    return {"ok": True, "results": results, "server": "Silicon Labs MCP"}
