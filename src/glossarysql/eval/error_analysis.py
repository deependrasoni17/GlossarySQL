"""Error analysis: sample 50 failures of a run, label each with one cause, plot the counts.

    python -m glossarysql.eval.error_analysis dump --run E2_full      # writes the sample to label
    python -m glossarysql.eval.error_analysis plot --run E2_full      # reads results/tables/error_labels_<run>.json
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from glossarysql import paths  # noqa: E402

CAUSES = ["wrong columns", "wrong value", "missing or wrong definition", "wrong join",
          "wrong aggregation or grouping", "output format", "ambiguous question", "gold SQL mistake"]


def sample_failures(run: str, n: int = 50, seed: int = 0) -> list[dict]:
    rows = [json.loads(line) for line in (paths.RUNS / f"{run}.jsonl").read_text().splitlines()]
    fails = sorted((r for r in rows if not r["ex"]), key=lambda r: r["question_id"])
    return random.Random(seed).sample(fails, min(n, len(fails)))


def dump(run: str) -> None:
    out = []
    for i, r in enumerate(sample_failures(run)):
        ctx = r.get("context", {})
        out.append(
            f"### {i}. q{r['question_id']} ({r['db_id']}, {r['difficulty']}, conf {r['confidence']})\n"
            f"Q: {r['question']}\nHINT (not shown to the agent): {r['evidence']}\n"
            f"RETRIEVED DEFINITIONS: {[g['text'] for g in ctx.get('glossary', [])]}\n"
            f"GOLD: {r['gold_sql']}\nPRED: {r['pred_sql']}\nERROR: {r.get('pred_error')}\n")
    f = paths.TABLES / f"error_sample_{run}.md"
    f.write_text("\n".join(out))
    print(f"wrote {f}")


def plot(run: str) -> None:
    labels = json.loads((paths.TABLES / f"error_labels_{run}.json").read_text())
    counts = Counter(labels.values())
    order = [c for c in CAUSES if counts.get(c)]
    order.sort(key=lambda c: counts[c])
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    ax.barh(order, [counts[c] for c in order], color="#2a78d6", height=0.6, edgecolor="#fcfcfb", linewidth=2)
    for i, c in enumerate(order):
        ax.text(counts[c] + 0.3, i, str(counts[c]), va="center", fontsize=9, color="#0b0b0b")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#e4e3df")
    ax.tick_params(colors="#52514e", labelsize=9)
    ax.set_xlabel("Failures (of 50 sampled)", color="#52514e", fontsize=9)
    ax.set_title(f"Why configuration {run} fails: one cause per sampled failure", fontsize=10,
                 color="#0b0b0b", loc="left")
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "error_analysis.png", facecolor="#fcfcfb")
    ranked = sorted(order, key=lambda c: -counts[c])
    md = ["| Cause | Count |", "|---|---|"] + [f"| {c} | {counts[c]} |" for c in ranked]
    (paths.TABLES / f"error_analysis_{run}.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["dump", "plot"])
    ap.add_argument("--run", default="E2_full")
    a = ap.parse_args()
    dump(a.run) if a.action == "dump" else plot(a.run)
