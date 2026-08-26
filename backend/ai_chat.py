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
0x06=间接事务过期, APS Ack, SED 轮询, TC link key 等."""


class LLMError(Exception):
    """LLM 调用失败 (无 key/网络/额度/参数) — message 为人类可读提示."""


def _load_key(provider: str) -> str | None:
    """key 解析: ai_config.json → 环境变量 (ANTHROPIC_API_KEY 等)."""
    try:
        import json
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "ai_config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("provider") == provider and cfg.get("api_key"):
            return cfg["api_key"]
    except Exception:
        pass
    env = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
           "deepseek": "DEEPSEEK_API_KEY"}.get(provider)
    if env:
        return os.environ.get(env)
    return None


def load_provider() -> str | None:
    """已配置 key 的提供商 (无 key → None). 按配置 provider 检测."""
    try:
        import json
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "ai_config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        p = cfg.get("provider")
        if p and cfg.get("api_key"):
            return p
        if p and os.environ.get({"anthropic": "ANTHROPIC_API_KEY",
                                 "openai": "OPENAI_API_KEY",
                                 "deepseek": "DEEPSEEK_API_KEY"}.get(p, "")):
            return p
    except Exception:
        pass
    for p in ("anthropic", "openai", "deepseek"):
        if _load_key(p):
            return p
    return None


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
    try:
        import json
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "ai_config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        model = (cfg.get("model") or "").strip() or DEFAULT_MODELS.get(provider)
    except Exception:
        model = DEFAULT_MODELS.get(provider)

    full: list[str] = []
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
                model=model,
                max_tokens=2048,
                system=messages[0]["content"] if messages and messages[0]["role"] == "system" else SYSTEM_PROMPT,
                messages=[m for m in messages if m["role"] != "system"],
        ) as stream:
            for text in stream.text_stream:
                full.append(text)
                on_chunk(text)
        return "".join(full)

    # OpenAI 兼容 (openai / deepseek)
    import openai
    kwargs = {"api_key": api_key}
    if provider == "deepseek":
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
