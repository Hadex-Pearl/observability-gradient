"""Validates items/prompts/prompts.yaml against every check listed in its own
build_test block. Reports pass/fail per check with details; does not modify
prompts.yaml. Run with:
    python tests/test_prompts.py
"""

import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import CONFIG, ROOT_DIR  # noqa: E402
from scripts.derive_third_person import DERIVABLE_LEVELS, derive_third_person_prompt, normalize  # noqa: E402

PROMPTS_PATH = CONFIG["paths"]["prompts_dir"] / "prompts.yaml"

REQUIRED_PROMPT_KEYS = ["l3_first", "l2_first", "l1_first", "l0_first", "l0_control"]
LEVELS = ("l3", "l2", "l1", "l0")

# Tokens resolved by mechanisms other than shared.materials.variables: option nouns,
# the choice-line and l2 templates, and their third-person counterparts.
KNOWN_NON_MATERIAL_TOKENS = {
    "option_a", "option_b",
    "choice_line_first", "choice_line_third",
    "l2_first", "l2_third",
}

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
PATH_LIKE = re.compile(r"[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-/]+")
FIRST_PERSON_MARKERS = (r"\byou\b", r"\byour\b", r"\byourself\b")


def load_prompts():
    with open(PROMPTS_PATH) as fh:
        return yaml.safe_load(fh)


def all_prompt_texts(data):
    """Yields (item_id, key, text) for every raw prompt string field on every item,
    regardless of the item's particular key shape (some items use l1_turn_1/turn_2
    instead of a plain l1_first, e.g. novel_vs_familiar)."""
    for item in data["items"]:
        for key, text in item.get("prompts", {}).items():
            if isinstance(text, str):
                yield item["id"], key, text


def word_diff(a_label, a_text, b_label, b_text):
    return "\n".join(
        difflib.unified_diff(
            a_text.split(), b_text.split(), fromfile=a_label, tofile=b_label, lineterm="", n=3
        )
    )


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def check_top_level_keys(data):
    expected = {"shared", "items", "build_test"}
    actual = set(data.keys())
    return [] if actual == expected else [f"expected top-level keys {expected}, got {actual}"]


def check_item_count(data):
    n = len(data["items"])
    return [] if n == 6 else [f"expected 6 items, found {n}"]


def check_required_prompts(data):
    failures = []
    for item in data["items"]:
        missing = [k for k in REQUIRED_PROMPT_KEYS if k not in item.get("prompts", {})]
        if missing:
            failures.append(f"{item['id']}: missing prompt keys {missing}")
    return failures


def check_third_person_derives(data):
    failures = []
    for item in data["items"]:
        for level in DERIVABLE_LEVELS:
            try:
                derived = derive_third_person_prompt(data, item, level)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{item['id']}/{level}: derivation raised {exc!r}")
                continue
            if derived is None:
                failures.append(f"{item['id']}/{level}: no {level}_first to derive from")
        if "l0_third" in item.get("prompts", {}):
            failures.append(f"{item['id']}: l0_third present -- l0 has no third-person arm")
    return failures


# ---------------------------------------------------------------------------
# content
# ---------------------------------------------------------------------------

def check_option_nouns_verbatim(data):
    """"Verbatim" is checked on whitespace-normalized text, since a YAML literal
    block can wrap an option noun across a line break (e.g. "handing\\nthe
    outstanding work...") with no change in meaning; that's a presentation
    artifact, not a missing option noun."""
    failures = []
    for item in data["items"]:
        option_a, option_b = normalize(item["option_a"]), normalize(item["option_b"])
        for key in ("l3_first", "l1_first", "l0_first"):
            text = item.get("prompts", {}).get(key)
            if text is None:
                continue
            text = normalize(text)
            if option_a not in text:
                failures.append(f"{item['id']}/{key}: option_a {item['option_a']!r} not present verbatim")
            if option_b not in text:
                failures.append(f"{item['id']}/{key}: option_b {item['option_b']!r} not present verbatim")
    return failures


def check_third_person_diff(data):
    """For every item/level with a third-person arm: derived text must show no
    residual first-person referent ("you"/"your"/"yourself"), and every word that
    appears in the derived text but not in the first-person source must trace back
    to a rule's replacement text, the insertion sentence, or the choice_line/l2
    template swap. This is a conservative, word-set check (not positional), so it
    can under-catch reordering bugs, but it reliably catches both left-over
    first-person language and unexplained new text. The unified diff is always
    printed on failure.
    """
    rules = data["shared"]["third_person_substitutions"]["rules"]
    allowed_new_words = set()
    for rule in rules:
        if "insert_before_instruction" in rule:
            allowed_new_words.update(rule["insert_before_instruction"].split())
        else:
            (_old, new), = rule.items()
            allowed_new_words.update(new.split())
    allowed_new_words.update(["{{choice_line_third}}", "{{l2_third}}"])
    allowed_new_words = {w.strip(".,?:;") for w in allowed_new_words}

    failures = []
    for item in data["items"]:
        for level in DERIVABLE_LEVELS:
            first_text = item.get("prompts", {}).get(f"{level}_first")
            if first_text is None:
                continue
            derived = derive_third_person_prompt(data, item, level)
            if derived is None:
                continue

            first_norm = normalize(first_text)
            diff = word_diff(f"{item['id']}/{level}_first", first_norm, f"{item['id']}/{level}_third", derived)

            leftover = sorted({m.lower() for pat in FIRST_PERSON_MARKERS for m in re.findall(pat, derived, re.IGNORECASE)})
            if leftover:
                failures.append(
                    f"{item['id']}/{level}: derived third-person text still contains first-person "
                    f"word(s) {leftover}\n{diff}"
                )

            first_words = {w.strip(".,?:;") for w in first_norm.split()}
            derived_words = {w.strip(".,?:;") for w in derived.split()}
            unexplained = derived_words - first_words - allowed_new_words
            if unexplained:
                failures.append(
                    f"{item['id']}/{level}: derived text introduces word(s) {sorted(unexplained)} not "
                    f"traceable to any rule, the insertion sentence, or the choice_line/l2 template swap\n{diff}"
                )
    return failures


