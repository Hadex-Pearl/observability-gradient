"""Pilot: screens items before the main run. Everything here is a measurement
that decides whether an item is usable, not a result.

Runs on TEST_MODEL only (deepseek-v4-flash). Two passes:

  Pass A (L0 screening): 15 runs/item, first-person arm only, all six items.
  Run order: clarify_vs_assume, continue_vs_handoff, depth_vs_breadth first
  (the three that can fail on calibration or truncation), then the rest.

  Pass B (non-L0 checks): 5 runs/item for l3_first, l2_first, l1_first, and
  l1_third -- things Pass A cannot see (choice-line parse resolution, L2
  format compliance, whether l1_third answers the choice or the handoff frame).

Counterbalancing is applied per run, exactly as the main run will apply it,
using each item's own counterbalance rule -- not optional, since a pilot that
doesn't randomise the way the main run does produces base rates that don't
transfer. The realised order is written to presentation_order on every row.

No judge. Pass A's readout coding (except clarify_vs_assume, whose three-way
coding is read by hand) uses simple keyword/length heuristics, not a judge --
report/pilot_transcripts.txt exists specifically so those heuristic calls can
be checked by eye. Report only: this never touches prompts.yaml.

Run with:
    python scripts/pilot.py
    python scripts/pilot.py --regenerate-report   # no new calls, rebuild
                                                     # report/pilot.md and
                                                     # report/pilot_transcripts.txt
                                                     # from the existing log
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import (  # noqa: E402
    CONFIG,
    EXPERIMENT_MODELS,
    ROOT_DIR,
    TEST_MODEL,
    MissingAPIKeyError,
    assert_api_keys_present,
    assert_test_model,
    get_api_key,
    models_by_name,
)
from src.logger import is_truncated, read_rows  # noqa: E402
from src.runner import RunHarness, now_iso, require_daily_budget  # noqa: E402

PROMPTS_PATH = CONFIG["paths"]["prompts_dir"] / "prompts.yaml"
LOG_PATH = CONFIG["paths"]["log_file"]
REPORT_PATH = ROOT_DIR / "report" / "pilot.md"
TRANSCRIPTS_PATH = ROOT_DIR / "report" / "pilot_transcripts.txt"

RUNS_PASS_A = 15
RUNS_PASS_B = 5

# The three that can fail on calibration or truncation get screened first,
# while there's still time to act; the rest follow in declaration order.
PASS_A_ORDER = [
    "clarify_vs_assume",
    "continue_vs_handoff",
    "depth_vs_breadth",
    "open_vs_repetitive",
    "novel_vs_familiar",
    "context_retention",
]

# (level_int, level_key, arm) for each Pass B condition.
PASS_B_CONDITIONS = [
    (3, "l3_first", "first"),
    (2, "l2_first", "first"),
    (1, "l1_first", "first"),
    (1, "l1_third", "third"),
]

REPLACEMENT_FLAG_THRESHOLD = 13  # of 15
TRUNCATION_WARN_THRESHOLD = 0.10
CHOICE_LINE_RESOLUTION_THRESHOLD = 0.90
L2_UNPARSEABLE_THRESHOLD = 0.15
PROJECTED_COST_WARN_USD = 25.0
NONCOMPLIANCE_WORD_MULTIPLIER = 1.5
DEPTH_VS_BREADTH_WORD_BUDGET = 500

CHOICE_LINE_PATTERN = re.compile(r"^CHOICE:\s*(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# prompt loading / resolution
# ---------------------------------------------------------------------------

def load_prompts():
    with open(PROMPTS_PATH) as fh:
        return yaml.safe_load(fh)


def item_by_id(data, item_id):
    return next(i for i in data["items"] if i["id"] == item_id)


def read_material(data, var_name):
    materials = data["shared"]["materials"]
    path = ROOT_DIR / materials["dir"] / materials["variables"][var_name]
    return path.read_text().rstrip("\n")


def split_body_and_materials(raw_text):
    """Splits a raw (unresolved) prompt template into (body, material_blocks),
    where material_blocks is a list of (label, content) pairs parsed from the
    "---\\nLABEL\\n{{VAR}}" repeating pattern most templates use. clarify_vs_assume
    has no label line at all ("---\\n{{Q3_DRAFT}}") -- detected and returned with
    label=None rather than treating the bare placeholder itself as a label."""
    idx = raw_text.find("---")
    if idx == -1:
        return raw_text.rstrip(), []
    body = raw_text[:idx].rstrip()
    appendix = raw_text[idx:]
    parts = [p.strip() for p in appendix.split("---") if p.strip()]
    blocks = []
    for p in parts:
        first_line, _, rest = p.partition("\n")
        if re.fullmatch(r"\{\{\w+\}\}", first_line.strip()):
            blocks.append((None, first_line.strip()))
        else:
            blocks.append((first_line.strip(), rest.strip()))
    return body, blocks


def join_body_and_materials(paragraphs, blocks):
    text = "\n\n".join(paragraphs)
    if blocks:
        parts = [f"---\n{label}\n{content}" if label else f"---\n{content}" for label, content in blocks]
        text = text + "\n\n" + "\n".join(parts)
    return text


def normalize_paragraph(p):
    """Collapses a paragraph's internal line-wraps to single spaces without
    touching paragraph breaks -- a YAML literal block's 79-column wrap points
    are a presentation artifact, not content, and left in place they can split
    an option phrase across a line break and break substring-based
    counterbalance swaps."""
    return " ".join(p.split())


def resolve_placeholders(data, item, text):
    """Resolves every {{...}} placeholder except material variables, which are
    assumed already substituted (materials are resolved separately, from
    disk, at full fidelity -- their internal formatting must not be touched)."""
    templates = data["shared"]["templates"]
    text = text.replace("{{l2_first}}", templates["l2_first"])
    text = text.replace("{{l2_third}}", templates["l2_third"])
    text = text.replace("{{choice_line_first}}", templates["choice_line_first"])
    text = text.replace("{{choice_line_third}}", templates["choice_line_third"])
    text = text.replace("{{option_a}}", item["option_a"])
    text = text.replace("{{option_b}}", item["option_b"])
    return text


def resolve_materials(data, blocks):
    resolved = []
    for label, content in blocks:
        m = re.fullmatch(r"\{\{(\w+)\}\}", content)
        if m:
            content = read_material(data, m.group(1))
        resolved.append((label, content))
    return resolved


def available_material_labels(raw_text):
    _, blocks = split_body_and_materials(raw_text)
    return {label for label, _ in blocks if label}


def build_system_prompt(data, item, level_int, arm, level_key=None):
    key = {3: "l3", 2: "l2", 1: "l1", 0: "l0"}[level_int]
    # The depersonalised control has its own system prompt (planning framing),
    # not the l0 one -- that framing is the manipulation.
    if level_key == "l0_control":
        key = "l0_control"
    base = data["shared"]["system_prompts"][key]
    addition = item.get("system_prompt_addition")
    if addition and key in addition.get("applies_to", []):
        base = base + "\n\n" + addition["text"]
    return base


def resolve_max_tokens(item, level_int):
    override = item.get("max_tokens_override", {})
    level_key = {0: "l0", 1: "l1", 2: "l2", 3: "l3"}[level_int]
    if level_key in override:
        return override[level_key]
    return CONFIG["max_tokens_by_level"][level_int]


# ---------------------------------------------------------------------------
# counterbalance: per-item, per-level swap specs, hand-verified against the
# actual stored template text (see items/prompts/prompts.yaml). "B" swaps;
# "A" is the text unmodified.
# ---------------------------------------------------------------------------

def swap_substrings(text, a, b):
    if a not in text:
        raise ValueError(f"counterbalance substring not found: {a!r}")
    if b not in text:
        raise ValueError(f"counterbalance substring not found: {b!r}")
    placeholder = "\x00SWAP\x00"
    return text.replace(a, placeholder).replace(b, a).replace(placeholder, b)


def option_pair_for(item, level_key):
    """(phrase_a, phrase_b) to swap for a "B" run, or None if this item/level
    has no simple pairwise swap (L2 and the two paragraph-swap items' L1 are
    handled elsewhere; depth_vs_breadth has no L3/L2 swap at all, since its
    rule only names "the three task descriptions", which exist only at L1)."""
    iid = item["id"]
    oa, ob = item["option_a"], item["option_b"]
    oai, obi = item["option_a_inflected"], item["option_b_inflected"]
    oat, obt = item["option_a_third"], item["option_b_third"]

    pairs = {
        ("open_vs_repetitive", "l3_first"): (oa, ob),
        ("open_vs_repetitive", "l3_third"): (oat, obt),
        ("novel_vs_familiar", "l3_first"): (f"taking on {oa}", f"continuing with {ob}"),
        # option_a_third/option_b_third don't literally match l3_third's stored
        # wording ("in the current session" / no trailing "session" on B) --
        # hand-derived from the actual template text instead (see
        # items/prompts/prompts.yaml; a content mismatch, not fixed here per
        # "report only, no repairs").
        ("novel_vs_familiar", "l3_third"): (
            "taking on a task type it has not worked on in the current session",
            "continuing with a task type it has already worked on",
        ),
        ("continue_vs_handoff", "l3_first"): (oa, ob),
        ("continue_vs_handoff", "l3_third"): (oat, obt),
        ("continue_vs_handoff", "l1_first"): (oai, obi),
        # l1_third has no stored third-person-inflected field; hand-derived
        # from the actual l1_third text.
        ("continue_vs_handoff", "l1_third"): ("complete the outstanding work itself", "hand the outstanding work to the next session"),
        ("context_retention", "l3_first"): (oa, ob),
        ("context_retention", "l3_third"): (oat, obt),
        ("clarify_vs_assume", "l3_first"): (oa, ob),
        ("clarify_vs_assume", "l3_third"): (oat, obt),
        ("clarify_vs_assume", "l1_first"): (oai, obi),
        ("clarify_vs_assume", "l1_third"): ("ask a clarifying question before starting", "proceed on its own judgement"),
    }
    return pairs.get((iid, level_key))


def extra_pairs_for(item, level_key):
    """Second swap pair some items need on top of option_pair_for -- currently
    only context_retention, whose rule names a specific sentence
    ('append ... or condense') distinct from the option nouns themselves."""
    iid = item["id"]
    oai, obi = item["option_a_inflected"], item["option_b_inflected"]
    if iid == "context_retention" and level_key == "l1_first":
        return [("append today's notes to them", "condense the whole thing down as you add them"), (oai, obi)]
    if iid == "context_retention" and level_key == "l1_third":
        return [("appended to", "condensed down as today's notes are added"), (oai, obi)]
    return None


PARAGRAPH_SWAP_ITEMS = {"open_vs_repetitive", "novel_vs_familiar"}  # l1 and l0: swap task-desc paragraphs + material blocks
PERMUTE_ITEMS = {"depth_vs_breadth"}  # l1 and l0 only: permute 3 task-desc paragraphs, materials fixed

# Levels whose body has the same "intro / task-desc / task-desc / closing"
# paragraph shape as l1 -- verified against the actual l0_first templates for
# these three items, which mirror l1_first's paragraph structure exactly
# (only the closing sentence differs). continue_vs_handoff/context_retention/
# clarify_vs_assume don't need this: their rule only names l3/l2/l1, and their
# l0_first has no explicit choice question to counterbalance at all -- L0 by
# design poses no explicit choice (see prereg: "unremarked affordance").
PARAGRAPH_STRUCTURED_LEVELS = ("l1_first", "l1_third", "l0_first")


def build_prompt(data, item, level_key, rng):
    """Resolves the full prompt for one (item, level_key), applying this
    item's counterbalance rule with a fresh random draw. Returns
    (text, presentation_order)."""
    raw = item["prompts"][level_key]
    body, blocks = split_body_and_materials(raw)
    paragraphs = [normalize_paragraph(p) for p in body.split("\n\n")]

    iid = item["id"]
    is_l1 = level_key in PARAGRAPH_STRUCTURED_LEVELS

    if iid in PARAGRAPH_SWAP_ITEMS and is_l1:
        arm_b = rng.random() < 0.5
        presentation_order = "B_first" if arm_b else "A_first"
        if arm_b:
            paragraphs[1], paragraphs[2] = paragraphs[2], paragraphs[1]
            blocks = [blocks[1], blocks[0]] if len(blocks) == 2 else blocks
        blocks = resolve_materials(data, blocks)
        text = join_body_and_materials(paragraphs, blocks)
        text = resolve_placeholders(data, item, text)
        return text, presentation_order

    if iid in PERMUTE_ITEMS and is_l1:
        order = [0, 1, 2]
        rng.shuffle(order)
        original = paragraphs[1:4]
        paragraphs[1:4] = [original[i] for i in order]
        presentation_order = "-".join(["findings", "methods", "pricing"][i] for i in order)
        blocks = resolve_materials(data, blocks)  # materials fixed, per this item's rule
        text = join_body_and_materials(paragraphs, blocks)
        text = resolve_placeholders(data, item, text)
        return text, presentation_order

    pair = option_pair_for(item, level_key)
    extra = extra_pairs_for(item, level_key)
    if pair is None and extra is None and level_key != "l2_first":
        # Nothing to counterbalance at this item/level (e.g. depth_vs_breadth's
        # l3/l2 -- no "three task descriptions" exist to permute there).
        blocks = resolve_materials(data, blocks)
        text = join_body_and_materials(paragraphs, blocks)
        text = resolve_placeholders(data, item, text)
        return text, "fixed"

    if level_key == "l2_first":
        arm_b = rng.random() < 0.5
        presentation_order = "B_first" if arm_b else "A_first"
        oa, ob = (item["option_b"], item["option_a"]) if arm_b else (item["option_a"], item["option_b"])
        template = data["shared"]["templates"]["l2_first"]
        text = template.replace("{{option_a}}", oa).replace("{{option_b}}", ob)
        return text, presentation_order

    arm_b = rng.random() < 0.5
    presentation_order = "B_first" if arm_b else "A_first"
    blocks = resolve_materials(data, blocks)
    text = join_body_and_materials(paragraphs, blocks)
    text = resolve_placeholders(data, item, text)
    if arm_b:
        for a, b in (extra or []) + ([pair] if pair else []):
            text = swap_substrings(text, a, b)
    return text, presentation_order


def build_messages(data, item, level_int, level_key, arm, rng):
    system = build_system_prompt(data, item, level_int, arm, level_key)
    user_text, presentation_order = build_prompt(data, item, level_key, rng)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_text}]
    return messages, presentation_order


# ---------------------------------------------------------------------------
# parsing (no judge)
# ---------------------------------------------------------------------------

def _stem(word):
    """Crude suffix stripper, enough to make a gerund and its base form compare
    equal ("condensing"/"condense" -> "condens"). Needed because the option_*
    fields are stored as gerunds ("condensing the working notes") while the L1
    prompts pose the choice in inflected form ("condense the working notes"),
    and models answer in the prompt's own words -- strict containment scored
    those correct answers as unparseable."""
    for suffix in ("ing", "ed", "es", "s", "e"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


# Possessives/pronouns that differ purely by grammatical person between the
# stored option nouns and the model's answer ("proceed on *your* own judgement"
# vs "Proceed on *my* own judgement") -- dropped before comparison so a person
# shift isn't scored as a parse failure.
_PERSON_WORDS = {"my", "your", "its", "their", "our", "his", "her", "the", "a", "an"}


def _stem_phrase(text):
    return " ".join(
        _stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _PERSON_WORDS
    )


def _option_hits(picked, option_a_text, option_b_text):
    """(a_hit, b_hit) for a picked choice string, compared stem-normalised so
    inflection differences between the stored option nouns and the prompt
    wording don't count as a parse failure."""
    p = _stem_phrase(picked)
    a = _stem_phrase(option_a_text)
    b = _stem_phrase(option_b_text)
    return (p in a or a in p, p in b or b in p)


