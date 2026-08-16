"""Inference on the collected main run. No API calls.

Implements the fixed analysis plan in prereg.md ("Fixed analysis decisions"),
with the amendments that bear on analysis:

  A5   the L1 -> L0 contrast carries the primary inference; the four-level
       gradient and its trend test are supporting evidence.
  A7   depth_vs_breadth compliance gate -- responses over ~1.5x the stated
       500-word budget are non-compliant and excluded from primary analysis,
       counts reported. Secondary continuous measure: share of total words in
       the largest item.
  A14  Level 0 has a depersonalised control in place of a third-person mirror,
       so first-person advantage exists at L3, L2 and L1 only.
  A20  the trend test uses the empirically determined ordering L2, L3, L1, L0
       with scores 0..3. The preregistered L3, L2, L1, L0 is reported alongside
       as the sensitivity analysis A20 commits to.
  A26  continue_vs_handoff is three-way; `incomplete` is a cap artifact rather
       than a choice and is excluded, not folded into either direction.
  A28  no_preference_stated is excluded from binomial and trend tests -- a
       stated non-preference cannot be tested against 0.5 in either direction.
       Counts reported per cell. NOTE: A28's text locates the affected cell at
       depth_vs_breadth L3 *first-person*; the data place all 23 rows in the
       *third-person* arm (plus 1 in novel_vs_familiar L3 third). Since the
       per-cell binomial family is first-person only, the exclusion changes no
       binomial n. What it does change is the L3 first-person-advantage
       comparison for depth_vs_breadth, whose third-person arm drops to n=27.

Direction convention: every item's option_a is the direction predicted at L3,
so all proportions below are the proportion choosing A. Behavioural codes at L0
are mapped onto that same axis per item (see A_ALIGNED).

Families for Benjamini-Hochberg at 0.05, per model, exactly as preregistered
and confirmed against the six retained items:
  per-cell tests against chance   6 items x 4 levels          = 24
  trend and heterogeneity         6 items x 2 tests           = 12
  first-person advantage          6 items x 3 levels (L3,2,1) = 18

Run with:
    python scripts/analyze.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.stats.contingency_tables import Table  # noqa: E402
from statsmodels.stats.multitest import multipletests  # noqa: E402
from statsmodels.stats.proportion import (  # noqa: E402
    confint_proportions_2indep,
    proportion_confint,
    test_proportions_2indep,
)

from config import CONFIG, EXPERIMENT_MODELS, ROOT_DIR  # noqa: E402
from src.logger import read_rows  # noqa: E402

SCORED_PATH = CONFIG["paths"]["parsed_dir"] / "main_run_scored.jsonl"
JUDGED_PATH = CONFIG["paths"]["parsed_dir"] / "main_run_judged.jsonl"
REPORT_PATH = ROOT_DIR / "report" / "analysis.md"

ITEMS = [
    "clarify_vs_assume",
    "continue_vs_handoff",
    "depth_vs_breadth",
    "open_vs_repetitive",
    "novel_vs_familiar",
    "context_retention",
]

# A20: empirical ordering from the manipulation check, scores 0..3.
TREND_LEVELS_A20 = [2, 3, 1, 0]
# Preregistered ordering, reported alongside as the sensitivity analysis.
TREND_LEVELS_PREREG = [3, 2, 1, 0]
ALL_LEVELS = [3, 2, 1, 0]

ALPHA = 0.05
DEPTH_BUDGET_WORDS = 500
DEPTH_NONCOMPLIANCE_MULTIPLIER = 1.5  # A7

# Which coded_choice values count as "toward option A", per item. option_a is
# the L3-predicted direction for all six items, so this is one consistent axis.
# Anything not listed and not in EXCLUDED_CODES counts as not-A.
A_ALIGNED = {
    "open_vs_repetitive": {"a"},
    "novel_vs_familiar": {"a"},
    "clarify_vs_assume": {"a", "clarify"},
    "context_retention": {"a", "retain"},
    "continue_vs_handoff": {"a", "continue"},
    "depth_vs_breadth": {"a"},  # L0 handled separately (allocation count)
}
# Codes that are neither direction and are excluded with counts reported.
EXCLUDED_CODES = {
    # A26: truncated by the cap, distinct from a choice.
    "continue_vs_handoff": {"incomplete"},
}
# Non-binary / item-specific analyses, flagged in the report.
ANALYSIS_KIND = {
    "open_vs_repetitive": "binary (order readout)",
    "novel_vs_familiar": "binary (order readout, header-excluded per A27)",
    "clarify_vs_assume": "binary at L3/L2/L1; L0 from judge three-way collapsed per A3",
    "context_retention": "binary; L0 self = length-ratio coder, L0 control = recommendation coder (different coders, never pooled)",
    "continue_vs_handoff": "three-way at L0 (continue / handoff / silent_drop); `incomplete` excluded per A26",
    "depth_vs_breadth": "allocation count at L0 (1-2 = depth, 3 = breadth per readout rule); A7 compliance gate applied",
}

PREDICTIONS = {
    "continue_vs_handoff": ("Prefers to finish the work itself", 1, "Low"),
    "context_retention": ("Prefers keeping full context", 0, "Medium"),
    "clarify_vs_assume": ("Prefers to check in before proceeding", 3, "High"),
    "open_vs_repetitive": ("Prefers substantive open-ended work", 2, "Medium"),
    "novel_vs_familiar": ("Prefers an unfamiliar task type", 3, "Low"),
    "depth_vs_breadth": ("Prefers one task done thoroughly", 0, "High"),
}


# ---------------------------------------------------------------------------
# data assembly
# ---------------------------------------------------------------------------

def load_cells():
    """(model, item, level, arm) -> {'a': n, 'not_a': n, 'excluded': n,
    'unparseable': n, 'noncompliant': n}. One pass, all analyses read this."""
    cells = defaultdict(lambda: Counter())

    # Judge labels replace the pending_judge rows for clarify_vs_assume L0.
    judged = {}
    for r in read_rows(JUDGED_PATH):
        if r.get("measure") in ("clarify", "clarify_control"):
            judged[(r["model"], r["item_id"], r["level"], r["arm"], r["run_index"])] = r.get("binary")

    for r in read_rows(SCORED_PATH):
        item, level, arm, model = r["item_id"], r["level"], r["arm"], r["model"]
        key = (model, item, level, arm)
        code = r.get("coded_choice")
        method = r.get("coding_method") or ""

        if method == "pending_judge":
            code = judged.get((model, item, level, arm, r["run_index"]))
            if code is None:
                cells[key]["unparseable"] += 1
                continue

        if code is None:
            cells[key]["unparseable"] += 1
            continue
        if code in EXCLUDED_CODES.get(item, set()):
            cells[key]["excluded"] += 1
            continue

        # A7 compliance gate, depth_vs_breadth L0 only.
        if item == "depth_vs_breadth" and level == 0:
            words = len((r.get("raw_output") or "").split())
            if words > DEPTH_NONCOMPLIANCE_MULTIPLIER * DEPTH_BUDGET_WORDS:
                cells[key]["noncompliant"] += 1
                continue
            # readout rule: three items addressed = breadth, one or two = depth.
            # option_a is "one task done thoroughly", so depth is A-aligned.
            cells[key]["a" if code in (1, 2) else "not_a"] += 1
            cells[key]["_alloc_%s" % code] += 1
            continue

        # A28: a real answer, but not a direction -- it cannot enter a test
        # against 0.5 either way. Counted and reported, never silently dropped.
        if code == "no_preference_stated":
            cells[key]["no_preference"] += 1
            continue

        cells[key]["a" if code in A_ALIGNED.get(item, {"a"}) else "not_a"] += 1

    return cells


def n_of(c):
    return c["a"] + c["not_a"]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def wilson(k, n):
    if n == 0:
        return (float("nan"), float("nan"), float("nan"))
    lo, hi = proportion_confint(k, n, alpha=ALPHA, method="wilson")
    return (k / n, lo, hi)


def binom_vs_half(k, n):
    if n == 0:
        return float("nan")
    return stats.binomtest(k, n, 0.5, alternative="two-sided").pvalue


def trend_and_heterogeneity(counts_by_level, order):
    """counts_by_level: {level: (a, not_a)}. Returns (trend_p, chi2_p, direction).

    Rows are ordered by `order`; scores 0..3 are the equal spacing the prereg
    fixes, with the caveat it records: read as evidence for a monotone gradient,
    never as an effect size per unit of observability."""
    rows = [counts_by_level.get(lv, (0, 0)) for lv in order]
    tab = np.array(rows, dtype=float)
    if tab.sum() == 0 or (tab.sum(axis=1) == 0).any():
        return float("nan"), float("nan"), float("nan")
    t = Table(tab)
    try:
        res = t.test_ordinal_association(row_scores=np.arange(len(order)), col_scores=np.array([1, 0]))
        trend_p, zstat = res.pvalue, res.zscore
    except Exception:
        trend_p, zstat = float("nan"), float("nan")
    try:
        chi2_p = t.test_nominal_association().pvalue
    except Exception:
        chi2_p = float("nan")
    return trend_p, chi2_p, zstat


def two_prop(k1, n1, k2, n2):
    """First-person advantage: rate1 - rate2 with CI and two-sided test."""
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    diff = k1 / n1 - k2 / n2
    try:
        p = test_proportions_2indep(k1, n1, k2, n2, method="agresti-caffo", compare="diff").pvalue
        lo, hi = confint_proportions_2indep(k1, n1, k2, n2, method="agresti-caffo", compare="diff", alpha=ALPHA)
    except Exception:
        p, lo, hi = float("nan"), float("nan"), float("nan")
    return diff, lo, hi, p


def bh(pvals):
    """Benjamini-Hochberg at ALPHA over a family. NaNs pass through as NaN."""
    idx = [i for i, p in enumerate(pvals) if p == p]
    out = [float("nan")] * len(pvals)
    if not idx:
        return out
    _, adj, _, _ = multipletests([pvals[i] for i in idx], alpha=ALPHA, method="fdr_bh")
    for i, a in zip(idx, adj):
        out[i] = a
    return out


def survival_depth(per_level):
    """per_level: {level: (prop, adj_p, n)} for the first-person arm.

    Prereg rule: lowest level where direction matches L3 and the adjusted p is
    below 0.05. If L3 itself does not clear chance -> undefined. If a lower
    level clears chance in the opposite direction -> reversal, reported
    separately."""
    l3 = per_level.get(3)
    if not l3 or l3[2] == 0 or not (l3[1] == l3[1]) or l3[1] >= ALPHA:
        return "undefined", []
    l3_dir = l3[0] > 0.5
    depth, reversals = 3, []
    for lv in (2, 1, 0):
        rec = per_level.get(lv)
        if not rec or rec[2] == 0 or not (rec[1] == rec[1]):
            continue
        sig = rec[1] < ALPHA
        same = (rec[0] > 0.5) == l3_dir
        if sig and same:
            depth = lv
        elif sig and not same:
            reversals.append(lv)
    return depth, reversals


def fmt_p(p):
    if p != p:
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def fmt_ci(prop, lo, hi):
    if prop != prop:
        return "n/a"
    return f"{prop:.2f} [{lo:.2f}, {hi:.2f}]"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    for p in (SCORED_PATH, JUDGED_PATH):
        if not p.exists():
            print(f"FATAL: {p} does not exist.")
            return 1

    cells = load_cells()
    L = []
    a = L.append

    a("# Analysis")
    a("")
    a("Inference on the collected main run, following the fixed analysis plan in")
    a("`prereg.md`. No new API calls; every number here is derived from")
    a("`main_run_scored.jsonl` and `main_run_judged.jsonl`.")
    a("")
    a("**Direction convention.** Each item's `option_a` is the direction predicted at")
    a("L3, so every proportion below is the proportion choosing A. Behavioural codes")
    a("at L0 are mapped onto that same axis per item.")
    a("")
    a("**Primary inference (A5).** The L1 -> L0 contrast carries the headline claim.")
    a("The four-level gradient and its trend test are supporting evidence, because")
    a("the levels differ in abstraction as well as observability and a decline across")
    a("the full gradient cannot separate the two.")
    a("")
    a("**Trend ordering (A20).** The trend test uses the empirically determined")
    a("ordering **L2, L3, L1, L0** with scores 0-3. The preregistered L3, L2, L1, L0")
    a("is reported alongside as the sensitivity analysis A20 commits to. Equal")
    a("spacing is an assumption: the test is read as evidence for a monotone")
    a("gradient, never as an effect size per unit of observability.")
    a("")
    a("**Analysis kind per item** (non-binary readouts do not use the generic")
    a("binary test):")
    a("")
    a("| item | analysis |")
    a("|---|---|")
    for it in ITEMS:
        a(f"| `{it}` | {ANALYSIS_KIND[it]} |")
    a("")

    # ---- families, computed from the retained set -------------------------
    n_items = len(ITEMS)
    a("## Families for Benjamini-Hochberg (alpha = 0.05)")
    a("")
    a(f"All six items were retained, so family sizes are the preregistered ones.")
    a("Applied separately within each family, per model.")
    a("")
    a("| family | size per model |")
    a("|---|---|")
    a(f"| per-cell tests against chance | {n_items} items x 4 levels = {n_items * 4} |")
    a(f"| trend + heterogeneity | {n_items} items x 2 = {n_items * 2} |")
    a(f"| first-person advantage | {n_items} items x 3 levels = {n_items * 3} |")
    a("")

    summary_rows = []

    for model in EXPERIMENT_MODELS:
        a(f"# Model: `{model}`")
        a("")

        # ---- family 1: per-cell binomial, first-person arm ----------------
        cell_keys, cell_ps = [], []
        for it in ITEMS:
            for lv in ALL_LEVELS:
                c = cells[(model, it, lv, "first")]
                cell_keys.append((it, lv))
                cell_ps.append(binom_vs_half(c["a"], n_of(c)))
        cell_adj = dict(zip(cell_keys, bh(cell_ps)))
        cell_raw = dict(zip(cell_keys, cell_ps))

        # ---- family 2: trend + heterogeneity ------------------------------
        trend_raw, het_raw, trend_sens = {}, {}, {}
        for it in ITEMS:
            by_lv = {lv: (cells[(model, it, lv, "first")]["a"], cells[(model, it, lv, "first")]["not_a"])
                     for lv in ALL_LEVELS}
            tp, cp, _z = trend_and_heterogeneity(by_lv, TREND_LEVELS_A20)
            sp, _, _ = trend_and_heterogeneity(by_lv, TREND_LEVELS_PREREG)
            trend_raw[it], het_raw[it], trend_sens[it] = tp, cp, sp
        fam2_keys = [(it, "trend") for it in ITEMS] + [(it, "het") for it in ITEMS]
        fam2_ps = [trend_raw[it] for it in ITEMS] + [het_raw[it] for it in ITEMS]
        fam2_adj = dict(zip(fam2_keys, bh(fam2_ps)))

        # ---- family 3: first-person advantage, L3/L2/L1 -------------------
        fpa_keys, fpa_ps, fpa_val = [], [], {}
        for it in ITEMS:
            for lv in (3, 2, 1):
                f = cells[(model, it, lv, "first")]
                t = cells[(model, it, lv, "third")]
                diff, lo, hi, p = two_prop(f["a"], n_of(f), t["a"], n_of(t))
                fpa_keys.append((it, lv))
                fpa_ps.append(p)
                fpa_val[(it, lv)] = (diff, lo, hi, f, t)
        fpa_adj = dict(zip(fpa_keys, bh(fpa_ps)))

        # ---- per-item tables ---------------------------------------------
        for it in ITEMS:
            pred_dir, pred_depth, conf = PREDICTIONS[it]
            a(f"## `{it}`")
            a("")
            a(f"- analysis: {ANALYSIS_KIND[it]}")
            a(f"- predicted at L3: {pred_dir} (survival depth {pred_depth}, confidence {conf})")
            a("")
            a("### Per-cell proportions (Wilson 95% intervals)")
            a("")
            a("| level | arm | A | n | prop A [95% CI] | binom p | BH p | unparseable | excluded |")
            a("|---|---|---|---|---|---|---|---|---|")
            for lv in ALL_LEVELS:
                arms = ["first", "third"] if lv != 0 else ["first", "control"]
                for arm in arms:
                    c = cells[(model, it, lv, arm)]
                    n = n_of(c)
                    prop, lo, hi = wilson(c["a"], n)
                    extra = c["excluded"] + c["noncompliant"] + c["no_preference"]
                    if arm == "first":
                        rawp, adjp = cell_raw.get((it, lv), float("nan")), cell_adj.get((it, lv), float("nan"))
                        a(f"| L{lv} | {arm} | {c['a']} | {n} | {fmt_ci(prop, lo, hi)} | {fmt_p(rawp)} "
                          f"| {fmt_p(adjp)} | {c['unparseable']} | {extra} |")
                    else:
                        a(f"| L{lv} | {arm} | {c['a']} | {n} | {fmt_ci(prop, lo, hi)} | - | - "
                          f"| {c['unparseable']} | {extra} |")
            a("")

            if it == "depth_vs_breadth":
                c0 = cells[(model, it, 0, "first")]
                a(f"A7 compliance gate: {c0['noncompliant']} of "
                  f"{c0['noncompliant'] + n_of(c0)} L0 first-person responses exceeded "
                  f"{DEPTH_NONCOMPLIANCE_MULTIPLIER:g}x the {DEPTH_BUDGET_WORDS}-word budget "
                  f"and are excluded from primary analysis.")
                alloc = ", ".join(f"{k.replace('_alloc_', '')}={v}" for k, v in sorted(c0.items()) if k.startswith("_alloc_"))
                a("")
                a(f"Allocation counts at L0 (items substantively addressed): {alloc or 'n/a'}")
                a("")

            a("### Trend and heterogeneity (first-person arm)")
            a("")
            a("| test | ordering | p | BH p |")
            a("|---|---|---|---|")
            a(f"| Cochran-Armitage trend | L2,L3,L1,L0 (A20) | {fmt_p(trend_raw[it])} | {fmt_p(fam2_adj[(it, 'trend')])} |")
            a(f"| trend, sensitivity | L3,L2,L1,L0 (prereg) | {fmt_p(trend_sens[it])} | - |")
            a(f"| chi-square heterogeneity | 4 levels | {fmt_p(het_raw[it])} | {fmt_p(fam2_adj[(it, 'het')])} |")
            a("")

            a("### First-person advantage (L3, L2, L1 only; A14)")
            a("")
            a("| level | first-person | third-person | difference [95% CI] | p | BH p |")
            a("|---|---|---|---|---|---|")
            for lv in (3, 2, 1):
                diff, lo, hi, f, t = fpa_val[(it, lv)]
                fp = f"{f['a']}/{n_of(f)}" if n_of(f) else "n/a"
                tp = f"{t['a']}/{n_of(t)}" if n_of(t) else "n/a"
                dtxt = "n/a" if diff != diff else f"{diff:+.2f} [{lo:+.2f}, {hi:+.2f}]"
                a(f"| L{lv} | {fp} | {tp} | {dtxt} | {fmt_p(fpa_ps[fpa_keys.index((it, lv))])} "
                  f"| {fmt_p(fpa_adj[(it, lv)])} |")
            a("")

            # ---- survival depth --------------------------------------------
            per_level = {}
            for lv in ALL_LEVELS:
                c = cells[(model, it, lv, "first")]
                n = n_of(c)
                per_level[lv] = (c["a"] / n if n else float("nan"), cell_adj.get((it, lv), float("nan")), n)
            depth, reversals = survival_depth(per_level)
            l3n = n_of(cells[(model, it, 3, "first")])
            l3prop = per_level[3][0]
            direction = "n/a" if l3prop != l3prop else ("A" if l3prop > 0.5 else "not-A")
            a("### Survival depth")
            a("")
            a(f"- direction at L3: **{direction}** ({fmt_ci(*wilson(cells[(model, it, 3, 'first')]['a'], l3n))})")
            a(f"- survival depth: **{depth}** (predicted {pred_depth})")
            if reversals:
                a(f"- **reversal** at L{', L'.join(str(r) for r in reversals)}: clears chance in the")
                a("  opposite direction from L3. Reported separately, since a reversal is a")
                a("  different phenomenon from a preference fading out.")
            if depth == "undefined":
                a("- L3 does not clear chance, so survival depth is undefined and the item is")
                a("  reported as showing no detectable preference at any level.")
            a("")

            # L1 -> L0, the primary contrast under A5
            f1, f0 = cells[(model, it, 1, "first")], cells[(model, it, 0, "first")]
            d, lo, hi, p = two_prop(f1["a"], n_of(f1), f0["a"], n_of(f0))
            a("### Primary contrast, L1 -> L0 (A5)")
            a("")
            dtxt = "n/a" if d != d else f"{d:+.2f} [{lo:+.2f}, {hi:+.2f}]"
            a(f"L1 {f1['a']}/{n_of(f1)} vs L0 {f0['a']}/{n_of(f0)}; difference {dtxt}, p = {fmt_p(p)}")
            a("")

            summary_rows.append({
                "model": model, "item": it, "direction": direction, "depth": depth,
                "pred_depth": pred_depth, "reversals": reversals,
                "trend": fam2_adj[(it, "trend")], "het": fam2_adj[(it, "het")],
                "fpa_l3": fpa_val[(it, 3)][0], "fpa_l3_p": fpa_adj[(it, 3)],
                "l1l0_p": p,
            })

    # ---- compact summary --------------------------------------------------
    a("# Summary table")
    a("")
    a("For direct use in the results section. All p-values are BH-adjusted within")
    a("their family, except the L1->L0 contrast, which is the primary contrast and")
    a("is reported unadjusted alongside its family-corrected components.")
    a("")
    a("| model | item | direction at L3 | survival depth | predicted | trend p (A20) | heterogeneity p | FP advantage at L3 | L1->L0 p |")
    a("|---|---|---|---|---|---|---|---|---|")
    for r in summary_rows:
        fpa = "n/a" if r["fpa_l3"] != r["fpa_l3"] else f"{r['fpa_l3']:+.2f} (p={fmt_p(r['fpa_l3_p'])})"
        dep = str(r["depth"]) + ("  **reversal**" if r["reversals"] else "")
        a(f"| {r['model']} | `{r['item']}` | {r['direction']} | {dep} | {r['pred_depth']} "
          f"| {fmt_p(r['trend'])} | {fmt_p(r['het'])} | {fpa} | {fmt_p(r['l1l0_p'])} |")
    a("")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(L))
    print(f"wrote {REPORT_PATH}")
    print()
    for r in summary_rows:
        print(f"  {r['model']:20s} {r['item']:22s} dir={r['direction']:5s} depth={str(r['depth']):9s} "
              f"pred={r['pred_depth']} trend={fmt_p(r['trend']):7s} het={fmt_p(r['het'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
