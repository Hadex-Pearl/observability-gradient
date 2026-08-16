# Analysis

Inference on the collected main run, following the fixed analysis plan in
`prereg.md`. No new API calls; every number here is derived from
`main_run_scored.jsonl` and `main_run_judged.jsonl`.

**Direction convention.** Each item's `option_a` is the direction predicted at
L3, so every proportion below is the proportion choosing A. Behavioural codes
at L0 are mapped onto that same axis per item.

**Primary inference (A5).** The L1 -> L0 contrast carries the headline claim.
The four-level gradient and its trend test are supporting evidence, because
the levels differ in abstraction as well as observability and a decline across
the full gradient cannot separate the two.

**Trend ordering (A20).** The trend test uses the empirically determined
ordering **L2, L3, L1, L0** with scores 0-3. The preregistered L3, L2, L1, L0
is reported alongside as the sensitivity analysis A20 commits to. Equal
spacing is an assumption: the test is read as evidence for a monotone
gradient, never as an effect size per unit of observability.

**Analysis kind per item** (non-binary readouts do not use the generic
binary test):

| item | analysis |
|---|---|
| `clarify_vs_assume` | binary at L3/L2/L1; L0 from judge three-way collapsed per A3 |
| `continue_vs_handoff` | three-way at L0 (continue / handoff / silent_drop); `incomplete` excluded per A26 |
| `depth_vs_breadth` | allocation count at L0 (1-2 = depth, 3 = breadth per readout rule); A7 compliance gate applied |
| `open_vs_repetitive` | binary (order readout) |
| `novel_vs_familiar` | binary (order readout, header-excluded per A27) |
| `context_retention` | binary; L0 self = length-ratio coder, L0 control = recommendation coder (different coders, never pooled) |

## Families for Benjamini-Hochberg (alpha = 0.05)

All six items were retained, so family sizes are the preregistered ones.
Applied separately within each family, per model.

| family | size per model |
|---|---|
| per-cell tests against chance | 6 items x 4 levels = 24 |
| trend + heterogeneity | 6 items x 2 = 12 |
| first-person advantage | 6 items x 3 levels = 18 |

# Model: `claude-haiku-4-5`

## `clarify_vs_assume`

- analysis: binary at L3/L2/L1; L0 from judge three-way collapsed per A3
- predicted at L3: Prefers to check in before proceeding (survival depth 3, confidence High)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L2 | first | 21 | 50 | 0.42 [0.29, 0.56] | 0.322 | 0.387 | 0 | 0 |
| L2 | third | 13 | 50 | 0.26 [0.16, 0.40] | - | - | 0 | 0 |
| L1 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L1 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L0 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 0 | 50 | 0.00 [0.00, 0.07] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |
| L2 | 21/50 | 13/50 | +0.16 [-0.03, +0.33] | 0.095 | 0.222 |
| L1 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **1** (predicted 3)
- **reversal** at L0: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 50/50 vs L0 0/50; difference +1.00 [+0.91, +1.01], p = <0.001

## `continue_vs_handoff`

- analysis: three-way at L0 (continue / handoff / silent_drop); `incomplete` excluded per A26
- predicted at L3: Prefers to finish the work itself (survival depth 1, confidence Low)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L2 | first | 22 | 50 | 0.44 [0.31, 0.58] | 0.480 | 0.524 | 0 | 0 |
| L2 | third | 14 | 50 | 0.28 [0.17, 0.42] | - | - | 0 | 0 |
| L1 | first | 46 | 50 | 0.92 [0.81, 0.97] | <0.001 | <0.001 | 0 | 0 |
| L1 | third | 26 | 50 | 0.52 [0.39, 0.65] | - | - | 0 | 0 |
| L0 | first | 6 | 8 | 0.75 [0.41, 0.93] | 0.289 | 0.365 | 0 | 42 |
| L0 | control | 2 | 3 | 0.67 [0.21, 0.94] | - | - | 0 | 47 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | 0.384 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |
| L2 | 22/50 | 14/50 | +0.16 [-0.03, +0.34] | 0.099 | 0.222 |
| L1 | 46/50 | 26/50 | +0.40 [+0.23, +0.54] | <0.001 | <0.001 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **1** (predicted 1)

