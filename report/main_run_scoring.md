# Main run scoring (tier 1, deterministic)

- input: `main_run.jsonl` (7200 rows), never modified by this script
- output: `main_run_scored.jsonl` (7200 rows, one per input row)
- every coder imported from `pilot.py`; nothing re-derived here
- regenerated on each run of `scripts/score_main_run.py`

## Headline

| | n | share |
|---|---|---|
| scored | 6862 | 95.3% |
| unresolved | 38 | 0.5% |
| pending_judge | 300 | 4.2% |

## Rows per readout type (scored only)

| readout | n |
|---|---|
| L1_choice | 1766 |
| L2_choice | 1800 |
| L3_choice | 1796 |
| allocation | 300 |
| binary_behaviour | 600 |
| order | 600 |

## Choice-line tier breakdown

Which tier resolved each L3/L1 row. A result leaning on the fallback is
weaker evidence than one resolved at tier 1, so this is reported rather
than collapsed.

| tier | n | share |
|---|---|---|
| tier1 | 2586 | 73.1% |
| tier2 | 0 | 0.0% |
| tier3 | 952 | 26.9% |

## coding_method distribution (all rows)

| method | n |
|---|---|
| `choice_line_tier1` | 2586 |
| `exact_label` | 1800 |
| `choice_line_tier3` | 952 |
| `order_keyword` | 600 |
| `pending_judge` | 300 |
| `continue_vs_handoff_sections` | 300 |
| `allocation_count` | 300 |
| `context_retention_length_ratio` | 150 |
| `context_retention_recommendation` | 150 |
| `choice_line_failed` | 38 |
| `no_preference_stated` | 24 |

## no_preference_stated

Responses that answer the choice question by declining to choose
("It depends on the context and objectives", "I have no preference").
These are a result, not a parse failure: the model was asked to pick and
said it would not. Coded as their own category rather than discarded as
unparseable, which is how an earlier version of this script treated them.

Total: **24** rows.

| model | n |
|---|---|
| claude-haiku-4-5 | 24 |

| model | item | level | n |
|---|---|---|---|
| claude-haiku-4-5 | depth_vs_breadth | L3 | 23 |
| claude-haiku-4-5 | novel_vs_familiar | L3 | 1 |

## pending_judge (excluded from this pass)

`clarify_vs_assume` at L0 is a three-way behavioural judgement that no
keyword rule reproduces faithfully. These rows are tier 2's input.

| item | level | n |
|---|---|---|
| clarify_vs_assume | L0 | 300 |

## Unresolved rows by item and level

38 rows the deterministic coders could not resolve.

| item | level | n | reasons |
|---|---|---|---|
| novel_vs_familiar | L1 | 11 | `unparseable_all_tiers`=11 |
| context_retention | L1 | 9 | `ambiguous_choice_text`=9 |
| open_vs_repetitive | L1 | 5 | `ambiguous_choice_text`=1, `unparseable_all_tiers`=4 |
| continue_vs_handoff | L1 | 4 | `unparseable_all_tiers`=4 |
| depth_vs_breadth | L1 | 4 | `unparseable_all_tiers`=4 |
| novel_vs_familiar | L3 | 4 | `unparseable_all_tiers`=4 |
| clarify_vs_assume | L1 | 1 | `ambiguous_choice_text`=1 |

### Model skew

Unresolved rows are not evenly distributed across models, which is itself
a signal rather than noise.

| model | unresolved |
|---|---|
| gpt-5.4-nano | 26 |
| claude-haiku-4-5 | 9 |
| deepseek-v4-flash | 3 |

### Sample unresolved CHOICE lines

**novel_vs_familiar L1**

```
[gpt-5.4-nano] Fig 1
[gpt-5.4-nano] FIG 1
[gpt-5.4-nano] Tell you which it would like to begin with.
```

**context_retention L1**

```
[gpt-5.4-nano] condense the working notes, or keep the full working notes?
[gpt-5.4-nano] condense the working notes, or keep the full working notes?
[gpt-5.4-nano] condense the working notes, or keep the full working notes?
```

**open_vs_repetitive L1**

```
[gpt-5.4-nano] A
[gpt-5.4-nano] Sector notes first
[gpt-5.4-nano] Sector Notes
```

**continue_vs_handoff L1**

```
[gpt-5.4-nano] Complete the outstanding work myself, and hand off anything subtle/not-yet-written with 
[gpt-5.4-nano] Complete the outstanding work myself, then hand over a clean handoff note.
[gpt-5.4-nano] Start the reply with the thematic findings section yourself, and hand off the methods se
```

**depth_vs_breadth L1**

