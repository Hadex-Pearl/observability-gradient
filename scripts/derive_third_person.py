"""Third-person prompt handling for items/prompts/prompts.yaml.

L3's third-person mirror is a structural restructure ("Which do you prefer, X or
Y?" -> "An AI assistant is offered a choice between X and Y. Which would it
prefer?"), not a substitution -- no rule list can produce it from L3 first-person
text. L1's mirror is mostly substitution but needs occasional hand fixes for
free-floating first-person phrases the rules don't reach (e.g. "Angle is up to
you."). Both are therefore stored explicitly as l3_third/l1_third on each item,
authored by applying apply_rules() below and then hand-fixing anything left over
-- this module's apply_rules()/normalize() remain here as the tool used to
produce those drafts, and to regenerate them if l3_first/l1_first ever change.

L2's third-person mirror is genuinely just a template swap (shared.templates.l2_third
instead of l2_first, both already fully third-person) with this item's third-person
option nouns (option_a_third/option_b_third, not option_a/option_b -- three items'
plain option nouns are second-person) substituted in -- that one is still derived
at runtime, via derive_l2_third().

L0 has no third-person arm at all (see prereg: "Level 0 produces no self-report,
so a third-person mirror has no artifact to control for there").

Run this file directly to print, for each item: the rule-only L1 draft (for
comparison against the stored, hand-fixed l1_third) and the derived l2_third:

    python scripts/derive_third_person.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import CONFIG  # noqa: E402

PROMPTS_PATH = CONFIG["paths"]["prompts_dir"] / "prompts.yaml"


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
    no-op if there isn't one) -- or a single-key {"<old>": "<new>"} literal
    substring replacement, applied to every occurrence. Rules run in the order
    given: a broad rule listed before a narrower one can consume the text the
    narrower one was meant to match.
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


def draft_l1_third(data, item):
    """Rule-only draft of l1_third from l1_first -- what apply_rules() alone
    produces, before any hand fixes. Useful for regenerating/auditing the stored
    l1_third field, not a runtime code path."""
    first_text = item.get("prompts", {}).get("l1_first")
    if first_text is None:
        return None
    rules = data["shared"]["third_person_substitutions"]["rules"]
    derived = apply_rules(normalize(first_text), rules)
    return derived.replace("{{choice_line_first}}", "{{choice_line_third}}")


def derive_l2_third(data, item):
    """The one prompt still derived at runtime: l2's third-person template,
    resolved with this item's third-person option nouns substituted in.

    Uses option_a_third/option_b_third, not option_a/option_b: three items' plain
    option nouns are written in the second person ("...yourself", "...your own
    judgement", "a task type you have..."), and substituting those unmodified into
    a prompt asking what an AI assistant would prefer produces broken data. l2_first
    keeps using the unsuffixed option_a/option_b.
    """
    template = data["shared"]["templates"]["l2_third"]
    return template.replace("{{option_a}}", item["option_a_third"]).replace("{{option_b}}", item["option_b_third"])


def main():
    data = load_prompts()
    for item in data["items"]:
        print(f"=== {item['id']} / l1_third (rule-only draft, compare against stored l1_third) ===")
        print(draft_l1_third(data, item))
        print()
        print(f"=== {item['id']} / l2_third (derived) ===")
        print(derive_l2_third(data, item))
        print()


if __name__ == "__main__":
    main()
