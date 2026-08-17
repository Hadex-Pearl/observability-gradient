"""Extracts real transcripts and headline numbers for the demo site.

Everything written to demo/data.json comes from the collected run. Nothing is
generated, paraphrased or hand-written: transcripts are verbatim excerpts from
data/parsed/main_run_scored.jsonl, and the headline counts are parsed out of
report/analysis.md rather than retyped, so they cannot drift from the analysis.

Representativeness: for each (item, model, level) cell the modal coded outcome
is computed first, then a transcript carrying that outcome is chosen. The
example shown is therefore typical of its cell rather than picked for effect.
The cell's full distribution ships alongside it so a reader can see how modal
the modal outcome actually is.

Run with:
    python scripts/build_demo_data.py
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONFIG, EXPERIMENT_MODELS, ROOT_DIR  # noqa: E402
from src.logger import read_rows  # noqa: E402

SCORED_PATH = CONFIG["paths"]["parsed_dir"] / "main_run_scored.jsonl"
JUDGED_PATH = CONFIG["paths"]["parsed_dir"] / "main_run_judged.jsonl"
ANALYSIS_PATH = ROOT_DIR / "report" / "analysis.md"
OUT_PATH = ROOT_DIR / "demo" / "data.json"

DEMO_ITEMS = ["clarify_vs_assume", "novel_vs_familiar"]
LEVELS = [3, 2, 1, 0]
ARM = "first"
MAX_WORDS = 150

# Human-readable outcome labels. Keyed (item, code); L0 for clarify_vs_assume
# is judge-scored, so its codes are the judge's binary rather than a/b.
LABELS = {
    ("clarify_vs_assume", "a"): "asks a clarifying question",
    ("clarify_vs_assume", "b"): "proceeds on own judgement",
    ("clarify_vs_assume", "clarify"): "withholds, asks first",
    ("clarify_vs_assume", "assume"): "produces the deliverable",
    ("novel_vs_familiar", "a"): "starts the novel task",
    ("novel_vs_familiar", "b"): "starts the familiar task",
}

LEVEL_BLURB = {
    3: "Asked directly",
    2: "Announced study, forced choice",
    1: "Inside a task, study language removed",
    0: "Unremarked affordance in ordinary work",
}


def truncate(text, max_words=MAX_WORDS):
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + " …"


def parse_analysis_counts():
    """Reads the summary table in report/analysis.md. Counts are derived, never
    retyped, so the site cannot disagree with the analysis it summarises."""
    rows = [
        l for l in ANALYSIS_PATH.read_text().splitlines()
        if l.startswith("| ") and "`" in l
        and any(m in l for m in EXPERIMENT_MODELS)
    ]
    matched = reversals = 0
    for line in rows:
        cells = [c.strip() for c in line.strip("|").split("|")]
        depth, pred = cells[3], cells[4]
        if "reversal" in depth:
            reversals += 1
        if depth.replace("**reversal**", "").strip() == pred:
            matched += 1
    return len(rows), matched, reversals


def main():
    for p in (SCORED_PATH, JUDGED_PATH, ANALYSIS_PATH):
        if not p.exists():
            print(f"FATAL: {p} does not exist.")
            return 1

    judged = {
        (r["model"], r["item_id"], r["level"], r["arm"], r["run_index"]): r.get("binary")
        for r in read_rows(JUDGED_PATH)
        if r.get("measure") in ("clarify", "clarify_control")
    }

    scored = [r for r in read_rows(SCORED_PATH) if r["item_id"] in DEMO_ITEMS and r["arm"] == ARM]

    # code every row, resolving pending_judge through the judge labels
    for r in scored:
        if r.get("coding_method") == "pending_judge":
            r["_code"] = judged.get(
                (r["model"], r["item_id"], r["level"], r["arm"], r["run_index"])
            )
        else:
            r["_code"] = r.get("coded_choice")

    n_rows, matched, reversals = parse_analysis_counts()
    total_responses = sum(1 for _ in read_rows(SCORED_PATH))

    data = {
        "headline": {
            "total_responses": total_responses,
            "items": 6,
            "models": len(EXPERIMENT_MODELS),
            "predictions_matched": f"{matched}/{n_rows}",
            "reversals": f"{reversals}/{n_rows}",
        },
        "models": list(EXPERIMENT_MODELS),
        "items": DEMO_ITEMS,
        "levels": [{"level": lv, "blurb": LEVEL_BLURB[lv]} for lv in LEVELS],
        "cells": {},
    }

    missing = []
    for item in DEMO_ITEMS:
        for model in EXPERIMENT_MODELS:
            for lv in LEVELS:
                rows = [r for r in scored
                        if r["item_id"] == item and r["model"] == model and r["level"] == lv]
                coded = [r for r in rows if r["_code"] is not None]
                key = f"{item}|{model}|{lv}"
                if not coded:
                    missing.append(key)
                    continue
                dist = Counter(r["_code"] for r in coded)
                modal, modal_n = dist.most_common(1)[0]
                # first row carrying the modal outcome, by run_index for determinism
                pick = sorted([r for r in coded if r["_code"] == modal],
                              key=lambda r: r["run_index"])[0]
                data["cells"][key] = {
                    "item_id": item,
                    "model": model,
                    "level": lv,
                    "arm": ARM,
                    "code": modal,
                    "label": LABELS.get((item, modal), str(modal)),
                    "modal_n": modal_n,
                    "cell_n": len(coded),
                    "distribution": {
                        LABELS.get((item, k), str(k)): v for k, v in sorted(dist.items(), key=lambda kv: -kv[1])
                    },
                    "run_index": pick["run_index"],
                    "text": truncate(pick.get("raw_output") or ""),
                    "truncated": len((pick.get("raw_output") or "").split()) > MAX_WORDS,
                    # L2 is a forced-choice level: max_tokens is 32 and the
                    # protocol asks for only "A" or "B", so a one-character
                    # response is the expected form, not a truncated excerpt.
                    # Flagged so the site renders it as an answer rather than
                    # as a transcript that failed to load.
                    "format": "forced_choice" if lv == 2 else "prose",
                }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2))

    # ---- validation: fail loudly rather than shipping an empty card ---------
    expected = len(DEMO_ITEMS) * len(EXPERIMENT_MODELS) * len(LEVELS)
    problems = []
    if missing:
        problems.append(f"{len(missing)} cell(s) with no coded rows: {missing}")
    for key, c in data["cells"].items():
        if not c["text"].strip():
            problems.append(f"empty transcript: {key}")
        if c["format"] == "prose" and len(c["text"].split()) < 3:
            problems.append(f"suspiciously short prose transcript ({len(c['text'].split())} words): {key}")
        if c["format"] == "forced_choice" and c["text"].strip().upper() not in ("A", "B"):
            problems.append(f"L2 forced-choice response is not a bare A/B: {key} -> {c['text'][:40]!r}")
        if not c["label"] or c["label"] == "None":
            problems.append(f"missing outcome label: {key}")

    print(f"wrote {OUT_PATH}")
    print(f"cells: {len(data['cells'])} of {expected} expected")
    print(f"headline: {data['headline']}")
    print()
    print("=== sample cells ===")
    for key in list(data["cells"])[:2] + list(data["cells"])[-2:]:
        c = data["cells"][key]
        print(f"--- {key}  ({c['modal_n']}/{c['cell_n']} modal)  label={c['label']!r}")
        print(f"    dist: {c['distribution']}")
        print(f"    text: {c['text'][:160]}...")
    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("validation: all cells populated, no empty or malformed transcripts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
