"""Execute and cache gold results once; every scoring run reuses them."""

from __future__ import annotations

import pickle
from concurrent.futures import ThreadPoolExecutor

from glossarysql import paths
from glossarysql.data import load_minidev
from glossarysql.sql.executor import execute_sql

GOLD_CACHE = paths.CACHE / "gold_results.pkl"


def build_gold_cache(workers: int = 16) -> dict[int, list[tuple]]:
    examples = load_minidev()

    def run(ex):
        res = execute_sql(paths.db_path(ex.db_id), ex.sql, timeout_s=600, max_rows=10_000_000)
        return ex.question_id, res

    out, failures, slow = {}, [], []
    with ThreadPoolExecutor(workers) as pool:
        for qid, res in pool.map(run, examples):
            if not res.ok:
                failures.append((qid, res.error))
            out[qid] = res.rows
            if res.elapsed > 5:
                slow.append((qid, round(res.elapsed, 1)))
    paths.CACHE.mkdir(parents=True, exist_ok=True)
    GOLD_CACHE.write_bytes(pickle.dumps(out))
    print(f"gold executed: {len(out)}  failures: {failures}  slow(>5s): {slow}")
    return out


def load_gold() -> dict[int, list[tuple]]:
    if not GOLD_CACHE.exists():
        return build_gold_cache()
    return pickle.loads(GOLD_CACHE.read_bytes())


if __name__ == "__main__":
    from glossarysql.eval.metrics import execution_match

    gold = build_gold_cache()
    ex = sum(execution_match(r, r) for r in gold.values()) / len(gold)
    empty = sum(1 for r in gold.values() if not r)
    print(f"gold-vs-gold EX = {ex:.3f}; empty gold results: {empty}")
