"""Together AI provider adapter (OpenAI-compatible API)."""

from . import _openai_compatible

BASE_URL = "https://api.together.xyz/v1"

# Most Together models are disabled by picking a non-reasoning checkpoint (e.g.
# Qwen3-235B-A22B-Instruct-2507 instead of the -Thinking variant). GLM-5.2 is an
# exception: it's a single checkpoint with thinking ON by default, toggled only
# via this extra body field (https://docs.together.ai/docs/glm-5.2-quickstart).
# Add a model here only if it actually needs this -- everything else should be
# disabled by model choice, not by a parameter.
REASONING_DISABLE_BODY = {
    "zai-org/GLM-5.2": {"reasoning": {"enabled": False}},
}

# Together api_ids known to have a separate reasoning-capable sibling checkpoint
# (e.g. Qwen3-235B-A22B-Instruct-2507 vs the -Thinking-2507 variant), so picking
# this one is a deliberate "model_choice" disable. An api_id in neither this set
# nor REASONING_DISABLE_BODY is assumed to have no reasoning capability at all
# ("not_supported") -- e.g. Llama-3.3-70B-Instruct-Turbo, a plain instruct model.
MODEL_CHOICE_DISABLE = {
    "Qwen/Qwen3-235B-A22B-Instruct-2507-tput",
}


def reasoning_disabled_by_for(api_id):
    if api_id in REASONING_DISABLE_BODY:
        return "api_parameter"
    if api_id in MODEL_CHOICE_DISABLE:
        return "model_choice"
    return "not_supported"


def call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    extra_body = REASONING_DISABLE_BODY.get(api_id) if not reasoning_enabled else None
    return _openai_compatible.call(
        "together",
        BASE_URL,
        api_id,
        messages,
        max_tokens=max_tokens,
        temperature=temperature,
        reasoning_enabled=reasoning_enabled,
        api_key=api_key,
        reasoning_disabled_by=reasoning_disabled_by_for(api_id),
        extra_body=extra_body,
    )