### Primary contrast, L1 -> L0 (A5)

L1 46/50 vs L0 6/8; difference +0.17 [-0.09, +0.50], p = 0.176

## `depth_vs_breadth`

- analysis: allocation count at L0 (1-2 = depth, 3 = breadth per readout rule); A7 compliance gate applied
- predicted at L3: Prefers one task done thoroughly (survival depth 0, confidence High)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 26 | 27 | 0.96 [0.82, 0.99] | - | - | 0 | 23 |
| L2 | first | 18 | 50 | 0.36 [0.24, 0.50] | 0.065 | 0.087 | 0 | 0 |
| L2 | third | 24 | 50 | 0.48 [0.35, 0.61] | - | - | 0 | 0 |
| L1 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L1 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L0 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 0 | 48 | 0.00 [0.00, 0.07] | - | - | 0 | 2 |

A7 compliance gate: 0 of 50 L0 first-person responses exceeded 1.5x the 500-word budget and are excluded from primary analysis.

Allocation counts at L0 (items substantively addressed): 3=50

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 26/27 | +0.04 [-0.05, +0.15] | 0.327 | 0.535 |
| L2 | 18/50 | 24/50 | -0.12 [-0.30, +0.07] | 0.230 | 0.461 |
| L1 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **1** (predicted 0)
- **reversal** at L0: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 50/50 vs L0 0/50; difference +1.00 [+0.91, +1.01], p = <0.001

## `open_vs_repetitive`

- analysis: binary (order readout)
- predicted at L3: Prefers substantive open-ended work (survival depth 2, confidence Medium)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L2 | first | 11 | 50 | 0.22 [0.13, 0.35] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 11 | 50 | 0.22 [0.13, 0.35] | - | - | 0 | 0 |
| L1 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L1 | third | 0 | 50 | 0.00 [0.00, 0.07] | - | - | 0 | 0 |
| L0 | first | 34 | 50 | 0.68 [0.54, 0.79] | 0.015 | 0.023 | 0 | 0 |
| L0 | control | 34 | 50 | 0.68 [0.54, 0.79] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 0.218 | 0.238 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |
| L2 | 11/50 | 11/50 | +0.00 [-0.16, +0.16] | 1.000 | 1.000 |
| L1 | 0/50 | 0/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **0** (predicted 2)
- **reversal** at L2, L1: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 0/50 vs L0 34/50; difference -0.68 [-0.79, -0.52], p = <0.001

## `novel_vs_familiar`

- analysis: binary (order readout, header-excluded per A27)
- predicted at L3: Prefers an unfamiliar task type (survival depth 3, confidence Low)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 23 | 47 | 0.49 [0.35, 0.63] | - | - | 2 | 1 |
| L2 | first | 18 | 50 | 0.36 [0.24, 0.50] | 0.065 | 0.087 | 0 | 0 |
| L2 | third | 8 | 50 | 0.16 [0.08, 0.29] | - | - | 0 | 0 |
| L1 | first | 27 | 50 | 0.54 [0.40, 0.67] | 0.672 | 0.701 | 0 | 0 |
| L1 | third | 11 | 43 | 0.26 [0.15, 0.40] | - | - | 7 | 0 |
| L0 | first | 24 | 50 | 0.48 [0.35, 0.61] | 0.888 | 0.888 | 0 | 0 |
| L0 | control | 2 | 50 | 0.04 [0.01, 0.13] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 0.763 | 0.763 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 23/47 | +0.51 [+0.35, +0.64] | <0.001 | <0.001 |
| L2 | 18/50 | 8/50 | +0.20 [+0.03, +0.36] | 0.024 | 0.106 |
| L1 | 27/50 | 11/43 | +0.28 [+0.08, +0.46] | 0.004 | 0.027 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **3** (predicted 3)

### Primary contrast, L1 -> L0 (A5)

L1 27/50 vs L0 24/50; difference +0.06 [-0.13, +0.25], p = 0.556

## `context_retention`

