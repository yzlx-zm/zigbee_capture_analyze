"""AI 侧边栏助手 API (U17).

- POST /api/ai/chat — 统一对话入口: 意图分流 (纯知识 → 芯科检索; 含范围/包 → 分析, 阶段二)
- GET  /api/ai/kb    — 知识检索快捷端点
- GET  /api/ai/config / PUT /api/ai/config — LLM key 本地配置 (ai_config.json, 不入 git)

key 安全 (用户明确 08-25): key 仅本地配置, 分发包不含; 响应不回传 key 明文.
"""
from __future__ import annotations

import json
import os
import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

AI_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai_config.json")

# ── 意图分流 (U17 对齐决策: 统一对话输入框, 自动分流, 非双 Tab) ──
# 分析信号: 范围/包关键词 → 阶段二对话式分析; 无信号 → 纯知识检索
_ADDR_RE = re.compile(r"0x[0-9A-Fa-f]{3,4}\b")        # 短地址/PAN (0x838D / 0xBE5A)
_TIME_RE = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")    # 时间窗 (10:00 / 10:00:30)
_SCOPE_WORDS = re.compile(
    r"(分析|为什么|怎么回事|什么原因|查看|检查|第\s*\d+\s*帧|时间线|抓包|日志|"
    r"帧|包|节点|范围|PAN|网段|入网|离线|掉线|收不到|失败)")

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
    has_scope = bool(_SCOPE_WORDS.search(m))
    is_kb_lead = bool(_KB_LEAD.match(m))
    # 4 位 hex (0x838D 这类短地址/PAN 是分析对象的强信号)
    if has_addr:
        return "analyze"
    # 时间窗 (10:00-10:30) 是范围强信号
    if has_time:
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


class ConfigRequest(BaseModel):
    provider: str = "anthropic"   # anthropic / openai / deepseek
    api_key: str = ""
    mcp_token: str = ""           # 可选: 芯科 MCP Bearer token (留空自动发现本机凭证)


@router.post("/ai/chat")
async def ai_chat(req: ChatRequest):
    """统一对话入口 — 意图分流:
    - 纯知识问题 → 芯科 MCP 检索结果
    - 含范围/包关键词 → 分析意图 (阶段二实现; 阶段一返回引导文案, 不臆测)
    """
    message = req.message.strip()
    if not message:
        return JSONResponse({"error": "消息不能为空"}, 400)
    intent = detect_intent(message)
    if intent == "kb":
        from .. import ai_kb
        return {"type": "kb", "query": message, **ai_kb.search_kb(message)}
    # analyze (阶段二): 范围解析 + 取数摘要 + LLM 对话 — 界面先行, 当前引导
    return {"type": "analyze", "message": "对话式分析（范围解析 → 取数摘要 → LLM 回答）将在阶段二上线；"
                                          "当前可先用知识检索，例如：什么是 end device？"}


@router.get("/ai/kb")
async def ai_kb_search(q: str = ""):
    """知识检索快捷端点 (侧边栏知识 Tab 直接搜索)."""
    q = q.strip()
    if not q:
        return JSONResponse({"error": "参数 q 不能为空"}, 400)
    from .. import ai_kb
    return {"type": "kb", "query": q, **ai_kb.search_kb(q)}


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
