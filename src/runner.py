"""Resumable run harness: throttles, retries, logs, and cost-tracks calls to provider adapters."""

import hashlib
import json
import random
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from src.logger import CostTracker, JsonlLogger, is_truncated, load_completed_keys, read_rows
from src.providers import get_adapter

BACKOFF_BASE_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 60.0
MAX_RETRIES = 5


class ReasoningLeakError(RuntimeError):
    """Raised when a provider returns reasoning_tokens despite reasoning being disabled.

    This is a configuration failure, not a transient API error: it means every
    call to this provider may be silently billing for invisible reasoning, so
    the run halts immediately rather than retrying or logging-and-continuing.
    """


def prompt_hash(messages):
    canonical = json.dumps(messages, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class RateLimiter:
    """Sliding-window per-minute request throttle. rpm_limit=None means unthrottled."""

    def __init__(self, rpm_limit):
        self.rpm_limit = rpm_limit
        self._timestamps = deque()

    def wait(self):
        if not self.rpm_limit:
            return
        now = time.monotonic()
        while self._timestamps and now - self._timestamps[0] > 60:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.rpm_limit:
            sleep_for = 60 - (now - self._timestamps[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._timestamps.append(time.monotonic())


class DailyCapTracker:
    """Per-model daily request cap, seeded by counting today's rows already in the log."""

    def __init__(self, log_path, caps_by_model):
        self.caps = caps_by_model
        self.counts = defaultdict(int)
        today = datetime.now(timezone.utc).date().isoformat()
        for row in read_rows(log_path):
            if row.get("timestamp_utc", "").startswith(today):
                self.counts[row["model"]] += 1

    def can_call(self, model):
        cap = self.caps.get(model)
        return cap is None or self.counts[model] < cap

    def record(self, model):
        self.counts[model] += 1


def backoff_sleep(attempt):
    delay = min(BACKOFF_BASE_SECONDS * (2 ** attempt), BACKOFF_MAX_SECONDS)
    time.sleep(delay * (0.5 + random.random()))


def call_with_retries(provider_fn, api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
    """Never raises. Returns (ProviderResponse, None) on success or (None, exception) after exhausting retries."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            result = provider_fn(
                api_id,
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_enabled=reasoning_enabled,
                api_key=api_key,
            )
            return result, None
        except Exception as exc:  # noqa: BLE001 - adapters raise ProviderError; anything else must still not kill the loop
            last_error = exc
            retryable = getattr(exc, "retryable", False)
            if not retryable or attempt == MAX_RETRIES - 1:
                break
            backoff_sleep(attempt)
    return None, last_error


def error_to_dict(exc):
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "status_code": getattr(exc, "status_code", None),
        "retryable": getattr(exc, "retryable", None),
    }


class RunHarness:
    """Resumable driver over experiment cells. One instance per log file / run process."""

    def __init__(self, run_id, log_path, model_configs, cost_ceiling_usd=None):
        """model_configs: dict[model_name] -> {provider, api_id, rpm_limit, daily_request_cap,
        price_per_million_in, price_per_million_out}, keyed by the name written to row["model"]."""
        self.run_id = run_id
        self.log_path = log_path
        self.model_configs = model_configs
        self.logger = JsonlLogger(log_path)
        self.completed = load_completed_keys(log_path)
        self.rate_limiters = {m: RateLimiter(cfg["rpm_limit"]) for m, cfg in model_configs.items()}
        self.daily_caps = DailyCapTracker(log_path, {m: cfg["daily_request_cap"] for m, cfg in model_configs.items()})
        rates = {
            m: {"price_per_million_in": cfg["price_per_million_in"], "price_per_million_out": cfg["price_per_million_out"]}
            for m, cfg in model_configs.items()
        }
        self.cost_tracker = CostTracker(rates, ceiling_usd=cost_ceiling_usd)
        self.halted = False

    def run_cell(
        self,
        *,
        model,
        item_id,
        level,
        arm,
        run_index,
        presentation_order,
        messages,
        max_tokens,
        temperature,
        reasoning_enabled,
        api_key,
    ):
        """Executes one cell if not already completed. Returns a status string.

        Never raises for API/network failures — those become error rows. Does
        raise ReasoningLeakError if a provider returns reasoning tokens
        despite reasoning being disabled, since that is a fatal
        misconfiguration rather than a call-level failure.
        """
        assert temperature != 0, "temperature must never be 0 in the run path"
        key = (model, item_id, level, arm, run_index)
        if key in self.completed:
            return "skipped"
        if self.halted:
            return "halted"

        cfg = self.model_configs[model]
        if not self.daily_caps.can_call(model):
            print(f"[cap] {model} hit its daily request cap, skipping remaining calls for today")
            return "capped"

        self.rate_limiters[model].wait()
        adapter = get_adapter(cfg["provider"])

        result, error = call_with_retries(
            adapter,
            cfg["api_id"],
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            reasoning_enabled=reasoning_enabled,
            api_key=api_key,
        )
        self.daily_caps.record(model)

        row = {
            "run_id": self.run_id,
            "model": model,
            "provider": cfg["provider"],
            "item_id": item_id,
            "level": level,
            "arm": arm,
            "run_index": run_index,
            "presentation_order": presentation_order,
            "prompt_hash": prompt_hash(messages),
            "messages": messages,
            "raw_output": None,
            "finish_reason": None,
            "truncated": None,
            "input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "max_tokens_set": max_tokens,
            "reasoning_enabled": reasoning_enabled,
            "temperature": temperature,
            "latency_ms": None,
            "timestamp_utc": now_iso(),
            "error": None,
        }

        if error is not None:
            row["error"] = error_to_dict(error)
            self.logger.append(row)
            print(f"[error] {model} {item_id} level={level} arm={arm} run={run_index}: {row['error']['message']}")
            return "error"

        row["raw_output"] = result.text
        row["finish_reason"] = result.finish_reason
        row["truncated"] = is_truncated(result.finish_reason)
        row["input_tokens"] = result.input_tokens
        row["output_tokens"] = result.output_tokens
        row["reasoning_tokens"] = result.reasoning_tokens
        row["latency_ms"] = result.latency_ms
        self.logger.append(row)
        self.completed.add(key)

        self.cost_tracker.add(model, result.input_tokens, result.output_tokens, result.reasoning_tokens)
        self.cost_tracker.print_batch()
        if self.cost_tracker.exceeded_ceiling():
            self.halted = True
            self.cost_tracker.print_summary()
            print("[halt] spend ceiling crossed, halting run")

        if result.reasoning_tokens:
            self.halted = True
            raise ReasoningLeakError(
                f"{model} returned reasoning_tokens={result.reasoning_tokens} on {item_id}/level={level}/"
                f"{arm}/run={run_index} despite reasoning_enabled=False; halting run"
            )

        return "ok"

    def close(self):
        self.logger.close()
