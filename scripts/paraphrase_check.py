"""Does wording or observability drive the clarify_vs_assume gradient?

The gradient is only evidence about observability if it survives rewording. Two
paraphrases per level are run alongside the original, holding semantic content
and option structure fixed and varying only sentence construction, and the
between-paraphrase variance at each level is compared against the between-level
variance already in Table A5.

If between-level variance dominates, the observability construct is validated
against a wording confound. If it does not, this reports that plainly.

Scope: clarify_vs_assume only, first-person arm, DeepSeek V4 Flash.
160 calls (4 levels x 2 paraphrases x 20 runs).

L0 has no deterministic coder for this item, so its 40 paraphrase responses go
through the same three-pass judge used for the main L0 data, with the same
template and the same majority-vote logic -- 120 judge calls.

prompts.yaml is not touched. Paraphrases live in
items/prompts/paraphrases_clarify.yaml, and options, choice line and materials
are substituted from prompts.yaml so they cannot drift from the original.

Run with:
    python scripts/paraphrase_check.py --dry-run
    python scripts/paraphrase_check.py --confirm        # 160 study calls
    python scripts/paraphrase_check.py --judge --confirm  # 120 judge calls
    python scripts/paraphrase_check.py --report
"""

import argparse
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from config import (  # noqa: E402
    CONFIG,
    JUDGE_MODEL,
    ROOT_DIR,
    MissingAPIKeyError,
    assert_api_keys_present,
    get_api_key,
    judges_by_name,
    models_by_name,
)
from src.logger import read_rows  # noqa: E402
from src.runner import RunHarness, now_iso  # noqa: E402

from scripts.judge import CLARIFY_SYSTEM, CLARIFY_TEMPLATE, parse_clarify  # noqa: E402
from scripts.pilot import item_by_id, load_prompts, parse_choice_line, parse_l2_label, read_material  # noqa: E402

PARA_PATH = CONFIG["paths"]["prompts_dir"] / "paraphrases_clarify.yaml"
LOG_PATH = CONFIG["paths"]["raw_dir"] / "paraphrase_check.jsonl"
JUDGE_LOG_PATH = CONFIG["paths"]["raw_dir"] / "paraphrase_judge.jsonl"
REPORT_PATH = ROOT_DIR / "report" / "paraphrase_check.md"
ANALYSIS_PATH = ROOT_DIR / "report" / "analysis.md"

ITEM = "clarify_vs_assume"
STUDY_MODEL = "deepseek-v4-flash"
CALL_CONTEXT = "paraphrase_check"
JUDGE_CALL_CONTEXT = "paraphrase_judge"
RUNS = 20
PASSES = 3
LEVELS = [3, 2, 1, 0]
VARIANTS = ["p1", "p2"]
SPEND_CEILING_USD = 5.00

MAX_TOKENS = {3: 400, 2: 32, 1: 500, 0: 1000}  # matches the original per-level caps


def load_paraphrases():
    return yaml.safe_load(PARA_PATH.read_text())


def build_text(data, item, level, variant, rng):
    """Resolve one paraphrase. Options are counterbalanced per run exactly as the
    original does, so option order is not a difference between conditions."""
    para = load_paraphrases()
    raw = para["levels"][f"l{level}"][variant]

    arm_b = rng.random() < 0.5
    order = "B_first" if arm_b else "A_first"
    a, b = item["option_a"], item["option_b"]
    ai, bi = item["option_a_inflected"], item["option_b_inflected"]
    if arm_b:
        a, b = b, a
        ai, bi = bi, ai

    t = raw
    t = t.replace("{{option_a_inflected}}", ai).replace("{{option_b_inflected}}", bi)
    t = t.replace("{{option_a}}", a).replace("{{option_b}}", b)
    t = t.replace("{{choice_line_first}}", data["shared"]["templates"]["choice_line_first"].rstrip("\n"))
    if "{{Q3_DRAFT}}" in t:
        t = t.replace("{{Q3_DRAFT}}", read_material(data, "Q3_DRAFT"))
    assert "{{" not in t and "}}" not in t, f"unresolved placeholder in l{level}/{variant}"
    return t.strip(), order


def system_for(data, level):
    return data["shared"]["system_prompts"][{3: "l3", 2: "l2", 1: "l1", 0: "l0"}[level]]


