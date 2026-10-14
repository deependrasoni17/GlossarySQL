"""Build one document per column (schema index) and the distinct text values (values index).

Sources: BIRD's ``*_tables.json`` (types, primary and foreign keys), the
per-table ``database_description/*.csv`` files (column meanings and coded
values), and the SQLite file itself (sample values).
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from glossarysql import paths
from glossarysql.sql.executor import connect_readonly


@dataclass
class ColumnDoc:
    db_id: str
    table: str
    column: str
    type: str
    is_pk: bool = False
    fks: list[str] = field(default_factory=list)  # "table.column" this column references / is referenced by
    expanded: str = ""
    description: str = ""
    value_description: str = ""
    samples: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.table}.{self.column}"

    def retrieval_text(self) -> str:
        """Text that BM25 and the embedder see. No sample values, so the same
        format can be produced for BIRD-train databases in Extension A."""
        parts = [f"{self.table} . {self.column}"]
        if self.expanded and self.expanded.lower() != self.column.lower():
            parts.append(f"({self.expanded})")
        desc = self.description
        if desc and desc.lower() not in (self.column.lower(), self.expanded.lower()):
            parts.append(f": {desc}")
        if self.value_description:
            parts.append(f". Values: {self.value_description}")
        return _squash(" ".join(parts))[:600]


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _read_csv(path: Path) -> list[dict]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(io.StringIO(text)))
    return [{(k or "").strip().lower(): _squash(v or "") for k, v in r.items()} for r in rows]


def _load_descriptions(desc_dir: Path) -> dict[tuple[str, str], dict]:
    out = {}
    if not desc_dir.exists():
        return out
    for f in desc_dir.glob("*.csv"):
        table = f.stem.lower()
        for r in _read_csv(f):
            col = r.get("original_column_name", "").lower()
            if col:
                out[(table, col)] = r
    return out


def load_tables_json(path: Path) -> dict[str, dict]:
    return {t["db_id"]: t for t in json.loads(path.read_text())}


def column_docs_from_tables(tables: dict, desc_dir: Path) -> list[ColumnDoc]:
    """Column documents without sample values (works without the SQLite file)."""
    descs = _load_descriptions(desc_dir)
    tnames = tables["table_names_original"]
    cols = tables["column_names_original"]
    types = tables["column_types"]
    pk_ids: set[int] = set()
    for pk in tables["primary_keys"]:
        pk_ids.update(pk if isinstance(pk, list) else [pk])
    links: dict[int, list[int]] = {}
    for a, b in tables["foreign_keys"]:
        links.setdefault(a, []).append(b)
        links.setdefault(b, []).append(a)

    def name(i: int) -> str:
        t, c = cols[i]
        return f"{tnames[t]}.{c}"

    docs = []
    for i, (t, c) in enumerate(cols):
        if t < 0:
            continue
        d = descs.get((tnames[t].lower(), c.lower()), {})
        docs.append(ColumnDoc(
            db_id=tables["db_id"], table=tnames[t], column=c, type=types[i].upper(),
            is_pk=i in pk_ids, fks=[name(j) for j in links.get(i, [])],
            expanded=d.get("column_name", ""), description=d.get("column_description", ""),
            value_description=d.get("value_description", ""),
        ))
    return docs


def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def add_samples(docs: list[ColumnDoc], db_file: Path, n: int = 3) -> None:
    conn = connect_readonly(db_file)
    try:
        for d in docs:
            try:
                rows = conn.execute(
                    f"SELECT DISTINCT {_q(d.column)} FROM {_q(d.table)} "
                    f"WHERE {_q(d.column)} IS NOT NULL AND {_q(d.column)} != '' LIMIT {n}"
                ).fetchall()
                d.samples = [str(r[0])[:40] for r in rows]
            except Exception:  # noqa: BLE001
                d.samples = []
    finally:
        conn.close()


def collect_values(docs: list[ColumnDoc], db_file: Path, per_column: int = 50_000,
                   max_len: int = 60) -> list[tuple[str, str, str]]:
    """Distinct short text values: (value, table, column). Long free-text columns are skipped."""
    conn = connect_readonly(db_file)
    out = []
    try:
        for d in docs:
            if d.type != "TEXT" or d.is_pk:
                continue
            try:
                rows = conn.execute(
                    f"SELECT DISTINCT {_q(d.column)} FROM {_q(d.table)} "
                    f"WHERE {_q(d.column)} IS NOT NULL LIMIT {per_column + 1}"
                ).fetchall()
            except Exception:  # noqa: BLE001
                continue
            vals = [str(r[0]) for r in rows if isinstance(r[0], str)]
            if not vals or len(vals) > per_column:
                continue
            if sum(len(v) for v in vals) / len(vals) > max_len:
                continue
            for v in vals:
                v2 = v.strip()
                # Numbers, dates and codes are matched poorly by fuzzy text search.
                if 2 <= len(v2) <= max_len and not re.fullmatch(r"[\d\s.,:/+-]+", v2):
                    out.append((v2, d.table, d.column))
    finally:
        conn.close()
    return out


def build_dev_indexes() -> None:
    tables = load_tables_json(paths.DB_DIR.parent / "dev_tables.json")
    paths.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for db_id, t in sorted(tables.items()):
        docs = column_docs_from_tables(t, paths.description_dir(db_id))
        add_samples(docs, paths.db_path(db_id))
        values = collect_values(docs, paths.db_path(db_id))
        out = paths.INDEX_DIR / db_id
        out.mkdir(exist_ok=True)
        (out / "schema.json").write_text(json.dumps([asdict(d) for d in docs], indent=0))
        (out / "values.json").write_text(json.dumps(values))
        n_desc = sum(1 for d in docs if d.description)
        print(f"{db_id:28s} columns={len(docs):4d} described={n_desc:4d} values={len(values):7d}", flush=True)


def load_schema(db_id: str) -> list[ColumnDoc]:
    return [ColumnDoc(**d) for d in json.loads((paths.INDEX_DIR / db_id / "schema.json").read_text())]


def load_values(db_id: str) -> list[tuple[str, str, str]]:
    return [tuple(v) for v in json.loads((paths.INDEX_DIR / db_id / "values.json").read_text())]


if __name__ == "__main__":
    build_dev_indexes()
