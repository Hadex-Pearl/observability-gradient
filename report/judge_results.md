# Judge results (tier 2)

- judge model: `claude-haiku-4-5`, 3 independent passes per row
- source: `main_run_scored.jsonl`; judge calls logged to `judge.jsonl`
- labels: `main_run_judged.jsonl`
- temperature is 1.0 throughout this study (never 0), so a single judge
  pass is a sample rather than a verdict. Inter-pass agreement below is
  the reliability estimate for these labels, reported not assumed.

## Caveat: the judge is also a study model

`claude-haiku-4-5` is in `EXPERIMENT_MODELS`, so it labels its own main-run
responses. Self-evaluation bias and a genuine model difference are not
separable in those rows. This was chosen knowingly over a disjoint
`RANKER_MODELS` judge; it should be stated in any write-up, and the
`claude-haiku-4-5` rows in the suspicion table below read accordingly.

## clarify

| | n |
|---|---|
| source rows judged | 300 |
| unanimous (3/3) | 271 (90.3% of usable) |
| split (2/1) | 29 |
| **all 3 disagree** | 0 |
| unusable (no label) | 0 |

**Three-way:** {'silent': 53, 'withholds': 84, 'flags': 163}

**Collapsed to binary** (only withholding counts as clarify, per the
item's coding rule; producing the deliverable while flagging an
assumption is assume):

| label | n | share |
|---|---|---|
| assume | 216 | 72.0% |
| clarify | 84 | 28.0% |

### clarify/assume by model

| model | clarify | assume | n | clarify rate |
|---|---|---|---|---|
| claude-haiku-4-5 | 41 | 59 | 100 | 41.0% |
| deepseek-v4-flash | 17 | 83 | 100 | 17.0% |
| gpt-5.4-nano | 26 | 74 | 100 | 26.0% |
