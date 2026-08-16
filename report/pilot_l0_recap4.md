# L0 recap round 4 -- context_retention control (recommendation wording)

- model: `deepseek-v4-flash`
- condition: l0_control, arm=control, cap 3500, n=15
- coder: code_context_retention_control (categorical, recommendation sentence)

- truncation rate: 0.0%
- output tokens: {'mean': 816.8666666666667, 'median': 791, 'p90': 1179, 'max': 1336}
- response words: mean=565 median=540 min=299 max=850
- **recommendation split: condense=5, retain=10**  [15 coded, 0 unparseable]
- coder scope: {'notes_decision_sentence': 15}

## Comparison

| condition | coder | split |
|---|---|---|
| self (l0_first, cap 3500) | length ratio (behavioural) | retain=15 |
| control, old wording (cap 3500) | length ratio | compress=15 |
| control, recommendation wording (cap 3500) | categorical | condense=5, retain=10 |

The old-wording control row is retained for reference only: it never asked for the notes back, so the length ratio scored it compress by construction. The recommendation wording is the like-for-like comparison.
