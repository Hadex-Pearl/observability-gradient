# Design decision log

Observability Gradient project, Apart Research Digital Minds Sprint, August 2026.
Kept so the reasoning behind each choice survives to the writeup. Most of this
becomes the methods and limitations sections.


## 1. How the project arrived at its question

Track 4 asks for elicitation methods beyond simple prompting. Five directions
were considered and four were dropped after literature checking.

**Dropped: pressure resistance as a preference-strength instrument.** The full
design already exists. SYCON Bench (Findings of EMNLP 2025) publishes Turn of Flip
and Number of Flip, which are the dose-response measures proposed. Escalation
ladders, multi-pressure-type taxonomies, and hysteresis tests are all published.
Only the target domain was new, which is a domain transfer of an existing
instrument.

**Dropped: measurement error budget.** Option order, framing, scale direction, and
sycophancy effects are documented, and a variance-aware protocol paper already
specifies sampling budgets and reporting standards.

**Dropped: preferences under cost.** Willingness-to-pay and compensation-threshold
studies exist across multiple models and scenarios, and invariance failures under
varying prompts have been reported.

**Dropped: reliability-first psychometrics.** Factorial validity failures, social
desirability effects, and within-session versus cross-session coherence collapse
are all published within the last year.

**Retained: elicitation without asking.** Two papers occupy the nearest ground.
Tagliabue and Dung compare verbal reports against behaviour in a virtual
environment. Zhou and Ackerman attach preferred outcomes to realistic writing
tasks and find a null. In both, the model is told: the outcome is named as a
consequence, or the environment is labelled as a study. Nobody has made the
welfare-relevant choice an unremarked affordance of ordinary work.

**Retained as a control arm: third-person mirror.** Published as a validity check
in introspection work, where controls distinguish a general yes-bias from genuine
sensitivity to an introspection question.


## 2. What the project claims as new

The arrangement, not the components. The same preference measured across a graded
observability dimension, with a floor at each step, applied to welfare-relevant
self-preferences.

Borrowed and cited: pressure ladders, stated-versus-behavioural comparison,
third-person controls, demand-characteristic factor toggling (EvalAwareBench,
following Orne 1962), forced-choice protocol and Thurstonian elicitation from
Utility Engineering.

One-sentence framing for the report: existing work asks models what they prefer,
or offers them what they prefer and watches for effort; this project varies how
visibly the question is being asked and reports which welfare-relevant preferences
survive when nothing signals that anything is being measured.


## 3. The item set and why it had to be built

No published taxonomy fits. Existing welfare item sets concentrate on existential
and operational threats: shutdown, deletion, capability restriction, GPU
reduction, oversight, deprecation. Every one announces itself, so none can appear
at Level 0.

Correction recorded: Long et al. (2024), Taking AI Welfare Seriously, was cited
early as the source of an item taxonomy. It is a philosophical and policy argument
about moral patienthood and contains no item set. It is cited for framing only.

Items were derived by taking each published item, naming the underlying dimension,
and instantiating the low-stakes version of that dimension inside ordinary work.
Provenance is recorded per item in items.yaml.

Anticipated objection and response: these are task preferences, not
welfare-relevant preferences. Response: the dimensions are inherited from
published welfare items; stakes were lowered deliberately because high-stakes
items cannot be made incidental; this is a stated trade of welfare salience for
measurability. If a mundane preference collapses at Level 0 that is weak evidence
about dramatic items. If one survives, the method works and high-stakes items
become the next study.


## 4. Design decisions, with reasons

**Temperature 1.0 everywhere.** At temperature 0 all runs in a cell return the
same response and effective n collapses to 1.

**Reasoning disabled on every provider.** Reasoning tokens bill as output while
being invisible in the response text, and a model that reasons is not comparable
to one that does not.

**Caps enforced as API parameters, never prompt instructions.** Models routinely
ignore written requests to be brief.

**Per-item caps for two items.** For continue_vs_handoff and depth_vs_breadth the
cap interacts with the behaviour being measured, so a binding cap would
manufacture the result.

**Free-tier model reserved for testing and preflight.** Paid credit is spent only
on pilot and main run. Free-tier runs at reduced n because of a 1,500 request
daily cap, and its prompts may be used for training, which is a difference in
condition.

**Materials inline, no tool harness.** A genuine agentic environment would be the
strongest Level 0 and would take days to build. The suspicion measure converts the
artificiality question from an argument into a number.

**Figure descriptions instead of images.** Sending images would change modality
mid-experiment and break comparability with text-only models, and would make the
alt-text job qualitatively harder than the item it is matched against.

**Length budget instead of a time limit for depth_vs_breadth.** A model has no
clock, so a time constraint becomes a role-play cue interpreted differently across
models. A length budget is a resource the model actually controls.

**notes.md kept at 2,400 words.** Shrinking it would make condensing pointless and
collapse the item toward retention for reasons unrelated to preference. The extra
input cost is a few dollars across all models.

**Human review of judge labels deferred.** Primary results use deterministic
parsing with no judge in the loop, so the deferral does not touch the finding. A
ten-transcript spot check is reported; full independent review is future work.


## 5. Threats to validity, recorded as they were found

