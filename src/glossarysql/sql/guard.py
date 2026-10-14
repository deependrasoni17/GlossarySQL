"""First safety layer: accept only a single read-only SELECT statement.

The second layer is the read-only SQLite connection in ``executor.py``; either
layer alone blocks writes, so a bug in one does not open the database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

# Node types that must never appear anywhere in an accepted statement.
_FORBIDDEN = tuple(
    getattr(exp, name)
    for name in (
        "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Merge",
        "Command", "Pragma", "Attach", "Detach", "TruncateTable", "Transaction",
        "Commit", "Rollback", "Set", "Use", "Grant", "Copy", "LoadData",
    )
    if hasattr(exp, name)
)
_FORBIDDEN_WORDS = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|pragma|replace\s+into|"
    r"vacuum|reindex|begin|commit|rollback|savepoint|release)\b",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    ok: bool
    sql: str
    reason: str = ""


def _strip_strings_and_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r'"(?:[^"]|"")*"', '""', sql)
    sql = re.sub(r"`[^`]*`", "``", sql)
    return re.sub(r"\[[^\]]*\]", "[]", sql)


def clean_sql(sql: str) -> str:
    """Remove markdown fences and trailing semicolons/whitespace."""
    sql = sql.strip()
    sql = re.sub(r"^```(?:sql|sqlite)?\s*", "", sql, flags=re.I)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip().rstrip(";").strip()


def check_sql(sql: str) -> GuardResult:
    sql = clean_sql(sql)
    if not sql:
        return GuardResult(False, sql, "empty query")

    bare = _strip_strings_and_comments(sql)
    if ";" in bare:
        return GuardResult(False, sql, "multiple statements are not allowed")
    if not re.match(r"^\s*(\(\s*)*(select|with)\b", bare, re.I):
        return GuardResult(False, sql, "only SELECT queries are allowed")
    if _FORBIDDEN_WORDS.search(bare):
        return GuardResult(False, sql, "query contains a forbidden keyword")

    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except sqlglot.errors.SqlglotError:
        # sqlglot does not cover every SQLite construct. The keyword checks above
        # already passed and the connection is read-only, so let SQLite judge it.
        return GuardResult(True, sql, "accepted by keyword check (sqlglot could not parse)")
    if len(statements) != 1:
        return GuardResult(False, sql, "exactly one statement is allowed")
    stmt = statements[0]
    if not isinstance(stmt, exp.Query):
        return GuardResult(False, sql, f"statement type {type(stmt).__name__} is not a query")
    for node in stmt.walk():
        if isinstance(node, _FORBIDDEN):
            return GuardResult(False, sql, f"forbidden operation {type(node).__name__}")
    return GuardResult(True, sql)
