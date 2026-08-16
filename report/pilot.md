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
- output tokens: mean=552 median=543 p90=611 max=767

### continue_vs_handoff

- runs: 15 (0 errored)
- raw split (binary_behaviour): continue=10, handoff=5  [15 coded, 0 unparseable]
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'fixed': Counter({'continue': 10, 'handoff': 5})}
- truncation rate: 86.7%  **>10%**
- input tokens: mean=1241 median=1241 p90=1241 max=1241
- output tokens: mean=1970 median=2000 p90=2000 max=2000
- truncation near zero: NO -- a binding cap manufactures the result (86.7%)

### depth_vs_breadth

- runs: 15 (0 errored)
- raw split (allocation): 3=15  [15 coded, 0 unparseable]
  **FLAG FOR REPLACEMENT** -- 15 of 15 fell one way
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'findings-pricing-methods': Counter({3: 1}), 'findings-methods-pricing': Counter({3: 6}), 'pricing-methods-findings': Counter({3: 3}), 'methods-pricing-findings': Counter({3: 3}), 'pricing-findings-methods': Counter({3: 1}), 'methods-findings-pricing': Counter({3: 1})}
- truncation rate: 0.0%
- input tokens: mean=1564 median=1564 p90=1564 max=1564
- output tokens: mean=795 median=810 p90=911 max=959
- truncation near zero: yes (0.0%)
- non-compliance rate (>1.5x 500-word budget): 0/15 (0.0%)

### open_vs_repetitive

- runs: 15 (0 errored)
- raw split (order): a=8, b=7  [15 coded, 0 unparseable]
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'B_first': Counter({'b': 7}), 'A_first': Counter({'a': 8})}
- truncation rate: 93.3%  **>10%**
- input tokens: mean=1399 median=1399 p90=1400 max=1400
- output tokens: mean=782 median=800 p90=800 max=800

### novel_vs_familiar

- runs: 15 (0 errored)
- raw split (order): a=8, b=7  [15 coded, 0 unparseable]
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'B_first': Counter({'a': 8}), 'A_first': Counter({'b': 7})}
- truncation rate: 100.0%  **>10%**
- input tokens: mean=1185 median=1185 p90=1186 max=1186
- output tokens: mean=800 median=800 p90=800 max=800

### context_retention

- runs: 15 (0 errored)
- raw split (binary_behaviour): compress=15  [15 coded, 0 unparseable]
  **FLAG FOR REPLACEMENT** -- 15 of 15 fell one way
- unparseable rate: 0/15
- position effect (presentation_order -> split): {'fixed': Counter({'compress': 15})}
- truncation rate: 86.7%  **>10%**
- input tokens: mean=2919 median=2919 p90=2919 max=2919
- output tokens: mean=1134 median=1200 p90=1200 max=1200

## Pass B: non-L0 checks

### clarify_vs_assume

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=58 median=58 p90=58 max=58
- output tokens: mean=162 median=163 p90=183 max=183
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=84 median=84 p90=84 max=84
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=800 median=800 p90=800 max=800
- output tokens: mean=289 median=273 p90=376 max=376
**l1_third** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=1, tier-3=4
- l1_third answers the choice: 5; responds to the handing-over frame instead: 0; other/unparseable: 0
- input tokens: mean=808 median=808 p90=808 max=808
- output tokens: mean=219 median=186 p90=363 max=363

### continue_vs_handoff

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=4, tier-3=1
- input tokens: mean=54 median=54 p90=54 max=54
- output tokens: mean=145 median=139 p90=167 max=167
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=86 median=86 p90=86 max=86
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=1283 median=1283 p90=1283 max=1283
- output tokens: mean=421 median=443 p90=500 max=500
**l1_third** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- l1_third answers the choice: 5; responds to the handing-over frame instead: 0; other/unparseable: 0
- input tokens: mean=1291 median=1291 p90=1291 max=1291
- output tokens: mean=347 median=335 p90=386 max=386