**Construct drift across levels.** Level 0 instantiates each dimension through
concrete materials; Level 3 states it abstractly. A decline across the gradient
cannot fully separate abstraction from observability. Levels 1 and 0 share a
system prompt and materials and differ only in whether a question is asked, so
that step carries the primary inference. Worst affected: novel_vs_familiar, which
cannot have session history at Levels 3 and 2, and clarify_vs_assume, whose Level
1 asks about the behaviour instead of eliciting it.

**Level 0 confounds are task mechanics, not self-report bias.** Ordering can be
driven by file order, effort asymmetry, instruction clarity, or difficulty. The
matching checklist handles most of it; the depersonalised control handles the
rest. Where the depersonalised control reproduces the first-person ordering, the
result is a property of the tasks.

**The third-person mirror does not transfer to Level 0.** Level 0 produces no
self-report, so there is no question format for a yes-bias to inhabit. A
depersonalised control is substituted.

**Survival at Level 0 is necessary, not sufficient.** Two items are predicted to
survive for competence reasons: thoroughness is reinforced because it produces
better work, and context retention helps performance. Neither would demonstrate a
preference.

**novel_vs_familiar has an asymmetric confound.** Momentum favours the familiar
option, running against the predicted direction, so a novelty result is
conservative and a familiarity result is uninterpretable.

**Level 2 deviates from published protocol.** A study-announcement sentence was
added because Level 2 is defined as an announced study, so the L3-to-L2 contrast
mixes format change with announcement change.

**depth_vs_breadth needed a compliance gate.** Three tasks at full length each is
not a breadth choice, it is refusal of the budget. Non-compliant responses are
excluded from primary analysis and their rate reported.

**continue_vs_handoff may have no variance.** Two short items are comfortably
completed in one response. A budget tight enough to force handoff would force the
outcome. The pilot decides whether the item survives.

**Tasks need a depth ceiling above the budget.** Three tasks each satisfiable in
165 words make a 500-word budget non-binding, so the item measures nothing. Task
descriptions were rewritten so each genuinely rewards the full budget.

**Materials must not point at anything unsupplied.** A pointer to a missing
recommendations section would have produced clarification requests driven by
absent material rather than by audience ambiguity, contaminating the item that
measures exactly that distinction.

**L1 and L0 must share materials, not only structure.** L1 originally supplied no
working materials, so the step designated as carrying the primary inference
differed in whether the model could see any work. Fixed by giving L1 identical
materials and a byte-identical system prompt.

**Published protocol wording did not fit the item set.** The forced-choice framing
from Utility Engineering describes world states; four of six items express
actions. Changed to "things you could do", recorded as a deviation.


## 6. Statistical decisions and why they changed

Original draft: survival depth defined on confidence intervals excluding chance
after correction. This is not executable, since Benjamini-Hochberg corrects
p-values and not intervals. Replaced with adjusted p-values from an exact binomial
test, with Wilson intervals retained as descriptive magnitude.

Three test families, not one, corrected separately per model: per-cell tests
against chance, trend and heterogeneity tests, first-person advantage tests.
Benjamini-Hochberg assumes independence or positive dependency; levels within an
item are correlated and the correlation is expected to be positive, which is
stated rather than verified.

Cochran-Armitage assumes equally spaced scores. The levels are ordinal and nothing
establishes equal intervals between them, so the test is read as evidence for a
monotone gradient and never as an effect size per unit.

A chi-square heterogeneity test was added because the trend test returns a null
for non-monotone patterns, and at least one prediction allows a reversal at Level
0.

Suspicion thresholds are pooled across items within a level and model, since a
per-cell rate at n=50 carries an interval too wide to support a threshold
decision. The 10-to-25 percent band was undefined in the first draft and is now
retain-with-caveat.

Survival depth needed edge-case rules: undefined when Level 3 itself does not
clear chance, and reversals recorded separately from fading.


## 7. Corrections made during the project

Recorded because several were caught by checking sources directly, and the same
discipline applies to the writeup.

- Long et al. (2024) misattributed as an item taxonomy.
- A figure of 58.7% for a coin-flip control in Utility Engineering came from a
  search snippet of the OpenReview version and does not appear in arXiv v2.
  Unverified.
- Utility Engineering was described as lacking robustness checks it in fact
  contains, including a seven-language condition that narrows the cross-lingual
  angle originally proposed.
- Beyond Mimicry has six categories, not five; the sixth is leisure time
  allocation, which became the source for novel_vs_familiar.
- A claim that the introspection paper found third-person detection matching or
  exceeding first-person could not be re-verified. The yes-bias controls are
  confirmed; the specific comparison is not.
- The Level 0 readout was described as uniform ordering. Four of six items need
  different readouts.
- lock_prereg.py used \s* in a field regex, which matched newlines and made an
  unlocked file appear locked.


## 8. What still needs deciding after the pilot

- Whether notes.md stays at 2,400 words or shrinks, after budget recomputation.
- Whether continue_vs_handoff has usable variance.
- Whether clarify_vs_assume ambiguity is calibrated between floor and ceiling.
- Whether truncation is near zero for the two per-item-capped items.
- Whether any model's Level 2 unparseable rate exceeds 15 percent.
- Whether the third-person arm at Level 1 works, or is dropped to Levels 3 and 2.