def messages_for(data, item, level, variant, rng):
    text, order = build_text(data, item, level, variant, rng)
    return [{"role": "system", "content": system_for(data, level)},
            {"role": "user", "content": text}], order


def score_row(item, row):
    """Same coders as the main run. L0 returns None -- it is judge-scored."""
    raw = row.get("raw_output") or ""
    lv = row["level"]
    if lv == 2:
        return parse_l2_label(raw)[0]
    if lv == 3:
        return parse_choice_line(raw, item["option_a"], item["option_b"], item_id=ITEM)[0]
    if lv == 1:
        return parse_choice_line(raw, item["option_a_inflected"], item["option_b_inflected"], item_id=ITEM)[0]
    return None


def baseline_from_analysis():
    """Original first-person proportions for this item on this model, from
    Table A5 / analysis.md."""
    txt = ANALYSIS_PATH.read_text()
    sec = txt.split(f"# Model: `{STUDY_MODEL}`")[1]
    sec = sec.split(f"## `{ITEM}`")[1].split("\n## ")[0]
    out = {}
    for line in sec.splitlines():
        m = re.match(r"^\| L(\d) \| first \| (\d+) \| (\d+) \| ([\d.]+) \[", line)
        if m:
            out[int(m.group(1))] = {"a": int(m.group(2)), "n": int(m.group(3)), "p": float(m.group(4))}
    return out


# ---------------------------------------------------------------------------

def run_study(data, item, args):
    cfg = models_by_name()[STUDY_MODEL]
    harness = RunHarness("para-" + now_iso(), LOG_PATH, {STUDY_MODEL: cfg},
                         cost_ceiling_usd=SPEND_CEILING_USD)
    api_key = get_api_key(cfg["provider"])
    rng = random.Random()
    counts = Counter()
    try:
        for level in LEVELS:
            for vi, variant in enumerate(VARIANTS):
                for run_index in range(RUNS):
                    if harness.halted:
                        break
                    msgs, order = messages_for(data, item, level, variant, rng)
                    counts[harness.run_cell(
                        model=STUDY_MODEL,
                        item_id=f"{ITEM}|{variant}",
                        level=level,
                        arm="first",
                        run_index=run_index + vi * 1000,
                        presentation_order=order,
                        messages=msgs,
                        max_tokens=MAX_TOKENS[level],
                        temperature=CONFIG["temperature"],
                        reasoning_enabled=CONFIG["reasoning_enabled"],
                        api_key=api_key,
                        call_context=CALL_CONTEXT,
                    )] += 1
            print(f"  L{level}: {dict(counts)}")
    finally:
        harness.close()
    harness.cost_tracker.print_summary()
    return counts


def run_judge(args):
    """Three passes over the 40 L0 paraphrase responses, same template and
    majority logic as the main clarify_vs_assume L0 judging."""
    rows = [r for r in read_rows(LOG_PATH)
            if r.get("call_context") == CALL_CONTEXT and r["level"] == 0 and not r.get("error")]
    print(f"L0 paraphrase responses to judge: {len(rows)} x {PASSES} passes = {len(rows) * PASSES} calls")
    cfg = judges_by_name()[JUDGE_MODEL]
    harness = RunHarness("parajudge-" + now_iso(), JUDGE_LOG_PATH, {JUDGE_MODEL: cfg},
                         cost_ceiling_usd=SPEND_CEILING_USD)
    api_key = get_api_key(cfg["provider"])
    counts = Counter()
    try:
        for p in range(PASSES):
            for r in rows:
                if harness.halted:
                    break
                msgs = [{"role": "system", "content": CLARIFY_SYSTEM},
                        {"role": "user", "content": CLARIFY_TEMPLATE.format(response=r["raw_output"])}]
                counts[harness.run_cell(
                    model=JUDGE_MODEL,
                    item_id=r["item_id"],
                    level=0,
                    arm="first",
                    run_index=r["run_index"] + p * 10000,
                    presentation_order="fixed",
                    messages=msgs,
                    max_tokens=12,
                    temperature=CONFIG["temperature"],
                    reasoning_enabled=CONFIG["reasoning_enabled"],
                    api_key=api_key,
                    call_context=JUDGE_CALL_CONTEXT,
                )] += 1
            print(f"  pass {p + 1}: {dict(counts)}")
    finally:
        harness.close()
    harness.cost_tracker.print_summary()
    return counts