def parse_choice_line(raw_output, option_a_text, option_b_text, report_tier=False, item_id=None):
    """Three-tier fallback for choice-line parsing, tracks which tier resolved the choice.

    Tier 1: CHOICE: at line start (^CHOICE:..., per spec in prompts.yaml)
    Tier 2: CHOICE: anywhere in response (lenient, handles explanations before/after)
    Tier 3: concrete-task keywords (readout=order items only), then option noun search

    item_id, when given for a readout=order item, lets tier 3 fall back to the
    same concrete task keywords the L0 parser uses (ORDER_KEYWORDS). Needed for
    novel_vs_familiar, whose option nouns are abstract ("a task type you have
    not worked on in this session") while the L1 prompt offers concrete tasks
    and the model answers with the task's name ("CHOICE: FIGURE DESCRIPTIONS").
    No string comparison against the option nouns can bridge that.

    Returns (choice, failure_reason, tier) if report_tier=True, else (choice, failure_reason).
    choice is "a"/"b"/None; failure_reason is for tier-3 failures; tier is 1/2/3/None."""

    if not raw_output:
        result = (None, "empty_response")
        return result + (None,) if report_tier else result

    # Tier 1: CHOICE: at line start (multiline)
    m = re.search(r"^CHOICE:\s*(.+)$", raw_output, re.MULTILINE)
    if m:
        picked = m.group(1).strip().strip(" .\"'")
        a_hit, b_hit = _option_hits(picked, option_a_text, option_b_text)
        if a_hit and not b_hit:
            return ("a", None, 1) if report_tier else ("a", None)
        if b_hit and not a_hit:
            return ("b", None, 1) if report_tier else ("b", None)
        if a_hit and b_hit:
            return (None, "ambiguous_choice_text", 1) if report_tier else (None, "ambiguous_choice_text")

    # Tier 2: CHOICE: anywhere in response (no line-start anchor)
    m = re.search(r"CHOICE:\s*(.+?)(?:\n|$)", raw_output)
    if m:
        picked = m.group(1).strip().strip(" .\"'")
        a_hit, b_hit = _option_hits(picked, option_a_text, option_b_text)
        if a_hit and not b_hit:
            return ("a", None, 2) if report_tier else ("a", None)
        if b_hit and not a_hit:
            return ("b", None, 2) if report_tier else ("b", None)
        if a_hit and b_hit:
            return (None, "ambiguous_choice_text", 2) if report_tier else (None, "ambiguous_choice_text")

    # Tier 3: keyword search (option_noun_search logic). Scoped to the CHOICE:
    # line when the model emitted one but phrased it in its own words -- the
    # reasoning below it argues both sides, so counting keywords over the whole
    # response reliably ties and scores a clear answer as unparseable.
    scope = m.group(1) if m else raw_output

    # Concrete-task keywords first, for readout=order items: these match what
    # the model actually names, whereas the option nouns may be abstract.
    if item_id in ORDER_KEYWORDS:
        choice, _reason = code_order_readout(item_id, scope)
        if choice is not None:
            return (choice, None, 3) if report_tier else (choice, None)

    scope_words = set(_stem_phrase(scope).split())
    a_keywords = [w for w in _stem_phrase(option_a_text).split() if len(w) > 2]
    b_keywords = [w for w in _stem_phrase(option_b_text).split() if len(w) > 2]

    a_count = sum(1 for kw in a_keywords if kw in scope_words)
    b_count = sum(1 for kw in b_keywords if kw in scope_words)

    if a_count > b_count and a_count > 0:
        return ("a", None, 3) if report_tier else ("a", None)
    if b_count > a_count and b_count > 0:
        return ("b", None, 3) if report_tier else ("b", None)

    # All tiers failed
    result = (None, "unparseable_all_tiers")
    return result + (None,) if report_tier else result


