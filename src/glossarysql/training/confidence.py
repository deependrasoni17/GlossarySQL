"""Extension B: a learned confidence model to replace raw vote agreement (5 levels).

Features come only from what the agent observes at run time (never the
difficulty label). Out-of-fold predictions from 5-fold cross-validation are
compared with agreement alone on AUROC and Brier score, then fed to the same
Learn-then-Test procedure by ``eval.report``.

    python -m glossarysql.training.confidence --run E
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from glossarysql import paths

FEATURES = ["agreement", "n_groups", "n_ok_share", "repaired", "winner_repaired", "empty",
            "log_rows", "n_tables", "sql_len", "schema_top", "schema_mean", "glossary_top",
            "example_top"]


def features(df: pd.DataFrame) -> pd.DataFrame:
    sc = df["context"].apply(lambda c: (c or {}).get("scores", {}))
    return pd.DataFrame({
        "agreement": df["confidence"],
        "n_groups": df["n_groups"],
        "n_ok_share": df["n_ok"] / df["n_candidates"].clip(lower=1),
        "repaired": (df["repairs"] > 0).astype(int),
        "winner_repaired": df["winner_repaired"].astype(int),
        "empty": df["empty"].astype(int),
        "log_rows": np.log1p(df["n_rows"]),
        "n_tables": df["n_tables"],
        "sql_len": df["sql_len"] / 100,
        "schema_top": sc.apply(lambda s: s.get("schema_top_dense", 0.0)),
        "schema_mean": sc.apply(lambda s: s.get("schema_mean_dense", 0.0)),
        "glossary_top": sc.apply(lambda s: s.get("glossary_top_dense", 0.0)),
        "example_top": sc.apply(lambda s: s.get("example_top_dense", 0.0)),
    }, index=df.index)


def main() -> None:
    import lightgbm as lgb

    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="E")
    args = ap.parse_args()
    df = pd.read_json(paths.RUNS / f"{args.run}.jsonl", lines=True).set_index("question_id").sort_index()
    X, y = features(df)[FEATURES].values, df["ex"].values.astype(int)
    models = {
        "logistic regression": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)),
        "gradient boosting": lambda: lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=8,
                                                        min_child_samples=15, subsample=0.8,
                                                        subsample_freq=1, colsample_bytree=0.8,
                                                        verbose=-1, random_state=0),
    }
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    oof = {name: np.zeros(len(y)) for name in models}
    for tr, te in skf.split(X, y):
        for name, make in models.items():
            m = make().fit(X[tr], y[tr])
            oof[name][te] = m.predict_proba(X[te])[:, 1]
    report = {"n": int(len(y)), "base_rate": float(y.mean()),
              "vote agreement": {"auroc": float(roc_auc_score(y, df["confidence"])),
                                 "brier": float(brier_score_loss(y, df["confidence"]))}}
    for name, p in oof.items():
        report[name] = {"auroc": float(roc_auc_score(y, p)), "brier": float(brier_score_loss(y, p))}
    lr = models["logistic regression"]().fit(X, y)
    coefs = lr[-1].coef_[0]
    report["logistic_coefficients_standardised"] = dict(
        sorted(zip(FEATURES, map(float, coefs)), key=lambda kv: -abs(kv[1])))
    (paths.TABLES / "confidence_model.json").write_text(json.dumps(report, indent=2))
    (paths.TABLES / "confidence_model_oof.json").write_text(json.dumps(
        {name: {"question_ids": df.index.tolist(), "scores": p.tolist()} for name, p in oof.items()}))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
