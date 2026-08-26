"""AI 侧边栏助手 API (U17).

- POST /api/ai/chat — 统一对话入口: 意图分流 (纯知识 → 芯科检索; 含范围/包 → 分析, 阶段二)
- GET  /api/ai/kb    — 知识检索快捷端点
- GET  /api/ai/config / PUT /api/ai/config — LLM key 本地配置 (ai_config.json, 不入 git)

key 安全 (用户明确 08-25): key 仅本地配置, 分发包不含; 响应不回传 key 明文.
"""
from __future__ import annotations

import json
import os
import queue
import re
import threading

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

router = APIRouter()

AI_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai_config.json")

# ── 意图分流 (U17 对齐决策: 统一对话输入框, 自动分流, 非双 Tab) ──
# 分析信号: 范围/包关键词 → 阶段二对话式分析; 无信号 → 纯知识检索
_ADDR_RE = re.compile(r"0x[0-9A-Fa-f]{3,4}\b")        # 短地址/PAN (0x838D / 0xBE5A)
_TIME_RE = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")    # 时间窗 (10:00 / 10:00:30)
_REL_TIME_RE = re.compile(r"(?:最近|前|过去)\s*\d+\s*(?:秒|分钟|分|小时)")  # 相对时间
_SCOPE_WORDS = re.compile(
    r"(分析|为什么|怎么回事|什么原因|查看|检查|看看|第\s*\d+\s*帧|时间线|抓包|日志|"
    r"帧|包|节点|范围|PAN|网段|入网|离线|掉线|收不到|失败|入网流程)")

# 知识问法 (以"什么/如何/解释/介绍/区别/支持"等开头且无分析信号 → kb)
_KB_LEAD = re.compile(r"^(什么是|什么|如何|怎么|解释|介绍|说说|区别|有哪些|支持|了解|查|查找)")


def detect_intent(message: str) -> str:
    """意图分流 → "kb" (纯知识检索) / "analyze" (对话式分析, 阶段二).

    规则 (按优先级): 4 位 hex 地址 / 时间窗 / 分析行为词 → analyze;
    知识问法开头且无分析信号 → kb; 其余含范围/包关键词 → analyze, 默认 kb.
    解析失败/无法判定 → 不臆测, 引导重述 (前端对 analyze 展示引导文案).
    """
    m = message.strip()
    if not m:
        return "kb"
    has_addr = bool(_ADDR_RE.search(m))
    has_time = bool(_TIME_RE.search(m))
    has_rel = bool(_REL_TIME_RE.search(m))   # 相对时间 (最近 5 分钟)
    has_scope = bool(_SCOPE_WORDS.search(m))
    is_kb_lead = bool(_KB_LEAD.match(m))
    # 4 位 hex (0x838D 这类短地址/PAN 是分析对象的强信号)
    if has_addr:
        return "analyze"
    # 时间窗 (10:00-10:30) 是范围强信号
    if has_time or has_rel:
        return "analyze"
    # 知识问法 ("什么是 parent end device") → kb, 但含范围词时以范围词为准
    if is_kb_lead and not has_scope:
        return "kb"
    if has_scope:
        return "analyze"
    return "kb"


