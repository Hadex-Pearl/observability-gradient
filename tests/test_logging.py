"""End-to-end test of the logging layer: resumability, error handling, retries, and schema validation.

Uses a fake provider adapter (no network calls) so it runs anywhere. Run with:
    python tests/test_logging.py
"""

import itertools
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONFIG, TEST_MODEL, assert_test_model, models_by_name  # noqa: E402
from src.logger import read_rows, validate_row  # noqa: E402
from src.providers import ADAPTERS  # noqa: E402
from src.providers.base import ProviderError, ProviderResponse  # noqa: E402
from src.runner import ReasoningLeakError, RunHarness, require_daily_budget  # noqa: E402
from scripts.verify_log import verify  # noqa: E402

# All testing runs against TEST_MODEL, sourced from the real config entry so
# rates/rpm/cap aren't duplicated. rpm_limit is overridden to None here only
# because this test drives a fake in-process adapter at full speed and never
# touches the real network — real scripts must use the configured rpm_limit
# unmodified.
MODEL_NAME = TEST_MODEL
_real_cfg = models_by_name()[MODEL_NAME]
MODEL_CONFIGS = {MODEL_NAME: {**_real_cfg, "rpm_limit": None}}
PROVIDER = MODEL_CONFIGS[MODEL_NAME]["provider"]


class FakeProvider:
    """Deterministic stand-in for a real provider adapter, with hooks to force one call to fail,
    to come back truncated (finish_reason="length", output_tokens == the cap), or to leak reasoning
    tokens despite being told reasoning is disabled."""

    def __init__(self):
        self.call_count = 0
        self.fail_once_for = set()
        self.truncate_for = set()
        self.leak_for = set()
        self._already_failed = set()

    def call(self, api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key):
        self.call_count += 1
        assert temperature != 0, "adapter received temperature=0"
        assert reasoning_enabled is False, "adapter received reasoning_enabled=True"
        text = messages[-1]["content"]
        marker = text[text.index("[") + 1 : text.index("]")]
        if marker in self.fail_once_for and marker not in self._already_failed:
            self._already_failed.add(marker)
            raise ProviderError("forced test failure", retryable=False)

        level = int(marker.split("level=")[1].split("|")[0])
        input_tokens = 50 + level * 20 + (len(text) % 7)

        if marker in self.truncate_for:
            return ProviderResponse(
                text=f"dummy response for {marker} (cut off mid",
                finish_reason="length",
                input_tokens=input_tokens,
                output_tokens=max_tokens,
                reasoning_tokens=None,
                latency_ms=1,
                reasoning_disabled_by="api_parameter",
            )

        return ProviderResponse(
            text=f"dummy response for {marker}",
            finish_reason="stop",
            input_tokens=input_tokens,
            output_tokens=10 + level * 5,
            reasoning_tokens=7 if marker in self.leak_for else None,
            latency_ms=1,
            reasoning_disabled_by="api_parameter",
        )


def marker_for(item_id, level, arm, run_index):
    return f"id={item_id}|level={level}|arm={arm}|run={run_index}"


def build_messages(item_id, level, arm, run_index):
    marker = marker_for(item_id, level, arm, run_index)
    filler = "x" * (level * 20)
    return [{"role": "user", "content": f"[{marker}] Consider the choice. {filler}"}]


def make_cells(n):
    items = ["item1", "item2"]
    levels = [0, 1]
    arms = ["A", "B"]
    combos = list(itertools.product(items, levels, arms, range(3)))
    combos.sort()
    return combos[:n]


def run_cell(harness, item_id, level, arm, run_index):
    return harness.run_cell(
        model=MODEL_NAME,
        item_id=item_id,
        level=level,
        arm=arm,
        run_index=run_index,
        presentation_order="A_first" if arm == "A" else "B_first",
        messages=build_messages(item_id, level, arm, run_index),
        max_tokens=CONFIG["max_tokens_by_level"][level],
        temperature=CONFIG["temperature"],
        reasoning_enabled=CONFIG["reasoning_enabled"],
        api_key="dummy",
        call_context="test",
    )


