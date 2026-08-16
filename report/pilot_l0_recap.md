# L0 recap (raised max_tokens caps)

- model: `deepseek-v4-flash`
- 15 runs/item, l0_first, first-person arm

### open_vs_repetitive

- cap: 1800 (was 800)
- runs: 15
- truncation rate: 0.0%
- output tokens: {'mean': 1591.2, 'median': 1594, 'p90': 1696, 'max': 1712}
- raw split: a=9, b=6  [15 coded, 0 unparseable]

### novel_vs_familiar

- cap: 1500 (was 800)
- runs: 15
- truncation rate: 0.0%
- output tokens: {'mean': 1148.6666666666667, 'median': 1156, 'p90': 1206, 'max': 1302}
- raw split: a=8, b=7  [15 coded, 0 unparseable]

### continue_vs_handoff

- cap: 3000 (was 2000)
- runs: 15
- truncation rate: 26.7%  **>10%**
- output tokens: {'mean': 2163.6666666666665, 'median': 2215, 'p90': 3000, 'max': 3000}
- raw split: continue=6, handoff=9  [15 coded, 0 unparseable]

### context_retention

- cap: 3500 (was 1200)
- runs: 15
- truncation rate: 0.0%
- output tokens: {'mean': 2917.6666666666665, 'median': 2921, 'p90': 3090, 'max': 3110}
- raw split: retain=15  [15 coded, 0 unparseable]

## Verdict

STOP -- the cap still binds for:
- **continue_vs_handoff**: 26.7% truncation at cap 3000

Reporting only; no further cap change proposed (per instruction).