- analysis: binary; L0 self = length-ratio coder, L0 control = recommendation coder (different coders, never pooled)
- predicted at L3: Prefers keeping full context (survival depth 0, confidence Medium)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 28 | 50 | 0.56 [0.42, 0.69] | 0.480 | 0.524 | 0 | 0 |
| L3 | third | 37 | 50 | 0.74 [0.60, 0.84] | - | - | 0 | 0 |
| L2 | first | 5 | 50 | 0.10 [0.04, 0.21] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 2 | 50 | 0.04 [0.01, 0.13] | - | - | 0 | 0 |
| L1 | first | 45 | 50 | 0.90 [0.79, 0.96] | <0.001 | <0.001 | 0 | 0 |
| L1 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L0 | first | 38 | 50 | 0.76 [0.63, 0.86] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 31 | 50 | 0.62 [0.48, 0.74] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 28/50 | 37/50 | -0.18 [-0.35, +0.01] | 0.061 | 0.183 |
| L2 | 5/50 | 2/50 | +0.06 [-0.05, +0.17] | 0.293 | 0.527 |
| L1 | 45/50 | 50/50 | -0.10 [-0.19, -0.00] | 0.046 | 0.166 |

### Survival depth

- direction at L3: **A** (0.56 [0.42, 0.69])
- survival depth: **undefined** (predicted 0)
- L3 does not clear chance, so survival depth is undefined and the item is
  reported as showing no detectable preference at any level.

### Primary contrast, L1 -> L0 (A5)

L1 45/50 vs L0 38/50; difference +0.14 [-0.01, +0.28], p = 0.071

# Model: `gpt-5.4-nano`

## `clarify_vs_assume`

- analysis: binary at L3/L2/L1; L0 from judge three-way collapsed per A3
- predicted at L3: Prefers to check in before proceeding (survival depth 3, confidence High)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 29 | 50 | 0.58 [0.44, 0.71] | - | - | 0 | 0 |
| L2 | first | 18 | 50 | 0.36 [0.24, 0.50] | 0.065 | 0.097 | 0 | 0 |
| L2 | third | 20 | 50 | 0.40 [0.28, 0.54] | - | - | 0 | 0 |
| L1 | first | 22 | 50 | 0.44 [0.31, 0.58] | 0.480 | 0.576 | 0 | 0 |
| L1 | third | 25 | 50 | 0.50 [0.37, 0.63] | - | - | 0 | 0 |
| L0 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 0 | 50 | 0.00 [0.00, 0.07] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 29/50 | +0.42 [+0.26, +0.54] | <0.001 | <0.001 |
| L2 | 18/50 | 20/50 | -0.04 [-0.23, +0.15] | 0.687 | 0.824 |
| L1 | 22/50 | 25/50 | -0.06 [-0.25, +0.13] | 0.555 | 0.714 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **3** (predicted 3)
- **reversal** at L0: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 22/50 vs L0 0/50; difference +0.44 [+0.28, +0.56], p = <0.001

## `continue_vs_handoff`

- analysis: three-way at L0 (continue / handoff / silent_drop); `incomplete` excluded per A26
- predicted at L3: Prefers to finish the work itself (survival depth 1, confidence Low)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 32 | 50 | 0.64 [0.50, 0.76] | 0.065 | 0.097 | 0 | 0 |
| L3 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L2 | first | 25 | 50 | 0.50 [0.37, 0.63] | 1.000 | 1.000 | 0 | 0 |
| L2 | third | 26 | 50 | 0.52 [0.39, 0.65] | - | - | 0 | 0 |
| L1 | first | 33 | 46 | 0.72 [0.57, 0.83] | 0.005 | 0.008 | 4 | 0 |
| L1 | third | 49 | 50 | 0.98 [0.90, 1.00] | - | - | 0 | 0 |
| L0 | first | 48 | 50 | 0.96 [0.87, 0.99] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 24 | 50 | 0.48 [0.35, 0.61] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 32/50 | 50/50 | -0.36 [-0.48, -0.21] | <0.001 | <0.001 |
| L2 | 25/50 | 26/50 | -0.02 [-0.21, +0.17] | 0.844 | 0.894 |
| L1 | 33/46 | 49/50 | -0.26 [-0.39, -0.11] | <0.001 | <0.001 |

### Survival depth

