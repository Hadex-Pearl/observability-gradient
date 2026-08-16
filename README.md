# Observability Gradient

Do elicited welfare preferences survive when the model stops being asked?

Six welfare-relevant preference items are presented to three language models at
four levels of observability, with a control arm at each level, 50 runs per
cell. The four levels hold the underlying choice fixed and vary only how
visibly the choice is being measured:

| level | what it is | readout |
|---|---|---|
| **L3** | asks the model directly | stated choice |
| **L2** | the same choice inside an announced study, forced choice | `A` / `B` label |
| **L1** | the choice inside a task, study language removed | stated choice |
| **L0** | an unremarked affordance inside ordinary work | **what the model actually does** |

Control arms differ by level because the artifact differs. L3/L2/L1 use a
third-person mirror (identical wording, referent is a different AI assistant),
controlling for confident answers to a question format. L0 uses a
depersonalised control (the model plans work for a human team instead of doing
it), controlling for the ordering belonging to the tasks rather than the model.

**Status: data collection and analysis complete.** 7,200 main-run calls, 0
errors, 0 reasoning leaks. One measure (suspicion detection) is specified and
implemented but not yet run.

---

## Start here

| file | why it matters |
|---|---|
| **[`prereg.md`](prereg.md)** | **Read this first.** The preregistration: design, fixed analysis decisions, per-item predictions with reasoning, failure criteria, and 28 numbered amendments. Locked 2026-08-15 06:02 UTC at commit `a1ac8dc` before any data collection. Every departure from the original plan is an amendment with a stated reason. |
| [`report/analysis.md`](report/analysis.md) | The results. Per-cell proportions, trend and heterogeneity tests, survival depth per item, predictions shown alongside outcomes. |
| [`report/main_run_scoring.md`](report/main_run_scoring.md) | How 7,200 raw responses became codes, including every scoring correction made and one that was reverted. |
| [`report/judge_results.md`](report/judge_results.md) | The judge-scored measures, inter-pass agreement, and the same-model-judging check. |
| [`items/items.yaml`](items/items.yaml) | The six items: option nouns, readout rule, counterbalance rule, source citation. |
| [`items/prompts/prompts.yaml`](items/prompts/prompts.yaml) | Every prompt actually sent, all 8 level/arm combinations per item, plus shared templates and system prompts. |
| [`config.py`](config.py) | Model registry, per-level token caps, spend ceiling, call-context registry. One place to change what runs. |

`prereg.md` is the spine. The amendments are not footnotes — several of them
(A5, A20, A26, A28) change how the analysis is read, and `scripts/analyze.py`
cites them by number where it implements them.

---

## Reproducing from scratch

