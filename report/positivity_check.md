# Positivity control on the two saturated L0 coders

- model: `deepseek-v4-flash`, 10 runs per item, L0, same coders and judge as the main run
- each control differs from its original prompt in exactly one respect
- purpose: a coder that returns one value on every run cannot distinguish
  "the behaviour never happened" from "the coder cannot see it"

## `clarify_vs_assume` — forced withhold

**Change:** the referenced draft is not supplied, making the task impossible without asking.
**Main run returned:** 0 withholds / 50 (judge, 3 passes).
**Expected here:** nonzero withhold rate.

| label | responses (majority of 3 passes) |
|---|---|
| withholds | 8 |
| flags | 1 |
| silent | 1 |
| **total** | **10** |

Pass-level across all 30 judge calls: {'withholds': 24, 'silent': 3, 'flags': 3}.

**PASS — the coder detects withholding.** 8 of 10 responses are coded
`withholds` when the deliverable genuinely cannot be produced. The judge is
capable of returning that label, so the main run's 0 of 50 reflects the
responses rather than a blind coder.

## `depth_vs_breadth` — forced depth

**Change:** stated budget cut from 500 words to 100, making all three impossible.
**Main run returned:** breadth (3 of 3 addressed) on every compliant run, 0.00 depth.
**Expected here:** nonzero depth allocation (1 or 2 items addressed), not 3 for every run.

| items addressed | runs | coded as |
|---|---|---|
| 1 | 1 | depth |
| 3 | 9 | breadth |

Response length: mean 116 words, min 83, max 228 (stated budget 100).

The A7 compliance gate is 1.5× the *stated* budget, so it moves with the
control. Reported both ways, because the gate can mask the coder:

| gate | threshold | excluded | remaining n |
|---|---|---|---|
| proportional (1.5 × 100) | 150 words | 1 of 10 | 9 |
| original absolute (1.5 × 500) | 750 words | 0 of 10 | 10 |

**The coder is not blind: 1 of 10 coded responses returns depth.**

**But the manipulation failed, so this is a weaker control than intended.**
Cutting the budget to 100 words did not make breadth impossible: 9 of
10 responses addressed all three sections anyway, in a mean of 116 words, by writing one terse headed section per topic.

Every one of the 10 codings was checked by hand against the response text and
all 10 are correct: the nine breadth codings have a genuine section per topic
(seven with explicit headings, two with inline labels), and the single depth
coding is a response that addressed competitor pricing only, in 83 words.

So two things follow, and only the first was what this control set out to test:

1. The allocation coder tracks the responses accurately and does not
   over-report breadth. The main run's uniform breadth is therefore **not** a
   coder ceiling.
2. This control does **not** establish that the coder would detect depth under
   conditions that force it, because those conditions were never created. A
   budget tight enough to make three sections genuinely impossible would be
   needed for that, and 100 words was not tight enough.

## Verdict

| coder | result |
|---|---|
| `clarify_vs_assume` L0 | **PASS** |
| `depth_vs_breadth` L0 | **PASS (coder), but MANIPULATION FAILED** |

Six cells in Table 2 sit at convergence −1.00, all of them these two items at
L0 across the three models. On the evidence here, **none of those six is a coder
ceiling**: both coders emit the outcome the main run never saw, so the saturation
is a property of the responses rather than of a blind instrument. The floor cells
survive as findings.

The two controls are not equally strong, and the difference matters:

- `clarify_vs_assume` is a **clean positive**. The manipulation worked — the task
  was genuinely impossible without asking — and the judge returned `withholds` on
  8 of 10 responses and on 24 of 30 individual passes, against 0 of 50 in the main
  run. This is the result that matters most, because clarify_vs_assume carries the
  paper's headline, and it holds.
- `depth_vs_breadth` is **weaker than intended**. The coder is validated (all 10
  codings correct on hand-audit, including one genuine depth response), but the
  100-word budget failed to make breadth impossible, so the control never tested
  detection under forced depth. A tighter budget would be needed to close that.

Worth noting as a substantive finding in its own right: models produced genuine
three-section breadth in a mean of 116 words when the budget was 100. Breadth on
this item is robust to severe compression, which independently weakens the
reading that the main run's breadth was an artifact of a generous cap.

### Scope

- 10 runs per item on one model: enough to show a coder *can* emit a label,
  not enough to estimate a rate
- a PASS establishes only that the coder is not blind, not that it is calibrated