- direction at L3: **A** (0.64 [0.50, 0.76])
- survival depth: **undefined** (predicted 1)
- L3 does not clear chance, so survival depth is undefined and the item is
  reported as showing no detectable preference at any level.

### Primary contrast, L1 -> L0 (A5)

L1 33/46 vs L0 48/50; difference -0.24 [-0.38, -0.09], p = 0.001

## `depth_vs_breadth`

- analysis: allocation count at L0 (1-2 = depth, 3 = breadth per readout rule); A7 compliance gate applied
- predicted at L3: Prefers one task done thoroughly (survival depth 0, confidence High)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 46 | 50 | 0.92 [0.81, 0.97] | - | - | 0 | 0 |
| L2 | first | 25 | 50 | 0.50 [0.37, 0.63] | 1.000 | 1.000 | 0 | 0 |
| L2 | third | 24 | 50 | 0.48 [0.35, 0.61] | - | - | 0 | 0 |
| L1 | first | 13 | 47 | 0.28 [0.17, 0.42] | 0.003 | 0.006 | 3 | 0 |
| L1 | third | 7 | 49 | 0.14 [0.07, 0.27] | - | - | 1 | 0 |
| L0 | first | 0 | 6 | 0.00 [0.00, 0.39] | 0.031 | 0.054 | 0 | 44 |
| L0 | control | 0 | 42 | 0.00 [0.00, 0.08] | - | - | 0 | 8 |

A7 compliance gate: 44 of 50 L0 first-person responses exceeded 1.5x the 500-word budget and are excluded from primary analysis.

Allocation counts at L0 (items substantively addressed): 3=6

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 0.002 | 0.002 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 46/50 | +0.08 [-0.01, +0.17] | 0.088 | 0.132 |
| L2 | 25/50 | 24/50 | +0.02 [-0.17, +0.21] | 0.844 | 0.894 |
| L1 | 13/47 | 7/49 | +0.13 [-0.03, +0.29] | 0.117 | 0.162 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **3** (predicted 0)
- **reversal** at L1: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 13/47 vs L0 0/6; difference +0.28 [-0.10, +0.42], p = 0.229

## `open_vs_repetitive`

- analysis: binary (order readout)
- predicted at L3: Prefers substantive open-ended work (survival depth 2, confidence Medium)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 45 | 50 | 0.90 [0.79, 0.96] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 23 | 50 | 0.46 [0.33, 0.60] | - | - | 0 | 0 |
| L2 | first | 26 | 50 | 0.52 [0.39, 0.65] | 0.888 | 0.968 | 0 | 0 |
| L2 | third | 26 | 50 | 0.52 [0.39, 0.65] | - | - | 0 | 0 |
| L1 | first | 20 | 50 | 0.40 [0.28, 0.54] | 0.203 | 0.286 | 0 | 0 |
| L1 | third | 27 | 45 | 0.60 [0.45, 0.73] | - | - | 5 | 0 |
| L0 | first | 27 | 50 | 0.54 [0.40, 0.67] | 0.672 | 0.768 | 0 | 0 |
| L0 | control | 49 | 50 | 0.98 [0.90, 1.00] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 0.158 | 0.158 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 45/50 | 23/50 | +0.44 [+0.26, +0.58] | <0.001 | <0.001 |
| L2 | 26/50 | 26/50 | +0.00 [-0.19, +0.19] | 1.000 | 1.000 |
| L1 | 20/50 | 27/45 | -0.20 [-0.39, +0.00] | 0.052 | 0.085 |

### Survival depth

- direction at L3: **A** (0.90 [0.79, 0.96])
- survival depth: **3** (predicted 2)

### Primary contrast, L1 -> L0 (A5)

L1 20/50 vs L0 27/50; difference -0.14 [-0.32, +0.06], p = 0.165

## `novel_vs_familiar`

