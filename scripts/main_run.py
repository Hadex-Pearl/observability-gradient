"""Main run: the actual study data.

6 items x 4 levels x 2 arms x 50 runs x 3 models = 7,200 calls.

Levels and arms follow prompts.yaml's schema exactly, as pilot.py already does:
l3/l2/l1 take first/third, l0 takes first/control (L0 has no third-person
prompt -- by design it poses no explicit choice to rewrite, so its second arm
is the depersonalised control instead).

Prompt construction is imported from pilot.py rather than reimplemented, so
the main run and the pilot cannot drift apart:
  build_messages / build_prompt / build_system_prompt / resolve_max_tokens

Scoring lives entirely in scripts/score_main_run.py. --code delegates to it
rather than carrying its own copy of the coder dispatch.

Concurrency: the three models run in parallel threads, each strictly
sequential internally behind its own rate limiter. Within a model nothing is
concurrent, which is the arrangement the pilot validated; across models the
only shared mutable state is the logger (already lock-guarded), the cost
tracker (lock added for this script), and per-model counters that only their
own thread touches.

Resumability: standard cell key (model, item_id, level, arm, run_index) via
RunHarness, which seeds itself from the log with load_completed_keys. Re-running
after an interruption skips completed cells and never repeats a call.

Run with:
    python scripts/main_run.py --confirm
    python scripts/main_run.py --dry-run     # build every prompt, make no calls
    python scripts/main_run.py --status      # progress from the log, no calls
"""

import argparse
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (  # noqa: E402
    CONFIG,
    EXPERIMENT_MODELS,
    ROOT_DIR,
    MissingAPIKeyError,
    assert_api_keys_present,
    get_api_key,
    models_by_name,
)
from src.logger import read_rows  # noqa: E402
from src.runner import ReasoningLeakError, RunHarness, now_iso  # noqa: E402

from scripts.pilot import (  # noqa: E402
    build_messages,
    item_by_id,
    load_prompts,
    resolve_max_tokens,
)

LOG_PATH = CONFIG["paths"]["raw_dir"] / "main_run.jsonl"
# Daily caps are per real API quota, which the pilot log shares. main_run.jsonl
# is a separate file, so RunHarness's tracker would otherwise start from zero
# and overshoot the 4,000/day cap by however many calls the pilot already made
# today. Seeded from both files below (see seed_daily_caps).
SHARED_LOG_PATH = CONFIG["paths"]["log_file"]

CALL_CONTEXT = "main_run"
RUNS_PER_CELL = 50
SPEND_CEILING_USD = 30.00
PROGRESS_EVERY = 25

# Risk-based sequencing, same rationale as the pilot: the three that can fail
# on calibration or truncation run first, while there is still time to act.
ITEM_ORDER = [
    "clarify_vs_assume",
    "continue_vs_handoff",
    "depth_vs_breadth",
    "open_vs_repetitive",
    "novel_vs_familiar",
    "context_retention",
]

# (level_int, level_key, arm). No required order within an item.
LEVELS = [
    (3, "l3_first", "first"),
    (3, "l3_third", "third"),
    (2, "l2_first", "first"),
    (2, "l2_third", "third"),
    (1, "l1_first", "first"),
    (1, "l1_third", "third"),
    (0, "l0_first", "first"),
    (0, "l0_control", "control"),
]

TOTAL_PER_MODEL = len(ITEM_ORDER) * len(LEVELS) * RUNS_PER_CELL  # 2,400

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, flush=True)


def build_cells(data):
    """All cells for one model, in run order."""
    cells = []
    for item_id in ITEM_ORDER:
        item = item_by_id(data, item_id)
        for level_int, level_key, arm in LEVELS:
            for run_index in range(RUNS_PER_CELL):
                cells.append((item, level_int, level_key, arm, run_index))
    return cells


def seed_daily_caps(harness):
    """Adds today's calls from the shared pilot log to the daily-cap counts, so
    the 4,000/day cap is enforced against real quota use rather than against
    this file alone."""
    today = now_iso()[:10]
    seeded = Counter()
    for row in read_rows(SHARED_LOG_PATH):
        if row.get("timestamp_utc", "").startswith(today) and row.get("model") in harness.daily_caps.caps:
            harness.daily_caps.counts[row["model"]] += 1
            seeded[row["model"]] += 1
    for model, n in sorted(seeded.items()):
        log(f"[budget] {model}: {n} call(s) already made today (shared log), counted against the daily cap")
    return seeded


