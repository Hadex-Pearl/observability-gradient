"""Reports on a run log JSONL file: row count, duplicate keys, rows per cell, errors, null tokens, spend.

Usage: python scripts/verify_log.py path/to/run.jsonl
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.logger import CELL_KEY_FIELDS, SchemaError, cell_key, read_rows, validate_row  # noqa: E402


def verify(path, model_configs=None):
    rows = list(read_rows(path))
    cell_counts = Counter()
    success_counts = Counter()
    error_types = Counter()
    null_input = null_output = null_reasoning = 0
    total_spend = 0.0
    schema_errors = []

    for row in rows:
        try:
            validate_row(row)
        except SchemaError as exc:
            schema_errors.append(str(exc))
            continue

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
        else:
            error_types[row["error"].get("type", "unknown")] += 1

    duplicate_success_keys = {k: n for k, n in success_counts.items() if n > 1}

    print(f"rows:            {len(rows)}")
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

    return {
        "rows": len(rows),
        "unique_cells": len(cell_counts),
        "duplicate_success_keys": duplicate_success_keys,
        "error_types": dict(error_types),
        "null_input": null_input,
        "null_output": null_output,
        "null_reasoning": null_reasoning,
        "total_spend": total_spend,
        "schema_errors": schema_errors,
    }


def main():
    parser = argparse.ArgumentParser(description="Verify a run log JSONL file")
    parser.add_argument("path")
    args = parser.parse_args()

    model_configs = None
    try:
        from config import models_by_name

        model_configs = models_by_name()
    except Exception:
        pass

    result = verify(args.path, model_configs)
    sys.exit(1 if result["schema_errors"] else 0)


if __name__ == "__main__":
    main()