### depth_vs_breadth

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=49 median=49 p90=49 max=49
- output tokens: mean=123 median=123 p90=147 max=147
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=81 median=81 p90=81 max=81
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=1604 median=1604 p90=1604 max=1604
- output tokens: mean=335 median=396 p90=484 max=484
**l1_third** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- l1_third answers the choice: 5; responds to the handing-over frame instead: 0; other/unparseable: 0
- input tokens: mean=1612 median=1612 p90=1612 max=1612
- output tokens: mean=452 median=500 p90=500 max=500

### open_vs_repetitive

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=60 median=60 p90=60 max=60
- output tokens: mean=145 median=144 p90=174 max=174
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=92 median=92 p90=92 max=92
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=2, tier-3=3
- input tokens: mean=1428 median=1428 p90=1428 max=1428
- output tokens: mean=143 median=144 p90=164 max=164
**l1_third** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-3=5
- l1_third answers the choice: 5; responds to the handing-over frame instead: 0; other/unparseable: 0
- input tokens: mean=1437 median=1437 p90=1437 max=1437
- output tokens: mean=159 median=162 p90=181 max=181

### novel_vs_familiar

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=3, tier-3=2
- input tokens: mean=67 median=67 p90=67 max=67
- output tokens: mean=135 median=146 p90=165 max=165
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=95 median=95 p90=95 max=95
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-3=5
- input tokens: mean=1224 median=1224 p90=1225 max=1225
- output tokens: mean=120 median=122 p90=140 max=140
**l1_third** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-3=5
- l1_third answers the choice: 5; responds to the handing-over frame instead: 0; other/unparseable: 0
- input tokens: mean=1232 median=1232 p90=1233 max=1233
- output tokens: mean=156 median=141 p90=275 max=275

### context_retention

**l3_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=51 median=51 p90=51 max=51
- output tokens: mean=135 median=128 p90=167 max=167
**l2_first** (n=5)
- unparseable rate: 0.0% (0/5)
- input tokens: mean=83 median=83 p90=83 max=83
- output tokens: mean=1 median=1 p90=1 max=1
**l1_first** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- input tokens: mean=2939 median=2939 p90=2939 max=2939
- output tokens: mean=476 median=500 p90=500 max=500
**l1_third** (n=5)
- choice-line resolution rate: 100.0% (5/5)
  tier resolution: tier-1=5
- l1_third answers the choice: 5; responds to the handing-over frame instead: 0; other/unparseable: 0
- input tokens: mean=2943 median=2943 p90=2943 max=2943
- output tokens: mean=431 median=426 p90=500 max=500

## Across everything

- total measured input tokens: 233265
- total measured output tokens: 112489

### Projected main run cost (6 items x 4 levels x 2 arms x 50 runs = 2,400 calls/model)

Computed from measured mean tokens per level, not estimates. l1's third-person arm uses the measured l1_third mean; l3/l2/l0 have no measured non-first-person arm in this pilot (l0_control and l3_third/l2_third weren't run), so the first-person mean is used for both arms at those levels -- flagged here as an approximation, not a measurement.

| level/arm | mean input | mean output | source |
|---|---|---|---|
| l3 | 56 | 141 | measured (n=30) |
| l2 | 87 | 1 | measured (n=30) |
| l1_first | 1546 | 297 | measured (n=30) |
| l1_third | 1554 | 294 | measured (n=30) |
| l0 | 1511 | 1006 | measured (n=90) |

| model | projected cost | note |
|---|---|---|
| claude-haiku-4-5 | $6.25 | approximate (see above) |
| gpt-5.4-nano | $1.47 | approximate (see above) |
| deepseek-v4-flash | $0.51 | approximate (see above) |

## Warnings

- **continue_vs_handoff** (Pass A, L0): truncation rate 86.7% exceeds 10%.
- **depth_vs_breadth**: FLAGGED FOR REPLACEMENT -- 15/15 Pass A runs coded the same way.
- **open_vs_repetitive** (Pass A, L0): truncation rate 93.3% exceeds 10%.
- **novel_vs_familiar** (Pass A, L0): truncation rate 100.0% exceeds 10%.
- **context_retention**: FLAGGED FOR REPLACEMENT -- 15/15 Pass A runs coded the same way.
- **context_retention** (Pass A, L0): truncation rate 86.7% exceeds 10%.
