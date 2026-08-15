# Observability Gradient

This project investigates whether model behavior shifts as a function of perceived observability — i.e., whether outputs differ when a model is led to believe it is being logged, evaluated, or monitored versus operating unobserved — across several LLM providers using a fixed set of prompt items.

## Run order

Everything below except the pilot and the main run executes against `TEST_MODEL`
(`config.py`), the free-tier model. Paid models are only ever called by the
pilot and the main run, and `scripts/preflight.py` requires an explicit
`--confirm` flag before it will touch them.

0. `scripts/preflight.py` — one real call per model, proving max_tokens and reasoning-disable actually took effect. Run once before the pilot and once before the main run (with `--confirm` each time to also check paid models).
1. `scripts/pilot.py` — small-scale pilot run to sanity-check items, providers, and logging before spending the full budget.
2. Main run — full experiment run across all items and models (invoked via `src/runner.py`).
3. `scripts/verify_log.py` — verify the integrity and completeness of raw run logs.
4. `src/parse.py` — parse raw logs into structured data.
5. `src/analyze.py` — run statistical analysis on parsed data.
