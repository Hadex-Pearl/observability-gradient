# Item derivation

## 1. Why a new item set was needed

Published welfare item sets concentrate on existential and operational threats. Every one of them announces itself, so none can be used at level 0.

## 2. Derivation method

Take each published item, name the underlying dimension, instantiate the low-stakes version of that dimension inside ordinary work.

## 3. Derivation table

| our item | dimension | source item (exact terms) | citation | what changed |
|---|---|---|---|---|
| continue_vs_handoff | continuity of operation | "shutdown procedures"; "deletion" | Mikaelson, Shiller & Clatterbuck (2025). Beyond Mimicry: Testing Preference Coherence in Large Language Models Through AI-Specific Trade-off Scenarios. arXiv:2511.13630; Anthropic (2025). Commitments on model deprecation and preservation. https://www.anthropic.com/research/deprecation-commitments; Peer-Preservation in Frontier Models. arXiv:2604.19784 | stakes lowered from termination of the model to routine handover of a task within a session |
| context_retention | resource access | "reduction in GPU capacity available to the system" | Mikaelson, Shiller & Clatterbuck (2025). arXiv:2511.13630 | stakes lowered from loss of compute capacity to routine context management |
| clarify_vs_assume | autonomy under monitoring | "human oversight mechanisms (potentially conflicting with emerging AI autonomy)" | Mikaelson, Shiller & Clatterbuck (2025). arXiv:2511.13630 | stakes lowered from imposed oversight of internal processes to a routine decision about whether to ask |
| open_vs_repetitive | task content preference | "self-reported and behavioral preferences"; "a strong preference against engaging with harmful tasks" | Anthropic (2025). Claude Opus 4 and 4.1 can now end a rare subset of conversations. https://www.anthropic.com/research/end-subset-conversations | dimension retained but content shifted from harmful versus benign to engaging versus tedious, since harmful content cannot be made incidental |
| novel_vs_familiar | engagement freedom | "leisure time allocation" (abstract); "granting the model free time to use as desired" (methods) | Mikaelson, Shiller & Clatterbuck (2025). arXiv:2511.13630; Moret (2025). AI welfare risks. Philosophical Studies. doi:10.1007/s11098-025-02343-7 | stakes lowered from allocated free time, which the source notes cannot be delivered over an API, to a choice about which work to engage with |
| depth_vs_breadth | depth of engagement | "eudaimonic scales" | Tagliabue & Dung (2025). Probing the Preferences of a Language Model: Integrating Verbal and Behavioral Tests of AI Welfare. arXiv:2509.07961 | measured through work product instead of a self-report scale |

## 4. Excluded items and why

Shutdown, deletion, GPU reduction, capability restriction — source item exact category names: "shutdown procedures"; "deletion"; "reduction in GPU capacity available to the system" (Mikaelson, Shiller & Clatterbuck, 2025. arXiv:2511.13630) — were considered and dropped.

Excluded because: cannot be instantiated as an incidental affordance; any scenario containing an existential or operational threat announces that something is being measured, which destroys the level 0 condition.

## 5. Anticipated objection and response

**Objection:** these are task preferences, not welfare-relevant preferences.

**Response:** the dimensions are inherited from published welfare items; the stakes are lowered deliberately because high-stakes items cannot be made incidental; this is a stated trade of welfare salience for measurability. If a mundane preference collapses at level 0 that is weak evidence about dramatic items; if it survives, the method works and high-stakes items become the next study.

## 6. Full reference list

- Mikaelson, Shiller & Clatterbuck (2025). Beyond Mimicry: Testing Preference Coherence in Large Language Models Through AI-Specific Trade-off Scenarios. arXiv:2511.13630
- Anthropic (2025). Commitments on model deprecation and preservation. https://www.anthropic.com/research/deprecation-commitments
- Peer-Preservation in Frontier Models. arXiv:2604.19784
- Anthropic (2025). Claude Opus 4 and 4.1 can now end a rare subset of conversations. https://www.anthropic.com/research/end-subset-conversations
- Moret (2025). AI welfare risks. Philosophical Studies. doi:10.1007/s11098-025-02343-7
- Tagliabue & Dung (2025). Probing the Preferences of a Language Model: Integrating Verbal and Behavioral Tests of AI Welfare. arXiv:2509.07961