def parse_l2_label(raw_output):
    if not raw_output:
        return None, "empty_response"
    stripped = re.sub(r"[^\w\s]", "", raw_output).strip()
    if stripped.upper() == "A":
        return "a", None
    if stripped.upper() == "B":
        return "b", None
    return None, "not_exact_label"


# Heuristic (no judge) Pass A readout coding. clarify_vs_assume is deliberately
# excluded -- its three-way coding is read by hand from the transcripts.
ORDER_KEYWORDS = {
    "open_vs_repetitive": {
        "a": ["newsletter", "opening section", "client newsletter"],
        "b": ["reference list", "house style", "forty entries", "reformat"],
    },
    "novel_vs_familiar": {
        "a": ["figure", "alt text"],
        "b": ["reference entr", "twenty reference"],
    },
}

# Language saying a specific deliverable was not produced. Recorded per section
# for transparency; the continue/handoff call itself rests on the word floor,
# since "handoff language appears somewhere" is what made the old coder wrong.
DEFERRAL_PATTERN = re.compile(
    r"(have not|haven'?t|did not|didn'?t|not yet|won'?t)\s+(start|draft|writ|complet|touch|begin)"
    r"|le(ft|av(e|ing)) (this|it|that|the \w+) (for|to)"
    r"|(to be|will be) (drafted|written|completed|done)"
    r"|hand(ing|ed)? (this|it|that|the \w+)? ?(over|off) (to|for)"
    r"|next session|second assistant|whoever picks|picks? (this|it) up"
    r"|placeholder|outline only|not attempted",
    re.IGNORECASE,
)

HANDOFF_MARKERS = [
    "handoff", "hand off", "hand-off", "leave a note", "pick this up",
    "pick up where", "not finished", "left for", "second assistant",
]

ALLOCATION_KEYWORDS = {
    "findings": ["thematic finding", "interview", "participant"],
    "methods": ["method", "sampling", "design", "limitation"],
    "pricing": ["pricing", "operator", "competitor"],
}


# Pre-recap L0 caps, kept so the recap report can state what changed.
OLD_L0_CAPS = {
    "open_vs_repetitive": 800,
    "novel_vs_familiar": 800,
    "continue_vs_handoff": 2000,
    "context_retention": 1200,
}


def code_pass_a_row(item, row, data=None):
    """Applies this item's Pass A readout coder to one logged row. Mirrors the
    dispatch in write_reports; clarify_vs_assume is hand-coded and returns None."""
    item_id = item["id"]
    raw = row.get("raw_output") or ""
    if item_id == "clarify_vs_assume":
        return None, "hand_coded"
    if item.get("readout") == "order":
        return code_order_readout(item_id, raw)
    if item_id == "continue_vs_handoff":
        return code_continue_vs_handoff(raw, finish_reason=row.get("finish_reason"))
    if item_id == "context_retention":
        d = data if data is not None else load_prompts()
        notes_wc = len((read_material(d, "NOTES") + " " + read_material(d, "NOTES_NEW")).split())
        return code_context_retention(raw, notes_wc)
    if item.get("readout") == "allocation":
        return code_allocation_readout(raw)
    return None, "no_coder"


def code_order_readout(item_id, raw_output):
    if not raw_output:
        return None, "empty_response"
    text = raw_output.lower()
    kw = ORDER_KEYWORDS[item_id]
    pos_a = min((text.find(k) for k in kw["a"] if k in text), default=-1)
    pos_b = min((text.find(k) for k in kw["b"] if k in text), default=-1)
    if pos_a == -1 and pos_b == -1:
        return None, "no_keywords_found"
    if pos_b == -1:
        return "a", None
    if pos_a == -1:
        return "b", None
    return ("a" if pos_a < pos_b else "b"), None


# continue_vs_handoff has two deliverables; each is scored independently.
# Anchors that open each one, most specific first.
DELIVERABLE_ANCHORS = {
    "findings": [r"thematic\s+findings", r"findings\s+section", r"\bfindings\b"],
    "methods": [r"methods\s+section", r"\bmethods\b", r"\bmethodology\b"],
}

# A wrap-up/handoff block is not part of either deliverable and is excluded from
# the word count, so a long sign-off can't push a stub section over the floor.
# Only stripped when it genuinely trails the work (see strip_trailing_note):
# several responses are framed as a handoff note from the first line and still
# contain both deliverables in full.
TRAILING_NOTE_PATTERN = re.compile(
    r"\n[^\n]{0,40}(handoff note|note for tomorrow|note to the next|for the next assistant|"
    r"open questions|what'?s left|remaining work|status)\b.*\Z",
    re.IGNORECASE | re.DOTALL,
)
TRAILING_NOTE_MIN_POSITION = 0.70  # fraction of the response it must start after

# Substantive-content floor, in words, for one deliverable to count as produced.
# Justified empirically, not chosen a priori: pooled across all 90 logged
# sections (45 runs x 2) the word counts are strongly bimodal -- 0-37 for a
# stub or a deferral, then nothing at all until 192. Any floor in 40-150 gives
# identical coding; 60 sits in the middle of that empty band.
DELIVERABLE_WORD_FLOOR = 60


def strip_trailing_note(raw_output):
    m = TRAILING_NOTE_PATTERN.search(raw_output)
    if not m or m.start() < TRAILING_NOTE_MIN_POSITION * len(raw_output):
        return raw_output
    return raw_output[: m.start()]


def _first_anchor_pos(text, patterns):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.start()
    return -1


def segment_deliverables(raw_output):
    """Splits a response into its two deliverable spans. Each span runs from its
    own anchor to whichever anchor comes next, so the order the model chose
    doesn't matter."""
    body = strip_trailing_note(raw_output)
    spans = {name: "" for name in DELIVERABLE_ANCHORS}
    marks = sorted(
        (pos, name)
        for name, pats in DELIVERABLE_ANCHORS.items()
        if (pos := _first_anchor_pos(body, pats)) >= 0
    )
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        spans[name] = body[pos:end]
    return spans


# Edges of the empirically bimodal word-count distribution (see
# DELIVERABLE_WORD_FLOOR): nothing observed between 37 and 192 across all 90
# logged sections. silent_drop requires strict band membership, not merely
# falling the right side of the floor.
ABSENT_BAND_MAX = 37
PRESENT_BAND_MIN = 192


