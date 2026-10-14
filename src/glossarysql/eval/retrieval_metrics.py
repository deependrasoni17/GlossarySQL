"""Retrieval-only metrics on Mini-Dev (no LLM needed).

* Column recall@k: share of the gold query's columns among the top-k retrieved.
* Glossary coverage: for each question, how similar is its *own* hint to the
  closest entry in the glossary built from the other half? Candidates above a
  similarity threshold are written out for manual checking.

    python -m glossarysql.eval.retrieval_metrics [--schema-embedder models/.../best]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

import numpy as np

from glossarysql import paths
from glossarysql.data import fold_sets, load_minidev
from glossarysql.ingest.knowledge import build_glossary, split_evidence
from glossarysql.ingest.schema import load_schema
from glossarysql.retrieval.hybrid import BGE_QUERY_PREFIX, DEFAULT_EMBEDDER, Embedder, HybridIndex, tokenize
from glossarysql.training.gold_columns import gold_columns

KS = (5, 10, 15)


def column_recall(embedder: Embedder) -> dict:
    exs = load_minidev()
    by_db = defaultdict(list)
    for e in exs:
        by_db[e.db_id].append(e)
    res = {"hybrid": {k: [] for k in KS}, "dense": {k: [] for k in KS}, "bm25": {k: [] for k in KS}}
    for db_id, items in by_db.items():
        docs = load_schema(db_id)
        schema = defaultdict(set)
        for d in docs:
            schema[d.table].add(d.column)
        idx = HybridIndex([d.retrieval_text() for d in docs], embedder, BGE_QUERY_PREFIX)
        dv = embedder.encode([d.retrieval_text() for d in docs])
        for e in items:
            gold = gold_columns(e.sql, schema)
            if not gold:
                continue
            hy = [docs[h.idx].key for h in idx.search(e.question, k=max(KS))]
            qv = embedder.encode([BGE_QUERY_PREFIX + e.question])[0]
            de = [docs[i].key for i in np.argsort(-(dv @ qv))[: max(KS)]]
            bm = idx.bm25.get_scores(tokenize(e.question))
            b = [docs[i].key for i in np.argsort(-bm)[: max(KS)]]
            for name, ranked in (("hybrid", hy), ("dense", de), ("bm25", b)):
                for k in KS:
                    res[name][k].append(len(set(ranked[:k]) & gold) / len(gold))
    return {name: {f"recall@{k}": float(np.mean(v)) for k, v in d.items()} for name, d in res.items()}


def glossary_coverage(embedder: Embedder, threshold: float = 0.85) -> dict:
    """Max cosine between each eval question's own definitions and its fold's glossary."""
    rows = []
    for fold in (0, 1):
        knowledge, evaluation = fold_sets(fold)
        gloss = build_glossary(knowledge)
        by_db = defaultdict(list)
        for g in gloss:
            by_db[g.db_id].append(g)
        for e in evaluation:
            defs = split_evidence(e.evidence)
            entries = by_db.get(e.db_id, [])
            if not defs or not entries:
                rows.append({"question_id": e.question_id, "max_sim": 0.0, "n_defs": len(defs)})
                continue
            dv = embedder.encode(defs)
            gv = embedder.encode([g.text for g in entries])
            sims = dv @ gv.T
            best = sims.max(axis=1)  # per own definition: closest glossary entry
            j = sims.argmax(axis=1)
            rows.append({
                "question_id": e.question_id, "fold": fold, "question": e.question,
                "n_defs": len(defs), "max_sim": float(best.max()),
                "share_defs_covered": float((best >= threshold).mean()),
                "pairs": [{"own": d, "closest": entries[int(jj)].text, "sim": round(float(s), 3)}
                          for d, jj, s in zip(defs, j, best)],
            })
    sims = np.array([r["max_sim"] for r in rows])
    full = np.array([r.get("share_defs_covered", 0.0) for r in rows])
    return {
        "threshold": threshold,
        "any_definition_covered": float((sims >= threshold).mean()),
        "all_definitions_covered": float((full >= 1.0).mean()),
        "mean_share_covered": float(full.mean()),
        "rows": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema-embedder", default=None)
    args = ap.parse_args()
    base = Embedder(DEFAULT_EMBEDDER)
    out = {"column_recall": {"bge-small (base)": column_recall(base)}}
    if args.schema_embedder:
        out["column_recall"]["bge-small (fine-tuned)"] = column_recall(Embedder(args.schema_embedder))
    cov = glossary_coverage(base)
    out["glossary_coverage"] = {k: v for k, v in cov.items() if k != "rows"}
    paths.TABLES.mkdir(parents=True, exist_ok=True)
    (paths.TABLES / "retrieval_metrics.json").write_text(json.dumps(out, indent=2))
    (paths.TABLES / "glossary_coverage_rows.json").write_text(json.dumps(cov["rows"], indent=1))
    base.save()
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
