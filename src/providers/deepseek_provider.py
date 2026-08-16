"""DeepSeek provider adapter (OpenAI-compatible API).

deepseek-v4-flash is a single checkpoint with thinking mode ON by default
(https://api-docs.deepseek.com/guides/thinking_mode/) -- unlike the older
deepseek-chat/deepseek-reasoner split, there's no non-reasoning checkpoint to
pick instead. Reasoning is disabled only by the extra_body field below.
"""

from . import _openai_compatible

BASE_URL = "https://api.deepseek.com"

REASONING_DISABLE_BODY = {"thinking": {"type": "disabled"}}


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    extra_body = REASONING_DISABLE_BODY if not reasoning_enabled else None
    return _openai_compatible.call(
        "deepseek",
        BASE_URL,
        api_id,
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_enabled=reasoning_enabled,
        api_key=api_key,
        reasoning_disabled_by="api_parameter",
        extra_body=extra_body,
    )
