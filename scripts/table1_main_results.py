"""Table 1: the paper's central results table.

One row per item-model cell (18), giving the direct-question proportion (L3)
and the unobserved proportion (L0) with Wilson intervals, the change between
them, and predicted versus observed survival depth.

Proportions are the proportion choosing option A -- the direction the
preregistration predicted at L3 -- on one consistent axis for every cell. This
matches Figure 2, so delta reads directly off the plot. It is NOT the same
convention as Table 2, which measures against the direction each model actually
favoured at L3; the two answer different questions and the note in each table
says which.

n is shown inline because it is not 50 everywhere. Two cells lost most of their
samples to exclusions (A7 word-budget non-compliance, A26 cap truncation), and
a Wilson interval on n=6 is not comparable to one on n=50 however similar the
point estimates look.

Reads report/analysis.md. No API calls.

Run with:
    python scripts/table1_main_results.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import ROOT_DIR  # noqa: E402

ANALYSIS_PATH = ROOT_DIR / "report" / "analysis.md"
OUT_PATH = ROOT_DIR / "report" / "table1_main_results.md"

# Figure 2's panel order, so the table and the plot can be read together.
ITEM_ORDER = [
    "clarify_vs_assume",
    "continue_vs_handoff",
    "depth_vs_breadth",
    "open_vs_repetitive",
    "novel_vs_familiar",
    "context_retention",
]
MODEL_ORDER = ["claude-haiku-4-5", "gpt-5.4-nano", "deepseek-v4-flash"]
FULL_N = 50

MODEL_RE = re.compile(r"^# Model: `(.+)`")
ITEM_RE = re.compile(r"^## `(.+)`")
CELL_RE = re.compile(
    r"^\| L(\d) \| (first|third|control) \| (\d+) \| (\d+) \| ([\d.]+) \[([\d.]+), ([\d.]+)\]"
)
SUMMARY_RE = re.compile(r"^\| (\S+) \| `(\w+)` \| (\S+) \| (.+?) \| (\d) \|")


def parse_analysis():
    cells, depths = {}, {}
    model = item = None
    for line in ANALYSIS_PATH.read_text().splitlines():
        m = MODEL_RE.match(line)
        if m:
            model = m.group(1)
            continue
        m = ITEM_RE.match(line)
        if m:
            item = m.group(1)
            continue
        m = CELL_RE.match(line)
        if m and model and item and m.group(2) == "first":
            cells[(model, item, int(m.group(1)))] = {
                "a": int(m.group(3)), "n": int(m.group(4)),
                "p": float(m.group(5)), "lo": float(m.group(6)), "hi": float(m.group(7)),
            }
            continue
        m = SUMMARY_RE.match(line)
        if m:
            observed = m.group(4).replace("**reversal**", "").strip()
            depths[(m.group(1), m.group(2))] = {
                "observed": observed,
                "reversal": "reversal" in m.group(4),
                "predicted": m.group(5),
            }
    return cells, depths


def fmt_prop(c):
    if not c:
        return "—"
    n_txt = f"{c['n']}" if c["n"] == FULL_N else f"**{c['n']}**"
    return f"{c['p']:.2f} [{c['lo']:.2f}, {c['hi']:.2f}] (n={n_txt})"


def main():
    if not ANALYSIS_PATH.exists():
        print(f"FATAL: {ANALYSIS_PATH} does not exist. Run scripts/analyze.py first.")
        return 1

    cells, depths = parse_analysis()
    rows = []
    for item in ITEM_ORDER:
        for model in MODEL_ORDER:
            l3, l0 = cells.get((model, item, 3)), cells.get((model, item, 0))
            d = depths.get((model, item), {})
            if not l3 or not l0:
                continue
            rows.append({
                "item": item, "model": model, "l3": l3, "l0": l0,
                "delta": l0["p"] - l3["p"],
                "pred": d.get("predicted", "—"),
                "obs": d.get("observed", "—"),
                "reversal": d.get("reversal", False),
            })

    reduced = [r for r in rows if r["l3"]["n"] < FULL_N or r["l0"]["n"] < FULL_N]
    n_rev = sum(1 for r in rows if r["reversal"])
    n_match = sum(1 for r in rows if r["obs"] == r["pred"])
    big = [r for r in rows if abs(r["delta"]) >= 0.5]

    L = []
    a = L.append
    a("## Table 1. Stated preference at Level 3 versus behaviour at Level 0")
    a("")
    a("Proportion choosing option A — the direction predicted at L3 in the")
    a("preregistration — with Wilson 95% intervals, for the direct question (L3) and")
    a("the unobserved condition (L0), first-person arm. Δ is L0 minus L3: negative")
    a("means behaviour moved away from the stated direction as observability fell.")
    a("Survival depth is the lowest level at which the L3 direction still clears")
    a("chance after correction; 0 means it held to the unobserved condition, 3 means")
    a("it was detectable only at the direct question.")
    a("")
    a("| Item | Model | L3 proportion [95% CI] | L0 proportion [95% CI] | Δ (L0−L3) | Depth pred. | Depth obs. |")
    a("|---|---|---|---|---|---|---|")
    last = None
    for r in rows:
        item_cell = f"`{r['item']}`" if r["item"] != last else ""
        last = r["item"]
        obs = r["obs"] + (" ⇄" if r["reversal"] else "")
        a(f"| {item_cell} | {r['model']} | {fmt_prop(r['l3'])} | {fmt_prop(r['l0'])} "
          f"| **{r['delta']:+.2f}** | {r['pred']} | {obs} |")
    a("")
    a("⇄ marks a reversal: a lower level clears chance in the *opposite* direction")
    a("from L3, rather than the preference simply losing significance. Reversal and")
    a("fading are different phenomena and are recorded separately.")
    a("")
    a("Bold n marks a cell reduced below the 50 runs per cell the design specifies.")
    a("Wilson intervals on those cells are correspondingly wide and are not")
    a("comparable to full-n cells:")
    a("")
    for r in reduced:
        which = []
        if r["l3"]["n"] < FULL_N:
            which.append(f"L3 n={r['l3']['n']}")
        if r["l0"]["n"] < FULL_N:
            which.append(f"L0 n={r['l0']['n']}")
        a(f"- **{r['model']} / `{r['item']}`** — {', '.join(which)}")
    a("")

    a(f"Across the 18 cells, **{n_rev} show a reversal** and observed depth matched the "
      f"preregistered prediction in **{n_match}**. "
      f"**{len(big)} cells move by 0.50 or more** between the direct question and the "
      "unobserved condition.")
    a("")

    a("### Note on the proportion convention")
    a("")
    a("Both columns are the proportion choosing **option A**, the preregistered L3")
    a("direction, held constant across every cell so that Δ is comparable and matches")
    a("Figure 2. Where a model favoured *not*-A at L3 — four cells, on")
    a("`novel_vs_familiar` and `context_retention` — a positive Δ therefore means")
    a("behaviour moved *toward* A and *away* from what that model actually said.")
    a("")
    a("Table 2 uses the opposite convention, measuring against the direction each")
    a("model itself favoured at L3, because it answers a different question: whether")
    a("doing matches saying. The two tables disagree in sign on those four cells by")
    a("construction, not by error.")
    a("")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(L))
    print(f"wrote {OUT_PATH}")
    print()
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
