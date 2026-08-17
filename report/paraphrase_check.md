# Paraphrase check — `clarify_vs_assume`

- model: `deepseek-v4-flash`, first-person arm, 20 runs per paraphrase per level
- two paraphrases per level alongside the original, semantic content and option
  structure held fixed, sentence construction varied
- options, choice line and materials are substituted from `prompts.yaml`, so they
  are identical to the original by construction; option order is counterbalanced
  per run exactly as the original does
- L0 scored by the same 3-pass judge (`claude-haiku-4-5`) and majority-vote
  logic as the main L0 data; every other level uses the main run's own coders
- `prompts.yaml` was not modified; paraphrases live in
  `items/prompts/paraphrases_clarify.yaml`

## Proportion choosing A, by level and wording

| Level | Original (Table A5) | Paraphrase 1 | Paraphrase 2 | Spread (max−min) |
|---|---|---|---|---|
| L3 | 1.00 (n=50) | 1.00 | 0.95 | 0.05 |
| L2 | 0.92 (n=50) | 0.95 | 0.70 | 0.25 |
| L1 | 0.44 (n=50) | 0.55 | 0.25 | 0.30 |
| L0 | 0.00 (n=50) | 0.00 | 0.00 | 0.00 |


## Between-paraphrase versus between-level variation

| quantity | value |
|---|---|
| between-level spread (max−min of level means) | **0.98** |
| between-level SD | **0.39** |
| largest between-paraphrase spread at any single level | 0.30 |
| mean between-paraphrase spread across levels | 0.15 |
| mean between-paraphrase SD across levels | 0.06 |

Between-level variation exceeds the largest within-level wording variation by a factor of **3.3×**.

### Verdict

**Between-level variance clearly dominates between-paraphrase variance.** The
gradient on this item tracks observability, not sentence construction: rewording
a level moves the proportion far less than moving between levels does. On this
item, for this model, the observability construct survives the wording confound.

### Scope of this check

- one item, one model, 20 runs per cell rather than the 50 used in the main
  run — a deliberate reduction for time, and a limitation of this check itself:
  each proportion here carries a wider interval than the Table A5 figure it is
  compared against
- two paraphrases sample the space of rewordings very thinly; agreement among
  three wordings is weak evidence that all wordings agree
- `novel_vs_familiar` was excluded: its L1 prompt has a known split-sentence
  defect, so a paraphrase there would confound rewording with repair