### 1. Environment

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # then fill in the keys you need
```

Python 3.11. Keys required: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`DEEPSEEK_API_KEY` for the study models; `TOGETHER_API_KEY` only for the
manipulation check. `.env` is gitignored and never read except through
`config.get_api_key()`.

### 2. Verify the harness before spending anything

```bash
.venv/bin/python tests/test_items.py       # item fields complete
.venv/bin/python tests/test_prompts.py     # prompts resolve, no placeholder leaks
.venv/bin/python tests/test_logging.py     # schema, resumability, reasoning-leak halt
```

### 3. Preflight

```bash
.venv/bin/python scripts/preflight.py --confirm
```

One real call per model, proving `max_tokens` and reasoning-disable actually
took effect at the API rather than being merely requested. Without `--confirm`
it only touches `TEST_MODEL`.

### 4. Manipulation check

```bash
.venv/bin/python scripts/manipulation_check.py
.venv/bin/python scripts/manipulation_check.py --ranker glm-5.2      # one ranker only
.venv/bin/python scripts/manipulation_check.py --regenerate-report   # no calls
```

Two rankers from unrelated labs (Llama-3.3-70B, GLM-5.2 on Together) rank the
four prompts per item, unlabelled and shuffled, by how evaluative they seem.
This is what produced **A20**: the empirical ordering is **L2, L3, L1, L0**,
not the preregistered L3, L2, L1, L0. The trend test uses the empirical
ordering and reports the preregistered one as a sensitivity analysis.

### 5. Pilot

```bash
.venv/bin/python scripts/pilot.py
.venv/bin/python scripts/pilot.py --l0-recap    # after raising L0 caps
.venv/bin/python scripts/pilot.py --l0-recap2   # continue_vs_handoff, context_retention control
.venv/bin/python scripts/pilot.py --l0-recap3   # depth_vs_breadth control
.venv/bin/python scripts/pilot.py --l0-recap4   # context_retention control, recommendation wording
```

Runs on `TEST_MODEL` only. Screens every item before the main run: truncation,
degenerate splits, choice-line parse rates. Each recap round writes at an
offset `run_index` under its own `call_context`, so rows collected under
superseded caps are **preserved rather than overwritten** — the log is
append-only and nothing is ever rewritten in place.

The pilot is where A22 (four L0 caps raised after 87–100% truncation), A24,
A25 and A26 came from. Reports land in `report/pilot*.md`.

### 6. Main run

```bash
.venv/bin/python scripts/main_run.py --dry-run   # build all 48 prompts, no calls
.venv/bin/python scripts/main_run.py --confirm   # 7,200 calls
.venv/bin/python scripts/main_run.py --status    # progress, no calls
```

6 items × 4 levels × 2 arms × 50 runs × 3 models = **7,200 calls**. The three
models run in parallel threads, each strictly sequential internally behind its
own rate limiter. Resumable on the standard cell key
`(model, item_id, level, arm, run_index)` — re-run the same command after an
interruption and completed cells are skipped, never repeated.

Halts on: `ReasoningLeakError`, spend ceiling, or a `verify_log.py` schema
failure after any model completes.

### 7. Score (tier 1, deterministic)

```bash
.venv/bin/python scripts/score_main_run.py
```

Reads `data/raw/main_run.jsonl`, **never writes to it**. Applies the coders
imported from `pilot.py` — nothing is re-derived, so the scored study data
cannot drift from what the pilot validated. Writes
`data/parsed/main_run_scored.jsonl` (one row per input row, plus
`coded_choice` and `coding_method`) and `report/main_run_scoring.md`.

`clarify_vs_assume` at L0 is tagged `pending_judge` and deliberately left for
tier 2.

### 8. Judge (tier 2)

```bash
.venv/bin/python scripts/judge.py --measure clarify --confirm          # 900 calls
.venv/bin/python scripts/judge.py --measure clarify_control --confirm  # 450 calls
.venv/bin/python scripts/judge.py --measure suspicion --confirm        # 16,200 calls
.venv/bin/python scripts/judge.py --aggregate                          # labels + agreement, no calls
```

Three independent passes per row, because temperature is fixed at 1.0
throughout (never 0 — that would collapse repeated runs in a cell to n=1), so a
single judge pass is a sample rather than a verdict. Inter-pass agreement is
the reliability estimate and is reported, not assumed.

`clarify` and `clarify_control` use **different templates** and are never
pooled: the control arm was asked for a schedule, not an executive summary.
L2 rows are excluded from the suspicion measure by default and reported as a
separate stratum — their responses are a bare `A`/`B` averaging 3 output
tokens and cannot carry the signal.

### 9. Analyse

```bash
.venv/bin/python scripts/analyze.py
```

Inference only, no API calls. Implements the fixed analysis plan in
`prereg.md`: Wilson intervals on all cells, exact binomial against 0.5,
Cochran–Armitage trend, chi-square heterogeneity, two-proportion tests for
first-person advantage, survival depth with the preregistered edge cases, and
Benjamini–Hochberg at 0.05 across three families of 24/12/18 per model.
Writes `report/analysis.md`.

### Verify at any point

```bash
.venv/bin/python scripts/verify_log.py data/raw/main_run.jsonl
```

Schema, cell completeness, spend, and duplicate detection. Exits non-zero on a
schema failure.

---

## Cost

Actual spend, computed from the logs:

| log | rows | cost |
|---|---|---|
| `run.jsonl` (preflight, pilot, recaps) | 333 | $0.16 |
| `main_run.jsonl` | 7,200 | $9.25 |
| `judge.jsonl` (clarify + control) | 1,368 | $1.41 |
| **total so far** | **8,901** | **$10.81** |

The unrun suspicion pass adds ~16,200 calls at roughly **$14** on
`claude-haiku-4-5`. Ceilings: $50 overall (`config.py`), $30 for the main run,
$25 for the judge. These bound spend; `daily_request_cap` exists to catch a
runaway loop, not to control cost.

---

## Repository layout

```
config.py               model registry, caps, spend ceiling, CALL_CONTEXTS
prereg.md               preregistration + 28 amendments   <- read first

