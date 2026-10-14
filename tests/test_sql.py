import sqlite3

import pytest

from glossarysql.sql.executor import execute_sql
from glossarysql.sql.guard import check_sql
from glossarysql.sql.normalize import result_key


@pytest.mark.parametrize("sql", [
    "SELECT 1",
    "select name from t where x = 'drop table t'",
    "WITH a AS (SELECT 1 AS x) SELECT x FROM a",
    "SELECT a FROM t UNION SELECT b FROM u",
    "```sql\nSELECT `Free Meal Count (K-12)` FROM frpm;\n```",
    "SELECT CAST(SUM(IIF(Currency = 'EUR', 1, 0)) AS FLOAT) / SUM(IIF(Currency = 'CZK', 1, 0)) FROM customers",
    "SELECT `unterminated FROM t",  # sqlglot TokenError: left for SQLite to reject
])
def test_guard_accepts_reads(sql):
    assert check_sql(sql).ok


@pytest.mark.parametrize("sql", [
    "DROP TABLE t",
    "DELETE FROM t",
    "UPDATE t SET x = 1",
    "INSERT INTO t VALUES (1)",
    "SELECT 1; DROP TABLE t",
    "PRAGMA writable_schema = 1",
    "ATTACH DATABASE 'x.db' AS x",
    "CREATE TABLE x AS SELECT 1",
    "",
])
def test_guard_rejects_writes_and_stacking(sql):
    assert not check_sql(sql).ok


@pytest.fixture
def db(tmp_path):
    p = tmp_path / "t.sqlite"
    conn = sqlite3.connect(p)
    conn.execute("CREATE TABLE t (x INTEGER, y TEXT)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [(i, f"v{i}") for i in range(100)])
    conn.commit()
    conn.close()
    return p


def test_executor_is_read_only_even_without_guard(db):
    res = execute_sql(db, "DELETE FROM t")
    assert not res.ok and "readonly" in res.error.replace(" ", "").lower()
    assert execute_sql(db, "SELECT COUNT(*) FROM t").rows == [(100,)]


def test_executor_row_cap_and_errors(db):
    res = execute_sql(db, "SELECT x FROM t", max_rows=10)
    assert len(res.rows) == 10 and res.truncated
    assert "no such column" in execute_sql(db, "SELECT nope FROM t").error


def test_executor_timeout(db):
    slow = ("WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c) "
            "SELECT COUNT(*) FROM c")
    res = execute_sql(db, slow, timeout_s=0.5)
    assert not res.ok and "timed out" in res.error


def test_result_key_ignores_order_duplicates_and_float_noise():
    a = [(1, 0.333333333), (2, "x")]
    b = [(2, "x"), (1, 0.33333334), (1, 0.333333333)]
    assert result_key(a) == result_key(b)
    assert result_key([(1.0,)]) == result_key([(1,)])
    assert result_key([(1,)]) != result_key([(2,)])
