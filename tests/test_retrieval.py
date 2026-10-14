from glossarysql.retrieval.hybrid import tokenize
from glossarysql.retrieval.values import ValueMatcher
from glossarysql.training.gold_columns import gold_columns

SCHEMA = {"schools": {"CDSCode", "County", "City"}, "frpm": {"CDSCode", "Free Meal Count (K-12)",
                                                              "Enrollment (K-12)"}}


def test_gold_columns_resolve_aliases_and_unqualified_names():
    sql = ("SELECT T1.City, `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM schools AS T1 "
           "JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE County = 'Alameda'")
    assert gold_columns(sql, SCHEMA) == {
        "schools.City", "schools.CDSCode", "frpm.CDSCode", "schools.County",
        "frpm.Free Meal Count (K-12)", "frpm.Enrollment (K-12)"}


def test_value_matcher_exact_and_fuzzy():
    vm = ValueMatcher([("Alameda", "schools", "County"), ("Los Angeles", "schools", "County"),
                       ("Oakland", "schools", "City")])
    got = {m.render() for m in vm.match("How many schools are in Alameda or Los Angels?")}
    assert "schools.County = 'Alameda'" in got
    assert "schools.County = 'Los Angeles'" in got  # fuzzy match of a typo
    assert vm.match("What is the average enrollment?") == []


def test_tokenize_splits_identifiers():
    assert tokenize("FreeMealCount enrollment_k12") == ["free", "meal", "count", "enrollment", "k12"]
