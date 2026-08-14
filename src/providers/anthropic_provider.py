"""Anthropic (Claude) provider adapter."""

import time

from .base import ProviderError, ProviderResponse

_warned_reasoning_tokens = False


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    global _warned_reasoning_tokens
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(f"anthropic package not installed: {exc}", retryable=False)

    client = anthropic.Anthropic(api_key=api_key)

    system = None
    chat_messages = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            chat_messages.append({"role": m["role"], "content": m["content"]})

    kwargs = dict(model=api_id, max_tokens=max_tokens, temperature=temperature, messages=chat_messages)
    if system is not None:
        kwargs["system"] = system
    # Extended thinking is opt-in via the `thinking` param; simply omitting it
    # keeps reasoning off. `reasoning_enabled` is accepted for interface
    # symmetry with the other adapters and recorded on the row by the caller.
    del reasoning_enabled

    start = time.monotonic()
    try:
        response = client.messages.create(**kwargs)
    except anthropic.RateLimitError as exc:
        raise ProviderError(str(exc), retryable=True, status_code=429) from exc
    except anthropic.APIStatusError as exc:
        retryable = exc.status_code in (429, 500, 502, 503, 504)
        raise ProviderError(str(exc), retryable=retryable, status_code=exc.status_code) from exc
    except anthropic.APIConnectionError as exc:
        raise ProviderError(str(exc), retryable=True) from exc
    latency_ms = int(round((time.monotonic() - start) * 1000))

    text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")

    if not _warned_reasoning_tokens:
        print("[warn] anthropic: reasoning_tokens not exposed by the API, logging as null")
        _warned_reasoning_tokens = True

    return ProviderResponse(
        text=text,
        finish_reason=response.stop_reason,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        reasoning_tokens=None,
        latency_ms=latency_ms,
    )
