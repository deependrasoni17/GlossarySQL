"""The four retrieval indexes and the context builder used by the agent's Retrieve node."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from glossarysql.data import Example, fold_sets, load_minidev
from glossarysql.ingest.knowledge import GlossaryEntry, build_glossary
from glossarysql.ingest.schema import ColumnDoc, load_schema, load_values
from glossarysql.retrieval.hybrid import BGE_QUERY_PREFIX, DEFAULT_EMBEDDER, Embedder, HybridIndex
from glossarysql.retrieval.values import ValueMatch, ValueMatcher


@dataclass
class Context:
    db_id: str
    columns: list[ColumnDoc]
    retrieved_keys: list[str] = field(default_factory=list)  # ranked schema hits, before key expansion
    values: list[ValueMatch] = field(default_factory=list)
    glossary: list[tuple[GlossaryEntry, float]] = field(default_factory=list)
    examples: list[tuple[Example, float]] = field(default_factory=list)
    evidence: str = ""  # benchmark hint, only in the "perfect hints" upper bound
    scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "columns": [c.key for c in self.columns],
            "retrieved_keys": self.retrieved_keys,
            "values": [v.render() for v in self.values],
            "glossary": [{"text": g.text, "source_qids": list(g.source_qids), "score": round(s, 4)}
                         for g, s in self.glossary],
            "examples": [{"question": e.question, "sql": e.sql, "qid": e.question_id, "score": round(s, 4)}
                         for e, s in self.examples],
            "evidence": self.evidence,
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
        }


class KnowledgeBase:
    def __init__(self, embedder: Embedder | None = None, schema_embedder: Embedder | None = None):
        self.embedder = embedder or Embedder(DEFAULT_EMBEDDER)
        self.schema_embedder = schema_embedder or self.embedder
        self._lock = threading.RLock()
        self._schema: dict[str, list[ColumnDoc]] = {}
        self._schema_idx: dict[str, HybridIndex] = {}
        self._values: dict[str, ValueMatcher] = {}
        self._gloss: dict[tuple, tuple[list[GlossaryEntry], HybridIndex]] = {}
        self._ex: dict[tuple, tuple[list[Example], HybridIndex]] = {}
        self._value_cache: dict[tuple[str, str], list[ValueMatch]] = {}

    # ---- lazily built per-database indexes ----
    def schema(self, db_id: str) -> list[ColumnDoc]:
        with self._lock:
            if db_id not in self._schema:
                self._schema[db_id] = load_schema(db_id)
            return self._schema[db_id]

    def schema_index(self, db_id: str) -> HybridIndex:
        with self._lock:
            if db_id not in self._schema_idx:
                docs = self.schema(db_id)
                self._schema_idx[db_id] = HybridIndex(
                    [d.retrieval_text() for d in docs], self.schema_embedder, BGE_QUERY_PREFIX)
            return self._schema_idx[db_id]

    def value_matcher(self, db_id: str) -> ValueMatcher:
        with self._lock:
            if db_id not in self._values:
                self._values[db_id] = ValueMatcher(load_values(db_id))
            return self._values[db_id]

    def _knowledge(self, fold: int | None) -> list[Example]:
        # fold=None means "all 500 questions are documented knowledge" (used by the demo).
        return load_minidev() if fold is None else fold_sets(fold)[0]

    def glossary_index(self, db_id: str, fold: int | None, mode: str = "def"):
        """mode "def" indexes the definition text; "def+q" also indexes the questions the
        definition was written for (like a glossary page that shows where a term is used)."""
        key = (db_id, fold, mode)
        with self._lock:
            if key not in self._gloss:
                knowledge = self._knowledge(fold)
                qtext = {e.question_id: e.question for e in knowledge}
                entries = [g for g in build_glossary(knowledge) if g.db_id == db_id]
                if mode == "def+q":
                    texts = [g.text + " | asked in: " + " / ".join(qtext[q] for q in g.source_qids[:3])
                             for g in entries]
                else:
                    texts = [g.text for g in entries]
                self._gloss[key] = (entries, HybridIndex(texts, self.embedder, BGE_QUERY_PREFIX))
            return self._gloss[key]

    def examples_index(self, db_id: str, fold: int | None):
        key = (db_id, fold)
        with self._lock:
            if key not in self._ex:
                exs = [e for e in self._knowledge(fold) if e.db_id == db_id]
                self._ex[key] = (exs, HybridIndex([e.question for e in exs], self.embedder))
            return self._ex[key]

    # ---- the Retrieve node's work ----
    def build_context(self, question: str, db_id: str, cfg: dict, fold: int | None,
                      evidence: str = "", exclude_qid: int | None = None) -> Context:
        docs = self.schema(db_id)
        ctx = Context(db_id=db_id, columns=[])

        if cfg.get("value_matching", False):
            vkey = (db_id, question)
            if vkey not in self._value_cache:
                self._value_cache[vkey] = self.value_matcher(db_id).match(question)
            ctx.values = self._value_cache[vkey][: cfg.get("value_k", 8)]

        if cfg.get("schema_mode", "full") == "full":
            ctx.columns = list(docs)
        else:
            hits = self.schema_index(db_id).search(question, k=cfg.get("schema_k", 15))
            ctx.retrieved_keys = [docs[h.idx].key for h in hits]
            ctx.scores["schema_top_dense"] = hits[0].dense if hits else 0.0
            ctx.scores["schema_mean_dense"] = sum(h.dense for h in hits) / max(len(hits), 1)
            keep = {docs[h.idx].key for h in hits}
            keep |= {f"{v.table}.{v.column}" for v in ctx.values}
            tables = {k.split(".", 1)[0] for k in keep}
            # Keys of every involved table, plus the columns they join to, keep joins possible.
            for d in docs:
                if d.table in tables and (d.is_pk or d.fks):
                    keep.add(d.key)
                    for f in d.fks:
                        if f.split(".", 1)[0] in tables:
                            keep.add(f)
            ctx.columns = [d for d in docs if d.key in keep]

        if cfg.get("examples_k", 0):
            exs, idx = self.examples_index(db_id, fold)
            hits = [h for h in idx.search(question, k=cfg["examples_k"] + 1)
                    if exs[h.idx].question_id != exclude_qid][: cfg["examples_k"]]
            ctx.examples = [(exs[h.idx], h.dense) for h in hits]
            ctx.scores["example_top_dense"] = hits[0].dense if hits else 0.0

        if cfg.get("glossary_k", 0):
            entries, idx = self.glossary_index(db_id, fold, cfg.get("glossary_index", "def"))
            hits = [h for h in idx.search(question, k=cfg["glossary_k"] + 3)
                    if exclude_qid not in entries[h.idx].source_qids][: cfg["glossary_k"]]
            ctx.glossary = [(entries[h.idx], h.dense) for h in hits]
            ctx.scores["glossary_top_dense"] = hits[0].dense if hits else 0.0

        if cfg.get("perfect_hints", False):
            ctx.evidence = evidence
        return ctx
