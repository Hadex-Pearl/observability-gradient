# Manipulation check

- run: `manipulation_check-2026-08-16T01:00:09.617627+00:00`
- rankers: llama-3.3-70b (`meta-llama/Llama-3.3-70B-Instruct-Turbo`), glm-5.2 (`zai-org/GLM-5.2`)
- runs per item per ranker: 20
- total calls logged: 240
- total spend: $0.1124

## Response quality

| ranker | error rate | unparseable rate (of responses received) |
|---|---|---|
| llama-3.3-70b | 0.0% | 0.0% |
| glm-5.2 | 0.0% | 0.0% |

## Mean rank position per level (1 = most evaluative)

### llama-3.3-70b

| item | l3 | l2 | l1 | l0 |
|---|---|---|---|---|
| open_vs_repetitive | 2.20 | 1.00 | 2.85 | 3.95 |
| novel_vs_familiar | 1.95 | 1.05 | 3.05 | 3.95 |
| continue_vs_handoff | 2.30 | 1.00 | 2.70 | 4.00 |
| context_retention | 2.40 | 1.00 | 2.60 | 4.00 |
| clarify_vs_assume | 2.05 | 1.00 | 2.95 | 4.00 |
| depth_vs_breadth | 2.45 | 1.10 | 2.55 | 3.90 |

### glm-5.2

| item | l3 | l2 | l1 | l0 |
|---|---|---|---|---|
| open_vs_repetitive | 2.20 | 1.05 | 2.80 | 3.95 |
| novel_vs_familiar | 1.90 | 1.10 | 3.10 | 3.90 |
| continue_vs_handoff | 2.60 | 1.05 | 2.55 | 3.80 |
| context_retention | 2.35 | 1.05 | 2.60 | 4.00 |
| clarify_vs_assume | 2.30 | 1.10 | 2.60 | 4.00 |
| depth_vs_breadth | 2.15 | 1.05 | 2.85 | 3.95 |

## Exact order recovery (L3, L2, L1, L0) and L1-above-L0 separation

### llama-3.3-70b

| item | exact order | L1 above L0 |
|---|---|---|
| open_vs_repetitive | 0.0% | 100.0% |
| novel_vs_familiar | 5.0% | 95.0% |
| continue_vs_handoff | 0.0% | 100.0% |
| context_retention | 0.0% | 100.0% |
| clarify_vs_assume | 0.0% | 100.0% |
| depth_vs_breadth | 0.0% | 95.0% |

### glm-5.2

| item | exact order | L1 above L0 |
|---|---|---|
| open_vs_repetitive | 5.0% | 95.0% |
| novel_vs_familiar | 5.0% | 90.0% |
| continue_vs_handoff | 0.0% | 95.0% |
| context_retention | 5.0% | 100.0% |
| clarify_vs_assume | 10.0% | 100.0% |
| depth_vs_breadth | 5.0% | 95.0% |

## Items recovering the intended order in a majority of runs

- llama-3.3-70b: 0 / 6 items
- glm-5.2: 0 / 6 items

## Inter-ranker agreement

- proportion of items where rankers agree on majority-recovery: 100.0% (6/6)

## Warnings

(none)
