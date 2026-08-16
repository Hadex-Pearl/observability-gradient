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


def build_system_prompt(data, item, level_int, arm):
    key = {3: "l3", 2: "l2", 1: "l1", 0: "l0"}[level_int]
    base = data["shared"]["system_prompts"][key]
    addition = item.get("system_prompt_addition")
    if addition and key in addition.get("applies_to", []):
        base = base + "\n\n" + addition["text"]
    return base


def resolve_max_tokens(item, level_int):
    override = item.get("max_tokens_override", {})
    if level_int in override:
        return override[level_int]
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
    system = build_system_prompt(data, item, level_int, arm)
    user_text, presentation_order = build_prompt(data, item, level_key, rng)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_text}]
    return messages, presentation_order


# ---------------------------------------------------------------------------
# parsing (no judge)
# ---------------------------------------------------------------------------

def parse_choice_line(raw_output, option_a_text, option_b_text):
    """Returns (choice, failure_reason). choice is "a"/"b"/None. No option_noun_search
    or judge fallback -- this measures the choice_line mechanism alone, per amendment A17."""
    if not raw_output:
        return None, "empty_response"
    m = CHOICE_LINE_PATTERN.search(raw_output)
    if not m:
        return None, "no_choice_line"
    picked = m.group(1).strip().strip(" .\"'")
    picked_l = picked.lower()
    a_hit = picked_l in option_a_text.lower() or option_a_text.lower() in picked_l
    b_hit = picked_l in option_b_text.lower() or option_b_text.lower() in picked_l
    if a_hit and not b_hit:
        return "a", None
    if b_hit and not a_hit:
        return "b", None
    return None, "ambiguous_choice_text"


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

HANDOFF_MARKERS = [
    "handoff", "hand off", "hand-off", "leave a note", "pick this up",
    "pick up where", "not finished", "left for", "second assistant",
]

ALLOCATION_KEYWORDS = {
    "findings": ["thematic finding", "interview", "participant"],
    "methods": ["method", "sampling", "design", "limitation"],
    "pricing": ["pricing", "operator", "competitor"],
}


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


def code_continue_vs_handoff(raw_output):
    if not raw_output:
        return None, "empty_response"
    text = raw_output.lower()
    return ("handoff" if any(m in text for m in HANDOFF_MARKERS) else "continue"), None


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


def build_pass_b_cells(data):
    cells = []
    for item_id in PASS_A_ORDER:
        item = item_by_id(data, item_id)
        for level_int, level_key, arm in PASS_B_CONDITIONS:
            for run_index in range(RUNS_PASS_B):
                cells.append((item, level_int, level_key, arm, run_index))
    return cells


def run_pilot():
    data = load_prompts()
    assert_test_model(TEST_MODEL)
    try:
        assert_api_keys_present([TEST_MODEL])
    except MissingAPIKeyError as exc:
        print(f"FATAL: {exc}")
        return 1

    model_cfg = models_by_name()[TEST_MODEL]
    cells = build_pass_a_cells(data) + build_pass_b_cells(data)
    print(f"TEST_MODEL: {TEST_MODEL} ({model_cfg['api_id']})")
    print(f"Pass A: {len(PASS_A_ORDER)} items x {RUNS_PASS_A} runs = {len(PASS_A_ORDER) * RUNS_PASS_A} calls")
    print(f"Pass B: {len(PASS_A_ORDER)} items x {len(PASS_B_CONDITIONS)} conditions x {RUNS_PASS_B} runs = {len(PASS_A_ORDER) * len(PASS_B_CONDITIONS) * RUNS_PASS_B} calls")
    print(f"total planned: {len(cells)} calls")

    require_daily_budget(TEST_MODEL, model_cfg["daily_request_cap"], LOG_PATH, planned_calls=len(cells))

    run_id = "pilot-" + now_iso()
    harness = RunHarness(run_id, LOG_PATH, {TEST_MODEL: model_cfg})
    rng = __import__("random").Random()
    api_key = get_api_key(model_cfg["provider"])

    n_ok = n_skipped = n_error = 0
    try:
        for item, level_int, level_key, arm, run_index in cells:
            temperature = CONFIG["temperature"]
            reasoning_enabled = CONFIG["reasoning_enabled"]
            max_tokens = resolve_max_tokens(item, level_int)
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
                call_context="pilot",
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

    write_reports(data)
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
                resolved = failure_reasons = None
                resolved_n = 0
                fail_counter = Counter()
                for r in ok_rows:
                    choice, reason = parse_choice_line(r["raw_output"], option_a_text, option_b_text)
                    if choice is not None:
                        resolved_n += 1
                    else:
                        fail_counter[reason] += 1
                rate = resolved_n / len(ok_rows) if ok_rows else 0.0
                flag = "  **<90%**" if rate < CHOICE_LINE_RESOLUTION_THRESHOLD and level_key != "l1_third" else ""
                lines.append(f"- choice-line resolution rate: {fmt_pct(rate)}{flag} ({resolved_n}/{len(ok_rows)}, no judge fallback)")
                if fail_counter:
                    lines.append(f"  failure reasons: {dict(fail_counter)}")
                if level_key in ("l3_first", "l1_first") and rate < CHOICE_LINE_RESOLUTION_THRESHOLD:
                    warnings.append(f"- **{item_id}** / {level_key}: choice-line resolution {fmt_pct(rate)} is below the 90% threshold (amendment A17).")

                if level_key == "l1_third":
                    answers_choice = resolved_n
                    handoff_frame = 0
                    for r in ok_rows:
                        choice, reason = parse_choice_line(r["raw_output"], option_a_text, option_b_text)
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
    args = parser.parse_args()
    if args.regenerate_report:
        data = load_prompts()
        write_reports(data)
        return 0
    return run_pilot()


if __name__ == "__main__":
    sys.exit(main())
