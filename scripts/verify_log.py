"""Reports on a run log JSONL file: row count, duplicate keys, rows per cell, errors, null tokens,
spend, truncation rate per level, and per-level output token calibration stats (mean/median/p90/max).

Usage: python scripts/verify_log.py path/to/run.jsonl
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import STUDY_CALL_CONTEXTS  # noqa: E402
from src.logger import CELL_KEY_FIELDS, SchemaError, cell_key, read_rows, validate_row  # noqa: E402

# Level 0 is the freest condition; if the cap is cutting more than this
# fraction of responses off before the model has produced anything, the cap
# is destroying the measurement rather than saving money on it.
LEVEL_0_TRUNCATION_WARN_THRESHOLD = 0.10


def percentile(sorted_values, pct):
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


def median(sorted_values):
    return percentile(sorted_values, 0.5)


def verify(path, model_configs=None, include_all=False):
    all_rows = list(read_rows(path))
    context_counts = Counter(row.get("call_context", "unknown") for row in all_rows)

    cell_counts = Counter()
    success_counts = Counter()
    error_types = Counter()
    null_input = null_output = null_reasoning = 0
    total_spend = 0.0
    schema_errors = []
    per_level = defaultdict(lambda: {"output_tokens": [], "truncated": 0, "total": 0})

    valid_rows = []
    for row in all_rows:
        try:
            validate_row(row)
            valid_rows.append(row)
        except SchemaError as exc:
            schema_errors.append(str(exc))

    rows = valid_rows if include_all else [r for r in valid_rows if r["call_context"] in STUDY_CALL_CONTEXTS]

    for row in rows:
        key = cell_key(row)
        cell_counts[key] += 1

        if row["error"] is None:
            success_counts[key] += 1
            null_input += row["input_tokens"] is None
            null_output += row["output_tokens"] is None
            null_reasoning += row["reasoning_tokens"] is None
            if model_configs and row["model"] in model_configs:
                cfg = model_configs[row["model"]]
                in_tok = row["input_tokens"] or 0
                out_tok = (row["output_tokens"] or 0) + (row["reasoning_tokens"] or 0)
                total_spend += in_tok / 1_000_000 * cfg["price_per_million_in"]
                total_spend += out_tok / 1_000_000 * cfg["price_per_million_out"]

            level_stats = per_level[row["level"]]
            level_stats["total"] += 1
            if row["truncated"]:
                level_stats["truncated"] += 1
            if row["output_tokens"] is not None:
                level_stats["output_tokens"].append(row["output_tokens"])
        else:
            error_types[row["error"].get("type", "unknown")] += 1

    duplicate_success_keys = {k: n for k, n in success_counts.items() if n > 1}

    print(f"rows in file:    {len(all_rows)}")
    print("call_context breakdown: " + ", ".join(f"{ctx}={n}" for ctx, n in context_counts.most_common()))
    if not include_all:
        excluded = len(all_rows) - len(rows)
        print(f"(excluding {excluded} non-study row(s) [{', '.join(c for c in context_counts if c not in STUDY_CALL_CONTEXTS)}] "
              f"from counts/spend below; pass --include-all to include them)")
    print(f"rows counted:    {len(rows)}")
    print(f"unique cells:    {len(cell_counts)}")
    print(f"duplicate successful keys: {len(duplicate_success_keys)}")
    for k, n in list(duplicate_success_keys.items())[:20]:
        print(f"  DUPLICATE {dict(zip(CELL_KEY_FIELDS, k))}: {n} success rows")
    if cell_counts:
        print(f"rows per cell:   min={min(cell_counts.values())} max={max(cell_counts.values())}")
    print(f"errors:          {sum(error_types.values())}")
    for t, n in error_types.most_common():
        print(f"  {t}: {n}")
    print(f"null input_tokens:     {null_input}")
    print(f"null output_tokens:    {null_output}")
    print(f"null reasoning_tokens: {null_reasoning}")
    if model_configs:
        print(f"total spend:     ${total_spend:.4f}")
    if schema_errors:
        print(f"SCHEMA ERRORS: {len(schema_errors)}")
        for e in schema_errors[:10]:
            print(f"  {e}")

    level_summary = {}
    print("\nper-level output token calibration:")
    print(f"{'level':<6}{'n':<6}{'mean':<8}{'median':<8}{'p90':<8}{'max':<8}{'truncation_rate':<16}")
    for level in sorted(per_level):
        stats = per_level[level]
        tokens = sorted(stats["output_tokens"])
        n = stats["total"]
        truncation_rate = stats["truncated"] / n if n else 0.0
        mean = sum(tokens) / len(tokens) if tokens else 0.0
        med = median(tokens) or 0.0
        p90 = percentile(tokens, 0.9) or 0.0
        mx = max(tokens) if tokens else 0
        print(f"{level:<6}{n:<6}{mean:<8.1f}{med:<8.1f}{p90:<8.1f}{mx:<8}{truncation_rate:<16.1%}")
        level_summary[level] = {
            "n": n,
            "mean": mean,
            "median": med,
            "p90": p90,
            "max": mx,
            "truncation_rate": truncation_rate,
        }

    if 0 in level_summary and level_summary[0]["truncation_rate"] > LEVEL_0_TRUNCATION_WARN_THRESHOLD:
        print(
            f"\nWARNING: level 0 truncation rate is {level_summary[0]['truncation_rate']:.1%}, "
            f"above the {LEVEL_0_TRUNCATION_WARN_THRESHOLD:.0%} threshold. The cap is cutting "
            "responses before the model has started, not just after — raise max_tokens_by_level[0]."
        )

    return {
        "rows": len(rows),
        "total_rows_in_file": len(all_rows),
        "context_counts": dict(context_counts),
        "unique_cells": len(cell_counts),
        "duplicate_success_keys": duplicate_success_keys,
        "error_types": dict(error_types),
        "null_input": null_input,
        "null_output": null_output,
        "null_reasoning": null_reasoning,
        "total_spend": total_spend,
        "schema_errors": schema_errors,
        "level_summary": level_summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify a run log JSONL file")
    parser.add_argument("path")
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include test/preflight rows in counts and spend (default: study rows only, i.e. pilot/main)",
    )
    args = parser.parse_args()

    model_configs = None
    try:
        from config import models_by_name

        model_configs = models_by_name()
    except Exception:
        pass

    result = verify(args.path, model_configs, include_all=args.include_all)
    sys.exit(1 if result["schema_errors"] else 0)


if __name__ == "__main__":
    main()