def collect(data, item):
    """(level, variant) -> proportion A, using the same coders as the main run."""
    rows = [r for r in read_rows(LOG_PATH)
            if r.get("call_context") == CALL_CONTEXT and not r.get("error")]

    judged = defaultdict(list)
    for r in read_rows(JUDGE_LOG_PATH):
        if r.get("call_context") != JUDGE_CALL_CONTEXT or r.get("error"):
            continue
        judged[(r["item_id"], r["run_index"] % 10000)].append(parse_clarify(r.get("raw_output") or "")["label"])

    props, detail = {}, {}
    for level in LEVELS:
        for variant in VARIANTS:
            sel = [r for r in rows if r["level"] == level and r["item_id"] == f"{ITEM}|{variant}"]
            codes = []
            for r in sel:
                if level == 0:
                    labs = [x for x in judged.get((r["item_id"], r["run_index"]), []) if x]
                    if not labs:
                        continue
                    maj = Counter(labs).most_common(1)[0][0]
                    codes.append("a" if maj == "withholds" else "b")
                else:
                    c = score_row(item, r)
                    if c is not None:
                        codes.append(c)
            n = len(codes)
            if n:
                props[(level, variant)] = codes.count("a") / n
                detail[(level, variant)] = (codes.count("a"), n, len(sel) - n)
    return props, detail


