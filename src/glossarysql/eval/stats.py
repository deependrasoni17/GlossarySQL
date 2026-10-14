"""Bootstrap confidence intervals, McNemar's exact test and the gap-closed metric."""

from __future__ import annotations

import numpy as np
from scipy.stats import binomtest


def bootstrap_ci(x: np.ndarray, n_boot: int = 1000, seed: int = 0, level: float = 0.95):
    x = np.asarray(x, float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), (n_boot, len(x)))].mean(axis=1)
    lo, hi = np.percentile(means, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(x.mean()), float(lo), float(hi)


def mcnemar_exact(a: np.ndarray, b: np.ndarray) -> dict:
    """Paired test on the questions where the two systems disagree."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    only_a, only_b = int((a & ~b).sum()), int((~a & b).sum())
    n = only_a + only_b
    p = binomtest(only_a, n, 0.5).pvalue if n else 1.0
    return {"only_a": only_a, "only_b": only_b, "p_value": float(p)}


def gap_closed(ex_d: np.ndarray, ex_e: np.ndarray, ex_f: np.ndarray, n_boot: int = 1000, seed: int = 0):
    """(EX_E - EX_D) / (EX_F - EX_D), with a paired bootstrap CI over questions."""
    d, e, f = (np.asarray(v, float) for v in (ex_d, ex_e, ex_f))
    point = (e.mean() - d.mean()) / (f.mean() - d.mean()) if f.mean() != d.mean() else float("nan")
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(d), len(d))
        den = f[i].mean() - d[i].mean()
        if den > 0:
            vals.append((e[i].mean() - d[i].mean()) / den)
    lo, hi = np.percentile(vals, [2.5, 97.5]) if vals else (np.nan, np.nan)
    return float(point), float(lo), float(hi)
