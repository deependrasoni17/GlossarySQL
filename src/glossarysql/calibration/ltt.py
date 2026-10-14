"""Learn-then-Test (Angelopoulos et al., 2021) threshold selection for abstention.

Guarantee: with probability at least 1 - delta over the calibration set, the
error rate on answered questions (confidence >= lambda_hat) is at most alpha,
for new questions drawn from the same distribution.

Thresholds are tested from strictest to loosest with an exact binomial test
and the procedure stops at the first non-rejection (fixed-sequence testing),
which controls the family-wise error without a multiple-comparison correction.

The grid is fixed in advance. A threshold that answers fewer than ``min_n``
calibration questions is skipped rather than tested: at n=0 or n=1 no test can
reject, and stopping there would end the sequence before any useful threshold.
The skip depends only on the count n, and given n the number of errors is
Binomial(n, risk), so each test that is run stays valid.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import binom


@dataclass
class LTTResult:
    threshold: float | None  # None = abstain on everything
    tested: list[tuple[float, int, int, float, bool]]  # (lambda, n, errors, p-value, accepted)


def binomial_pvalue(n: int, k: int, alpha: float) -> float:
    """P(Binomial(n, alpha) <= k): small when k errors out of n is implausible if the risk were alpha."""
    if n == 0:
        return 1.0
    return float(binom.cdf(k, n, alpha))


def learn_then_test(conf: np.ndarray, correct: np.ndarray, alpha: float, delta: float,
                    grid: np.ndarray | None = None, min_n: int = 20) -> LTTResult:
    conf = np.asarray(conf, float)
    correct = np.asarray(correct, bool)
    if grid is None:
        grid = np.unique(conf)
    grid = np.sort(np.asarray(grid, float))[::-1]  # strictest first
    accepted, tested = None, []
    for lam in grid:
        mask = conf >= lam
        n = int(mask.sum())
        k = int((~correct[mask]).sum())
        if n < min_n:
            continue
        p = binomial_pvalue(n, k, alpha)
        ok = p <= delta
        tested.append((float(lam), n, k, p, ok))
        if not ok:
            break
        accepted = float(lam)
    return LTTResult(accepted, tested)


def evaluate_splits(conf: np.ndarray, correct: np.ndarray, alpha: float, delta: float,
                    n_splits: int = 100, cal_frac: float = 0.5, seed: int = 0,
                    grid: np.ndarray | None = None) -> dict:
    """Repeat random calibration/test splits; report accuracy, coverage and violation rate."""
    rng = np.random.default_rng(seed)
    conf, correct = np.asarray(conf, float), np.asarray(correct, bool)
    n = len(conf)
    accs, covs, viol, thresholds = [], [], [], []
    for _ in range(n_splits):
        perm = rng.permutation(n)
        cal, test = perm[: int(n * cal_frac)], perm[int(n * cal_frac):]
        res = learn_then_test(conf[cal], correct[cal], alpha, delta, grid)
        thresholds.append(np.nan if res.threshold is None else res.threshold)
        if res.threshold is None:
            covs.append(0.0)
            accs.append(np.nan)
            viol.append(False)  # answering nothing cannot violate the risk bound
            continue
        ans = conf[test] >= res.threshold
        covs.append(ans.mean())
        acc = correct[test][ans].mean() if ans.any() else np.nan
        accs.append(acc)
        viol.append(bool(ans.any() and (1 - acc) > alpha))
    return {
        "alpha": alpha, "delta": delta, "target_accuracy": 1 - alpha,
        "mean_accuracy_answered": float(np.nanmean(accs)) if not np.all(np.isnan(accs)) else float("nan"),
        "mean_coverage": float(np.mean(covs)),
        "violation_rate": float(np.mean(viol)),
        "mean_threshold": float(np.nanmean(thresholds)) if not np.all(np.isnan(thresholds)) else float("nan"),
        "abstain_all_rate": float(np.mean(np.isnan(thresholds))),
    }


def risk_coverage(conf: np.ndarray, correct: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Error on answered questions vs share answered, sweeping the threshold."""
    conf, correct = np.asarray(conf, float), np.asarray(correct, bool)
    covs, risks = [], []
    for lam in np.sort(np.unique(conf))[::-1]:
        m = conf >= lam
        covs.append(m.mean())
        risks.append(1 - correct[m].mean())
    return np.array(covs), np.array(risks)
