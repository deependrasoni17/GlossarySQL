"""Build every results table and figure from the per-question run files.

    python -m glossarysql.eval.report
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from glossarysql import paths  # noqa: E402
from glossarysql.calibration.ltt import evaluate_splits, learn_then_test, risk_coverage  # noqa: E402
from glossarysql.eval.run import load_config  # noqa: E402
from glossarysql.eval.stats import bootstrap_ci, gap_closed, mcnemar_exact  # noqa: E402

MAIN = ["A", "B", "C", "D", "E", "F"]
EXTRA = ["Cg", "Cg2", "Cf", "E2", "E_ft", "D_full", "E_full", "E2_full", "F_full",
         "D_32b", "E_32b", "F_32b", "D_full_32b", "E2_full_32b", "F_full_32b"]
PAIRS = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "E"), ("D", "E2"), ("D", "F"), ("E", "F"),
         ("C", "Cg"), ("C", "Cg2"), ("C", "Cf"), ("E", "E2"), ("E", "E_ft"), ("A", "D_full"),
         ("D", "D_full"), ("D_full", "E_full"), ("D_full", "E2_full"), ("E_full", "E2_full"),
         ("E2_full", "F_full"), ("D_32b", "E_32b"), ("D_full_32b", "E2_full_32b"),
         ("E2_full", "E2_full_32b")]
CALIBRATE = "E2_full"  # the best system with retrieved definitions

# Reference palette (dataviz skill): blue = baseline series, orange = proposed system.
BLUE, ORANGE, AQUA, INK, INK2, GRID, SURFACE = ("#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b",
                                                "#52514e", "#e4e3df", "#fcfcfb")


def load_runs(names) -> dict[str, pd.DataFrame]:
    runs = {}
    for n in names:
        f = paths.RUNS / f"{n}.jsonl"
        if f.exists():
            df = pd.read_json(f, lines=True).set_index("question_id").sort_index()
            runs[n] = df
    return runs


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def main_table(runs) -> pd.DataFrame:
    rows = []
    for n, df in runs.items():
        cfg = load_config(str(paths.CONFIGS / f"{n}.yaml")) if (paths.CONFIGS / f"{n}.yaml").exists() else {}
        m, lo, hi = bootstrap_ci(df["ex"].values)
        row = {"Config": n, "What it adds": cfg.get("description", ""), "n": len(df),
               "EX % (95% CI)": f"{100 * m:.1f} [{100 * lo:.1f}, {100 * hi:.1f}]", "EX": m,
               "Soft F1": round(100 * df["f1"].mean(), 1)}
        for d in ("simple", "moderate", "challenging"):
            sub = df[df["difficulty"] == d]
            row[f"EX {d}"] = round(100 * sub["ex"].mean(), 1) if len(sub) else np.nan
        row["Tokens/q"] = int((df["prompt_tokens"] + df["completion_tokens"]).mean())
        row["LLM calls/q"] = round(df["llm_calls"].mean(), 2)
        row["Median latency (s)"] = round(df["latency"].median(), 2)
        row["p95 latency (s)"] = round(df["latency"].quantile(0.95), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def plot_ex(table: pd.DataFrame, runs) -> None:
    order = [n for n in MAIN + ["E2", "E_ft", "D_full", "E_full", "E2_full", "F_full"] if n in runs]
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    for i, n in enumerate(order):
        m, lo, hi = bootstrap_ci(runs[n]["ex"].values)
        color = ORANGE if n.startswith("E") else BLUE
        ax.bar(i, 100 * m, width=0.6, color=color, edgecolor=SURFACE, linewidth=2)
        ax.plot([i, i], [100 * lo, 100 * hi], color=INK2, linewidth=1.2)
        ax.text(i, 100 * hi + 1.2, f"{100 * m:.1f}", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(range(len(order)), order)
    ax.set_ylabel("Execution accuracy (%)", color=INK2, fontsize=9)
    ax.set_title("Execution accuracy by configuration (95% bootstrap CI); "
                 "orange = with retrieved glossary (E variants)",
                 fontsize=10, color=INK, loc="left")
    ax.set_ylim(0, max(100 * runs[n]["ex"].mean() for n in order) + 12)
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "ex_by_config.png", facecolor=SURFACE)
    plt.close(fig)


def calibration(runs, extra_scores: dict[str, np.ndarray] | None = None) -> dict:
    out = {}
    if CALIBRATE not in runs:
        return out
    df = runs[CALIBRATE]
    correct = df["ex"].values.astype(bool)
    scores = {"vote agreement": df["confidence"].values}
    scores.update(extra_scores or {})
    for name, conf in scores.items():
        grid = np.unique(conf) if name == "vote agreement" else np.quantile(conf, np.linspace(0, 1, 41))
        out[name] = [evaluate_splits(conf, correct, a, 0.1, n_splits=100, grid=grid)
                     for a in (0.1, 0.2, 0.3)]
    # Risk-coverage plot with the operating points from one calibration on all of E.
    fig, ax = plt.subplots(figsize=(6.2, 4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    for (name, conf), color in zip(scores.items(), (BLUE, ORANGE, AQUA)):
        cov, risk = risk_coverage(conf, correct)
        ax.plot(100 * cov, 100 * risk, color=color, linewidth=2, marker="o" if len(cov) < 8 else None,
                markersize=6, label=name)
        for r in out[name]:
            if not np.isnan(r["mean_threshold"]):
                ax.scatter(100 * r["mean_coverage"], 100 * (1 - r["mean_accuracy_answered"]), s=70,
                           color=color, edgecolor=SURFACE, linewidth=2, zorder=5)
                if name == "vote agreement":
                    ax.annotate(f"α={r['alpha']}", (100 * r["mean_coverage"],
                                                    100 * (1 - r["mean_accuracy_answered"])),
                                xytext=(6, -12), textcoords="offset points", fontsize=8, color=INK2)
    ax.set_xlabel("Coverage: share of questions answered (%)", color=INK2, fontsize=9)
    ax.set_ylabel("Error on answered questions (%)", color=INK2, fontsize=9)
    ax.set_title(f"Risk-coverage for {CALIBRATE} (dots: LTT operating points, mean of 100 splits)",
                 fontsize=9, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2)
    fig.tight_layout()
    fig.savefig(paths.FIGURES / "risk_coverage.png", facecolor=SURFACE)
    plt.close(fig)
    # One concrete calibration on a fixed half, for the README narrative.
    rng = np.random.default_rng(0)
    perm = rng.permutation(len(df))
    cal = perm[: len(df) // 2]
    res = learn_then_test(scores["vote agreement"][cal], correct[cal], 0.2, 0.1)
    out["example_ltt_alpha0.2"] = {"threshold": res.threshold, "tested": res.tested}
    return out


def main() -> None:
    paths.TABLES.mkdir(parents=True, exist_ok=True)
    paths.FIGURES.mkdir(parents=True, exist_ok=True)
    runs = load_runs(MAIN + EXTRA)
    table = main_table(runs)
    show = table.drop(columns=["EX"])
    (paths.TABLES / "main_results.md").write_text(to_markdown(show))
    table.to_csv(paths.TABLES / "main_results.csv", index=False)
    summary = {"main": table.drop(columns=["What it adds"]).to_dict(orient="records")}

    sig = []
    for a, b in PAIRS:
        if a in runs and b in runs:
            common = runs[a].index.intersection(runs[b].index)
            m = mcnemar_exact(runs[a].loc[common, "ex"].values, runs[b].loc[common, "ex"].values)
            sig.append({"pair": f"{a} vs {b}", "EX_a": round(100 * runs[a].loc[common, "ex"].mean(), 1),
                        "EX_b": round(100 * runs[b].loc[common, "ex"].mean(), 1), **m})
    summary["mcnemar"] = sig
    (paths.TABLES / "significance.md").write_text(to_markdown(pd.DataFrame(sig)) if sig else "")

    gaps = {}
    for d, e, f, label in (("D", "E", "F", "7B agent, top-15 schema, glossary top-3 (D/E/F)"),
                           ("D", "E2", "F", "7B agent, top-15 schema, glossary def+q top-5 (D/E2/F)"),
                           ("D_full", "E_full", "F_full", "7B agent, full schema, glossary top-3"),
                           ("D_full", "E2_full", "F_full", "7B agent, full schema, glossary def+q top-5"),
                           ("C", "Cg", "Cf", "7B single-shot, glossary top-3 (C/Cg/Cf)"),
                           ("C", "Cg2", "Cf", "7B single-shot, glossary def+q top-5"),
                           ("D_32b", "E_32b", "F_32b", "32B agent, top-15 schema, glossary top-3"),
                           ("D_full_32b", "E2_full_32b", "F_full_32b",
                            "32B agent, full schema, glossary def+q top-5")):
        if all(x in runs for x in (d, e, f)):
            common = runs[d].index.intersection(runs[e].index).intersection(runs[f].index)
            p, lo, hi = gap_closed(*(runs[x].loc[common, "ex"].values for x in (d, e, f)))
            gaps[label] = {"gap_closed": p, "ci95": [lo, hi], "n": len(common)}
    summary["gap_closed"] = gaps

    ext_b = paths.TABLES / "confidence_model_oof.json"
    extra_scores = {}
    if ext_b.exists():
        oof = json.loads(ext_b.read_text())
        idx = runs[CALIBRATE].index
        for name, vals in oof.items():
            s = pd.Series(vals["scores"], index=[int(k) for k in vals["question_ids"]])
            extra_scores[name] = s.loc[idx].values
    summary["calibration"] = calibration(runs, extra_scores)
    if runs:
        plot_ex(table, runs)
    (paths.TABLES / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(to_markdown(show))
    print(json.dumps({k: summary[k] for k in ("mcnemar", "gap_closed")}, indent=1, default=float))
    for name, rows in summary["calibration"].items():
        if isinstance(rows, list):
            for r in rows:
                print(name, {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})


if __name__ == "__main__":
    main()
