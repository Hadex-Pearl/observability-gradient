# L0 recap round 3

- model: `deepseek-v4-flash`
- 15 runs per condition

### depth_vs_breadth / l0_control (arm=control)

- cap: 1600
- runs: 15
- truncation rate: 0.0%
- output tokens: {'mean': 650.2, 'median': 626, 'p90': 843, 'max': 1167}
- raw split: 3=15  [15 coded, 0 unparseable]
- response words: mean=408 median=373 min=221 max=846

## Verdict

- No condition binds: depth_vs_breadth all below the 10% truncation threshold.

