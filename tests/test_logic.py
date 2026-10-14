import numpy as np

from glossarysql.agent.graph import GlossarySQLAgent, choose_chart
from glossarysql.agent.prompts import parse_candidate
from glossarysql.calibration.ltt import binomial_pvalue, evaluate_splits, learn_then_test
from glossarysql.data import load_minidev, make_split
from glossarysql.eval.metrics import execution_match, soft_f1
from glossarysql.eval.stats import gap_closed, mcnemar_exact
from glossarysql.ingest.knowledge import split_evidence


def _vote(results, n=None):
    agent = GlossarySQLAgent.__new__(GlossarySQLAgent)
    agent.cfg = {}
    cands = [{"sql": f"q{i}"} for i in range(n or len(results))]
    return agent.vote({"candidates": cands, "results": results})


def test_vote_majority_on_result_sets():
    ok = lambda rows: {"ok": True, "rows": rows, "columns": ["a"]}  # noqa: E731
    out = _vote([ok([(1,)]), ok([(2,)]), ok([(2,), (2,)]), {"ok": False, "error": "x"}, ok([(1,)])])
    # [(2,)] and [(2,),(2,)] are the same set, so they tie with [(1,)] at 2 votes; earliest wins.
    assert out["confidence"] == 0.4
    assert out["winner_sql"] == "q0"


def test_vote_prefers_non_empty_on_tie_and_handles_all_failed():
    ok = lambda rows: {"ok": True, "rows": rows, "columns": ["a"]}  # noqa: E731
    assert _vote([ok([]), ok([(3,)])])["winner_sql"] == "q1"
    out = _vote([{"ok": False, "error": "e"}] * 2)
    assert out["confidence"] == 0.0 and out["winner_sql"] == "q0"


def test_metrics_follow_bird():
    assert execution_match([(1,), (2,)], [(2,), (1,), (1,)]) == 1
    assert execution_match([(1, 2)], [(2, 1)]) == 0
    assert soft_f1([(1, 2)], [(1, 2)]) == 1.0
    assert 0 < soft_f1([(1, 3)], [(1, 2)]) < 1


def test_ltt_toy_data():
    # Confidence 1.0 -> always right, 0.2 -> always wrong.
    conf = np.array([1.0] * 200 + [0.2] * 200)
    correct = np.array([True] * 200 + [False] * 200)
    res = learn_then_test(conf, correct, alpha=0.1, delta=0.1)
    assert res.threshold == 1.0
    # Too strict a target on a useless score: abstain on everything.
    res = learn_then_test(np.ones(50), np.zeros(50, bool), alpha=0.1, delta=0.1)
    assert res.threshold is None
    assert binomial_pvalue(100, 0, 0.1) < 1e-4
    rep = evaluate_splits(conf, correct, 0.1, 0.1, n_splits=20)
    assert rep["violation_rate"] == 0 and abs(rep["mean_coverage"] - 0.5) < 0.1


def test_stats():
    a = np.array([1, 1, 0, 0, 1])
    b = np.array([1, 0, 0, 1, 1])
    m = mcnemar_exact(a, b)
    assert m["only_a"] == 1 and m["only_b"] == 1 and m["p_value"] == 1.0
    d, e, f = np.zeros(10), np.r_[np.ones(5), np.zeros(5)], np.ones(10)
    assert gap_closed(d, e, f)[0] == 0.5


def test_split_evidence_respects_quotes():
    parts = split_evidence("rate = A / B; name = 'x;y'; ")
    assert parts == ["rate = A / B", "name = 'x;y'"]


def test_parse_candidate():
    c = parse_candidate("Reasoning: use frpm.\n```sql\nSELECT 1;\n```")
    assert c.sql == "SELECT 1" and c.reasoning == "use frpm."
    assert parse_candidate("SELECT a FROM t").sql == "SELECT a FROM t"


def test_chart_rules():
    assert choose_chart(["n"], [(5,)])["type"] == "number"
    assert choose_chart(["year", "n"], [(2001, 3), (2002, 4)])["type"] == "line"
    assert choose_chart(["county", "n"], [("A", 3), ("B", 4)])["type"] == "bar"


def test_split_is_balanced_and_stratified():
    exs = load_minidev()
    half = make_split(exs)
    assert len(half) == 500
    for db in {e.db_id for e in exs}:
        for diff in ("simple", "moderate", "challenging"):
            ids = [e.question_id for e in exs if e.db_id == db and e.difficulty == diff]
            a = sum(half[i] == "A" for i in ids)
            assert abs(a - (len(ids) - a)) <= 1
