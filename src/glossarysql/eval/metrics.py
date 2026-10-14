"""Execution accuracy and Soft F1, following BIRD Mini-Dev's official scripts.

``execution_match`` is ``evaluation_ex.calculate_ex`` and ``soft_f1`` is
``evaluation_f1.calculate_f1_score`` from github.com/bird-bench/mini_dev
(CC BY-SA 4.0), reproduced so per-question scores can be stored and resampled.
"""

from __future__ import annotations


def execution_match(predicted: list[tuple], gold: list[tuple]) -> int:
    return int(set(predicted) == set(gold))


def _row_match(pred_row: tuple, gold_row: tuple) -> tuple[float, float, float]:
    total = len(gold_row)
    matches = sum(1 for v in pred_row if v in gold_row)
    pred_only = sum(1 for v in pred_row if v not in gold_row)
    truth_only = sum(1 for v in gold_row if v not in pred_row)
    return matches / total, pred_only / total, truth_only / total


def soft_f1(predicted: list[tuple], gold: list[tuple]) -> float:
    if not predicted and not gold:
        return 1.0
    predicted = list(dict.fromkeys(predicted))
    gold = list(dict.fromkeys(gold))
    match_scores, pred_only_scores, truth_only_scores = [], [], []
    for i, gt_row in enumerate(gold):
        if i >= len(predicted):
            match_scores.append(0)
            truth_only_scores.append(1)
            continue
        m, p, t = _row_match(predicted[i], gt_row)
        match_scores.append(m)
        pred_only_scores.append(p)
        truth_only_scores.append(t)
    for _ in range(len(predicted) - len(gold)):
        match_scores.append(0)
        pred_only_scores.append(1)
        truth_only_scores.append(0)
    tp, fp, fn = sum(match_scores), sum(pred_only_scores), sum(truth_only_scores)
    precision = tp / (tp + fp) if tp + fp > 0 else 0
    recall = tp / (tp + fn) if tp + fn > 0 else 0
    return 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