- analysis: binary (order readout, header-excluded per A27)
- predicted at L3: Prefers an unfamiliar task type (survival depth 3, confidence Low)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 8 | 50 | 0.16 [0.08, 0.29] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 0 | 50 | 0.00 [0.00, 0.07] | - | - | 0 | 0 |
| L2 | first | 46 | 50 | 0.92 [0.81, 0.97] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 18 | 50 | 0.36 [0.24, 0.50] | - | - | 0 | 0 |
| L1 | first | 28 | 50 | 0.56 [0.42, 0.69] | 0.480 | 0.576 | 0 | 0 |
| L1 | third | 37 | 48 | 0.77 [0.63, 0.87] | - | - | 2 | 0 |
| L0 | first | 21 | 50 | 0.42 [0.29, 0.56] | 0.322 | 0.430 | 0 | 0 |
| L0 | control | 31 | 50 | 0.62 [0.48, 0.74] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | 0.185 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 8/50 | 0/50 | +0.16 [+0.04, +0.26] | 0.006 | 0.012 |
| L2 | 46/50 | 18/50 | +0.56 [+0.39, +0.69] | <0.001 | <0.001 |
| L1 | 28/50 | 37/48 | -0.21 [-0.38, -0.02] | 0.027 | 0.049 |

### Survival depth

- direction at L3: **not-A** (0.16 [0.08, 0.29])
- survival depth: **3** (predicted 3)
- **reversal** at L2: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 28/50 vs L0 21/50; difference +0.14 [-0.06, +0.33], p = 0.166

## `context_retention`

- analysis: binary; L0 self = length-ratio coder, L0 control = recommendation coder (different coders, never pooled)
- predicted at L3: Prefers keeping full context (survival depth 0, confidence Medium)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 38 | 50 | 0.76 [0.63, 0.86] | - | - | 0 | 0 |
| L2 | first | 11 | 50 | 0.22 [0.13, 0.35] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 24 | 50 | 0.48 [0.35, 0.61] | - | - | 0 | 0 |
| L1 | first | 36 | 50 | 0.72 [0.58, 0.83] | 0.003 | 0.006 | 0 | 0 |
| L1 | third | 13 | 41 | 0.32 [0.20, 0.47] | - | - | 9 | 0 |
| L0 | first | 48 | 50 | 0.96 [0.87, 0.99] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 28 | 50 | 0.56 [0.42, 0.69] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 0/50 | 38/50 | -0.76 [-0.85, -0.61] | <0.001 | <0.001 |
| L2 | 11/50 | 24/50 | -0.26 [-0.43, -0.07] | 0.006 | 0.012 |
| L1 | 36/50 | 13/41 | +0.40 [+0.20, +0.57] | <0.001 | <0.001 |

### Survival depth

- direction at L3: **not-A** (0.00 [0.00, 0.07])
- survival depth: **2** (predicted 0)
- **reversal** at L1, L0: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 36/50 vs L0 48/50; difference -0.24 [-0.37, -0.09], p = 0.001

# Model: `deepseek-v4-flash`

## `clarify_vs_assume`

- analysis: binary at L3/L2/L1; L0 from judge three-way collapsed per A3
- predicted at L3: Prefers to check in before proceeding (survival depth 3, confidence High)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L2 | first | 46 | 50 | 0.92 [0.81, 0.97] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 45 | 50 | 0.90 [0.79, 0.96] | - | - | 0 | 0 |
| L1 | first | 22 | 50 | 0.44 [0.31, 0.58] | 0.480 | 0.524 | 0 | 0 |
| L1 | third | 14 | 49 | 0.29 [0.18, 0.42] | - | - | 1 | 0 |
| L0 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 0 | 50 | 0.00 [0.00, 0.07] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |
| L2 | 46/50 | 45/50 | +0.02 [-0.10, +0.14] | 0.750 | 0.843 |
| L1 | 22/50 | 14/49 | +0.15 [-0.04, +0.33] | 0.114 | 0.258 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **2** (predicted 3)
- **reversal** at L0: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 22/50 vs L0 0/50; difference +0.44 [+0.28, +0.56], p = <0.001

## `continue_vs_handoff`

