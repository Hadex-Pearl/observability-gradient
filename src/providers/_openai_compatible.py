"""Shared call logic for OpenAI-compatible chat completion APIs (OpenAI, DeepSeek, Together)."""

import time

from .base import ProviderError, ProviderResponse

_warned_providers = set()


def call(
    provider_name,
    base_url,
    api_id,
    messages,
    *,
    max_tokens,
    temperature,
    reasoning_enabled,
    api_key,
    reasoning_disabled_by,
    extra_body=None,
):
    try:
        import openai
    except ImportError as exc:
        raise ProviderError(f"openai package not installed: {exc}", retryable=False)

    client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)

    kwargs = dict(
        model=api_id,
        messages=messages,
        temperature=temperature,
    )
    if provider_name == "openai":
        # OpenAI's newer chat-completions models (the reasoning-capable
        # families, including gpt-5.4-nano) reject `max_tokens` outright and
        # require `max_completion_tokens` instead (confirmed live: gpt-5 -- the
        # study model this replaced -- returned a 400 until this was fixed).
        # DeepSeek and Together's OpenAI-compatible endpoints still use `max_tokens`.
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
    if extra_body:
        # Provider/model-specific fields with no place in the standard schema,
        # e.g. Together's GLM-5.2 reasoning toggle (see together_provider.py).
        kwargs["extra_body"] = extra_body
    if not reasoning_enabled and provider_name == "openai":
        # gpt-5.4-nano (and the newer reasoning-capable OpenAI family generally)
        # expose `reasoning_effort`; "none" genuinely disables reasoning, unlike
        # "minimal", which was tried first and still consumed an entire response
        # budget on reasoning_tokens with zero visible output (verified against
        # a live gpt-5 preflight call before this model was replaced).
        kwargs["reasoning_effort"] = "none"
    elif reasoning_enabled and provider_name != "openai":
        # DeepSeek and Together have no reasoning_effort-style toggle here:
        # each is disabled either by model choice or by an extra_body field the
        # specific provider module computes (see reasoning_disabled_by_for() in
        # together_provider.py and deepseek_provider.py). Neither can be turned
        # *on* through this adapter, so fail loudly instead of silently
        # ignoring the request.
        raise ProviderError(
            f"{provider_name} adapter has no reasoning toggle; reasoning must stay disabled",
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
        reasoning_disabled_by=reasoning_disabled_by,
    )
