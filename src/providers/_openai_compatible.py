"""Shared call logic for OpenAI-compatible chat completion APIs (OpenAI, DeepSeek, Together)."""

import time

from .base import ProviderError, ProviderResponse

_warned_providers = set()


def call(provider_name, base_url, api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    try:
        import openai
    except ImportError as exc:
        raise ProviderError(f"openai package not installed: {exc}", retryable=False)

    client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)

    kwargs = dict(
        model=api_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if not reasoning_enabled and provider_name == "openai":
        # Reasoning-capable OpenAI models expose `reasoning_effort`; pin it to
        # "minimal" so reasoning stays off (or point config.py at a
        # non-reasoning model, e.g. gpt-4o, if "minimal" isn't low enough).
        kwargs["reasoning_effort"] = "minimal"
    elif reasoning_enabled and provider_name != "openai":
        # DeepSeek and Together have no reasoning_effort-style toggle here:
        # DeepSeek is disabled by choosing the deepseek-chat model id rather
        # than deepseek-reasoner, and Together by choosing a non-reasoning
        # model. Neither can be turned *on* through this adapter, so fail
        # loudly instead of silently ignoring the request.
        raise ProviderError(
            f"{provider_name} adapter has no reasoning toggle; reasoning must stay disabled via model choice",
            retryable=False,
        )

    start = time.monotonic()
    try:
        response = client.chat.completions.create(**kwargs)
    except openai.RateLimitError as exc:
        raise ProviderError(str(exc), retryable=True, status_code=429) from exc
    except openai.APIStatusError as exc:
        retryable = exc.status_code in (429, 500, 502, 503, 504)
        raise ProviderError(str(exc), retryable=retryable, status_code=exc.status_code) from exc
    except openai.APIConnectionError as exc:
        raise ProviderError(str(exc), retryable=True) from exc
    latency_ms = int(round((time.monotonic() - start) * 1000))

    choice = response.choices[0]
    usage = response.usage
    reasoning_tokens = None
    details = getattr(usage, "completion_tokens_details", None)
    if details is not None:
        reasoning_tokens = getattr(details, "reasoning_tokens", None)
    if reasoning_tokens is None and provider_name not in _warned_providers:
        print(f"[warn] {provider_name}: reasoning_tokens not exposed by API, logging as null")
        _warned_providers.add(provider_name)

    return ProviderResponse(
        text=choice.message.content or "",
        finish_reason=choice.finish_reason,
        input_tokens=usage.prompt_tokens if usage else None,
        output_tokens=usage.completion_tokens if usage else None,
        reasoning_tokens=reasoning_tokens,
        latency_ms=latency_ms,
    )
