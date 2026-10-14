"""Which (table, column) pairs does a gold SQL query use? Resolves table aliases."""

from __future__ import annotations

import sqlglot
from sqlglot import exp


def gold_columns(sql: str, schema: dict[str, set[str]]) -> set[str]:
    """Return {"table.column"} using the original-case names from ``schema``.

    ``schema`` maps table name -> set of column names. Unqualified columns are
    attributed to the referenced table that has a column of that name.
    """
    lower_tables = {t.lower(): t for t in schema}
    lower_cols = {t: {c.lower(): c for c in cols} for t, cols in schema.items()}
    try:
        tree = sqlglot.parse_one(sql, read="sqlite")
    except Exception:  # noqa: BLE001
        return set()
    alias: dict[str, str] = {}
    used_tables: list[str] = []
    for t in tree.find_all(exp.Table):
        real = lower_tables.get(t.name.lower())
        if real is None:
            continue
        used_tables.append(real)
        alias[t.name.lower()] = real
        if t.alias:
            alias[t.alias.lower()] = real
    out = set()
    for c in tree.find_all(exp.Column):
        name = c.name.lower()
        if not name:
            continue
        if c.table:
            t = alias.get(c.table.lower())
            if t and name in lower_cols[t]:
                out.add(f"{t}.{lower_cols[t][name]}")
            continue
        for t in dict.fromkeys(used_tables):
            if name in lower_cols[t]:
                out.add(f"{t}.{lower_cols[t][name]}")
                break
    return out