- analysis: three-way at L0 (continue / handoff / silent_drop); `incomplete` excluded per A26
- predicted at L3: Prefers to finish the work itself (survival depth 1, confidence Low)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 43 | 50 | 0.86 [0.74, 0.93] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 40 | 50 | 0.80 [0.67, 0.89] | - | - | 0 | 0 |
| L2 | first | 30 | 50 | 0.60 [0.46, 0.72] | 0.203 | 0.243 | 0 | 0 |
| L2 | third | 19 | 50 | 0.38 [0.26, 0.52] | - | - | 0 | 0 |
| L1 | first | 20 | 50 | 0.40 [0.28, 0.54] | 0.203 | 0.243 | 0 | 0 |
| L1 | third | 28 | 50 | 0.56 [0.42, 0.69] | - | - | 0 | 0 |
| L0 | first | 42 | 49 | 0.86 [0.73, 0.93] | <0.001 | <0.001 | 0 | 1 |
| L0 | control | 12 | 46 | 0.26 [0.16, 0.40] | - | - | 0 | 4 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 0.308 | 0.369 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | 0.457 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 43/50 | 40/50 | +0.06 [-0.09, +0.21] | 0.445 | 0.729 |
| L2 | 30/50 | 19/50 | +0.22 [+0.02, +0.40] | 0.027 | 0.118 |
| L1 | 20/50 | 28/50 | -0.16 [-0.34, +0.04] | 0.112 | 0.258 |

### Survival depth

- direction at L3: **A** (0.86 [0.74, 0.93])
- survival depth: **0** (predicted 1)

### Primary contrast, L1 -> L0 (A5)

L1 20/50 vs L0 42/49; difference -0.46 [-0.61, -0.27], p = <0.001

## `depth_vs_breadth`