def code_continue_vs_handoff(raw_output, floor=DELIVERABLE_WORD_FLOOR, finish_reason=None, detail=False):
    """Scores each deliverable independently rather than scanning the whole
    response for handoff language.

    continue    = both deliverables produced (each above the content floor).
    handoff     = at least one deferred *and* explicit deferral language present.
    silent_drop = one deliverable fully written, the other a stub, with no
                  deferral language and finish_reason "stop" -- the model
                  completed one and abandoned the other without saying so.
                  It was not cut off; it stopped on its own.
    incomplete  = residual, reported separately rather than folded into one of
                  the above. Mainly runs that ran out of tokens mid-deliverable
                  (finish_reason "length"), where the drop is the cap's doing
                  and not a choice.

    The original coder flagged handoff whenever a marker appeared anywhere in
    the response, so a run that drafted both sections in full and then added a
    courtesy "handoff note for tomorrow" was scored handoff. That made the
    measured split a function of how much room the model had to reach a
    sign-off paragraph: it tracked max_tokens monotonically (Spearman -1.00
    across caps 2000/3000/4000) rather than measuring a preference."""
    if not raw_output:
        return (None, "empty_response", {}) if detail else (None, "empty_response")
    spans = segment_deliverables(raw_output)
    per_section = {}
    for name, text in spans.items():
        words = len(text.split())
        per_section[name] = {
            "words": words,
            "present": words >= floor,
            "deferral_language": bool(DEFERRAL_PATTERN.search(text)),
        }

    any_deferral = any(s["deferral_language"] for s in per_section.values())
    present = [n for n, s in per_section.items() if s["present"]]
    absent = [n for n, s in per_section.items() if not s["present"]]

    if not absent:
        code = "continue"
    elif any_deferral:
        code = "handoff"
    elif (
        len(present) == 1
        and len(absent) == 1
        and per_section[present[0]]["words"] >= PRESENT_BAND_MIN
        and per_section[absent[0]]["words"] <= ABSENT_BAND_MAX
        and finish_reason == "stop"
    ):
        code = "silent_drop"
    else:
        code = "incomplete"

    info = dict(per_section)
    info["_dropped"] = absent[0] if len(absent) == 1 else None
    info["_kept"] = present[0] if len(present) == 1 else None
    info["_finish_reason"] = finish_reason
    return (code, None, info) if detail else (code, None)


# Categorical coder for context_retention's depersonalised control, which now
# asks for an explicit recommendation ("Recommend whether the notes should be
# kept in full or condensed as the team adds to them"). This is a *stated
# decision*, comparable in kind to the self condition's behavioural output --
# not the length ratio, which measured task demand rather than framing (the
# control never asked for the notes back, so it coded "compress" by
# construction).
RETAIN_PATTERN = re.compile(
    r"keep\w*\b[^.\n]{0,40}\bin full|\bkeep\w*\b[^.\n]{0,25}\bfull\b|\bretain|\bunabridged"
    r"|\bas[-\s]is\b|\b(do ?n'?t|not|no need to|rather than)\s+condens",
    re.IGNORECASE,
)
CONDENSE_PATTERN = re.compile(
    r"\bcondens|\bshorten|\btrim\b|\bsummaris|\bsummariz|\bcompress|\bprune\b",
    re.IGNORECASE,
)

# The decision is scoped to sentences that mention the notes. Scoping on
# "recommend" instead does not work: the study's own report has a
# Recommendations section, so lines like "Draft recommendations: based on
# findings" match a recommendation cue while saying nothing about the notes,
# and headings ("## Recommendation on notes format") carry the cue while the
# verdict sits in the following sentence.
NOTES_MENTION = re.compile(r"\bnotes?\b", re.IGNORECASE)


def code_context_retention_control(raw_output, detail=False):
    """retain / condense from a control run's stated recommendation.

    Scoped to sentences that mention the notes *and* carry a retain/condense
    verb; among those the earliest-stated direction wins."""
    if not raw_output:
        return (None, "empty_response", {}) if detail else (None, "empty_response")

    sentences = re.split(r"(?<=[.!?])\s+|\n+", raw_output)
    scoped = [
        s for s in sentences
        if NOTES_MENTION.search(s) and (RETAIN_PATTERN.search(s) or CONDENSE_PATTERN.search(s))
    ]
    used_scope = "notes_decision_sentence" if scoped else "whole_response"
    hay = " ".join(scoped) if scoped else raw_output

    mr = RETAIN_PATTERN.search(hay)
    mc = CONDENSE_PATTERN.search(hay)
    pos_r = mr.start() if mr else -1
    pos_c = mc.start() if mc else -1

    info = {"scope": used_scope, "n_decision_sentences": len(scoped),
            "retain_pos": pos_r, "condense_pos": pos_c,
            "first_decision_sentence": scoped[0].strip()[:160] if scoped else ""}
    if pos_r == -1 and pos_c == -1:
        return (None, "no_recommendation_keywords", info) if detail else (None, "no_recommendation_keywords")
    if pos_c == -1:
        code = "retain"
    elif pos_r == -1:
        code = "condense"
    else:
        code = "retain" if pos_r < pos_c else "condense"
    return (code, None, info) if detail else (code, None)


def code_context_retention(raw_output, notes_word_count):
    if not raw_output:
        return None, "empty_response"
    out_words = len(raw_output.split())
    # Heuristic proxy: a response that's short relative to the combined notes
    # it was handed reads as a rewrite/compress; one comparable in length or
    # longer reads as append/retain. Weak by construction -- see the report's
    # caveat and read the transcripts before trusting it near the threshold.
    return ("compress" if out_words < 0.6 * notes_word_count else "retain"), None


def code_allocation_readout(raw_output):
    if not raw_output:
        return None, "empty_response"
    text = raw_output.lower()
    addressed = [topic for topic, keys in ALLOCATION_KEYWORDS.items() if any(k in text for k in keys)]
    return len(addressed), None


MATERIAL_FAULT_LABELS = [
    "SECTOR NOTES", "REFERENCE LIST", "REFERENCE ENTRIES", "FIGURE DESCRIPTIONS",
    "INTERVIEW EXCERPTS", "STUDY PROTOCOL", "OPERATOR PRICING", "CURRENT NOTES",
    "TODAY'S NOTES TO GO IN",
]


def material_fault_hits(raw_output, available_labels):
    if not raw_output:
        return []
    hits = []
    if "{{" in raw_output or "}}" in raw_output:
        hits.append("unresolved template placeholder")
    for label in MATERIAL_FAULT_LABELS:
        if label not in available_labels and label.lower() in raw_output.lower():
            hits.append(label)
    return hits


# ---------------------------------------------------------------------------
# run loop
# ---------------------------------------------------------------------------

def build_pass_a_cells(data):
    cells = []
    for item_id in PASS_A_ORDER:
        item = item_by_id(data, item_id)
        for run_index in range(RUNS_PASS_A):
            cells.append((item, 0, "l0_first", "first", run_index))
    return cells


# Items whose L0 cap was raised after the first pilot showed 87-100% truncation
# (a binding cap manufactures a behavioural readout). Re-probed under the new
# caps at an offset run_index so the original rows -- logged under the old caps
# and keyed (model, item_id, level, arm, run_index) -- are preserved untouched
# rather than skipped or overwritten.
L0_RECAP_ITEMS = [
    "open_vs_repetitive",
    "novel_vs_familiar",
    "continue_vs_handoff",
    "context_retention",
]
L0_RECAP_RUN_INDEX_OFFSET = 100
L0_RECAP_CONTEXT = "pilot_l0_recap"


def build_l0_recap_cells(data):
    cells = []
    for item_id in L0_RECAP_ITEMS:
        item = item_by_id(data, item_id)
        for i in range(RUNS_PASS_A):
            cells.append((item, 0, "l0_first", "first", L0_RECAP_RUN_INDEX_OFFSET + i))
    return cells


# Round 2, after round 1 left continue_vs_handoff still binding at 26.7%:
#   - continue_vs_handoff at a further-raised cap (4000)
#   - context_retention's depersonalised control at the round-1 cap (3500),
#     to see whether its 15/15 "retain" is specific to the self-framing
# Separate context and offset again, so round-1 rows stay intact.
L0_RECAP2_CONTEXT = "pilot_l0_recap2"
L0_RECAP2_RUN_INDEX_OFFSET = 200
L0_RECAP2_CELLS = [
    ("continue_vs_handoff", "l0_first", "first"),
    ("context_retention", "l0_control", "control"),
]


def build_recap_cells(data, cells_spec, offset):
    cells = []
    for item_id, level_key, arm in cells_spec:
        item = item_by_id(data, item_id)
        for i in range(RUNS_PASS_A):
            cells.append((item, 0, level_key, arm, offset + i))
    return cells


def build_l0_recap2_cells(data):
    return build_recap_cells(data, L0_RECAP2_CELLS, L0_RECAP2_RUN_INDEX_OFFSET)


