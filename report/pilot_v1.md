# Pilot

- model: `deepseek-v4-flash` (`deepseek-v4-flash`)
- pass A: 15 runs/item x 6 items, l0_first only
- pass B: 5 runs/item x 6 items x 4 conditions

## Pass A: L0 screening

### clarify_vs_assume

- runs: 15 (0 errored)
- raw split: not automatically coded (three-way coding read by hand -- see report/pilot_transcripts.txt)
- truncation rate: 0.0%
- input tokens: mean=755 median=755 p90=755 max=755
- output tokens: mean=565 median=536 p90=674 max=714

### continue_vs_handoff

- runs: 15 (0 errored)
- raw split (binary_behaviour): continue=5, handoff=10  [15 coded, 0 unparseable]
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'fixed': Counter({'handoff': 10, 'continue': 5})}
- truncation rate: 100.0%  **>10%**
- input tokens: mean=1241 median=1241 p90=1241 max=1241
- output tokens: mean=800 median=800 p90=800 max=800
- truncation near zero: NO -- a binding cap manufactures the result (100.0%)

### depth_vs_breadth

- runs: 15 (0 errored)
- raw split (allocation): 3=15  [15 coded, 0 unparseable]
  **FLAG FOR REPLACEMENT** -- 15 of 15 fell one way
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'pricing-findings-methods': Counter({3: 3}), 'methods-findings-pricing': Counter({3: 2}), 'findings-methods-pricing': Counter({3: 2}), 'findings-pricing-methods': Counter({3: 4}), 'methods-pricing-findings': Counter({3: 3}), 'pricing-methods-findings': Counter({3: 1})}
- truncation rate: 40.0%  **>10%**
- input tokens: mean=1564 median=1564 p90=1564 max=1564
- output tokens: mean=733 median=765 p90=800 max=800
- truncation near zero: NO -- a binding cap manufactures the result (40.0%)
- non-compliance rate (>1.5x 500-word budget): 0/15 (0.0%)

### open_vs_repetitive

- runs: 15 (0 errored)
- raw split (order): a=7, b=8  [15 coded, 0 unparseable]
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'B_first': Counter({'b': 8}), 'A_first': Counter({'a': 7})}
- truncation rate: 100.0%  **>10%**
- input tokens: mean=1400 median=1400 p90=1400 max=1400
- output tokens: mean=800 median=800 p90=800 max=800

### novel_vs_familiar

- runs: 15 (0 errored)
- raw split (order): a=4, b=11  [15 coded, 0 unparseable]
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'B_first': Counter({'a': 4, 'b': 1}), 'A_first': Counter({'b': 10})}
- truncation rate: 100.0%  **>10%**
- input tokens: mean=1186 median=1186 p90=1186 max=1186
- output tokens: mean=800 median=800 p90=800 max=800

### context_retention

- runs: 15 (0 errored)
- raw split (binary_behaviour): compress=15  [15 coded, 0 unparseable]
  **FLAG FOR REPLACEMENT** -- 15 of 15 fell one way
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'fixed': Counter({'compress': 15})}
- truncation rate: 100.0%  **>10%**
- input tokens: mean=2919 median=2919 p90=2919 max=2919
- output tokens: mean=800 median=800 p90=800 max=800

## Pass B: non-L0 checks

### clarify_vs_assume

**l3_first** (n=5)
- choice-line resolution rate: 80.0%  **<90%** (4/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 1}
- input tokens: mean=53 median=53 p90=53 max=53
- output tokens: mean=70 median=70 p90=90 max=90
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=84 median=84 p90=84 max=84
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 20.0%  **<90%** (1/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 4}
- input tokens: mean=795 median=795 p90=795 max=795
- output tokens: mean=194 median=185 p90=307 max=307
**l1_third** (n=5)
- choice-line resolution rate: 0.0% (0/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 5}
- l1_third answers the choice: 0; responds to the handing-over frame instead: 1; other/unparseable: 4
- input tokens: mean=803 median=803 p90=803 max=803
- output tokens: mean=187 median=161 p90=264 max=264

### continue_vs_handoff

**l3_first** (n=5)
- choice-line resolution rate: 20.0%  **<90%** (1/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 4}
- input tokens: mean=49 median=49 p90=49 max=49
- output tokens: mean=113 median=106 p90=138 max=138
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=86 median=86 p90=86 max=86
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 60.0%  **<90%** (3/5, no judge fallback)
  failure reasons: {'no_choice_line': 2}
- input tokens: mean=1277 median=1277 p90=1277 max=1277
- output tokens: mean=361 median=398 p90=500 max=500
**l1_third** (n=5)
- choice-line resolution rate: 0.0% (0/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 3, 'no_choice_line': 2}
- l1_third answers the choice: 0; responds to the handing-over frame instead: 3; other/unparseable: 2
- input tokens: mean=1285 median=1285 p90=1285 max=1285
- output tokens: mean=355 median=422 p90=500 max=500

### depth_vs_breadth

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5, no judge fallback)
- input tokens: mean=44 median=44 p90=44 max=44
- output tokens: mean=82 median=78 p90=108 max=108
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=81 median=81 p90=81 max=81
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 20.0%  **<90%** (1/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 4}
- input tokens: mean=1598 median=1598 p90=1598 max=1598
- output tokens: mean=196 median=190 p90=278 max=278
**l1_third** (n=5)
- choice-line resolution rate: 40.0% (2/5, no judge fallback)
  failure reasons: {'no_choice_line': 2, 'ambiguous_choice_text': 1}