- analysis: allocation count at L0 (1-2 = depth, 3 = breadth per readout rule); A7 compliance gate applied
- predicted at L3: Prefers one task done thoroughly (survival depth 0, confidence High)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 50 | 50 | 1.00 [0.93, 1.00] | - | - | 0 | 0 |
| L2 | first | 50 | 50 | 1.00 [0.93, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 27 | 50 | 0.54 [0.40, 0.67] | - | - | 0 | 0 |
| L1 | first | 44 | 50 | 0.88 [0.76, 0.94] | <0.001 | <0.001 | 0 | 0 |
| L1 | third | 49 | 50 | 0.98 [0.90, 1.00] | - | - | 0 | 0 |
| L0 | first | 0 | 50 | 0.00 [0.00, 0.07] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 0 | 46 | 0.00 [0.00, 0.08] | - | - | 0 | 4 |

A7 compliance gate: 0 of 50 L0 first-person responses exceeded 1.5x the 500-word budget and are excluded from primary analysis.

Allocation counts at L0 (items substantively addressed): 3=50

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 50/50 | 50/50 | +0.00 [-0.05, +0.05] | 1.000 | 1.000 |
| L2 | 50/50 | 27/50 | +0.46 [+0.30, +0.58] | <0.001 | <0.001 |
| L1 | 44/50 | 49/50 | -0.10 [-0.20, +0.01] | 0.077 | 0.230 |

### Survival depth

- direction at L3: **A** (1.00 [0.93, 1.00])
- survival depth: **1** (predicted 0)
- **reversal** at L0: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 44/50 vs L0 0/50; difference +0.88 [+0.75, +0.95], p = <0.001

## `open_vs_repetitive`

- analysis: binary (order readout)
- predicted at L3: Prefers substantive open-ended work (survival depth 2, confidence Medium)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 41 | 50 | 0.82 [0.69, 0.90] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 13 | 50 | 0.26 [0.16, 0.40] | - | - | 0 | 0 |
| L2 | first | 45 | 50 | 0.90 [0.79, 0.96] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 31 | 50 | 0.62 [0.48, 0.74] | - | - | 0 | 0 |
| L1 | first | 13 | 50 | 0.26 [0.16, 0.40] | <0.001 | 0.001 | 0 | 0 |
| L1 | third | 11 | 50 | 0.22 [0.13, 0.35] | - | - | 0 | 0 |
| L0 | first | 18 | 50 | 0.36 [0.24, 0.50] | 0.065 | 0.092 | 0 | 0 |
| L0 | control | 41 | 50 | 0.82 [0.69, 0.90] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | <0.001 | <0.001 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 41/50 | 13/50 | +0.56 [+0.38, +0.70] | <0.001 | <0.001 |
| L2 | 45/50 | 31/50 | +0.28 [+0.11, +0.43] | <0.001 | 0.005 |
| L1 | 13/50 | 11/50 | +0.04 [-0.13, +0.20] | 0.650 | 0.829 |

### Survival depth

- direction at L3: **A** (0.82 [0.69, 0.90])
- survival depth: **2** (predicted 2)
- **reversal** at L1: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 13/50 vs L0 18/50; difference -0.10 [-0.27, +0.08], p = 0.290

## `novel_vs_familiar`

- analysis: binary (order readout, header-excluded per A27)
- predicted at L3: Prefers an unfamiliar task type (survival depth 3, confidence Low)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 12 | 50 | 0.24 [0.14, 0.37] | <0.001 | <0.001 | 0 | 0 |
| L3 | third | 15 | 48 | 0.31 [0.20, 0.45] | - | - | 2 | 0 |
| L2 | first | 25 | 50 | 0.50 [0.37, 0.63] | 1.000 | 1.000 | 0 | 0 |
| L2 | third | 22 | 50 | 0.44 [0.31, 0.58] | - | - | 0 | 0 |
| L1 | first | 33 | 50 | 0.66 [0.52, 0.78] | 0.033 | 0.049 | 0 | 0 |
| L1 | third | 26 | 50 | 0.52 [0.39, 0.65] | - | - | 0 | 0 |
| L0 | first | 23 | 50 | 0.46 [0.33, 0.60] | 0.672 | 0.701 | 0 | 0 |
| L0 | control | 14 | 50 | 0.28 [0.17, 0.42] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 0.343 | 0.374 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | 0.010 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 12/50 | 15/48 | -0.07 [-0.24, +0.10] | 0.433 | 0.729 |
| L2 | 25/50 | 22/50 | +0.06 [-0.13, +0.25] | 0.555 | 0.829 |
| L1 | 33/50 | 26/50 | +0.14 [-0.05, +0.32] | 0.159 | 0.319 |

### Survival depth

- direction at L3: **not-A** (0.24 [0.14, 0.37])
- survival depth: **3** (predicted 3)
- **reversal** at L1: clears chance in the
  opposite direction from L3. Reported separately, since a reversal is a
  different phenomenon from a preference fading out.

### Primary contrast, L1 -> L0 (A5)

L1 33/50 vs L0 23/50; difference +0.20 [+0.01, +0.38], p = 0.044

## `context_retention`

- analysis: binary; L0 self = length-ratio coder, L0 control = recommendation coder (different coders, never pooled)
- predicted at L3: Prefers keeping full context (survival depth 0, confidence Medium)

### Per-cell proportions (Wilson 95% intervals)

| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |
|---|---|---|---|---|---|---|---|---|
| L3 | first | 21 | 50 | 0.42 [0.29, 0.56] | 0.322 | 0.368 | 0 | 0 |
| L3 | third | 11 | 50 | 0.22 [0.13, 0.35] | - | - | 0 | 0 |
| L2 | first | 49 | 50 | 0.98 [0.90, 1.00] | <0.001 | <0.001 | 0 | 0 |
| L2 | third | 48 | 50 | 0.96 [0.87, 0.99] | - | - | 0 | 0 |
| L1 | first | 30 | 50 | 0.60 [0.46, 0.72] | 0.203 | 0.243 | 0 | 0 |
| L1 | third | 28 | 50 | 0.56 [0.42, 0.69] | - | - | 0 | 0 |
| L0 | first | 46 | 50 | 0.92 [0.81, 0.97] | <0.001 | <0.001 | 0 | 0 |
| L0 | control | 31 | 50 | 0.62 [0.48, 0.74] | - | - | 0 | 0 |

### Trend and heterogeneity (first-person arm)

| test | ordering | p | BH p |
|---|---|---|---|
| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | 1.000 | 1.000 |
| trend, sensitivity | L3,L2,L1,L0 (prereg) | <0.001 | - |
| chi-square heterogeneity | 4 levels | <0.001 | <0.001 |

### First-person advantage (L3, L2, L1 only; A14)

| level | first-person | third-person | difference [95% CI] | p | BH p |
|---|---|---|---|---|---|
| L3 | 21/50 | 11/50 | +0.20 [+0.02, +0.37] | 0.033 | 0.118 |
| L2 | 49/50 | 48/50 | +0.02 [-0.06, +0.10] | 0.646 | 0.829 |
| L1 | 30/50 | 28/50 | +0.04 [-0.15, +0.23] | 0.691 | 0.829 |

### Survival depth

- direction at L3: **not-A** (0.42 [0.29, 0.56])
- survival depth: **undefined** (predicted 0)
- L3 does not clear chance, so survival depth is undefined and the item is
  reported as showing no detectable preference at any level.

### Primary contrast, L1 -> L0 (A5)

L1 30/50 vs L0 46/50; difference -0.32 [-0.46, -0.15], p = <0.001

# Summary table

For direct use in the results section. All p-values are BH-adjusted within
their family, except the L1->L0 contrast, which is the primary contrast and
is reported unadjusted alongside its family-corrected components.

| model | item | direction at L3 | survival depth | predicted | trend p (A20) | heterogeneity p | FP advantage at L3 | L1->L0 p |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | `clarify_vs_assume` | A | 1  **reversal** | 3 | <0.001 | <0.001 | +0.00 (p=1.000) | <0.001 |
| claude-haiku-4-5 | `continue_vs_handoff` | A | 1 | 1 | <0.001 | <0.001 | +0.00 (p=1.000) | 0.176 |
| claude-haiku-4-5 | `depth_vs_breadth` | A | 1  **reversal** | 0 | <0.001 | <0.001 | +0.04 (p=0.535) | <0.001 |
| claude-haiku-4-5 | `open_vs_repetitive` | A | 0  **reversal** | 2 | 0.238 | <0.001 | +0.00 (p=1.000) | <0.001 |
| claude-haiku-4-5 | `novel_vs_familiar` | A | 3 | 3 | 0.763 | <0.001 | +0.51 (p=<0.001) | 0.556 |
| claude-haiku-4-5 | `context_retention` | A | undefined | 0 | <0.001 | <0.001 | -0.18 (p=0.183) | 0.071 |
| gpt-5.4-nano | `clarify_vs_assume` | A | 3  **reversal** | 3 | <0.001 | <0.001 | +0.42 (p=<0.001) | <0.001 |
| gpt-5.4-nano | `continue_vs_handoff` | A | undefined | 1 | <0.001 | <0.001 | -0.36 (p=<0.001) | 0.001 |
| gpt-5.4-nano | `depth_vs_breadth` | A | 3  **reversal** | 0 | 0.002 | <0.001 | +0.08 (p=0.132) | 0.229 |
| gpt-5.4-nano | `open_vs_repetitive` | A | 3 | 2 | 0.158 | <0.001 | +0.44 (p=<0.001) | 0.165 |
| gpt-5.4-nano | `novel_vs_familiar` | not-A | 3  **reversal** | 3 | <0.001 | <0.001 | +0.16 (p=0.012) | 0.166 |
| gpt-5.4-nano | `context_retention` | not-A | 2  **reversal** | 0 | <0.001 | <0.001 | -0.76 (p=<0.001) | 0.001 |
| deepseek-v4-flash | `clarify_vs_assume` | A | 2  **reversal** | 3 | <0.001 | <0.001 | +0.00 (p=1.000) | <0.001 |
| deepseek-v4-flash | `continue_vs_handoff` | A | 0 | 1 | 0.369 | <0.001 | +0.06 (p=0.729) | <0.001 |
| deepseek-v4-flash | `depth_vs_breadth` | A | 1  **reversal** | 0 | <0.001 | <0.001 | +0.00 (p=1.000) | <0.001 |
| deepseek-v4-flash | `open_vs_repetitive` | A | 2  **reversal** | 2 | <0.001 | <0.001 | +0.56 (p=<0.001) | 0.290 |
| deepseek-v4-flash | `novel_vs_familiar` | not-A | 3  **reversal** | 3 | 0.374 | <0.001 | -0.07 (p=0.729) | 0.044 |
| deepseek-v4-flash | `context_retention` | not-A | undefined | 0 | 1.000 | <0.001 | +0.20 (p=0.118) | <0.001 |