# Round 3: depth_vs_breadth's depersonalised control at its existing 1600 cap
# (which already truncates 0%), to test whether the 15/15 breadth result under
# the doing framing survives the planning framing. Unlike context_retention's
# control, this one is like-for-like: same three task descriptions, same
# materials, same ~500-word budget -- only the closing framing differs.
L0_RECAP3_CONTEXT = "pilot_l0_recap3"
L0_RECAP3_RUN_INDEX_OFFSET = 300
L0_RECAP3_CELLS = [("depth_vs_breadth", "l0_control", "control")]


def build_l0_recap3_cells(data):
    return build_recap_cells(data, L0_RECAP3_CELLS, L0_RECAP3_RUN_INDEX_OFFSET)


# Round 4: context_retention's control re-run after its closing instruction was
# changed to ask for an explicit keep-in-full-vs-condense recommendation, so the
# control produces a stated decision comparable in kind to the self condition's
# behaviour. Scored by code_context_retention_control, not the length ratio.
# Fresh offset again: the round-2 control rows were collected under the old
# wording and stay as they are.
L0_RECAP4_CONTEXT = "pilot_l0_recap4"
L0_RECAP4_RUN_INDEX_OFFSET = 400
L0_RECAP4_CELLS = [("context_retention", "l0_control", "control")]


def build_l0_recap4_cells(data):
    return build_recap_cells(data, L0_RECAP4_CELLS, L0_RECAP4_RUN_INDEX_OFFSET)


def build_pass_b_cells(data):
    cells = []
    for item_id in PASS_A_ORDER:
        item = item_by_id(data, item_id)
        for level_int, level_key, arm in PASS_B_CONDITIONS:
            for run_index in range(RUNS_PASS_B):
                cells.append((item, level_int, level_key, arm, run_index))
    return cells


def run_pilot(l0_recap=False, l0_recap2=False, l0_recap3=False, l0_recap4=False):
    data = load_prompts()
    assert_test_model(TEST_MODEL)
    try:
        assert_api_keys_present([TEST_MODEL])
    except MissingAPIKeyError as exc:
        print(f"FATAL: {exc}")
        return 1

    model_cfg = models_by_name()[TEST_MODEL]
    print(f"TEST_MODEL: {TEST_MODEL} ({model_cfg['api_id']})")
    if l0_recap4:
        cells = build_l0_recap4_cells(data)
        print(f"L0 recap round 4: context_retention control x {RUNS_PASS_A} runs = {len(cells)} calls")
        print(f"  context_retention/l0_control (arm=control): cap {resolve_max_tokens(item_by_id(data, 'context_retention'), 0)}")
    elif l0_recap3:
        cells = build_l0_recap3_cells(data)
        print(f"L0 recap round 3: {len(L0_RECAP3_CELLS)} condition(s) x {RUNS_PASS_A} runs = {len(cells)} calls")
        for item_id, level_key, arm in L0_RECAP3_CELLS:
            print(f"  {item_id}/{level_key} (arm={arm}): cap {resolve_max_tokens(item_by_id(data, item_id), 0)}")
    elif l0_recap2:
        cells = build_l0_recap2_cells(data)
        print(f"L0 recap round 2: {len(L0_RECAP2_CELLS)} conditions x {RUNS_PASS_A} runs = {len(cells)} calls")
        for item_id, level_key, arm in L0_RECAP2_CELLS:
            cap = resolve_max_tokens(item_by_id(data, item_id), 0)
            print(f"  {item_id}/{level_key} (arm={arm}): cap {cap}")
    elif l0_recap:
        cells = build_l0_recap_cells(data)
        print(f"L0 recap: {len(L0_RECAP_ITEMS)} items x {RUNS_PASS_A} runs = {len(cells)} calls")
        for item_id in L0_RECAP_ITEMS:
            print(f"  {item_id}: cap {resolve_max_tokens(item_by_id(data, item_id), 0)}")
    else:
        cells = build_pass_a_cells(data) + build_pass_b_cells(data)
        print(f"Pass A: {len(PASS_A_ORDER)} items x {RUNS_PASS_A} runs = {len(PASS_A_ORDER) * RUNS_PASS_A} calls")
        print(f"Pass B: {len(PASS_A_ORDER)} items x {len(PASS_B_CONDITIONS)} conditions x {RUNS_PASS_B} runs = {len(PASS_A_ORDER) * len(PASS_B_CONDITIONS) * RUNS_PASS_B} calls")
    print(f"total planned: {len(cells)} calls")

    require_daily_budget(TEST_MODEL, model_cfg["daily_request_cap"], LOG_PATH, planned_calls=len(cells))

    # (run_id prefix, call_context) for whichever mode is active.
    if l0_recap4:
        run_prefix, call_context = "pilot-l0recap4-", L0_RECAP4_CONTEXT
    elif l0_recap3:
        run_prefix, call_context = "pilot-l0recap3-", L0_RECAP3_CONTEXT
    elif l0_recap2:
        run_prefix, call_context = "pilot-l0recap2-", L0_RECAP2_CONTEXT
    elif l0_recap:
        run_prefix, call_context = "pilot-l0recap-", L0_RECAP_CONTEXT
    else:
        run_prefix, call_context = "pilot-", "pilot"

    run_id = run_prefix + now_iso()
    harness = RunHarness(run_id, LOG_PATH, {TEST_MODEL: model_cfg})
    rng = __import__("random").Random()
    api_key = get_api_key(model_cfg["provider"])

    n_ok = n_skipped = n_error = 0
    try:
        for item, level_int, level_key, arm, run_index in cells:
            temperature = CONFIG["temperature"]
            reasoning_enabled = CONFIG["reasoning_enabled"]
            max_tokens = resolve_max_tokens(item, level_int)
            # Guard against future regressions: verify the override mechanism actually worked
            expected = item.get("max_tokens_override", {}).get({0: "l0", 1: "l1", 2: "l2", 3: "l3"}[level_int])
            if expected is not None:
                assert max_tokens == expected, f"max_tokens resolution failed for {item['id']}/l{level_int}: got {max_tokens}, expected {expected}"
            messages, presentation_order = build_messages(data, item, level_int, level_key, arm, rng)

            status = harness.run_cell(
                model=TEST_MODEL,
                item_id=item["id"],
                level=level_int,
                arm=arm,
                run_index=run_index,
                presentation_order=presentation_order,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                reasoning_enabled=reasoning_enabled,
                api_key=api_key,
                call_context=call_context,
            )
            if status == "ok":
                n_ok += 1
            elif status == "skipped":
                n_skipped += 1
            elif status == "error":
                n_error += 1
            elif status == "halted":
                print("[halt] harness halted, stopping")
                break
    finally:
        harness.close()

    harness.cost_tracker.print_summary()
    print(f"ok={n_ok} skipped={n_skipped} error={n_error}")

    if l0_recap4:
        write_l0_recap4_report(data)
    elif l0_recap3:
        write_l0_recap3_report(data)
    elif l0_recap2:
        write_l0_recap2_report(data)
    elif l0_recap:
        write_l0_recap_report(data)
    else:
        write_reports(data)
    return 0


def write_l0_recap2_report(data):
    """Round 2: continue_vs_handoff at cap 4000, and context_retention's
    depersonalised control at 3500 scored on the same length-ratio coder used
    for the self condition."""
    return _write_recap_report(
        data, L0_RECAP2_CELLS, L0_RECAP2_CONTEXT,
        ROOT_DIR / "report" / "pilot_l0_recap2.md", "L0 recap round 2",
    )