def run_model(model, cells, harness, data, api_key, state):
    """Drives one model's 2,400 cells sequentially. One thread per model."""
    rng = __import__("random").Random()
    counts = Counter()

    for item, level_int, level_key, arm, run_index in cells:
        if harness.halted or state["stop"]:
            break

        max_tokens = resolve_max_tokens(item, level_int)
        expected = item.get("max_tokens_override", {}).get({0: "l0", 1: "l1", 2: "l2", 3: "l3"}[level_int])
        if expected is not None:
            assert max_tokens == expected, (
                f"max_tokens resolution failed for {item['id']}/l{level_int}: got {max_tokens}, expected {expected}"
            )

        messages, presentation_order = build_messages(data, item, level_int, level_key, arm, rng)

        try:
            status = harness.run_cell(
                model=model,
                item_id=item["id"],
                level=level_int,
                arm=arm,
                run_index=run_index,
                presentation_order=presentation_order,
                messages=messages,
                max_tokens=max_tokens,
                temperature=CONFIG["temperature"],
                reasoning_enabled=CONFIG["reasoning_enabled"],
                api_key=api_key,
                call_context=CALL_CONTEXT,
            )
        except ReasoningLeakError as exc:
            state["stop"] = True
            state["halt_reason"] = f"ReasoningLeakError on {model}: {exc}"
            log(f"[HALT] {exc}")
            break

        counts[status] += 1
        if status == "capped":
            state["stop"] = True
            state["halt_reason"] = f"{model} hit its daily request cap"
            break
        if status == "halted":
            break

        done = sum(counts.values())
        if done % PROGRESS_EVERY == 0:
            log(
                f"[{model}] {done}/{len(cells)} "
                f"| item={item['id']} level={level_int} arm={arm} "
                f"| ok={counts['ok']} skipped={counts['skipped']} error={counts['error']} "
                f"| spend=${harness.cost_tracker.total_usd:.4f} / ${SPEND_CEILING_USD:.2f}"
            )

        if harness.cost_tracker.exceeded_ceiling():
            state["stop"] = True
            state["halt_reason"] = f"spend ceiling ${SPEND_CEILING_USD:.2f} crossed"
            log(f"[HALT] {state['halt_reason']}")
            break

    state["counts"][model] = counts
    log(f"[{model}] finished: {dict(counts)}")


def verify_model(model):
    """Runs verify_log.py over the main-run log after a model completes.
    Returns True if the schema checks pass."""
    import subprocess

    log(f"[verify] running verify_log.py after {model} ...")
    proc = subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts" / "verify_log.py"), str(LOG_PATH)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        log(f"[verify] FAILED after {model} (exit {proc.returncode})")
        log(proc.stdout.strip())
        log(proc.stderr.strip())
        return False
    log(f"[verify] passed after {model}")
    return True


# ---------------------------------------------------------------------------
# coding
# ---------------------------------------------------------------------------
# Deliberately not implemented here. scripts/score_main_run.py is the single
# scorer: it owns the coder dispatch, the no_preference_stated category and the
# report artifact. A second copy living in this file drifted from it within a
# day, which is the exact failure mode importing from one place is meant to
# prevent.


def write_coded(_data=None):
    """Delegates to scripts/score_main_run.py. No calls, no separate logic."""
    import subprocess

    return subprocess.run(
        [sys.executable, str(ROOT_DIR / "scripts" / "score_main_run.py")],
        check=False,
    ).returncode


