"""Run one experiment configuration over the evaluation questions of both folds.

    python -m glossarysql.eval.run --config configs/E.yaml [--limit 20] [--workers 48]

Writes one JSON line per question to results/runs/<name>.jsonl.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import sqlglot
import yaml
from sqlglot import exp

from glossarysql import paths
from glossarysql.agent.graph import GlossarySQLAgent, summarize_usage
from glossarysql.data import fold_sets
from glossarysql.eval.gold import load_gold
from glossarysql.eval.metrics import execution_match, soft_f1
from glossarysql.llm import LLM
from glossarysql.retrieval.hybrid import DEFAULT_EMBEDDER, Embedder
from glossarysql.retrieval.knowledge_base import KnowledgeBase


def load_config(path: str) -> dict:
    cfg = yaml.safe_load(open(path))
    base = cfg.pop("extends", None)
    if base:
        parent = load_config(str(paths.CONFIGS / f"{base}.yaml"))
        parent.update(cfg)
        cfg = parent
    return cfg


def n_tables(sql: str) -> int:
    try:
        return len({t.name.lower() for t in sqlglot.parse_one(sql, read="sqlite").find_all(exp.Table)})
    except Exception:  # noqa: BLE001
        return 0


def record_for(ex, fold: int, state: dict, gold_rows: list, wall: float) -> dict:
    results = state.get("results", [])
    winner = state.get("winner_idx", 0)
    win_res = results[winner] if results else {}
    pred_rows = win_res.get("rows", []) if win_res.get("ok") else []
    usage = summarize_usage(state.get("usage", []))
    cached_llm = sum(u.get("llm_seconds", 0) for u in state.get("usage", []) if u.get("cached"))
    cands = state.get("candidates", [])
    return {
        "question_id": ex.question_id, "db_id": ex.db_id, "difficulty": ex.difficulty, "fold": fold,
        "question": ex.question, "evidence": ex.evidence, "gold_sql": ex.sql,
        "pred_sql": state.get("winner_sql", ""),
        "ex": execution_match(pred_rows, gold_rows) if win_res.get("ok") else 0,
        "f1": soft_f1(pred_rows, gold_rows) if win_res.get("ok") else 0.0,
        "confidence": state.get("confidence", 0.0),
        "n_groups": len(state.get("vote_groups", [])),
        "n_ok": sum(1 for r in results if r.get("ok")),
        "n_candidates": len(cands),
        "repairs": state.get("attempts", 0),
        "winner_repaired": bool(cands and cands[winner].get("origin", "").startswith("repair")),
        "pred_error": None if win_res.get("ok") else win_res.get("error"),
        "n_rows": len(pred_rows), "empty": len(pred_rows) == 0,
        "n_tables": n_tables(state.get("winner_sql", "")),
        "sql_len": len(state.get("winner_sql", "")),
        "candidates": [{"sql": c["sql"], "origin": c.get("origin"), "ok": r.get("ok"),
                        "error": r.get("error"), "reasoning": c.get("reasoning", "")}
                       for c, r in zip(cands, results)],
        "context": state.get("context", {}),
        "trace": state.get("trace", []),
        "llm_calls": usage.get("calls", 0),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "latency": wall + cached_llm,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--limit", type=int, default=0, help="evaluate a random subset (dry run)")
    ap.add_argument("--workers", type=int, default=48)
    ap.add_argument("--folds", default="0,1")
    ap.add_argument("--name", default=None)
    ap.add_argument("--resume", action="store_true",
                    help="keep finished records, rerun only missing or crashed questions")
    args = ap.parse_args()

    cfg = load_config(args.config)
    name = args.name or cfg["name"]
    gold = load_gold()
    embedder = Embedder(DEFAULT_EMBEDDER)
    schema_emb = Embedder(cfg["schema_embedder"]) if cfg.get("schema_embedder") else embedder
    kb = KnowledgeBase(embedder, schema_emb)
    llm = LLM(cfg.get("base_url"), cfg.get("model")) if cfg.get("base_url") else LLM()
    agent = GlossarySQLAgent(kb, llm, cfg)

    jobs = []
    for fold in [int(f) for f in args.folds.split(",")]:
        _, evaluation = fold_sets(fold)
        jobs += [(fold, e) for e in evaluation]
    if args.limit:
        jobs = random.Random(0).sample(jobs, args.limit)

    paths.RUNS.mkdir(parents=True, exist_ok=True)
    out_file = paths.RUNS / f"{name}{'_dry' if args.limit else ''}.jsonl"
    kept: list[dict] = []
    if args.resume and out_file.exists():
        kept = [r for r in map(json.loads, out_file.read_text().splitlines()) if r["trace"] != ["crash"]]
        done_ids = {r["question_id"] for r in kept}
        jobs = [(f, e) for f, e in jobs if e.question_id not in done_ids]
        print(f"[{name}] resume: keeping {len(kept)}, rerunning {len(jobs)}", flush=True)

    # Build every index before timing starts, so latency measures per-question work only.
    t_warm = time.time()
    for fold, db_id in sorted({(f, e.db_id) for f, e in jobs}):
        kb.build_context("warm up", db_id, cfg, fold)
    print(f"[{name}] indexes ready in {time.time() - t_warm:.0f}s", flush=True)

    def run_one(job):
        fold, ex = job
        t0 = time.perf_counter()
        try:
            state = agent.run(ex.question, ex.db_id, fold=fold, evidence=ex.evidence)
        except Exception:  # noqa: BLE001 - one failure must not stop a 500-question run
            state = {"winner_sql": "", "results": [], "trace": ["crash"],
                     "candidates": [], "usage": [], "error": traceback.format_exc()}
            print(state["error"], flush=True)
        return record_for(ex, fold, state, gold[ex.question_id], time.perf_counter() - t0)

    t_start = time.time()
    records = list(kept)
    with ThreadPoolExecutor(args.workers) as pool, open(out_file, "w") as f:
        for rec in kept:
            f.write(json.dumps(rec, default=str) + "\n")
        futures = [pool.submit(run_one, j) for j in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            rec = fut.result()
            records.append(rec)
            f.write(json.dumps(rec, default=str) + "\n")
            if i % 50 == 0 or i == len(jobs):
                acc = sum(r["ex"] for r in records) / len(records)
                print(f"[{name}] {i}/{len(jobs)} EX={acc:.3f} elapsed={time.time() - t_start:.0f}s",
                      flush=True)
    embedder.save()
    if schema_emb is not embedder:
        schema_emb.save()
    acc = sum(r["ex"] for r in records) / len(records)
    toks = sum(r["prompt_tokens"] + r["completion_tokens"] for r in records) / len(records)
    print(f"DONE {name}: n={len(records)} EX={acc:.4f} tokens/q={toks:.0f} -> {out_file}")


if __name__ == "__main__":
    main()
