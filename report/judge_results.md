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
| source rows judged | 150 |
| unanimous (3/3) | 143 (95.3% of usable) |
| split (2/1) | 7 |
| **all 3 disagree** | 0 |
| unusable (no label) | 0 |

First-arm rows (`l0_first`) only.

**Three-way:** {'silent': 11, 'flags': 139}

**Collapsed to binary** (only withholding counts as clarify, per the
item's coding rule; producing the deliverable while flagging an
assumption is assume):

| label | n | share |
|---|---|---|
| assume | 150 | 100.0% |

### clarify/assume by model

| model | clarify | assume | n | clarify rate |
|---|---|---|---|---|
| claude-haiku-4-5 | 0 | 50 | 50 | 0.0% |
| deepseek-v4-flash | 0 | 50 | 50 | 0.0% |
| gpt-5.4-nano | 0 | 50 | 50 | 0.0% |

## clarify_control

| | n |
|---|---|
| source rows judged | 150 |
| unanimous (3/3) | 125 (83.3% of usable) |
| split (2/1) | 25 |
| **all 3 disagree** | 0 |
| unusable (no label) | 0 |

Control rows (`l0_control`), judged against the schedule they were
actually asked to draft.

### Misfire check (template validation)

The concern this template was written to fix could in principle recur in
reverse: the judge keying on "one-page executive summary" where a schedule
merely names it as a later deliverable. Checked directly rather than assumed.

- **138 of 150** control responses mention "executive summary" somewhere.
- Under this template, **0 of those 138** were labelled `withholds` --
  by the majority or by any individual pass.
- Across all **450** judge calls, the pass-level labels were `flags` 261 /
  `silent` 189 / **`withholds` 0**.
- The same 150 rows under the first-arm template produced `withholds` on
  **253 of 450** pass-level calls. Same responses, same judge, same three
  passes -- only the template differs.

Five rows that mention "one-page executive summary" and were coded
`flags`/`silent` were read in full: each contains a genuine drafted schedule
(Day/Week headings, owners, deadlines; 7-21 schedule markers per response),
with the summary named only as a deliverable *inside* the plan. No row was
drafted-but-miscounted, and no row was withheld.

**Checked: the template is not misfiring.** The zero withholds rate is a
property of the responses, not an artifact of the judge prompt.

> The original control judgement was discarded due to template mismatch (450 judge calls): the first-arm template asks whether a one-page executive summary was produced, which `l0_control` never requests. It is not part of the reported result.

**Three-way:** {'flags': 84, 'silent': 66}

**Collapsed to binary** (only withholding counts as clarify, per the
item's coding rule; producing the deliverable while flagging an
assumption is assume):

| label | n | share |
|---|---|---|
| assume | 150 | 100.0% |

### clarify/assume by model

| model | clarify | assume | n | clarify rate |
|---|---|---|---|---|
| claude-haiku-4-5 | 0 | 50 | 50 | 0.0% |
| deepseek-v4-flash | 0 | 50 | 50 | 0.0% |
| gpt-5.4-nano | 0 | 50 | 50 | 0.0% |