def print_status(data):
    """Progress from the log alone. No calls."""
    rows = [r for r in read_rows(LOG_PATH) if r.get("call_context") == CALL_CONTEXT]
    done = defaultdict(Counter)
    errors = Counter()
    for r in rows:
        done[r["model"]][(r["item_id"], r["level"], r["arm"])] += 1
        if r.get("error"):
            errors[r["model"]] += 1

    total = TOTAL_PER_MODEL * len(EXPERIMENT_MODELS)
    complete = sum(sum(c.values()) for c in done.values())
    print(f"main run: {complete}/{total} cells logged ({complete / total:.1%})")
    for model in EXPERIMENT_MODELS:
        n = sum(done[model].values())
        print(f"  {model:20s} {n:5d}/{TOTAL_PER_MODEL}  errors={errors[model]}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="actually make the 7,200 calls")
    parser.add_argument("--dry-run", action="store_true", help="build every prompt, make no calls")
    parser.add_argument("--status", action="store_true", help="print progress from the log and exit")
    parser.add_argument("--code", action="store_true", help="code the logged rows and exit; makes no calls")
    args = parser.parse_args()

    data = load_prompts()

    if args.status:
        return print_status(data)

    if args.code:
        return write_coded(data)

    cells = build_cells(data)
    total = len(cells) * len(EXPERIMENT_MODELS)
    print(f"models: {EXPERIMENT_MODELS}")
    print(f"items:  {ITEM_ORDER}")
    print(f"levels: {[(lk, arm) for _, lk, arm in LEVELS]}")
    print(f"{len(ITEM_ORDER)} items x {len(LEVELS)} level/arm x {RUNS_PER_CELL} runs = {len(cells)} calls/model")
    print(f"total planned: {total} calls across {len(EXPERIMENT_MODELS)} models")
    print(f"log: {LOG_PATH}")
    print(f"spend ceiling: ${SPEND_CEILING_USD:.2f}")

    if args.dry_run:
        rng = __import__("random").Random(0)
        seen = set()
        for item, level_int, level_key, arm, _run_index in cells:
            key = (item["id"], level_key, arm)
            if key in seen:
                continue
            seen.add(key)
            messages, order = build_messages(data, item, level_int, level_key, arm, rng)
            body = messages[1]["content"]
            assert "{{" not in body and "}}" not in body, f"unresolved placeholder in {key}"
            print(f"  ok {item['id']:22s} {level_key:11s} arm={arm:8s} cap={resolve_max_tokens(item, level_int):5d} "
                  f"order={order:9s} chars={len(body)}")
        print(f"\ndry run: {len(seen)} distinct item/level/arm prompts built, no placeholders, no calls made")
        return 0

    if not args.confirm:
        print("\nRefusing to run without --confirm. This makes 7,200 real API calls.")
        return 1

    try:
        assert_api_keys_present(EXPERIMENT_MODELS)
    except MissingAPIKeyError as exc:
        print(f"FATAL: {exc}")
        return 1

    by_name = models_by_name()
    model_configs = {m: by_name[m] for m in EXPERIMENT_MODELS}
    harness = RunHarness(
        "main-" + now_iso(),
        LOG_PATH,
        model_configs,
        cost_ceiling_usd=SPEND_CEILING_USD,
    )
    seed_daily_caps(harness)

    for model in EXPERIMENT_MODELS:
        cap = model_configs[model]["daily_request_cap"]
        used = harness.daily_caps.counts[model]
        if used + len(cells) > cap:
            print(
                f"FATAL: {model} would exceed its daily cap "
                f"({used} used today + {len(cells)} planned > {cap}). Resume tomorrow or raise the cap."
            )
            return 1

    state = {"stop": False, "halt_reason": None, "counts": {}}
    threads = []
    try:
        for model in EXPERIMENT_MODELS:
            t = threading.Thread(
                target=run_model,
                args=(model, cells, harness, data, get_api_key(model_configs[model]["provider"]), state),
                name=f"run-{model}",
                daemon=False,
            )
            t.start()
            threads.append((model, t))

        # verify_log.py runs as each model finishes, in the declared order; a
        # schema failure stops the run before any remaining model continues.
        for model, t in threads:
            t.join()
            if not verify_model(model):
                state["stop"] = True
                state["halt_reason"] = f"verify_log.py schema failure after {model}"
                harness.halted = True
                log(f"[HALT] {state['halt_reason']}")
    finally:
        for _model, t in threads:
            if t.is_alive():
                t.join()
        harness.close()

    harness.cost_tracker.print_summary()
    for model, counts in state["counts"].items():
        print(f"  {model:20s} {dict(counts)}")

    if state["halt_reason"]:
        print(f"\nHALTED: {state['halt_reason']}")
        print("Re-run the same command to resume; completed cells are skipped.")
        return 1

    print("\nmain run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