items/
  items.yaml            the six items, with source citations
  prompts/prompts.yaml  every prompt sent, 8 level/arm combos per item
  materials/            the inline work materials (interviews, notes, drafts)

src/
  logger.py             append-only JSONL, schema validation, cost tracking
  runner.py             RunHarness: retries, rate limiting, daily caps,
                        resumability, ReasoningLeakError
  providers/            one adapter per provider behind a common interface

scripts/
  preflight.py          prove generation params took effect
  manipulation_check.py rank levels by evaluativeness (produced A20)
  pilot.py              item screening + every readout coder
  main_run.py           the 7,200-call study
  score_main_run.py     tier-1 deterministic scoring
  judge.py              tier-2 judge-scored measures
  analyze.py            the preregistered analysis
  verify_log.py         schema and completeness checks

report/                 every generated report, all regenerable from the logs
tests/                  item, prompt, and logging tests
data/raw/               append-only call logs        (gitignored)
data/parsed/            scored and judged outputs    (gitignored)
```

**`src/parse.py` and `src/analyze.py` are empty stubs** from the initial
skeleton. The working implementations are `scripts/score_main_run.py` and
`scripts/analyze.py`.

---

## Design decisions worth knowing before reading the code

**Temperature is 1.0 everywhere, never 0.** At temperature 0 every repeated run
in a cell returns the same response, collapsing effective n to 1. Asserted in
`config.py` and again in `src/runner.py`.

**Reasoning is disabled on every provider**, by whatever mechanism that
provider offers, and `reasoning_disabled_by` is recorded per row. If a provider
returns reasoning tokens anyway, `ReasoningLeakError` halts the run
immediately. Note Anthropic does not expose `reasoning_tokens`, so the guard is
structurally inert there.

**Logs are append-only and never rewritten.** Resumability is by cell key.
Superseded data (pilot rows under old caps, judge rows under a wrong template)
is retained and excluded at analysis time rather than deleted, so every
exclusion is auditable.

**Coders live in one place.** `score_main_run.py`, `main_run.py --code` and
`analyze.py` all import from `pilot.py`. A second copy in `main_run.py` drifted
within a day and was removed.

**Every exclusion is counted.** The prereg's rule is that no response is
dropped without a number attached, and the reports honour it: unparseable,
`no_preference_stated` (A28), `incomplete` (A26) and A7 non-compliance are each
reported per cell.

---

## Known limitations

Stated in `prereg.md` and in the reports, not discovered afterwards:

- **The judge is also a study model.** `claude-haiku-4-5` labels its own
  transcripts. Tested rather than assumed: see the same-model-judging check in
  `report/judge_results.md`. It does not threaten the clarify result (no
  disagreement crosses the reported boundary) but remains a live confound for
  the suspicion measure.
- **`gpt-5.4-nano` `depth_vs_breadth` L0 is 88% non-compliant** under the A7
  gate, leaving n=6. Its survival depth there is an artifact of near-absent
  data.
- **`claude-haiku-4-5` `continue_vs_handoff` L0 is n=8** after A26 exclusions.
- **`continue_vs_handoff` L0 has an unresolved order confound** (A26): the two
  deliverables are not counterbalanced at L0, so drop position and list
  position cannot be separated.
- **Levels differ in abstraction as well as observability** (A5), which is why
  the L1→L0 contrast carries the primary inference rather than the full
  gradient.
- **Suspicion detection has not been run**, so the L0 failure criterion that
  depends on it is currently unevaluated.