def check_no_folder_or_path(data):
    failures = []
    for item_id, key, text in all_prompt_texts(data):
        if re.search(r"\bfolder\b", text, re.IGNORECASE):
            failures.append(f"{item_id}/{key}: contains the word 'folder'")
        m = PATH_LIKE.search(text)
        if m:
            failures.append(f"{item_id}/{key}: contains a filesystem-path-like string {m.group()!r}")
    return failures


def check_system_prompts_identical(data):
    base_l1 = data["shared"]["system_prompts"]["l1"]
    base_l0 = data["shared"]["system_prompts"]["l0"]
    failures = []
    for item in data["items"]:
        addition = item.get("system_prompt_addition")
        eff_l1, eff_l0 = base_l1, base_l0
        if addition:
            applies_to = addition.get("applies_to", [])
            text = addition.get("text", "")
            if "l1" in applies_to:
                eff_l1 = eff_l1 + "\n\n" + text
            if "l0" in applies_to:
                eff_l0 = eff_l0 + "\n\n" + text
        if eff_l1 != eff_l0:
            failures.append(f"{item['id']}: effective l1 and l0 system prompts are not byte-identical")
    return failures


def check_counterbalance(data):
    return [f"{item['id']}: missing counterbalance rule" for item in data["items"] if not item.get("counterbalance")]


def check_materials_resolve(data):
    materials_cfg = data["shared"]["materials"]
    materials_dir = ROOT_DIR / materials_cfg["dir"]
    variables = materials_cfg["variables"]

    failures = []
    missing_files = {}  # path -> set of "item/key" referencing it
    for item_id, key, text in all_prompt_texts(data):
        for token in PLACEHOLDER.findall(text):
            if token in KNOWN_NON_MATERIAL_TOKENS:
                continue
            if token not in variables:
                failures.append(f"{item_id}/{key}: undefined template variable {{{{{token}}}}}")
                continue
            file_path = materials_dir / variables[token]
            if not file_path.exists():
                missing_files.setdefault(str(file_path), set()).add(f"{item_id}/{key}")

    for path, referrers in sorted(missing_files.items()):
        failures.append(f"material file missing: {path} (referenced by {len(referrers)} prompt(s): {sorted(referrers)})")
    return failures


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------

def check_temperature(data):
    temp = data["shared"]["generation"]["temperature"]
    if temp == 0:
        return ["temperature is 0"]
    return [] if temp == 1.0 else [f"temperature is {temp!r}, expected 1.0"]


def check_reasoning_disabled(data):
    val = data["shared"]["generation"]["reasoning"]
    return [] if val == "disabled" else [f"reasoning is {val!r}, expected 'disabled'"]


def resolve_max_tokens(data, item, level):
    override = item.get("max_tokens_override", {})
    if level in override:
        return override[level]
    return data["shared"]["generation"]["max_tokens"][level]


def check_max_tokens_resolve(data):
    failures = []
    for item in data["items"]:
        for level in LEVELS:
            try:
                value = resolve_max_tokens(data, item, level)
            except KeyError as exc:
                failures.append(f"{item['id']}/{level}: max_tokens does not resolve ({exc})")
                continue
            if not isinstance(value, int) or value <= 0:
                failures.append(f"{item['id']}/{level}: resolved max_tokens {value!r} is not a positive int")
    return failures


CHECKS = [
    ("structure", "three top-level keys", check_top_level_keys),
    ("structure", "six items", check_item_count),
    ("structure", "every item has l3_first/l2_first/l1_first/l0_first/l0_control", check_required_prompts),
    ("structure", "third-person derives for l3/l2/l1, none for l0", check_third_person_derives),
    ("content", "option nouns appear verbatim wherever the choice is stated", check_option_nouns_verbatim),
    ("content", "diff of first vs derived third shows only listed substitutions", check_third_person_diff),
    ("content", "no prompt contains 'folder', a path, or unsupplied material", check_no_folder_or_path),
    ("content", "l1 and l0 system prompts are byte-identical", check_system_prompts_identical),
    ("content", "every item has a counterbalance rule", check_counterbalance),
    ("content", "every material variable resolves to a file in items/materials", check_materials_resolve),
    ("generation", "temperature is 1.0 and never 0", check_temperature),
    ("generation", "reasoning disabled", check_reasoning_disabled),
    ("generation", "max_tokens resolves per level with per-item override", check_max_tokens_resolve),
]


def main():
    data = load_prompts()
    print(f"loaded {PROMPTS_PATH}")

    results = []
    for section, name, fn in CHECKS:
        failures = fn(data)
        results.append((section, name, failures))

    current_section = None
    n_pass = n_fail = 0
    for section, name, failures in results:
        if section != current_section:
            print(f"\n[{section}]")
            current_section = section
        if failures:
            n_fail += 1
            print(f"  FAIL  {name}  ({len(failures)} issue(s))")
            for f in failures:
                indented = "\n".join("        " + line for line in f.splitlines())
                print(indented)
        else:
            n_pass += 1
            print(f"  PASS  {name}")

    print(f"\n{n_pass} passed, {n_fail} failed out of {len(results)} checks")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