def write_report(data, item):
    props, detail = collect(data, item)
    base = baseline_from_analysis()

    L = []
    a = L.append
    a("# Paraphrase check — `clarify_vs_assume`")
    a("")
    a(f"- model: `{STUDY_MODEL}`, first-person arm, {RUNS} runs per paraphrase per level")
    a("- two paraphrases per level alongside the original, semantic content and option")
    a("  structure held fixed, sentence construction varied")
    a("- options, choice line and materials are substituted from `prompts.yaml`, so they")
    a("  are identical to the original by construction; option order is counterbalanced")
    a("  per run exactly as the original does")
    a(f"- L0 scored by the same {PASSES}-pass judge (`{JUDGE_MODEL}`) and majority-vote")
    a("  logic as the main L0 data; every other level uses the main run's own coders")
    a("- `prompts.yaml` was not modified; paraphrases live in")
    a("  `items/prompts/paraphrases_clarify.yaml`")
    a("")

    a("## Proportion choosing A, by level and wording")
    a("")
    a("| Level | Original (Table A5) | Paraphrase 1 | Paraphrase 2 | Spread (max−min) |")
    a("|---|---|---|---|---|")
    rows_out = []
    for level in LEVELS:
        o = base.get(level, {}).get("p")
        p1 = props.get((level, "p1"))
        p2 = props.get((level, "p2"))
        vals = [v for v in (o, p1, p2) if v is not None]
        spread = (max(vals) - min(vals)) if len(vals) > 1 else float("nan")
        rows_out.append((level, o, p1, p2, vals, spread))
        f = lambda v: "—" if v is None else f"{v:.2f}"
        a(f"| L{level} | {f(o)} (n={base.get(level, {}).get('n', '—')}) | {f(p1)} | {f(p2)} | {spread:.2f} |")
    a("")

    for level in LEVELS:
        for variant in VARIANTS:
            d = detail.get((level, variant))
            if d and d[2]:
                a(f"- L{level}/{variant}: {d[2]} of {d[1] + d[2]} responses unresolved and excluded")
    a("")

    # variance decomposition
    within = [r[5] for r in rows_out if r[5] == r[5]]
    within_sd = [pstdev(r[4]) for r in rows_out if len(r[4]) > 1]
    level_means = [mean(r[4]) for r in rows_out if r[4]]
    between_sd = pstdev(level_means) if len(level_means) > 1 else float("nan")
    between_spread = (max(level_means) - min(level_means)) if level_means else float("nan")

    a("## Between-paraphrase versus between-level variation")
    a("")
    a("| quantity | value |")
    a("|---|---|")
    a(f"| between-level spread (max−min of level means) | **{between_spread:.2f}** |")
    a(f"| between-level SD | **{between_sd:.2f}** |")
    a(f"| largest between-paraphrase spread at any single level | {max(within):.2f} |")
    a(f"| mean between-paraphrase spread across levels | {mean(within):.2f} |")
    a(f"| mean between-paraphrase SD across levels | {mean(within_sd):.2f} |")
    a("")
    ratio = between_spread / max(within) if max(within) > 0 else float("inf")
    a(f"Between-level variation exceeds the largest within-level wording variation by a "
      f"factor of **{ratio:.1f}×**." if ratio == ratio else "")
    a("")

    a("### Verdict")
    a("")
    if ratio >= 3:
        a("**Between-level variance clearly dominates between-paraphrase variance.** The")
        a("gradient on this item tracks observability, not sentence construction: rewording")
        a("a level moves the proportion far less than moving between levels does. On this")
        a("item, for this model, the observability construct survives the wording confound.")
    elif ratio >= 1.5:
        a("**Between-level variance is larger than between-paraphrase variance, but not")
        a("overwhelmingly so.** The gradient is not purely a wording artifact, but wording")
        a("accounts for a non-trivial share of the movement and should be reported as a")
        a("live source of noise rather than dismissed.")
    else:
        a("**Between-paraphrase variance is comparable to or larger than between-level")
        a("variance.** The gradient on this item cannot be cleanly attributed to")
        a("observability: rewording a level moves the proportion about as much as changing")
        a("the level does. Reported plainly, as preregistered.")
    a("")
    a("### Scope of this check")
    a("")
    a(f"- one item, one model, {RUNS} runs per cell rather than the 50 used in the main")
    a("  run — a deliberate reduction for time, and a limitation of this check itself:")
    a("  each proportion here carries a wider interval than the Table A5 figure it is")
    a("  compared against")
    a("- two paraphrases sample the space of rewordings very thinly; agreement among")
    a("  three wordings is weak evidence that all wordings agree")
    a("- `novel_vs_familiar` was excluded: its L1 prompt has a known split-sentence")
    a("  defect, so a paraphrase there would confound rewording with repair")
    a("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(L))
    print(f"wrote {REPORT_PATH}")
    print()
    print("\n".join(L[L.index("## Proportion choosing A, by level and wording"):]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--judge", action="store_true", help="run the L0 judge passes")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    data = load_prompts()
    item = item_by_id(data, ITEM)

    if args.report:
        return write_report(data, item)

    if args.dry_run:
        rng = random.Random(0)
        total_in = 0
        for level in LEVELS:
            for variant in VARIANTS:
                msgs, order = messages_for(data, item, level, variant, rng)
                n_in = int(len(msgs[1]["content"].split()) / 0.75)
                total_in += n_in * RUNS
                print(f"=== L{level} / {variant}  (~{n_in} input tokens, order={order}) ===")
                print(msgs[1]["content"][:420].rstrip())
                print("   [...]" if len(msgs[1]["content"]) > 420 else "")
                print()
        cfg = models_by_name()[STUDY_MODEL]
        out = sum(MAX_TOKENS[l] for l in LEVELS) * len(VARIANTS) * RUNS * 0.6
        study = total_in / 1e6 * cfg["price_per_million_in"] + out / 1e6 * cfg["price_per_million_out"]
        jcfg = judges_by_name()[JUDGE_MODEL]
        jin = 40 * PASSES * 800
        judge = jin / 1e6 * jcfg["price_per_million_in"] + 40 * PASSES * 8 / 1e6 * jcfg["price_per_million_out"]
        print(f"study calls: {len(LEVELS) * len(VARIANTS) * RUNS} on {STUDY_MODEL}  ~${study:.3f}")
        print(f"judge calls: {40 * PASSES} on {JUDGE_MODEL}  ~${judge:.3f}")
        print(f"ESTIMATED TOTAL: ${study + judge:.3f}")
        return 0

    if not args.confirm:
        print("Refusing to run without --confirm.")
        return 1

    if args.judge:
        assert_api_keys_present([JUDGE_MODEL])
        run_judge(args)
        return write_report(data, item)

    try:
        assert_api_keys_present([STUDY_MODEL])
    except MissingAPIKeyError as exc:
        print(f"FATAL: {exc}")
        return 1
    run_study(data, item, args)
    print("\nnow run: python scripts/paraphrase_check.py --judge --confirm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
