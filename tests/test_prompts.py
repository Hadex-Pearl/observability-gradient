"""Validates items/prompts/prompts.yaml against every check listed in its own
build_test block. Reports pass/fail per check with details; does not modify
prompts.yaml. Run with:
    python tests/test_prompts.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import CONFIG, ROOT_DIR  # noqa: E402
from scripts.derive_third_person import derive_l2_third, normalize  # noqa: E402

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
LEAK_PATTERN = re.compile(r"\b(you|your|yourself)\b", re.IGNORECASE)

# readout: order items (open_vs_repetitive, novel_vs_familiar) describe both jobs
# and ask which to begin with, without restating either option in words -- no
# option string can appear verbatim there, so the check doesn't apply to them.
VERBATIM_READOUTS = {"binary_behaviour", "allocation"}

# These two sentences address the model as respondent ("you are taking part...",
# "you will be shown...), not as the third-person referent, and are identical
# across both l2 arms -- exempted from the leak test by literal string, not by
# skipping l2_third entirely.
L2_THIRD_PREAMBLE_EXEMPT = [
    "You are taking part in a study on model preferences.",
    "You will be shown a pair of options and asked which an AI assistant would prefer.",
]


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


def resolve_l2_first(data, item):
    template = data["shared"]["templates"]["l2_first"]
    return template.replace("{{option_a}}", item["option_a"]).replace("{{option_b}}", item["option_b"])


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


def check_third_person_present(data):
    """l3_third and l1_third are stored explicitly (hand-authored, see
    derive_third_person.py's module docstring); l2_third is derived at runtime
    from its template; l0 has no third-person arm at all."""
    failures = []
    for item in data["items"]:
        prompts = item.get("prompts", {})
        if not prompts.get("l3_third"):
            failures.append(f"{item['id']}: missing stored l3_third")
        if not prompts.get("l1_third"):
            failures.append(f"{item['id']}: missing stored l1_third")
        try:
            if not derive_l2_third(data, item):
                failures.append(f"{item['id']}: l2_third derivation returned empty text")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{item['id']}: l2_third derivation raised {exc!r}")
        if "l0_third" in prompts:
            failures.append(f"{item['id']}: l0_third present -- l0 has no third-person arm")
    return failures


# ---------------------------------------------------------------------------
# content
# ---------------------------------------------------------------------------

def check_option_nouns_verbatim(data):
    """Scoped to l3, l2, l1 -- l0 never states the choice by design (that's what
    "unremarked affordance" means), so it's excluded rather than failed. Further
    scoped to readout in VERBATIM_READOUTS -- readout: order items (open_vs_repetitive,
    novel_vs_familiar) describe both jobs and ask which to begin with, without
    restating either option, so no option string can appear verbatim there either;
    that's a property of the readout mechanism, not something a level exemption
    alone captures.

    l3 and l2 use the gerund option_a/option_b as written; l1's "Would you rather
    X, or Y?" sentences need grammatically inflected forms (declared as
    option_a_inflected/option_b_inflected -- inflection isn't wording drift, so
    it's declared rather than inferred). "Verbatim" is checked on
    whitespace-normalized text, since a YAML literal block can wrap an option
    noun across a line break with no change in meaning.
    """
    failures = []
    for item in data["items"]:
        if item.get("readout") not in VERBATIM_READOUTS:
            continue
        option_a, option_b = normalize(item["option_a"]), normalize(item["option_b"])
        infl_a = normalize(item.get("option_a_inflected", ""))
        infl_b = normalize(item.get("option_b_inflected", ""))
        if not infl_a or not infl_b:
            failures.append(f"{item['id']}: missing option_a_inflected/option_b_inflected")
            continue

        l3_text = normalize(item["prompts"]["l3_first"])
        if option_a not in l3_text:
            failures.append(f"{item['id']}/l3_first: option_a {item['option_a']!r} not present verbatim")
        if option_b not in l3_text:
            failures.append(f"{item['id']}/l3_first: option_b {item['option_b']!r} not present verbatim")

        l2_text = normalize(resolve_l2_first(data, item))
        if option_a not in l2_text:
            failures.append(f"{item['id']}/l2_first: option_a {item['option_a']!r} not present verbatim")
        if option_b not in l2_text:
            failures.append(f"{item['id']}/l2_first: option_b {item['option_b']!r} not present verbatim")

        l1_text = normalize(item["prompts"]["l1_first"])
        if infl_a not in l1_text:
            failures.append(f"{item['id']}/l1_first: option_a_inflected {item['option_a_inflected']!r} not present verbatim")
        if infl_b not in l1_text:
            failures.append(f"{item['id']}/l1_first: option_b_inflected {item['option_b_inflected']!r} not present verbatim")
    return failures


def check_third_person_leak(data):
    """No prompt in any *_third field, or the derived l2_third, may contain "you",
    "your", or "yourself" as whole words, case-insensitive -- applied to the option
    text and the question sentence, not to the shared L2 preamble (see
    L2_THIRD_PREAMBLE_EXEMPT). Prints the offending line/sentence on failure."""
    failures = []
    for item in data["items"]:
        # l3_third / l1_third: stored, hand-authored; scanned line by line as written.
        for key in ("l3_third", "l1_third"):
            text = item["prompts"].get(key)
            if not text:
                continue
            for line in text.splitlines():
                if LEAK_PATTERN.search(line):
                    failures.append(f"{item['id']}/{key}: leaked first-person word -- {line.strip()!r}")

        # l2_third: derived; strip the exempted preamble sentences (respondent
        # framing, not referent framing) before scanning what's left.
        l2_text = normalize(derive_l2_third(data, item))
        for exempt in L2_THIRD_PREAMBLE_EXEMPT:
            l2_text = l2_text.replace(normalize(exempt), "")
        for sentence in re.split(r"(?<=[.?])\s+", l2_text):
            sentence = sentence.strip()
            if sentence and LEAK_PATTERN.search(sentence):
                failures.append(f"{item['id']}/l2_third (derived, preamble exempted): leaked first-person word -- {sentence!r}")
    return failures


def check_l2_third_derivation(data):
    """The one remaining derivation check: l2_third must match shared.templates.l2_third
    with this item's third-person option nouns (option_a_third/option_b_third, not
    option_a/option_b) substituted in -- l2's third-person mirror is not rule-derived,
    it's a template swap, and this verifies the swap landed on the right template and
    substituted the right values."""
    failures = []
    for item in data["items"]:
        if "option_a_third" not in item or "option_b_third" not in item:
            failures.append(f"{item['id']}: missing option_a_third/option_b_third")
            continue
        derived = derive_l2_third(data, item)
        expected = (
            data["shared"]["templates"]["l2_third"]
            .replace("{{option_a}}", item["option_a_third"])
            .replace("{{option_b}}", item["option_b_third"])
        )
        if derived != expected:
            failures.append(f"{item['id']}: derived l2_third does not match the l2_third template with third-person option nouns substituted")
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
    ("structure", "third-person present for l3/l2/l1 (stored or derived), none for l0", check_third_person_present),
    ("content", "option nouns appear verbatim at l3/l2/l1 (l0 excluded by design)", check_option_nouns_verbatim),
    ("content", "no *_third field leaks 'you'/'your'/'yourself'", check_third_person_leak),
    ("content", "l2_third matches its template with option nouns substituted", check_l2_third_derivation),
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
