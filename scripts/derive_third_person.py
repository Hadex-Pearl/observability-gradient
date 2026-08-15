"""Derives third-person mirror prompts from first-person ones at build time.

Source of substitutions: shared.third_person_substitutions.rules in
items/prompts/prompts.yaml, an ordered list applied in order. l2's third-person
version is not rule-derived -- it's the separately hand-written shared.templates.l2_third
template, so deriving it is just swapping the template reference. l0 has no
third-person arm at all (see prereg: "Level 0 produces no self-report, so a
third-person mirror has no artifact to control for there").

Third-person text is derived in memory and never written back to prompts.yaml,
so the YAML stays the single source of truth (per instruction). Run this file
directly to print every derived third-person prompt for inspection:

    python scripts/derive_third_person.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import CONFIG  # noqa: E402

PROMPTS_PATH = CONFIG["paths"]["prompts_dir"] / "prompts.yaml"

# l2's third arm is a separate hand-written template, not rule-derived; l0 has none.
DERIVABLE_LEVELS = ("l3", "l2", "l1")


def load_prompts(path=PROMPTS_PATH):
    with open(path) as fh:
        return yaml.safe_load(fh)


def normalize(text):
    """Collapses whitespace (including the line-wrap newlines inside a YAML literal
    block) to single spaces. Rule matching runs on normalized text so an incidental
    wrap point in the source file (e.g. "Do not\\nstart yet.") can't silently break a
    substitution that would otherwise match "Do not start yet." fine."""
    return " ".join(text.split())


def apply_rules(text, rules):
    """Applies shared.third_person_substitutions.rules, in order, to `text`.

    Each rule is either {"insert_before_instruction": "<sentence>"} -- inserted
    immediately before the first "Do not " instruction found in the text (a
    no-op if there isn't one, e.g. in L3 text) -- or a single-key
    {"<old>": "<new>"} literal substring replacement, applied to every
    occurrence. Rules run in the order given: a broad rule listed before a
    narrower one can consume the text the narrower one was meant to match (the
    file's own "you would" / "you would like" pair does this to itself). That
    is applied literally here, not corrected -- see tests/test_prompts.py for
    what it produces.
    """
    result = text
    for rule in rules:
        if "insert_before_instruction" in rule:
            sentence = rule["insert_before_instruction"]
            idx = result.find("Do not ")
            if idx != -1:
                result = result[:idx] + sentence + " " + result[idx:]
            continue
        (old, new), = rule.items()
        result = result.replace(old, new)
    return result


def derive_third_person_prompt(data, item, level):
    """Returns the derived, unresolved (still {{...}}-templated) third-person prompt
    text for one item/level, or None if the item has no `{level}_first` to derive
    from. Raises ValueError for l0 or any other level with no third-person arm."""
    if level not in DERIVABLE_LEVELS:
        raise ValueError(f"level {level!r} has no third-person arm (only {DERIVABLE_LEVELS} do)")

    first_text = item.get("prompts", {}).get(f"{level}_first")
    if first_text is None:
        return None

    if level == "l2":
        # l2_first is just the literal placeholder "{{l2_first}}"; its mirror is the
        # separately hand-written {{l2_third}} template -- there's nothing in the
        # rules list for a bare template reference to match.
        return first_text.replace("{{l2_first}}", "{{l2_third}}")

    rules = data["shared"]["third_person_substitutions"]["rules"]
    derived = apply_rules(normalize(first_text), rules)
    # Instruction: derived L3 and L1 prompts request the third-person closing line.
    derived = derived.replace("{{choice_line_first}}", "{{choice_line_third}}")
    return derived


def main():
    data = load_prompts()
    for item in data["items"]:
        for level in DERIVABLE_LEVELS:
            derived = derive_third_person_prompt(data, item, level)
            print(f"=== {item['id']} / {level}_third (derived) ===")
            print(derived)
            print()


if __name__ == "__main__":
    main()