# ── 配置存取 (ai_config.json, 本地仅用户可见) ──
def _load_config() -> dict:
    try:
        with open(AI_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict) -> None:
    with open(AI_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class ChatRequest(BaseModel):
    message: str
    prev_scope: dict | None = None   # 上轮范围 (追问继承; 前端从会话状态带)


class AnalyzeRequest(BaseModel):
    scope: dict                      # 解析后的范围 (确认卡确认后回传)
    history: list[dict] = []         # 对话历史 [{role, content}] (消息级, 窗口限制前端截)


class ConfigRequest(BaseModel):
    provider: str = "anthropic"   # anthropic / openai / deepseek
    api_key: str = ""
    mcp_token: str = ""           # 可选: 芯科 MCP Bearer token (留空自动发现本机凭证)


@router.post("/ai/chat")
async def ai_chat(req: ChatRequest):
    """统一对话入口 — 意图分流:
    - 纯知识问题 → 芯科 MCP 检索结果
    - 含范围/包关键词 → 分析: 范围解析 → 展示范围确认卡 (前端确认后调 /ai/analyze)
    """
    message = req.message.strip()
    if not message:
        return JSONResponse({"error": "消息不能为空"}, 400)
    intent = detect_intent(message)
    if intent == "kb":
        from .. import ai_kb
        return {"type": "kb", "query": message, **ai_kb.search_kb(message)}
    # analyze: 范围解析 (失败 → 引导重述不臆测; 追问无范围信号 → 继承上轮)
    from .files import get_packets
    from .. import ai_scope
    packets = get_packets()
    r = ai_scope.parse_scope(message, packets, prev=req.prev_scope)
    if not r["ok"]:
        return {"type": "analyze", "kind": "scope_error",
                "message": r["error"] or "范围解析失败，请换种说法重试"}
    scope = r["scope"]
    summary = ai_scope.build_scope_summary(packets, scope)
    return {"type": "scope", "scope": scope, "summary": summary,
            "message": ("解析到分析范围: " + scope.get("text", "全部")
                        + ("（沿用了上一轮范围）" if scope.get("inherit") else ""))}


@router.get("/ai/kb")
async def ai_kb_search(q: str = ""):
    """知识检索快捷端点 (侧边栏知识 Tab 直接搜索)."""
    q = q.strip()
    if not q:
        return JSONResponse({"error": "参数 q 不能为空"}, 400)
    from .. import ai_kb
    return {"type": "kb", "query": q, **ai_kb.search_kb(q)}


_FRAME_REF_RE = re.compile(r"(?:第\s*(\d+)\s*帧|帧\s*[#＃]\s*(\d+))")


def _extract_frame_refs(text: str, packets: list[dict]) -> list[dict]:
    """LLM 回答中的帧引用 ("第 352 帧") → [{packet_id, id}]; packet_id 是抓包帧号
    (摘要事件行口径), 时间线跳转需要列表索引 id (tlJumpToFrame 参数)."""
    refs: list[dict] = []
    seen: set[int] = set()
    # packet_id → 索引 映射 (单遍)
    id_by_pid: dict[int, int] = {}
    for idx, p in enumerate(packets):
        pid = p.get("packet_id")
        if pid is not None and pid not in id_by_pid:
            id_by_pid[pid] = idx
    for m in _FRAME_REF_RE.finditer(text):
        n = int(m.group(1) or m.group(2))
        if n in seen:
            continue
        seen.add(n)
        if n in id_by_pid:
            refs.append({"packet_id": n, "id": id_by_pid[n]})
        elif 0 <= n < len(packets):   # 兜底: LLM 可能引用列表索引
            refs.append({"packet_id": packets[n].get("packet_id"), "id": n})
    return refs


@router.post("/ai/analyze")
async def ai_analyze(req: AnalyzeRequest):
    """范围确认后的对话分析: 范围摘要 → LLM 流式回答 (SSE).

    无 key → 提示配置 (不崩); 流式 data: {"delta": ...}, 结束 data: {"done", "refs"}.
    """
    from .files import get_packets
    from .. import ai_scope, ai_chat
    packets = get_packets()
    if not packets:
        return JSONResponse({"error": "无数据 — 请先导入抓包"}, 400)
    scope = req.scope or {}
    summary = ai_scope.build_scope_summary(packets, scope)

    # 无 key: 普通 JSON 提示 (前端显示配置引导, 不崩)
    provider = ai_chat.load_provider()
    if not provider:
        return {"type": "no_key", "message": "未配置 LLM API Key — 请在 AI 助手「设置」中填写（仅存本地）"}

    history = [m for m in (req.history or [])[-10:]
               if m.get("role") in ("user", "assistant") and m.get("content")]
    messages = [{"role": "system",
                 "content": ai_chat.SYSTEM_PROMPT + "\n\n" + summary}] + history

    def gen():
        """流式 SSE: 线程跑 LLM, 队列转发 delta; 结束附帧引用 refs."""
        q: "queue.Queue[tuple]" = queue.Queue()

        def _cb(t: str) -> None:
            q.put(("t", t))

        def _run() -> None:
            try:
                ai_chat.stream_chat(provider, messages, _cb)
                q.put(("done", None))
            except ai_chat.LLMError as e:
                q.put(("e", str(e)))
            except Exception as e:
                q.put(("e", f"LLM 调用失败: {e}"))

        threading.Thread(target=_run, daemon=True).start()
        chunks: list[str] = []
        while True:
            try:
                kind, val = q.get(timeout=15)
            except queue.Empty:
                yield "data: {\"ping\": true}\n\n"   # 保活 (长回答防代理超时)
                continue
            if kind == "t":
                chunks.append(val)
                yield f"data: {json.dumps({'delta': val}, ensure_ascii=False)}\n\n"
            elif kind == "e":
                yield f"data: {json.dumps({'error': val}, ensure_ascii=False)}\n\n"
                return
            else:  # done
                refs = _extract_frame_refs("".join(chunks), packets)
                yield f"data: {json.dumps({'done': True, 'refs': refs}, ensure_ascii=False)}\n\n"
                return

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/ai/config")
async def ai_config_get():
    """读取 LLM 配置状态 — 不回传 key 明文, 仅回传是否已配置."""
    cfg = _load_config()
    from .. import ai_kb
    return {
        "provider": cfg.get("provider", "anthropic"),
        "key_set": bool((cfg.get("api_key") or "").strip()),
        "kb_token_ok": bool(ai_kb.resolve_token()),   # 知识源 token 可用性 (自动发现也算)
        "key_location": AI_CONFIG_PATH,
    }


@router.put("/ai/config")
async def ai_config_put(req: ConfigRequest):
    """保存 LLM key / MCP token 到本地 ai_config.json (仅存本地, 不入 git/分发包)."""
    if req.provider not in ("anthropic", "openai", "deepseek"):
        return JSONResponse({"error": f"不支持的提供商: {req.provider}"}, 400)
    cfg = _load_config()
    cfg["provider"] = req.provider
    if req.api_key.strip():
        cfg["api_key"] = req.api_key.strip()
    # 空 key 传回 = 保留原 key (前端不回传明文)
    if req.mcp_token.strip():
        cfg["mcp_token"] = req.mcp_token.strip()
    try:
        _save_config(cfg)
    except OSError as e:
        return JSONResponse({"error": f"配置写入失败: {e}"}, 500)
    return {"ok": True, "key_set": bool(cfg.get("api_key", "").strip())}
