"""DeepSeek provider adapter (OpenAI-compatible API). Uses deepseek-chat, not deepseek-reasoner, to keep reasoning off."""

from . import _openai_compatible

BASE_URL = "https://api.deepseek.com"


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    return _openai_compatible.call(
        "deepseek",
        BASE_URL,
        api_id,
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_enabled=reasoning_enabled,
        api_key=api_key,
    )