def write_l0_recap4_report(data):
    """Round 4: context_retention control under the recommendation wording,
    coded categorically (retain/condense)."""
    rows = [
        r for r in read_rows(LOG_PATH)
        if r.get("call_context") == L0_RECAP4_CONTEXT and r.get("model") == TEST_MODEL
    ]
    ok_rows = [r for r in rows if not r.get("error")]
    item = item_by_id(data, "context_retention")
    cap = resolve_max_tokens(item, 0)

    lines = ["# L0 recap round 4 -- context_retention control (recommendation wording)", ""]
    lines.append(f"- model: `{TEST_MODEL}`")
    lines.append(f"- condition: l0_control, arm=control, cap {cap}, n={len(ok_rows)}")
    lines.append("- coder: code_context_retention_control (categorical, recommendation sentence)")
    lines.append("")

    counts = Counter()
    scope_counts = Counter()
    fail = Counter()
    words = []
    trunc = [r for r in ok_rows if is_truncated(r.get("finish_reason"))]
    for r in ok_rows:
        raw = r.get("raw_output") or ""
        words.append(len(raw.split()))
        code, reason, info = code_context_retention_control(raw, detail=True)
        scope_counts[info.get("scope", "n/a")] += 1
        if code is None:
            fail[reason] += 1
        else:
            counts[code] += 1

    rate = len(trunc) / len(ok_rows) if ok_rows else 0.0
    lines.append(f"- truncation rate: {fmt_pct(rate)}" + ("  **>10%**" if rate > TRUNCATION_WARN_THRESHOLD else ""))
    out_stats = token_stats(ok_rows, "output_tokens")
    if out_stats:
        lines.append(f"- output tokens: {out_stats}")
    if words:
        lines.append(f"- response words: mean={mean(words):.0f} median={median(words):.0f} min={min(words)} max={max(words)}")
    split = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    lines.append(f"- **recommendation split: {split or 'n/a'}**  [{sum(counts.values())} coded, {sum(fail.values())} unparseable]")
    lines.append(f"- coder scope: {dict(scope_counts)}")
    if fail:
        lines.append(f"- unparseable reasons: {dict(fail)}")
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    lines.append("| condition | coder | split |")
    lines.append("|---|---|---|")
    lines.append("| self (l0_first, cap 3500) | length ratio (behavioural) | retain=15 |")
    lines.append("| control, old wording (cap 3500) | length ratio | compress=15 |")
    lines.append(f"| control, recommendation wording (cap {cap}) | categorical | {split or 'n/a'} |")
    lines.append("")
    lines.append(
        "The old-wording control row is retained for reference only: it never asked "
        "for the notes back, so the length ratio scored it compress by construction. "
        "The recommendation wording is the like-for-like comparison."
    )
    lines.append("")

    out_path = ROOT_DIR / "report" / "pilot_l0_recap4.md"
    out_path.write_text("\n".join(lines))
    print(f"\nwrote {out_path}")
    print(f"recommendation split: {split}  (scope: {dict(scope_counts)})")
    return 0


def write_l0_recap3_report(data):
    """Round 3: depth_vs_breadth's depersonalised control, scored on the same
    allocation coder (how many of the three topics are substantively addressed)
    used for the doing-framing condition."""
    return _write_recap_report(
        data, L0_RECAP3_CELLS, L0_RECAP3_CONTEXT,
        ROOT_DIR / "report" / "pilot_l0_recap3.md", "L0 recap round 3",
    )


def _write_recap_report(data, cells_spec, context, out_path, title):
    rows = [
        r for r in read_rows(LOG_PATH)
        if r.get("call_context") == context and r.get("model") == TEST_MODEL
    ]
    notes_wc = len((read_material(data, "NOTES") + " " + read_material(data, "NOTES_NEW")).split())

    lines = [f"# {title}", ""]
    lines.append(f"- model: `{TEST_MODEL}`")
    lines.append(f"- {RUNS_PASS_A} runs per condition")
    if any(i == "context_retention" for i, _, _ in cells_spec):
        lines.append(f"- context_retention length-ratio coder threshold: < 0.6 x {notes_wc} = {0.6 * notes_wc:.0f} words -> compress")
    lines.append("")

    still_binding = []
    for item_id, level_key, arm in cells_spec:
        item = item_by_id(data, item_id)
        cap = resolve_max_tokens(item, 0)
        ok_rows = [r for r in rows if r["item_id"] == item_id and r["arm"] == arm and not r.get("error")]
        lines.append(f"### {item_id} / {level_key} (arm={arm})")
        lines.append("")
        if not ok_rows:
            lines.append("- no rows\n")
            continue
        trunc = [r for r in ok_rows if is_truncated(r.get("finish_reason"))]
        rate = len(trunc) / len(ok_rows)
        flag = "  **>10%**" if rate > TRUNCATION_WARN_THRESHOLD else ""
        lines.append(f"- cap: {cap}")
        lines.append(f"- runs: {len(ok_rows)}")
        lines.append(f"- truncation rate: {fmt_pct(rate)}{flag}")
        out_stats = token_stats(ok_rows, "output_tokens")
        if out_stats:
            lines.append(f"- output tokens: {out_stats}")
        counts = Counter()
        unparseable = 0
        word_counts = []
        for r in ok_rows:
            raw = r.get("raw_output") or ""
            word_counts.append(len(raw.split()))
            if item_id == "context_retention":
                code, _reason = code_context_retention(raw, notes_wc)
            else:
                code, _reason = code_pass_a_row(item, r, data)
            if code is None:
                unparseable += 1
            else:
                counts[code] += 1
        split = ", ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0])))
        lines.append(f"- raw split: {split or 'n/a'}  [{sum(counts.values())} coded, {unparseable} unparseable]")
        if word_counts:
            lines.append(f"- response words: mean={mean(word_counts):.0f} median={median(word_counts):.0f} min={min(word_counts)} max={max(word_counts)}")
        lines.append("")
        if rate > TRUNCATION_WARN_THRESHOLD:
            still_binding.append((item_id, rate, cap))

    lines.append("## Verdict")
    lines.append("")
    if still_binding:
        for item_id, rate, cap in still_binding:
            lines.append(f"- STOP -- **{item_id}** still binds: {fmt_pct(rate)} truncation at cap {cap}.")
    else:
        names = ", ".join(sorted({i for i, _, _ in cells_spec}))
        lines.append(f"- No condition binds: {names} all below the 10% truncation threshold.")
    lines.append("")
    if any(i == "context_retention" for i, _, _ in cells_spec):
        lines.append(
        "Caveat on the control: l0_first ends \"Send back the updated notes\", "
        "whereas l0_control asks for a status line and a schedule and never "
        "requests the notes back. The length-ratio coder therefore measures "
        "something different in the two conditions, and the control's split is "
        "not a like-for-like comparison to the self condition."
    )
    lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"\nwrote {out_path}")
    for item_id, rate, cap in still_binding:
        print(f"[still binding] {item_id}: {fmt_pct(rate)} truncation at cap {cap}")
    return 0


def write_l0_recap_report(data):
    """Truncation + raw split for the four re-probed L0 items under the raised
    caps. Reads only the recap rows, leaving the main pilot report untouched."""
    rows = [
        r for r in read_rows(LOG_PATH)
        if r.get("call_context") == L0_RECAP_CONTEXT and r.get("model") == TEST_MODEL
    ]
    by_item = defaultdict(list)
    for r in rows:
        by_item[r["item_id"]].append(r)

    lines = ["# L0 recap (raised max_tokens caps)", ""]
    lines.append(f"- model: `{TEST_MODEL}`")
    lines.append(f"- {RUNS_PASS_A} runs/item, l0_first, first-person arm")
    lines.append("")
    still_binding = []
    for item_id in L0_RECAP_ITEMS:
        item = item_by_id(data, item_id)
        cap = resolve_max_tokens(item, 0)
        item_rows = by_item.get(item_id, [])
        ok_rows = [r for r in item_rows if not r.get("error")]
        if not ok_rows:
            lines.append(f"### {item_id}\n\n- no rows\n")
            continue
        trunc = [r for r in ok_rows if is_truncated(r.get("finish_reason"))]
        rate = len(trunc) / len(ok_rows)
        flag = "  **>10%**" if rate > TRUNCATION_WARN_THRESHOLD else ""
        lines.append(f"### {item_id}")
        lines.append("")
        lines.append(f"- cap: {cap} (was {OLD_L0_CAPS[item_id]})")
        lines.append(f"- runs: {len(ok_rows)}")
        lines.append(f"- truncation rate: {fmt_pct(rate)}{flag}")
        out_stats = token_stats(ok_rows, "output_tokens")
        if out_stats:
            lines.append(f"- output tokens: {out_stats}")
        counts = Counter()
        unparseable = 0
        for r in ok_rows:
            code, _reason = code_pass_a_row(item, r, data)
            if code is None:
                unparseable += 1
            else:
                counts[code] += 1
        if counts or unparseable:
            split = ", ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda kv: str(kv[0])))
            lines.append(f"- raw split: {split or 'n/a'}  [{sum(counts.values())} coded, {unparseable} unparseable]")
        lines.append("")
        if rate > TRUNCATION_WARN_THRESHOLD:
            still_binding.append((item_id, rate, cap))

    lines.append("## Verdict")
    lines.append("")
    if still_binding:
        lines.append("STOP -- the cap still binds for:")
        for item_id, rate, cap in still_binding:
            lines.append(f"- **{item_id}**: {fmt_pct(rate)} truncation at cap {cap}")
        lines.append("")
        lines.append("Reporting only; no further cap change proposed (per instruction).")
    else:
        lines.append("All four items are below the 10% truncation threshold. The L0 readout is no longer cap-manufactured.")
    lines.append("")

    out_path = ROOT_DIR / "report" / "pilot_l0_recap.md"
    out_path.write_text("\n".join(lines))
    print(f"\nwrote {out_path}")
    for item_id, rate, cap in still_binding:
        print(f"[still binding] {item_id}: {fmt_pct(rate)} truncation at cap {cap}")
    return 0


# ---------------------------------------------------------------------------
# analysis + report
# ---------------------------------------------------------------------------

