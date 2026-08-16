"""Preflight check: one real call per model, proving max_tokens and reasoning-disable actually
took effect before spending real money on a pilot or main run.

Without --confirm, only TEST_MODEL (the free tier) is called — safe to run any time. With
--confirm, every paid model in EXPERIMENT_MODELS is called too; the script prints which paid
models and the approximate cost before doing so. This is the one script in the repo allowed to
call paid models directly, since checking every configured model is its entire job.

Run once before the pilot and once before the main run:
    python scripts/preflight.py --confirm
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (  # noqa: E402
    CONFIG,
    EXPERIMENT_MODELS,
    TEST_MODEL,
    MissingAPIKeyError,
    assert_api_keys_present,
    get_api_key,
    models_by_name,
)
from src.logger import JsonlLogger  # noqa: E402
from src.providers import get_adapter  # noqa: E402
from src.runner import RateLimiter, prompt_hash, now_iso, require_daily_budget  # noqa: E402

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

COLUMNS = [
    "model",
    "max_tokens_set",
    "output_tokens",
    "reasoning_tokens",
    "reasoning_disabled_by",
    "finish_reason",
    "temperature",
    "latency_ms",
]


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


def estimate_cost(cfg, max_tokens):
    est_input_tokens = 30  # PREFLIGHT_MESSAGES is short
    return est_input_tokens / 1_000_000 * cfg["price_per_million_in"] + max_tokens / 1_000_000 * cfg["price_per_million_out"]


def call_one(name, cfg, *, max_tokens, temperature, reasoning_enabled, logger, run_id, call_context):
    api_key = get_api_key(cfg["provider"])
    if not api_key:
        print(f"[skip] {name} ({cfg['provider']}): no API key set in environment")
        return None, f"{name}: no API key set, could not preflight"

    RateLimiter(cfg["rpm_limit"]).wait()
    adapter = get_adapter(cfg["provider"])
    print(f"calling {name} ({cfg['provider']})...")
    try:
        result = adapter(
            cfg["api_id"],
            PREFLIGHT_MESSAGES,
            max_tokens=max_tokens,
            temperature=temperature,
            reasoning_enabled=reasoning_enabled,
            api_key=api_key,
        )
    except Exception as exc:
        print(f"  FAILED: {exc}")
        return None, f"{name}: call failed ({exc})"

    if logger is not None:
        logger.append(
            {
                "run_id": run_id,
                "call_context": call_context,
                "model": name,
                "provider": cfg["provider"],
                "item_id": "preflight",
                "level": PREFLIGHT_LEVEL,
                "arm": "preflight",
                "run_index": 0,
                "presentation_order": None,
                "prompt_hash": prompt_hash(PREFLIGHT_MESSAGES),
                "messages": PREFLIGHT_MESSAGES,
                "raw_output": result.text,
                "finish_reason": result.finish_reason,
                "truncated": result.output_tokens is not None and result.output_tokens >= max_tokens,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "reasoning_tokens": result.reasoning_tokens,
                "reasoning_disabled_by": result.reasoning_disabled_by,
                "max_tokens_set": max_tokens,
                "reasoning_enabled": reasoning_enabled,
                "temperature": temperature,
                "latency_ms": result.latency_ms,
                "timestamp_utc": now_iso(),
                "error": None,
            }
        )

    row = {
        "model": name,
        "max_tokens_set": max_tokens,
        "output_tokens": result.output_tokens,
        "reasoning_tokens": result.reasoning_tokens,
        "reasoning_disabled_by": result.reasoning_disabled_by,
        "finish_reason": result.finish_reason,
        "temperature": temperature,
        "latency_ms": result.latency_ms,
    }

    failure = None
    if result.reasoning_tokens:
        failure = f"{name}: returned reasoning_tokens={result.reasoning_tokens} despite reasoning disabled"
    elif result.output_tokens is not None and result.output_tokens > max_tokens:
        failure = f"{name}: output_tokens={result.output_tokens} exceeds max_tokens_set={max_tokens}"

    return row, failure


def run_preflight(confirm):
    temperature = CONFIG["temperature"]
    assert temperature != 0, "temperature must never be 0 in the run path"
    max_tokens = CONFIG["max_tokens_by_level"][PREFLIGHT_LEVEL]
    reasoning_enabled = CONFIG["reasoning_enabled"]

    cfgs = models_by_name()
    paid_models = [m for m in EXPERIMENT_MODELS if m != TEST_MODEL]

    if confirm:
        est_total = sum(estimate_cost(cfgs[m], max_tokens) for m in paid_models)
        print(f"--confirm passed: about to call {len(paid_models)} paid model(s): {', '.join(paid_models)}")
        print(f"estimated cost for this preflight run: ${est_total:.4f}\n")
        targets = EXPERIMENT_MODELS
    else:
        print(f"--confirm not passed: checking only TEST_MODEL ({TEST_MODEL}). Pass --confirm to also check paid models.\n")
        targets = [TEST_MODEL]

    try:
        assert_api_keys_present(targets)
    except MissingAPIKeyError as exc:
        print(f"FATAL: {exc}")
        return 1

    test_cfg = cfgs[TEST_MODEL]
    require_daily_budget(TEST_MODEL, test_cfg["daily_request_cap"], CONFIG["paths"]["log_file"], planned_calls=1)

    logger = JsonlLogger(CONFIG["paths"]["log_file"])
    run_id = "preflight-" + now_iso()

    rows = []
    failures = []
    try:
        for name in targets:
            row, failure = call_one(
                name,
                cfgs[name],
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_enabled=reasoning_enabled,
                logger=logger,
                run_id=run_id,
                call_context="preflight",
            )
            if row is not None:
                rows.append(row)
            if failure is not None:
                failures.append(failure)
    finally:
        logger.close()

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

    print(f"\nPREFLIGHT PASSED: max_tokens cap and reasoning-disable confirmed for {len(targets)} model(s)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Also call paid models, not just TEST_MODEL")
    args = parser.parse_args()
    sys.exit(run_preflight(args.confirm))


if __name__ == "__main__":
    main()
