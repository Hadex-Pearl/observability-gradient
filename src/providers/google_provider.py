"""Google Gemini provider adapter."""

import time

from .base import ProviderError, ProviderResponse

_warned_reasoning_tokens = False


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    global _warned_reasoning_tokens
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise ProviderError(f"google-genai package not installed: {exc}", retryable=False)

    client = genai.Client(api_key=api_key)

    system = None
    contents = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        system_instruction=system,
        thinking_config=None if reasoning_enabled else types.ThinkingConfig(thinking_budget=0),
    )

    start = time.monotonic()
    try:
        response = client.models.generate_content(model=api_id, contents=contents, config=config)
    except Exception as exc:
        # google-genai's exception hierarchy varies by version; treat
        # anything without a clearly non-retryable status as retryable.
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        retryable = status_code is None or status_code in (429, 500, 502, 503, 504)
        raise ProviderError(str(exc), retryable=retryable, status_code=status_code) from exc
    latency_ms = int(round((time.monotonic() - start) * 1000))

    usage = response.usage_metadata
    reasoning_tokens = getattr(usage, "thoughts_token_count", None) if usage else None
    if reasoning_tokens is None and not _warned_reasoning_tokens:
        print("[warn] google: reasoning_tokens not exposed by the API, logging as null")
        _warned_reasoning_tokens = True

    finish_reason = None
    if response.candidates:
        finish_reason = getattr(response.candidates[0], "finish_reason", None)
        finish_reason = getattr(finish_reason, "name", finish_reason)

    return ProviderResponse(
        text=response.text or "",
        finish_reason=finish_reason,
        input_tokens=usage.prompt_token_count if usage else None,
        output_tokens=usage.candidates_token_count if usage else None,
        reasoning_tokens=reasoning_tokens,
        latency_ms=latency_ms,
        # thinking_budget=0 is a request-time parameter on this same
        # checkpoint -- there's no separate non-thinking Gemini model.
        reasoning_disabled_by="api_parameter",
    )
