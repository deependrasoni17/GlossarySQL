"""Glossary entries and solved examples, built from the *knowledge* split only."""

from __future__ import annotations

import re
from dataclasses import dataclass

from glossarysql.data import Example


@dataclass(frozen=True)
class GlossaryEntry:
    db_id: str
    text: str
    source_qids: tuple[int, ...]  # pointer back to the questions it came from (leakage audit)


def split_evidence(evidence: str) -> list[str]:
    """Split a hint into single definitions on semicolons that are outside quotes."""
    parts, buf, quote = [], [], None
    for ch in evidence or "":
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
            buf.append(ch)
        elif ch == ";":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip(" .;")
        if len(p) >= 4:
            out.append(p)
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def build_glossary(knowledge: list[Example]) -> list[GlossaryEntry]:
    merged: dict[tuple[str, str], tuple[str, list[int]]] = {}
    for ex in knowledge:
        for d in split_evidence(ex.evidence):
            key = (ex.db_id, _norm(d))
            if key in merged:
                merged[key][1].append(ex.question_id)
            else:
                merged[key] = (d, [ex.question_id])
    return [GlossaryEntry(db, text, tuple(q)) for (db, _), (text, q) in merged.items()]