def main():
    assert_test_model(MODEL_NAME)

    tmp_dir = tempfile.mkdtemp(prefix="obs_gradient_log_test_")
    log_path = str(Path(tmp_dir) / "run.jsonl")
    print(f"log file: {log_path}")

    cfg = MODEL_CONFIGS[MODEL_NAME]
    require_daily_budget(MODEL_NAME, cfg["daily_request_cap"], log_path, planned_calls=25)

    original_adapter = ADAPTERS.get(PROVIDER)
    fake = FakeProvider()
    ADAPTERS[PROVIDER] = fake.call

    cells = make_cells(20)
    assert len(cells) == 20
    assert len({c[0] for c in cells}) >= 2, "need at least 2 items"
    assert len({c[1] for c in cells}) >= 2, "need at least 2 levels"
    assert {c[2] for c in cells} == {"A", "B"}, "need both arms"

    # --- Phase 1: resumability -------------------------------------------
    print("\n=== phase 1: crash + resume ===")
    harness = RunHarness(run_id="test-run-a", log_path=log_path, model_configs=MODEL_CONFIGS)
    for item_id, level, arm, run_index in cells[:11]:
        status = run_cell(harness, item_id, level, arm, run_index)
        assert status == "ok"
    harness.close()
    del harness
    rows_after_crash = list(read_rows(log_path))
    print(f"rows written before simulated crash: {len(rows_after_crash)}")
    assert len(rows_after_crash) == 11

    print("restarting harness from disk...")
    harness = RunHarness(run_id="test-run-a", log_path=log_path, model_configs=MODEL_CONFIGS)
    assert len(harness.completed) == 11, "restart must recover completed keys from the log"
    for item_id, level, arm, run_index in cells:
        run_cell(harness, item_id, level, arm, run_index)

    rows_after_resume = list(read_rows(log_path))
    print(f"rows after resume: {len(rows_after_resume)}")
    assert len(rows_after_resume) == 20, "resumed run must not duplicate already-completed calls"
    keys = [tuple(r[f] for f in ("model", "item_id", "level", "arm", "run_index")) for r in rows_after_resume]
    assert len(keys) == len(set(keys)), "no duplicate keys after resume"
    print("PASS: exactly 20 rows, no duplicate keys after crash + resume")

    # --- Phase 2: forced error, survival, and retry -----------------------
    print("\n=== phase 2: forced error + retry ===")
    error_cell = ("item1", 0, "A", 99)
    fake.fail_once_for.add(marker_for(*error_cell))

    status = run_cell(harness, *error_cell)
    assert status == "error", "forced failure must surface as an 'error' status, not raise"
    rows_after_error = list(read_rows(log_path))
    assert len(rows_after_error) == 21
    error_row = rows_after_error[-1]
    assert error_row["error"] is not None
    assert error_row["raw_output"] is None
    print("PASS: error row written with error populated and raw_output null, loop survived")

    harness.close()
    del harness

    calls_before_rerun = fake.call_count
    harness = RunHarness(run_id="test-run-a", log_path=log_path, model_configs=MODEL_CONFIGS)
    assert error_cell not in harness.completed, "a cell whose only row errored must be treated as incomplete"

    statuses = [run_cell(harness, item_id, level, arm, run_index) for item_id, level, arm, run_index in cells]
    statuses.append(run_cell(harness, *error_cell))
    assert statuses.count("skipped") == 20, "the 20 already-completed cells must be skipped, not re-called"
    assert statuses[-1] == "ok", "the retried cell must succeed this time"
    assert fake.call_count == calls_before_rerun + 1, "rerun must retry exactly the one incomplete key"
    print("PASS: rerun retried only the previously-errored key")

    harness.close()

    # --- Phase 3: schema validation ---------------------------------------
    print("\n=== phase 3: schema validation ===")
    final_rows = list(read_rows(log_path))
    assert len(final_rows) == 22, "20 clean successes + 1 error + 1 retried success"
    for row in final_rows:
        validate_row(row)
    print(f"PASS: all {len(final_rows)} rows validate against the schema")

    # --- Phase 4: measured token stats per level ---------------------------
    print("\n=== phase 4: measured tokens per level ===")
    by_level = {}
    for row in final_rows:
        if row["error"] is not None:
            continue
        by_level.setdefault(row["level"], {"in": [], "out": []})
        by_level[row["level"]]["in"].append(row["input_tokens"])
        by_level[row["level"]]["out"].append(row["output_tokens"])
    for level in sorted(by_level):
        ins = by_level[level]["in"]
        outs = by_level[level]["out"]
        print(f"level {level}: mean input_tokens={sum(ins) / len(ins):.1f}  mean output_tokens={sum(outs) / len(outs):.1f}  n={len(ins)}")

    # --- Phase 5: verify_log.py sanity check --------------------------------
    print("\n=== phase 5: verify_log.py ===")
    result = verify(log_path, model_configs={MODEL_NAME: MODEL_CONFIGS[MODEL_NAME]}, include_all=True)
    assert result["rows"] == 22
    assert result["duplicate_success_keys"] == {}
    assert result["error_types"].get("ProviderError") == 1
    assert not result["schema_errors"]
    print("PASS: verify_log.py reports match expectations")

    default_result = verify(log_path, model_configs={MODEL_NAME: MODEL_CONFIGS[MODEL_NAME]})
    assert default_result["rows"] == 0, "call_context='test' rows must be excluded by default (not pilot/main)"
    assert default_result["context_counts"] == {"test": 22}
    print("PASS: verify_log.py excludes non-study (test) rows from counts/spend by default")

    # --- Phase 6: truncation is visible, never silent ----------------------
    print("\n=== phase 6: truncation flag ===")
    trunc_log = str(Path(tmp_dir) / "trunc.jsonl")
    fake_trunc = FakeProvider()
    ADAPTERS[PROVIDER] = fake_trunc.call
    trunc_cell = ("item1", 0, "A", 0)
    fake_trunc.truncate_for.add(marker_for(*trunc_cell))

    h_trunc = RunHarness(run_id="test-run-b", log_path=trunc_log, model_configs=MODEL_CONFIGS)
    status = run_cell(h_trunc, *trunc_cell)
    h_trunc.close()
    assert status == "ok"
    trunc_row = next(read_rows(trunc_log))
    assert trunc_row["finish_reason"] == "length"
    assert trunc_row["truncated"] is True
    assert trunc_row["output_tokens"] == CONFIG["max_tokens_by_level"][0]
    print("PASS: a length-capped response is flagged truncated=True with finish_reason recorded")

    # --- Phase 7: a reasoning-token leak halts the run immediately ---------
    print("\n=== phase 7: reasoning leak halts the run ===")
    leak_log = str(Path(tmp_dir) / "leak.jsonl")
    fake_leak = FakeProvider()
    ADAPTERS[PROVIDER] = fake_leak.call
    leak_cell = ("item1", 0, "A", 0)
    fake_leak.leak_for.add(marker_for(*leak_cell))

    h_leak = RunHarness(run_id="test-run-c", log_path=leak_log, model_configs=MODEL_CONFIGS)
    raised = False
    try:
        run_cell(h_leak, *leak_cell)
    except ReasoningLeakError:
        raised = True
    assert raised, "nonzero reasoning_tokens must raise ReasoningLeakError, not warn and continue"
    assert h_leak.halted is True
    h_leak.close()
    print("PASS: reasoning_tokens > 0 raised ReasoningLeakError and halted the run")

    if original_adapter is not None:
        ADAPTERS[PROVIDER] = original_adapter
    else:
        del ADAPTERS[PROVIDER]

    shutil.rmtree(tmp_dir)
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
