"""Shared types every provider adapter uses: the normalized response and the error contract."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderResponse:
    text: str
    finish_reason: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    reasoning_tokens: Optional[int]
    latency_ms: int


class ProviderError(Exception):
    """Raised by adapters on any API failure. `retryable` drives the runner's backoff loop."""

    def __init__(self, message, *, retryable, status_code=None):
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
