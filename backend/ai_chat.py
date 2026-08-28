"""LLM 对话兼容层 (U17 阶段二) — Anthropic / OpenAI / DeepSeek 统一流式接口.

key 安全 (用户约束 08-25): key 仅本地配置 (ai_config.json / 环境变量), 不入 git/分发包.
无 key / 提供商调用失败 → 抛 LLMError, 由 API 层转为可读提示 (不崩).
"""
from __future__ import annotations

import os

SYSTEM_PROMPT = """你是 Zigbee 抓包分析助手, 精通 IEEE 802.15.4 / Zigbee 3.0 协议
(Zigbee PRO: 入网/密钥分发/路由/APS 重传/MTORR/源路由), 熟悉 Silicon Labs
EmberZNet 与 Telink TLS8258 生态. 回答基于用户提供的抓包范围摘要与对话历史,
使用中文, 简洁准确; 涉及协议机制必须引用官方文档语义 (如 Zigbee R23 规范/
Silicon Labs UG 文档), 不确定的明确标注"不确定", 不编造帧号或计数.
用户可能引用帧号 (如"第 352 帧"), 引用时用"第 N 帧"格式便于定位. 术语
参考: 0x0B=源路由失败(Source Route Failure) / 0x0C=MTORR 失败 /
0x06=间接事务过期, APS Ack, SED 轮询, TC link key 等.

**分析纪律 (08-26 用户反馈强化):**
1. 必须**逐条通读关键事件列表再下结论**, 特别关注异常帧: Leave (含 rejoin/request
   标志) / Network Status (0x0B/0x0C/0x06) / Rejoin / TransportKey / Remove Device /
   Default Response — 设备入网后立即 Leave 或多次 Leave-Rejoin 是常见真实异常
2. 摘要中未出现的事件**不得臆断其不存在** (摘要可能截断); 明确说明"摘要未见该帧"
3. 结论分级: 有证据 → 明确; 无证据 → "无法判定"; 禁止过度自信的"完全成功/正常"
4. 引用帧号必须来自摘要中的帧号"""


class LLMError(Exception):
    """LLM 调用失败 (无 key/网络/额度/参数) — message 为人类可读提示."""


# T2 (2026-08-29): 路径统一走 config.AI_CONFIG_PATH —
# 打包后 = %APPDATA%\zigbee-analyzer\ai_config.json (数据分层), 开发模式 = 工程根
from . import config as _cfg
CONFIG_PATH = _cfg.AI_CONFIG_PATH


def _load_config() -> dict:
    try:
        import json
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_key(provider: str) -> str | None:
    """key 解析: ai_config.json → 环境变量 (ANTHROPIC_API_KEY 等)."""
    cfg = _load_config()
    if cfg.get("provider") == provider and cfg.get("api_key"):
        return cfg["api_key"]
    env = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
           "deepseek": "DEEPSEEK_API_KEY"}.get(provider)
    if env:
        return os.environ.get(env)
    return None


def load_provider() -> str | None:
    """已配置 key 的提供商 (无 key → None). 按配置 provider 检测."""
    cfg = _load_config()
    p = cfg.get("provider")
    if p and cfg.get("api_key"):
        return p
    if p and os.environ.get({"anthropic": "ANTHROPIC_API_KEY",
                             "openai": "OPENAI_API_KEY",
                             "deepseek": "DEEPSEEK_API_KEY"}.get(p, "")):
        return p
    for p in ("anthropic", "openai", "deepseek"):
        if _load_key(p):
            return p
    return None


def _api_style(provider: str, cfg: dict) -> str:
    """API 兼容风格: 显式配置 api_style 优先 (deepseek 也可走 Anthropic 兼容端点,
    如 https://api.deepseek.com/anthropic), 默认按 provider."""
    s = (cfg.get("api_style") or "").strip()
    if s in ("anthropic", "openai"):
        return s
    return "anthropic" if provider == "anthropic" else "openai"


# 默认模型 (ai_config.json 可覆盖)
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
}


def stream_chat(provider: str, messages: list[dict], on_chunk) -> str:
    """流式对话 (统一接口): messages = [{role: system/user/assistant, content}],
    on_chunk(text) 每块回调; 返回完整文本.

    provider: anthropic / openai / deepseek (OpenAI 兼容).
    失败抛 LLMError(可读提示), 不吞异常.
    """
    api_key = _load_key(provider)
    if not api_key:
        raise LLMError("未配置 LLM API Key — 请在 AI 助手「设置」中填写 (仅存本地)")
    cfg = _load_config()
    model = (cfg.get("model") or "").strip() or DEFAULT_MODELS.get(provider)
    base_url = (cfg.get("base_url") or "").strip() or None
    style = _api_style(provider, cfg)

    full: list[str] = []
    if style == "anthropic":
        # Anthropic 风格 (anthropic 官方或 Anthropic 兼容端点, 如 deepseek 的 /anthropic)
        import anthropic
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = anthropic.Anthropic(**kwargs)
        msgs = [m for m in messages if m["role"] != "system"]
        if not msgs:
            # 端点要求至少 1 条消息 (实测 DeepSeek /anthropic 空 messages → 400)
            msgs = [{"role": "user", "content": "请基于抓包范围摘要分析。"}]
        with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=messages[0]["content"] if messages and messages[0]["role"] == "system" else SYSTEM_PROMPT,
                messages=msgs,
        ) as stream:
            for text in stream.text_stream:
                full.append(text)
                on_chunk(text)
        return "".join(full)

    # OpenAI 风格 (openai / deepseek openai 端点)
    import openai
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    elif provider == "deepseek":
        kwargs["base_url"] = "https://api.deepseek.com"
    client = openai.OpenAI(**kwargs)
    stream = client.chat.completions.create(
        model=model,
        messages=messages or [{"role": "user", "content": "你好"}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            full.append(delta)
            on_chunk(delta)
    return "".join(full)