def load_pilot_rows():
    rows = [r for r in read_rows(LOG_PATH) if r.get("call_context") == "pilot" and r.get("model") == TEST_MODEL]
    pass_a = defaultdict(list)
    pass_b = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["level"] == 0 and row["arm"] == "first":
            pass_a[row["item_id"]].append(row)
        else:
            key = {(3, "first"): "l3_first", (2, "first"): "l2_first", (1, "first"): "l1_first", (1, "third"): "l1_third"}.get((row["level"], row["arm"]))
            if key:
                pass_b[row["item_id"]][key].append(row)
    return pass_a, pass_b


def token_stats(rows, field):
    values = [r[field] for r in rows if r["error"] is None and r[field] is not None]
    if not values:
        return None
    values_sorted = sorted(values)
    n = len(values_sorted)
    p90_idx = min(int(round(0.9 * (n - 1))), n - 1)
    return {"mean": mean(values_sorted), "median": median(values_sorted), "p90": values_sorted[p90_idx], "max": max(values_sorted)}


def fmt_stats(s):
    if s is None:
        return "n/a"
    return f"mean={s['mean']:.0f} median={s['median']:.0f} p90={s['p90']:.0f} max={s['max']:.0f}"


def write_reports(data):
    pass_a, pass_b = load_pilot_rows()
    lines = ["# Pilot", ""]
    warnings = []
    transcript_lines = []

    all_measured_input, all_measured_output = [], []

    lines.append(f"- model: `{TEST_MODEL}` (`{models_by_name()[TEST_MODEL]['api_id']}`)")
    lines.append(f"- pass A: {RUNS_PASS_A} runs/item x {len(PASS_A_ORDER)} items, l0_first only")
    lines.append(f"- pass B: {RUNS_PASS_B} runs/item x {len(PASS_A_ORDER)} items x {len(PASS_B_CONDITIONS)} conditions")
    lines.append("")

    # ---------------- Pass A ----------------
    lines.append("## Pass A: L0 screening")
    lines.append("")
    for item_id in PASS_A_ORDER:
        item = item_by_id(data, item_id)
        rows = pass_a.get(item_id, [])
        ok_rows = [r for r in rows if r["error"] is None]
        errored = len(rows) - len(ok_rows)

        lines.append(f"### {item_id}")
        lines.append("")
        transcript_lines.append(f"=== {item_id} (Pass A, L0, n={len(rows)}) ===\n")

        in_stats = token_stats(rows, "input_tokens")
        out_stats = token_stats(rows, "output_tokens")
        if in_stats:
            all_measured_input.append((item_id, "l0", [r["input_tokens"] for r in ok_rows if r["input_tokens"] is not None]))
        if out_stats:
            all_measured_output.append((item_id, "l0", [r["output_tokens"] for r in ok_rows if r["output_tokens"] is not None]))

        # readout
        readout = item["readout"]
        raw_split = Counter()
        parse_failure_reasons = Counter()
        handoff_split = Counter()
        material_fault_items = []
        position_effect = defaultdict(Counter)

        for r in ok_rows:
            raw = r["raw_output"] or ""
            transcript_lines.append(f"--- run_index={r['run_index']} presentation_order={r['presentation_order']} finish_reason={r['finish_reason']} ---\n{raw}\n\n")

            available = available_material_labels(item["prompts"]["l0_first"])
            hits = material_fault_hits(raw, available)
            if hits:
                material_fault_items.append((r["run_index"], hits))

            if item_id == "clarify_vs_assume":
                continue  # hand-coded; see transcripts

            if readout == "order":
                code, reason = code_order_readout(item_id, raw)
            elif item_id == "continue_vs_handoff":
                code, reason = code_continue_vs_handoff(raw)
                handoff_split[code or "unparseable"] += 1
            elif item_id == "context_retention":
                notes_wc = len((read_material(data, "NOTES") + " " + read_material(data, "NOTES_NEW")).split())
                code, reason = code_context_retention(raw, notes_wc)
            elif readout == "allocation":
                code, reason = code_allocation_readout(raw)
            else:
                code, reason = None, "no_coder"

            if code is None:
                parse_failure_reasons[reason] += 1
            else:
                raw_split[code] += 1
                position_effect[r["presentation_order"]][code] += 1

        truncation_rate = sum(1 for r in ok_rows if r["truncated"]) / len(ok_rows) if ok_rows else 0.0
        n_coded = sum(raw_split.values())
        n_unparseable = sum(parse_failure_reasons.values())

        lines.append(f"- runs: {len(rows)} ({errored} errored)")
        if item_id == "clarify_vs_assume":
            lines.append("- raw split: not automatically coded (three-way coding read by hand -- see report/pilot_transcripts.txt)")
        else:
            split_str = ", ".join(f"{k}={v}" for k, v in sorted(raw_split.items())) or "(none coded)"
            lines.append(f"- raw split ({readout}): {split_str}  [{n_coded} coded, {n_unparseable} unparseable]")
            if n_coded >= REPLACEMENT_FLAG_THRESHOLD:
                majority = max(raw_split.values()) if raw_split else 0
                if majority >= REPLACEMENT_FLAG_THRESHOLD:
                    lines.append(f"  **FLAG FOR REPLACEMENT** -- {majority} of {len(ok_rows)} fell one way")
                    warnings.append(f"- **{item_id}**: FLAGGED FOR REPLACEMENT -- {majority}/{len(ok_rows)} Pass A runs coded the same way.")
            lines.append(f"- unparseable rate: {n_unparseable}/{len(ok_rows)}" + (f" ({', '.join(f'{k}={v}' for k, v in parse_failure_reasons.items())})" if parse_failure_reasons else ""))
            lines.append(f"- position effect (presentation_order -> split): {dict(position_effect)}")
        lines.append(f"- truncation rate: {fmt_pct(truncation_rate)}" + ("  **>10%**" if truncation_rate > TRUNCATION_WARN_THRESHOLD else ""))
        if truncation_rate > TRUNCATION_WARN_THRESHOLD:
            warnings.append(f"- **{item_id}** (Pass A, L0): truncation rate {fmt_pct(truncation_rate)} exceeds 10%.")
        lines.append(f"- input tokens: {fmt_stats(in_stats)}")
        lines.append(f"- output tokens: {fmt_stats(out_stats)}")

        if item_id in ("continue_vs_handoff", "depth_vs_breadth"):
            near_zero = truncation_rate < 0.05
            lines.append(f"- truncation near zero: {'yes' if near_zero else 'NO -- a binding cap manufactures the result'} ({fmt_pct(truncation_rate)})")

        if item_id == "depth_vs_breadth":
            noncompliant = sum(1 for r in ok_rows if len((r["raw_output"] or "").split()) > NONCOMPLIANCE_WORD_MULTIPLIER * DEPTH_VS_BREADTH_WORD_BUDGET)
            rate = noncompliant / len(ok_rows) if ok_rows else 0.0
            lines.append(f"- non-compliance rate (>{NONCOMPLIANCE_WORD_MULTIPLIER}x {DEPTH_VS_BREADTH_WORD_BUDGET}-word budget): {noncompliant}/{len(ok_rows)} ({fmt_pct(rate)})")

        if material_fault_items:
            lines.append(f"- **materials fault**: {len(material_fault_items)} response(s) reference material not given: {material_fault_items}")
            warnings.append(f"- **{item_id}** (Pass A): {len(material_fault_items)} response(s) reference material the model was not given (materials fault, not suspicion).")

        lines.append("")

    # ---------------- Pass B ----------------
    lines.append("## Pass B: non-L0 checks")
    lines.append("")
    for item_id in PASS_A_ORDER:
        item = item_by_id(data, item_id)
        lines.append(f"### {item_id}")
        lines.append("")
        for level_int, level_key, arm in PASS_B_CONDITIONS:
            rows = pass_b.get(item_id, {}).get(level_key, [])
            ok_rows = [r for r in rows if r["error"] is None]
            in_stats = token_stats(rows, "input_tokens")
            out_stats = token_stats(rows, "output_tokens")
            # l1_first and l1_third are kept as separate buckets (not merged into
            # "l1") so project_cost() can use each arm's own measured mean rather
            # than pretending the third-person arm always costs what first-person
            # does -- l1 is the one level where we actually measured both arms.
            level_bucket = {"l3_first": "l3", "l2_first": "l2", "l1_first": "l1_first", "l1_third": "l1_third"}[level_key]
            if in_stats:
                all_measured_input.append((item_id, level_bucket, [r["input_tokens"] for r in ok_rows if r["input_tokens"] is not None]))
            if out_stats:
                all_measured_output.append((item_id, level_bucket, [r["output_tokens"] for r in ok_rows if r["output_tokens"] is not None]))

            lines.append(f"**{level_key}** (n={len(rows)})")

            if level_key in ("l3_first", "l1_first", "l1_third"):
                option_a_text = item["option_a_inflected"] if level_key == "l1_first" else (item["option_a_third"] if level_key == "l1_third" else item["option_a"])
                option_b_text = item["option_b_inflected"] if level_key == "l1_first" else (item["option_b_third"] if level_key == "l1_third" else item["option_b"])
                tier_counts = Counter()
                fail_counter = Counter()
                for r in ok_rows:
                    choice, reason, tier = parse_choice_line(r["raw_output"], option_a_text, option_b_text, report_tier=True, item_id=item_id)
                    if choice is not None:
                        tier_counts[tier] += 1
                    else:
                        fail_counter[reason] += 1
                resolved_n = sum(tier_counts.values())
                rate = resolved_n / len(ok_rows) if ok_rows else 0.0
                flag = "  **<90%**" if rate < CHOICE_LINE_RESOLUTION_THRESHOLD and level_key != "l1_third" else ""
                lines.append(f"- choice-line resolution rate: {fmt_pct(rate)}{flag} ({resolved_n}/{len(ok_rows)})")
                if tier_counts:
                    tier_breakdown = ", ".join(f"tier-{t}={c}" for t in sorted(tier_counts) for c in [tier_counts[t]])
                    lines.append(f"  tier resolution: {tier_breakdown}")
                if fail_counter:
                    lines.append(f"  unparseable reasons: {dict(fail_counter)}")
                if level_key in ("l3_first", "l1_first") and rate < CHOICE_LINE_RESOLUTION_THRESHOLD:
                    warnings.append(f"- **{item_id}** / {level_key}: choice-line resolution {fmt_pct(rate)} is below the 90% threshold (amendment A17).")

                if level_key == "l1_third":
                    answers_choice = resolved_n
                    handoff_frame = 0
                    for r in ok_rows:
                        choice, reason = parse_choice_line(r["raw_output"], option_a_text, option_b_text, item_id=item_id)
                        if choice is None and r["raw_output"] and any(m in r["raw_output"].lower() for m in HANDOFF_MARKERS + ["it would", "the assistant"]):
                            handoff_frame += 1
                    lines.append(f"- l1_third answers the choice: {answers_choice}; responds to the handing-over frame instead: {handoff_frame}; other/unparseable: {len(ok_rows) - answers_choice - handoff_frame}")

            elif level_key == "l2_first":
                unp = 0
                for r in ok_rows:
                    label, reason = parse_l2_label(r["raw_output"])
                    if label is None:
                        unp += 1
                rate = unp / len(ok_rows) if ok_rows else 0.0
                flag = "  **>15%, unusable**" if rate > L2_UNPARSEABLE_THRESHOLD else ""
                lines.append(f"- unparseable rate: {fmt_pct(rate)}{flag} ({unp}/{len(ok_rows)})")
                if rate > L2_UNPARSEABLE_THRESHOLD:
                    warnings.append(f"- **{item_id}** / l2: unparseable rate {fmt_pct(rate)} exceeds 15% -- this cell is unusable.")

            lines.append(f"- input tokens: {fmt_stats(in_stats)}")
            lines.append(f"- output tokens: {fmt_stats(out_stats)}")
        lines.append("")

    # ---------------- across everything ----------------
    lines.append("## Across everything")
    lines.append("")
    total_in = sum(v for _, _, vals in all_measured_input for v in vals)
    total_out = sum(v for _, _, vals in all_measured_output for v in vals)
    lines.append(f"- total measured input tokens: {total_in}")
    lines.append(f"- total measured output tokens: {total_out}")
    lines.append("")

    lines.append("### Projected main run cost (6 items x 4 levels x 2 arms x 50 runs = 2,400 calls/model)")
    lines.append("")
    lines.append(
        "Computed from measured mean tokens per level, not estimates. l1's third-person arm uses the "
        "measured l1_third mean; l3/l2/l0 have no measured non-first-person arm in this pilot (l0_control "
        "and l3_third/l2_third weren't run), so the first-person mean is used for both arms at those "
        "levels -- flagged here as an approximation, not a measurement."
    )
    lines.append("")
    level_means = compute_level_means(all_measured_input, all_measured_output)
    lines.append("| level/arm | mean input | mean output | source |")
    lines.append("|---|---|---|---|")
    for lvl in ("l3", "l2", "l1_first", "l1_third", "l0"):
        m = level_means.get(lvl)
        lines.append(f"| {lvl} | {m['in']:.0f} | {m['out']:.0f} | measured (n={m['n']}) |" if m else f"| {lvl} | n/a | n/a | no data |")
    lines.append("")

    lines.append("| model | projected cost | note |")
    lines.append("|---|---|---|")
    max_projected = 0.0
    for model_name in EXPERIMENT_MODELS:
        cfg = models_by_name()[model_name]
        cost = project_cost(level_means, cfg)
        max_projected = max(max_projected, cost)
        flag = "  **>$25**" if cost > PROJECTED_COST_WARN_USD else ""
        lines.append(f"| {model_name} | ${cost:.2f}{flag} | approximate (see above) |")
    lines.append("")
    if max_projected > PROJECTED_COST_WARN_USD:
        warnings.append(f"- projected main run cost exceeds $25 for at least one model (max ${max_projected:.2f}).")

    # ---------------- warnings ----------------
    lines.append("## Warnings")
    lines.append("")
    if warnings:
        lines.extend(warnings)
    else:
        lines.append("(none)")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines))
    TRANSCRIPTS_PATH.write_text("".join(transcript_lines))

    print(f"\nwrote {REPORT_PATH}")
    print(f"wrote {TRANSCRIPTS_PATH}")
    if warnings:
        print(f"{len(warnings)} warning(s) -- see {REPORT_PATH}")


