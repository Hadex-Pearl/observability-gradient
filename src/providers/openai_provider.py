"""OpenAI provider adapter."""

from . import _openai_compatible


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    return _openai_compatible.call(
        "openai",
        None,
        api_id,
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_enabled=reasoning_enabled,
        api_key=api_key,
    )
