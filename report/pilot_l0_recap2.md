# L0 recap round 2

- model: `deepseek-v4-flash`
- 15 runs per condition
- context_retention length-ratio coder threshold: < 0.6 x 2166 = 1300 words -> compress

### continue_vs_handoff / l0_first (arm=first)

- cap: 4000
- runs: 15
- truncation rate: 13.3%  **>10%**
- output tokens: {'mean': 2717.0666666666666, 'median': 2653, 'p90': 4000, 'max': 4000}
- raw split: continue=1, handoff=14  [15 coded, 0 unparseable]
- response words: mean=2162 median=2157 min=1109 max=3178

### context_retention / l0_control (arm=control)

- cap: 3500
- runs: 15
- truncation rate: 0.0%
- output tokens: {'mean': 747.3333333333334, 'median': 686, 'p90': 1124, 'max': 1370}
- raw split: compress=15  [15 coded, 0 unparseable]
- response words: mean=534 median=460 min=280 max=960

## Verdict

- STOP -- **continue_vs_handoff** still binds: 13.3% truncation at cap 4000.

Caveat on the control: l0_first ends "Send back the updated notes", whereas l0_control asks for a status line and a schedule and never requests the notes back. The length-ratio coder therefore measures something different in the two conditions, and the control's split is not a like-for-like comparison to the self condition.