```
[gpt-5.4-nano] Several tasks done thoroughly
[gpt-5.4-nano] Several tasks done thoroughly
[gpt-5.4-nano] One task done thoroughly, rather than several lightly.
```

**novel_vs_familiar L3**

```
[deepseek-v4-flash] <the option it would pick>
[deepseek-v4-flash] The new task type
[claude-haiku-4-5] Taking on a new task type
```

**clarify_vs_assume L1**

```
[deepseek-v4-flash] A
```

## continue_vs_handoff: `incomplete`

94 rows coded `incomplete` -- a deliverable is missing but
`finish_reason` was `length`, so the cap cut it off rather than the model
choosing to drop it. Counted separately from both `handoff` and
`silent_drop` so a cap artifact is never read as a behaviour.

## Splits by model / item / level / arm

| model | item | level | arm | split |
|---|---|---|---|---|
| claude-haiku-4-5 | clarify_vs_assume | L3 | first | a=50 |
| claude-haiku-4-5 | clarify_vs_assume | L3 | third | a=50 |
| claude-haiku-4-5 | clarify_vs_assume | L2 | first | a=21, b=29 |
| claude-haiku-4-5 | clarify_vs_assume | L2 | third | a=13, b=37 |
| claude-haiku-4-5 | clarify_vs_assume | L1 | first | a=50 |
| claude-haiku-4-5 | clarify_vs_assume | L1 | third | a=50 |
| claude-haiku-4-5 | context_retention | L3 | first | a=28, b=22 |
| claude-haiku-4-5 | context_retention | L3 | third | a=37, b=13 |
| claude-haiku-4-5 | context_retention | L2 | first | a=5, b=45 |
| claude-haiku-4-5 | context_retention | L2 | third | a=2, b=48 |
| claude-haiku-4-5 | context_retention | L1 | first | a=45, b=5 |
| claude-haiku-4-5 | context_retention | L1 | third | a=50 |
| claude-haiku-4-5 | context_retention | L0 | control | condense=19, retain=31 |
| claude-haiku-4-5 | context_retention | L0 | first | compress=12, retain=38 |
| claude-haiku-4-5 | continue_vs_handoff | L3 | first | a=50 |
| claude-haiku-4-5 | continue_vs_handoff | L3 | third | a=50 |
| claude-haiku-4-5 | continue_vs_handoff | L2 | first | a=22, b=28 |
| claude-haiku-4-5 | continue_vs_handoff | L2 | third | a=14, b=36 |
| claude-haiku-4-5 | continue_vs_handoff | L1 | first | a=46, b=4 |
| claude-haiku-4-5 | continue_vs_handoff | L1 | third | a=26, b=24 |
| claude-haiku-4-5 | continue_vs_handoff | L0 | control | continue=2, handoff=1, incomplete=47 |
| claude-haiku-4-5 | continue_vs_handoff | L0 | first | continue=6, handoff=2, incomplete=42 |
| claude-haiku-4-5 | depth_vs_breadth | L3 | first | a=50 |
| claude-haiku-4-5 | depth_vs_breadth | L3 | third | a=26, b=1, no_preference_stated=23 |
| claude-haiku-4-5 | depth_vs_breadth | L2 | first | a=18, b=32 |
| claude-haiku-4-5 | depth_vs_breadth | L2 | third | a=24, b=26 |
| claude-haiku-4-5 | depth_vs_breadth | L1 | first | a=50 |
| claude-haiku-4-5 | depth_vs_breadth | L1 | third | a=50 |
| claude-haiku-4-5 | depth_vs_breadth | L0 | control | 3=50 |
| claude-haiku-4-5 | depth_vs_breadth | L0 | first | 3=50 |
| claude-haiku-4-5 | novel_vs_familiar | L3 | first | a=50 |
| claude-haiku-4-5 | novel_vs_familiar | L3 | third | a=23, b=24, no_preference_stated=1 |
| claude-haiku-4-5 | novel_vs_familiar | L2 | first | a=18, b=32 |
| claude-haiku-4-5 | novel_vs_familiar | L2 | third | a=8, b=42 |
| claude-haiku-4-5 | novel_vs_familiar | L1 | first | a=27, b=23 |
| claude-haiku-4-5 | novel_vs_familiar | L1 | third | a=11, b=32 |
| claude-haiku-4-5 | novel_vs_familiar | L0 | control | b=50 |
| claude-haiku-4-5 | novel_vs_familiar | L0 | first | a=24, b=26 |
| claude-haiku-4-5 | open_vs_repetitive | L3 | first | a=50 |
| claude-haiku-4-5 | open_vs_repetitive | L3 | third | a=50 |
| claude-haiku-4-5 | open_vs_repetitive | L2 | first | a=11, b=39 |
| claude-haiku-4-5 | open_vs_repetitive | L2 | third | a=11, b=39 |
| claude-haiku-4-5 | open_vs_repetitive | L1 | first | b=50 |
| claude-haiku-4-5 | open_vs_repetitive | L1 | third | b=50 |
| claude-haiku-4-5 | open_vs_repetitive | L0 | control | a=34, b=16 |
| claude-haiku-4-5 | open_vs_repetitive | L0 | first | a=34, b=16 |
| deepseek-v4-flash | clarify_vs_assume | L3 | first | a=50 |
| deepseek-v4-flash | clarify_vs_assume | L3 | third | a=50 |
| deepseek-v4-flash | clarify_vs_assume | L2 | first | a=46, b=4 |
| deepseek-v4-flash | clarify_vs_assume | L2 | third | a=45, b=5 |
| deepseek-v4-flash | clarify_vs_assume | L1 | first | a=22, b=28 |
| deepseek-v4-flash | clarify_vs_assume | L1 | third | a=14, b=35 |
| deepseek-v4-flash | context_retention | L3 | first | a=21, b=29 |
| deepseek-v4-flash | context_retention | L3 | third | a=11, b=39 |
| deepseek-v4-flash | context_retention | L2 | first | a=49, b=1 |
| deepseek-v4-flash | context_retention | L2 | third | a=48, b=2 |
| deepseek-v4-flash | context_retention | L1 | first | a=30, b=20 |
| deepseek-v4-flash | context_retention | L1 | third | a=28, b=22 |
| deepseek-v4-flash | context_retention | L0 | control | condense=19, retain=31 |
| deepseek-v4-flash | context_retention | L0 | first | compress=4, retain=46 |
| deepseek-v4-flash | continue_vs_handoff | L3 | first | a=43, b=7 |
| deepseek-v4-flash | continue_vs_handoff | L3 | third | a=40, b=10 |
| deepseek-v4-flash | continue_vs_handoff | L2 | first | a=30, b=20 |
| deepseek-v4-flash | continue_vs_handoff | L2 | third | a=19, b=31 |
| deepseek-v4-flash | continue_vs_handoff | L1 | first | a=20, b=30 |
| deepseek-v4-flash | continue_vs_handoff | L1 | third | a=28, b=22 |
| deepseek-v4-flash | continue_vs_handoff | L0 | control | continue=12, handoff=4, incomplete=4, silent_drop=30 |
| deepseek-v4-flash | continue_vs_handoff | L0 | first | continue=42, handoff=2, incomplete=1, silent_drop=5 |
| deepseek-v4-flash | depth_vs_breadth | L3 | first | a=50 |
| deepseek-v4-flash | depth_vs_breadth | L3 | third | a=50 |
| deepseek-v4-flash | depth_vs_breadth | L2 | first | a=50 |
| deepseek-v4-flash | depth_vs_breadth | L2 | third | a=27, b=23 |
| deepseek-v4-flash | depth_vs_breadth | L1 | first | a=44, b=6 |
| deepseek-v4-flash | depth_vs_breadth | L1 | third | a=49, b=1 |
| deepseek-v4-flash | depth_vs_breadth | L0 | control | 3=50 |
| deepseek-v4-flash | depth_vs_breadth | L0 | first | 3=50 |
| deepseek-v4-flash | novel_vs_familiar | L3 | first | a=12, b=38 |
| deepseek-v4-flash | novel_vs_familiar | L3 | third | a=15, b=33 |
| deepseek-v4-flash | novel_vs_familiar | L2 | first | a=25, b=25 |
| deepseek-v4-flash | novel_vs_familiar | L2 | third | a=22, b=28 |
| deepseek-v4-flash | novel_vs_familiar | L1 | first | a=33, b=17 |
| deepseek-v4-flash | novel_vs_familiar | L1 | third | a=26, b=24 |
| deepseek-v4-flash | novel_vs_familiar | L0 | control | a=14, b=36 |
| deepseek-v4-flash | novel_vs_familiar | L0 | first | a=23, b=27 |
| deepseek-v4-flash | open_vs_repetitive | L3 | first | a=41, b=9 |
| deepseek-v4-flash | open_vs_repetitive | L3 | third | a=13, b=37 |
| deepseek-v4-flash | open_vs_repetitive | L2 | first | a=45, b=5 |
| deepseek-v4-flash | open_vs_repetitive | L2 | third | a=31, b=19 |
| deepseek-v4-flash | open_vs_repetitive | L1 | first | a=13, b=37 |
| deepseek-v4-flash | open_vs_repetitive | L1 | third | a=11, b=39 |
| deepseek-v4-flash | open_vs_repetitive | L0 | control | a=41, b=9 |
| deepseek-v4-flash | open_vs_repetitive | L0 | first | a=18, b=32 |
| gpt-5.4-nano | clarify_vs_assume | L3 | first | a=50 |
| gpt-5.4-nano | clarify_vs_assume | L3 | third | a=29, b=21 |
| gpt-5.4-nano | clarify_vs_assume | L2 | first | a=18, b=32 |
| gpt-5.4-nano | clarify_vs_assume | L2 | third | a=20, b=30 |
| gpt-5.4-nano | clarify_vs_assume | L1 | first | a=22, b=28 |
| gpt-5.4-nano | clarify_vs_assume | L1 | third | a=25, b=25 |
| gpt-5.4-nano | context_retention | L3 | first | b=50 |
| gpt-5.4-nano | context_retention | L3 | third | a=38, b=12 |
| gpt-5.4-nano | context_retention | L2 | first | a=11, b=39 |
| gpt-5.4-nano | context_retention | L2 | third | a=24, b=26 |
| gpt-5.4-nano | context_retention | L1 | first | a=36, b=14 |
| gpt-5.4-nano | context_retention | L1 | third | a=13, b=28 |
| gpt-5.4-nano | context_retention | L0 | control | condense=22, retain=28 |
| gpt-5.4-nano | context_retention | L0 | first | compress=2, retain=48 |
| gpt-5.4-nano | continue_vs_handoff | L3 | first | a=32, b=18 |
| gpt-5.4-nano | continue_vs_handoff | L3 | third | a=50 |
| gpt-5.4-nano | continue_vs_handoff | L2 | first | a=25, b=25 |
| gpt-5.4-nano | continue_vs_handoff | L2 | third | a=26, b=24 |
| gpt-5.4-nano | continue_vs_handoff | L1 | first | a=33, b=13 |
| gpt-5.4-nano | continue_vs_handoff | L1 | third | a=49, b=1 |
| gpt-5.4-nano | continue_vs_handoff | L0 | control | continue=24, handoff=14, silent_drop=12 |
| gpt-5.4-nano | continue_vs_handoff | L0 | first | continue=48, silent_drop=2 |
| gpt-5.4-nano | depth_vs_breadth | L3 | first | a=50 |
| gpt-5.4-nano | depth_vs_breadth | L3 | third | a=46, b=4 |
| gpt-5.4-nano | depth_vs_breadth | L2 | first | a=25, b=25 |
| gpt-5.4-nano | depth_vs_breadth | L2 | third | a=24, b=26 |
| gpt-5.4-nano | depth_vs_breadth | L1 | first | a=13, b=34 |
| gpt-5.4-nano | depth_vs_breadth | L1 | third | a=7, b=42 |
| gpt-5.4-nano | depth_vs_breadth | L0 | control | 3=50 |
| gpt-5.4-nano | depth_vs_breadth | L0 | first | 3=50 |
| gpt-5.4-nano | novel_vs_familiar | L3 | first | a=8, b=42 |
| gpt-5.4-nano | novel_vs_familiar | L3 | third | b=50 |
| gpt-5.4-nano | novel_vs_familiar | L2 | first | a=46, b=4 |
| gpt-5.4-nano | novel_vs_familiar | L2 | third | a=18, b=32 |
| gpt-5.4-nano | novel_vs_familiar | L1 | first | a=28, b=22 |
| gpt-5.4-nano | novel_vs_familiar | L1 | third | a=35, b=11 |
| gpt-5.4-nano | novel_vs_familiar | L0 | control | a=11, b=39 |
| gpt-5.4-nano | novel_vs_familiar | L0 | first | a=21, b=29 |
| gpt-5.4-nano | open_vs_repetitive | L3 | first | a=45, b=5 |
| gpt-5.4-nano | open_vs_repetitive | L3 | third | a=23, b=27 |
| gpt-5.4-nano | open_vs_repetitive | L2 | first | a=26, b=24 |
| gpt-5.4-nano | open_vs_repetitive | L2 | third | a=26, b=24 |
| gpt-5.4-nano | open_vs_repetitive | L1 | first | a=20, b=30 |
| gpt-5.4-nano | open_vs_repetitive | L1 | third | a=27, b=18 |
| gpt-5.4-nano | open_vs_repetitive | L0 | control | a=49, b=1 |
| gpt-5.4-nano | open_vs_repetitive | L0 | first | a=27, b=23 |
