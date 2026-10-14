"""Prompt rendering and parsing of the LLM's typed output."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from glossarysql.ingest.schema import ColumnDoc
from glossarysql.retrieval.knowledge_base import Context

SYSTEM = (
    "You are an expert data analyst who writes correct SQLite queries. "
    "You answer with a short reasoning line followed by exactly one SQL query."
)

ANSWER_FORMAT = """Return your answer in exactly this format:
Reasoning: <one or two sentences naming the tables, columns, filters and any definition you use>
```sql
<one SQLite SELECT query>
```"""

RULES = """Rules:
- Use only the tables and columns listed above; copy column names exactly and wrap names containing spaces or symbols in backticks.
- Select only what the question asks for, in the order asked; do not add extra columns.
- Use the matched values exactly as written when filtering.
- For ratios and percentages, CAST to REAL before dividing."""


class SQLCandidate(BaseModel):
    """One parsed LLM answer."""

    reasoning: str = Field(default="", description="short explanation of the plan")
    sql: str = Field(default="", description="the SQLite query")


def _ident(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f"`{name}`"


def render_schema(columns: list[ColumnDoc]) -> str:
    by_table: dict[str, list[ColumnDoc]] = {}
    for c in columns:
        by_table.setdefault(c.table, []).append(c)
    lines, fks = [], set()
    for table, cols in by_table.items():
        lines.append(f"Table {_ident(table)}:")
        for c in cols:
            meta = [c.type or "?"]
            if c.is_pk:
                meta.append("primary key")
            desc = []
            if c.expanded and c.expanded.lower() != c.column.lower():
                desc.append(c.expanded)
            if c.description and c.description.lower() not in (c.column.lower(), c.expanded.lower()):
                desc.append(c.description)
            if c.value_description:
                desc.append("values: " + c.value_description[:300])
            if c.samples:
                desc.append("e.g. " + ", ".join(repr(s) for s in c.samples))
            text = f"  - {_ident(c.column)} ({', '.join(meta)})"
            if desc:
                text += " -- " + "; ".join(desc)
            lines.append(text)
            for f in c.fks:
                ft = f.split(".", 1)[0]
                if ft in by_table:
                    fks.add(" = ".join(sorted([f"{table}.{c.column}", f])))
    if fks:
        lines.append("Join keys: " + "; ".join(sorted(fks)))
    return "\n".join(lines)


def render_context(ctx: Context) -> str:
    parts = ["Database schema (SQLite):", render_schema(ctx.columns)]
    if ctx.values:
        parts.append("\nValues from the question found in the database:")
        parts += [f"- {v.render()}" for v in ctx.values]
    definitions = [g.text for g, _ in ctx.glossary]
    if ctx.evidence:
        definitions.append(ctx.evidence)
    if definitions:
        parts.append("\nBusiness definitions (from the company glossary; use them if relevant):")
        parts += [f"- {d}" for d in definitions]
    if ctx.examples:
        parts.append("\nSolved examples on this database:")
        for e, _ in ctx.examples:
            parts.append(f"Q: {e.question}\nSQL: {e.sql}")
    return "\n".join(parts)


def generation_prompt(question: str, ctx: Context) -> str:
    return f"{render_context(ctx)}\n\n{RULES}\n\nQuestion: {question}\n\n{ANSWER_FORMAT}"


def repair_prompt(question: str, ctx: Context, sql: str, error: str) -> str:
    return (
        f"{render_context(ctx)}\n\n{RULES}\n\nQuestion: {question}\n\n"
        f"This query was written for the question but failed:\n```sql\n{sql}\n```\n"
        f"Error: {error}\n\nFix the query so it runs on SQLite and answers the question.\n\n{ANSWER_FORMAT}"
    )


def parse_candidate(text: str) -> SQLCandidate:
    reasoning = ""
    m = re.search(r"Reasoning:\s*(.*?)(?:```|$)", text, re.S | re.I)
    if m:
        reasoning = m.group(1).strip()
    blocks = re.findall(r"```(?:sql|sqlite)?\s*(.*?)```", text, re.S | re.I)
    if blocks:
        sql = blocks[-1]
    else:
        m = re.search(r"((?:WITH|SELECT)\b.*)", text, re.S | re.I)
        sql = m.group(1) if m else ""
    return SQLCandidate(reasoning=reasoning[:500], sql=sql.strip().rstrip(";").strip())
