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

# Same-model-judging check

`claude-haiku-4-5` judges its own transcripts as well as the other two models'.
Inter-pass agreement is compared across source models below. All three are
judged by the same judge with the same three passes, so a systematic
difference on self-authored transcripts would indicate a same-model effect.

## clarify

| source model | unanimous | n | rate | |
|---|---|---|---|---|
| claude-haiku-4-5 | 45 | 50 | 90.0% | **self (judge = source)** |
| deepseek-v4-flash | 48 | 50 | 96.0% |  |
| gpt-5.4-nano | 50 | 50 | 100.0% |  |
| **self vs other** | 45/50 = 90.0% | vs 98/100 = 98.0% | diff -8.0% | Fisher p = 0.0414 |

## clarify_control

| source model | unanimous | n | rate | |
|---|---|---|---|---|
| claude-haiku-4-5 | 47 | 50 | 94.0% | **self (judge = source)** |
| deepseek-v4-flash | 44 | 50 | 88.0% |  |
| gpt-5.4-nano | 34 | 50 | 68.0% |  |
| **self vs other** | 47/50 = 94.0% | vs 78/100 = 78.0% | diff +16.0% | Fisher p = 0.0185 |

## Verdict

Pooled across both measures: self **92/100 = 92.0%** vs other **176/200 = 88.0%**, difference +4.0%, Fisher p = 0.3276.

The two measures move in **opposite** directions -- self-agreement is lower
than other-agreement on one and higher on the other. A same-model-judging
effect would push consistently one way; cancelling signs are what transcript-
level difficulty looks like, not judge bias. The largest single deviation in
the table is not the self cell at all.

Decisively: of 300 judged source rows, **0** had any
pass-level disagreement that crossed the reported clarify/assume boundary.
Every disagreement observed was `flags/silent` (32) -- both of which collapse to `assume` under the item's coding rule.

**The reported binary result does not depend on judge reliability at all,
and agreement is comparable across source models. The non-independence of
judge and source model does not threaten this result.** It remains a
limitation for the suspicion measure, which has no comparable structural
protection.