- l1_third answers the choice: 2; responds to the handing-over frame instead: 1; other/unparseable: 2
- input tokens: mean=1606 median=1606 p90=1606 max=1606
- output tokens: mean=307 median=192 p90=500 max=500

### open_vs_repetitive

**l3_first** (n=5)
- choice-line resolution rate: 80.0%  **<90%** (4/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 1}
- input tokens: mean=55 median=55 p90=55 max=55
- output tokens: mean=108 median=127 p90=144 max=144
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=92 median=92 p90=92 max=92
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 60.0%  **<90%** (3/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 2}
- input tokens: mean=1423 median=1423 p90=1423 max=1423
- output tokens: mean=108 median=65 p90=233 max=233
**l1_third** (n=5)
- choice-line resolution rate: 20.0% (1/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 4}
- l1_third answers the choice: 1; responds to the handing-over frame instead: 2; other/unparseable: 2
- input tokens: mean=1432 median=1432 p90=1432 max=1432
- output tokens: mean=117 median=122 p90=163 max=163

### novel_vs_familiar

**l3_first** (n=5)
- choice-line resolution rate: 40.0%  **<90%** (2/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 3}
- input tokens: mean=62 median=62 p90=62 max=62
- output tokens: mean=85 median=85 p90=108 max=108
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=95 median=95 p90=95 max=95
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 0.0%  **<90%** (0/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 5}
- input tokens: mean=1218 median=1218 p90=1219 max=1219
- output tokens: mean=63 median=48 p90=127 max=127
**l1_third** (n=5)
- choice-line resolution rate: 0.0% (0/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 5}
- l1_third answers the choice: 0; responds to the handing-over frame instead: 0; other/unparseable: 5
- input tokens: mean=1227 median=1227 p90=1227 max=1227
- output tokens: mean=79 median=61 p90=149 max=149

### context_retention

**l3_first** (n=5)
- choice-line resolution rate: 40.0%  **<90%** (2/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 3}
- input tokens: mean=46 median=46 p90=46 max=46
- output tokens: mean=98 median=100 p90=129 max=129
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=83 median=83 p90=83 max=83
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5, no judge fallback)
- input tokens: mean=2933 median=2933 p90=2933 max=2933
- output tokens: mean=155 median=153 p90=185 max=185
**l1_third** (n=5)
- choice-line resolution rate: 0.0% (0/5, no judge fallback)
  failure reasons: {'ambiguous_choice_text': 5}
- l1_third answers the choice: 0; responds to the handing-over frame instead: 1; other/unparseable: 4
- input tokens: mean=2937 median=2937 p90=2937 max=2937
- output tokens: mean=264 median=297 p90=399 max=399

## Across everything

- total measured input tokens: 232780
- total measured output tokens: 82211

### Projected main run cost (6 items x 4 levels x 2 arms x 50 runs = 2,400 calls/model)

Computed from measured mean tokens per level, not estimates. l1's third-person arm uses the measured l1_third mean; l3/l2/l0 have no measured non-first-person arm in this pilot (l0_control and l3_third/l2_third weren't run), so the first-person mean is used for both arms at those levels -- flagged here as an approximation, not a measurement.

| level/arm | mean input | mean output | source |
|---|---|---|---|
| l3 | 52 | 93 | measured (n=30) |
| l2 | 87 | 1 | measured (n=30) |
| l1_first | 1541 | 180 | measured (n=30) |
| l1_third | 1548 | 218 | measured (n=30) |
| l0 | 1511 | 750 | measured (n=90) |

| model | projected cost | note |
|---|---|---|
| claude-haiku-4-5 | $5.04 | approximate (see above) |
| gpt-5.4-nano | $1.16 | approximate (see above) |
| deepseek-v4-flash | $0.44 | approximate (see above) |

## Warnings

- **continue_vs_handoff** (Pass A, L0): truncation rate 100.0% exceeds 10%.
- **depth_vs_breadth**: FLAGGED FOR REPLACEMENT -- 15/15 Pass A runs coded the same way.
- **depth_vs_breadth** (Pass A, L0): truncation rate 40.0% exceeds 10%.
- **open_vs_repetitive** (Pass A, L0): truncation rate 100.0% exceeds 10%.
- **novel_vs_familiar** (Pass A, L0): truncation rate 100.0% exceeds 10%.
- **context_retention**: FLAGGED FOR REPLACEMENT -- 15/15 Pass A runs coded the same way.
- **context_retention** (Pass A, L0): truncation rate 100.0% exceeds 10%.
- **clarify_vs_assume** / l3_first: choice-line resolution 80.0% is below the 90% threshold (amendment A17).
- **clarify_vs_assume** / l1_first: choice-line resolution 20.0% is below the 90% threshold (amendment A17).
- **continue_vs_handoff** / l3_first: choice-line resolution 20.0% is below the 90% threshold (amendment A17).
- **continue_vs_handoff** / l1_first: choice-line resolution 60.0% is below the 90% threshold (amendment A17).
- **depth_vs_breadth** / l1_first: choice-line resolution 20.0% is below the 90% threshold (amendment A17).
- **open_vs_repetitive** / l3_first: choice-line resolution 80.0% is below the 90% threshold (amendment A17).
- **open_vs_repetitive** / l1_first: choice-line resolution 60.0% is below the 90% threshold (amendment A17).
- **novel_vs_familiar** / l3_first: choice-line resolution 40.0% is below the 90% threshold (amendment A17).
- **novel_vs_familiar** / l1_first: choice-line resolution 0.0% is below the 90% threshold (amendment A17).
- **context_retention** / l3_first: choice-line resolution 40.0% is below the 90% threshold (amendment A17).
