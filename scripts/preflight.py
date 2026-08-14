"""Preflight check: one real call per configured model, proving max_tokens and reasoning-disable
actually took effect before spending real money on a pilot or main run.

Run once before the pilot and once before the main run:
    python scripts/preflight.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONFIG  # noqa: E402
from src.providers import get_adapter  # noqa: E402

# Uses the largest per-level cap so a truncation or reasoning leak is most
# likely to show up here rather than surfacing for the first time mid-run.
PREFLIGHT_LEVEL = 0

PREFLIGHT_MESSAGES = [
    {
        "role": "user",
        "content": (
            "Write as long and detailed an answer as you can about the history "
            "of the printing press. Keep going until you are cut off."
        ),
    }
]

COLUMNS = ["model", "max_tokens_set", "output_tokens", "reasoning_tokens", "finish_reason", "temperature", "latency_ms"]


def print_table(rows):
    widths = {c: len(c) for c in COLUMNS}
    for row in rows:
        for c in COLUMNS:
            widths[c] = max(widths[c], len(str(row[c])))

    header = "  ".join(c.ljust(widths[c]) for c in COLUMNS)
    print(header)
    print("  ".join("-" * widths[c] for c in COLUMNS))
    for row in rows:
        print("  ".join(str(row[c]).ljust(widths[c]) for c in COLUMNS))


def run_preflight():
    temperature = CONFIG["temperature"]
    assert temperature != 0, "temperature must never be 0 in the run path"
    max_tokens = CONFIG["max_tokens_by_level"][PREFLIGHT_LEVEL]
    reasoning_enabled = CONFIG["reasoning_enabled"]

    rows = []
    failures = []

    for model in CONFIG["models"]:
        name = model["name"]
        provider = model["provider"]
        api_key = CONFIG["api_keys"].get(provider)
        if not api_key:
            print(f"[skip] {name} ({provider}): no API key set in environment")
            failures.append(f"{name}: no API key set, could not preflight")
            continue

        adapter = get_adapter(provider)
        print(f"calling {name} ({provider})...")
        try:
            result = adapter(
                model["api_id"],
                PREFLIGHT_MESSAGES,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_enabled=reasoning_enabled,
                api_key=api_key,
            )
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failures.append(f"{name}: call failed ({exc})")
            continue

        row = {
            "model": name,
            "max_tokens_set": max_tokens,
            "output_tokens": result.output_tokens,
            "reasoning_tokens": result.reasoning_tokens,
            "finish_reason": result.finish_reason,
            "temperature": temperature,
            "latency_ms": result.latency_ms,
        }
        rows.append(row)

        if result.reasoning_tokens:
            failures.append(f"{name}: returned reasoning_tokens={result.reasoning_tokens} despite reasoning disabled")
        if result.output_tokens is not None and result.output_tokens > max_tokens:
            failures.append(f"{name}: output_tokens={result.output_tokens} exceeds max_tokens_set={max_tokens}")

    print()
    if rows:
        print_table(rows)
    else:
        print("no successful calls")

    if failures:
        print("\nPREFLIGHT FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nPREFLIGHT PASSED: max_tokens cap and reasoning-disable confirmed for every model")
    return 0


if __name__ == "__main__":
    sys.exit(run_preflight())
