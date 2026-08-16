"""Shared types every provider adapter uses: the normalized response and the error contract."""

from dataclasses import dataclass
from typing import Optional

# How this call's reasoning was kept off, so a run can show the mechanism, not
# just the outcome:
#   "model_choice"   -- a non-reasoning checkpoint was chosen (a reasoning-capable
#                        sibling checkpoint exists, e.g. deepseek-chat vs
#                        deepseek-reasoner, Qwen3 Instruct vs Thinking).
#   "api_parameter"  -- same checkpoint; reasoning is toggled by a request
#                        parameter (Anthropic/Google/OpenAI's request-time
#                        toggle, or Together's GLM-5.2, which defaults to
#                        reasoning ON and needs the parameter to turn it off).
#   "not_supported"  -- the checkpoint has no reasoning capability at all, so
#                        there is nothing to disable (e.g. Llama-3.3-70B-Instruct).
REASONING_DISABLED_BY_VALUES = ("model_choice", "api_parameter", "not_supported")


@dataclass
class ProviderResponse:
    text: str
    finish_reason: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    reasoning_tokens: Optional[int]
    latency_ms: int
    reasoning_disabled_by: str

    def __post_init__(self):
        if self.reasoning_disabled_by not in REASONING_DISABLED_BY_VALUES:
            raise ValueError(
                f"reasoning_disabled_by must be one of {REASONING_DISABLED_BY_VALUES}, "
                f"got {self.reasoning_disabled_by!r}"
            )


class ProviderError(Exception):
    """Raised by adapters on any API failure. `retryable` drives the runner's backoff loop."""

    def __init__(self, message, *, retryable, status_code=None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
