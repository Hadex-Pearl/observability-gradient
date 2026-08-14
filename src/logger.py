"""Append-only JSONL logger for run rows, schema validation, and running cost tracking."""

import json
import os
import threading

SCHEMA_FIELDS = [
    "run_id",
    "model",
    "provider",
    "item_id",
    "level",
    "arm",
    "run_index",
    "presentation_order",
    "prompt_hash",
    "messages",
    "raw_output",
    "finish_reason",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "max_tokens_set",
    "reasoning_enabled",
    "temperature",
    "latency_ms",
    "timestamp_utc",
    "error",
]

CELL_KEY_FIELDS = ("model", "item_id", "level", "arm", "run_index")


class SchemaError(ValueError):
    pass


def validate_row(row):
    missing = [f for f in SCHEMA_FIELDS if f not in row]
    if missing:
        raise SchemaError(f"row missing required fields: {missing}")
    return row


def cell_key(row):
    return tuple(row[f] for f in CELL_KEY_FIELDS)


class JsonlLogger:
    """Append-only JSONL writer. Every row is validated, written, and flushed to disk immediately."""

    def __init__(self, path):
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._fh = open(path, "a", buffering=1)
        self._lock = threading.Lock()

    def append(self, row):
        validate_row(row)
        with self._lock:
            self._fh.write(json.dumps(row) + "\n")
            self._fh.flush()
            os.fsync(self._fh.fileno())

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def read_rows(path):
    if not os.path.exists(path):
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_completed_keys(path):
    """Cell keys with at least one successful (error is None) row. Error-only keys are retried."""
    completed = set()
    for row in read_rows(path):
        if row.get("error") is None:
            completed.add(cell_key(row))
    return completed


class CostTracker:
    """Accumulates spend from row token counts using per-model $/million rates."""

    def __init__(self, rates_by_model, ceiling_usd=None):
        self.rates = rates_by_model
        self.ceiling_usd = ceiling_usd
        self.total_usd = 0.0
        self._since_batch_print = 0

    def add(self, model, input_tokens, output_tokens, reasoning_tokens=None):
        rates = self.rates.get(model)
        if rates is None:
            return 0.0
        in_tok = input_tokens or 0
        out_tok = (output_tokens or 0) + (reasoning_tokens or 0)
        cost = (in_tok / 1_000_000) * rates["price_per_million_in"] + (out_tok / 1_000_000) * rates["price_per_million_out"]
        self.total_usd += cost
        self._since_batch_print += 1
        return cost

    def exceeded_ceiling(self):
        return self.ceiling_usd is not None and self.total_usd >= self.ceiling_usd

    def print_batch(self, batch_size=10):
        if self._since_batch_print >= batch_size:
            print(f"[cost] running total: ${self.total_usd:.4f}")
            self._since_batch_print = 0

    def print_summary(self):
        ceiling = "none" if self.ceiling_usd is None else f"${self.ceiling_usd:.2f}"
        print(f"[cost] FINAL total: ${self.total_usd:.4f} (ceiling {ceiling})")