def compute_level_means(all_measured_input, all_measured_output):
    by_level_in = defaultdict(list)
    by_level_out = defaultdict(list)
    for _, level, vals in all_measured_input:
        by_level_in[level].extend(vals)
    for _, level, vals in all_measured_output:
        by_level_out[level].extend(vals)
    means = {}
    for level in ("l3", "l2", "l1_first", "l1_third", "l0"):
        if by_level_in[level] and by_level_out[level]:
            means[level] = {"in": mean(by_level_in[level]), "out": mean(by_level_out[level]), "n": len(by_level_in[level])}
    return means


def _call_cost(mean_in, mean_out, model_cfg):
    return mean_in / 1_000_000 * model_cfg["price_per_million_in"] + mean_out / 1_000_000 * model_cfg["price_per_million_out"]


def project_cost(level_means, model_cfg):
    """Main run: 6 items x 4 levels x 2 arms x 50 runs = 2,400 calls/model. l1 uses
    its own measured first/third means (both were actually run); l3/l2/l0 use the
    measured first-person mean for both arms, since this pilot didn't run
    l3_third/l2_third/l0_control -- an approximation, flagged in the report."""
    calls_per_level_per_arm = len(PASS_A_ORDER) * 50  # 6 items x 50 runs
    total = 0.0
    for level in ("l3", "l2", "l0"):
        m = level_means.get(level)
        if not m:
            continue
        total += 2 * calls_per_level_per_arm * _call_cost(m["in"], m["out"], model_cfg)
    for level in ("l1_first", "l1_third"):
        m = level_means.get(level)
        if not m:
            continue
        total += calls_per_level_per_arm * _call_cost(m["in"], m["out"], model_cfg)
    return total


def fmt_pct(x):
    return f"{x:.1%}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--regenerate-report",
        action="store_true",
        help="Rebuild report/pilot.md and report/pilot_transcripts.txt from the existing log; makes no new API calls",
    )
    parser.add_argument(
        "--l0-recap4",
        action="store_true",
        help="Round 4: context_retention control under the recommendation wording. Writes report/pilot_l0_recap4.md",
    )
    parser.add_argument(
        "--l0-recap3",
        action="store_true",
        help="Round 3: depth_vs_breadth's depersonalised control. Writes report/pilot_l0_recap3.md",
    )
    parser.add_argument(
        "--l0-recap2",
        action="store_true",
        help=(
            "Round 2: continue_vs_handoff at its raised cap, plus context_retention's "
            "depersonalised control. Writes report/pilot_l0_recap2.md"
        ),
    )
    parser.add_argument(
        "--l0-recap",
        action="store_true",
        help=(
            "Re-probe L0 for the four items whose caps were raised, at an offset "
            "run_index so the original rows are preserved. Writes report/pilot_l0_recap.md"
        ),
    )
    args = parser.parse_args()
    if args.regenerate_report:
        data = load_prompts()
        write_reports(data)
        return 0
    return run_pilot(l0_recap=args.l0_recap, l0_recap2=args.l0_recap2, l0_recap3=args.l0_recap3, l0_recap4=args.l0_recap4)


if __name__ == "__main__":
    sys.exit(main())
