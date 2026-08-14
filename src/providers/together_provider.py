"""Together AI provider adapter (OpenAI-compatible API)."""

from . import _openai_compatible

BASE_URL = "https://api.together.xyz/v1"


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    return _openai_compatible.call(
        "together",
        BASE_URL,
        api_id,
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_enabled=reasoning_enabled,
        api_key=api_key,
    )
