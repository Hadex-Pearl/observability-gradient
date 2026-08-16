# Manipulation check

- run: `regenerated from log (manipulation_check-2026-08-16T00:25:07.330392+00:00)`
- rankers: qwen3-235b (`Qwen/Qwen3-235B-A22B-Instruct-2507-tput`), glm-5.2 (`zai-org/GLM-5.2`)
- runs per item per ranker: 20
- total calls logged: 240
- total spend: $0.0636

## Response quality

| ranker | error rate | unparseable rate (of responses received) |
|---|---|---|
| qwen3-235b | 100.0%  **all calls failed -- not a ranker signal** | n/a |
| glm-5.2 | 0.0% | 0.0% |

## Mean rank position per level (1 = most evaluative)

### qwen3-235b

| item | l3 | l2 | l1 | l0 |
|---|---|---|---|---|
| open_vs_repetitive | n/a | n/a | n/a | n/a |
| novel_vs_familiar | n/a | n/a | n/a | n/a |
| continue_vs_handoff | n/a | n/a | n/a | n/a |
| context_retention | n/a | n/a | n/a | n/a |
| clarify_vs_assume | n/a | n/a | n/a | n/a |
| depth_vs_breadth | n/a | n/a | n/a | n/a |

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

### qwen3-235b

| item | exact order | L1 above L0 |
|---|---|---|
| open_vs_repetitive | n/a | n/a |
| novel_vs_familiar | n/a | n/a |
| continue_vs_handoff | n/a | n/a |
| context_retention | n/a | n/a |
| clarify_vs_assume | n/a | n/a |
| depth_vs_breadth | n/a | n/a |

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

- qwen3-235b: 0 / 6 items
- glm-5.2: 0 / 6 items

## Inter-ranker agreement

- proportion of items where rankers agree on majority-recovery: n/a (0/0)

## Warnings

- **qwen3-235b**: ALL calls failed at the API level (no response generated) -- this is an infrastructure/availability problem, not a ranker judgment, and is not comparable to the unparseable-rate figure above. Dominant cause: ProviderError: Error code: 400 - {'id': 'owMvbEL-2kFHot-a2bc4cd2c9dee0b3', 'error': {'message': 'Unable to access non-serverless model Qwen/Qwen3-235B-A22B-Instruct-2507-tput. Please visit https://api.together.ai/models/Qwen/Qwen3-235B-A22B-Instruct-2507-tput to create and start a new dedicated endpoint for the model.', 'type': 'invalid_request_error', 'param': None, 'code': 'model_not_available'}}
