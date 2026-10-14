"""Extension A: contrastive fine-tuning of the schema retriever on BIRD train.

Pairs are (question, column document) for every column the gold SQL uses; a
column from the same database that the query does not use is attached as a hard
negative. MultipleNegativesRankingLoss (InfoNCE) also treats every other column
in the batch as a negative. BIRD-train databases never overlap with Mini-Dev's,
so recall on Mini-Dev measures generalisation to unseen databases.

    python -m glossarysql.training.finetune --epochs 2
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict

from glossarysql import paths
from glossarysql.ingest.schema import column_docs_from_tables, load_tables_json
from glossarysql.retrieval.hybrid import BGE_QUERY_PREFIX, DEFAULT_EMBEDDER
from glossarysql.training.gold_columns import gold_columns


def build_pairs(seed: int = 0, holdout_frac: float = 0.1):
    rng = random.Random(seed)
    tables = load_tables_json(paths.TRAIN_DIR / "train_tables.json")
    train = json.loads((paths.TRAIN_DIR / "train.json").read_text())
    docs_by_db = {}
    for db_id, t in tables.items():
        docs = column_docs_from_tables(t, paths.TRAIN_DIR / "train_databases" / db_id / "database_description")
        docs_by_db[db_id] = {d.key: d for d in docs}
    # Hold out whole questions (not pairs) to pick the epoch.
    qids = list(range(len(train)))
    rng.shuffle(qids)
    held = set(qids[: int(len(qids) * holdout_frac)])
    triplets, holdout, skipped = [], [], 0
    for i, ex in enumerate(train):
        docs = docs_by_db.get(ex["db_id"])
        if not docs:
            skipped += 1
            continue
        schema = defaultdict(set)
        for d in docs.values():
            schema[d.table].add(d.column)
        gold = [k for k in gold_columns(ex["SQL"], schema) if k in docs]
        if not gold:
            skipped += 1
            continue
        if i in held:
            holdout.append({"question": ex["question"], "db_id": ex["db_id"], "gold": gold})
            continue
        gold_tables = {k.split(".", 1)[0] for k in gold}
        # Hard negatives: unused columns, preferring the tables the query touches.
        near = [k for k in docs if k not in gold and k.split(".", 1)[0] in gold_tables]
        far = [k for k in docs if k not in gold]
        for g in gold:
            pool = near if near and rng.random() < 0.7 else far
            if not pool:
                continue
            neg = rng.choice(pool)
            triplets.append((BGE_QUERY_PREFIX + ex["question"], docs[g].retrieval_text(),
                             docs[neg].retrieval_text()))
    return triplets, holdout, docs_by_db, skipped


def recall_at_k(model, holdout, docs_by_db, ks=(5, 10, 15)) -> dict:
    import numpy as np

    by_db = defaultdict(list)
    for h in holdout:
        by_db[h["db_id"]].append(h)
    hits = {k: [] for k in ks}
    for db_id, items in by_db.items():
        keys = list(docs_by_db[db_id])
        dv = model.encode([docs_by_db[db_id][k].retrieval_text() for k in keys], normalize_embeddings=True,
                          batch_size=256, show_progress_bar=False)
        qv = model.encode([BGE_QUERY_PREFIX + h["question"] for h in items], normalize_embeddings=True,
                          batch_size=256, show_progress_bar=False)
        order = np.argsort(-(qv @ dv.T), axis=1)
        for h, row in zip(items, order):
            for k in ks:
                top = {keys[j] for j in row[:k]}
                hits[k].append(len(top & set(h["gold"])) / len(h["gold"]))
    return {f"recall@{k}": float(np.mean(v)) for k, v in hits.items()}


def main() -> None:
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformer,
        SentenceTransformerTrainer,
        SentenceTransformerTrainingArguments,
    )
    from sentence_transformers.losses import MultipleNegativesRankingLoss
    from sentence_transformers.training_args import BatchSamplers

    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=3e-5)
    args = ap.parse_args()

    triplets, holdout, docs_by_db, skipped = build_pairs()
    print(f"triplets={len(triplets)} holdout_questions={len(holdout)} skipped={skipped}", flush=True)
    ds = Dataset.from_dict({"anchor": [t[0] for t in triplets], "positive": [t[1] for t in triplets],
                            "negative": [t[2] for t in triplets]})
    model = SentenceTransformer(DEFAULT_EMBEDDER, device="cuda")
    report = {"base": recall_at_k(model, holdout, docs_by_db)}
    print("base holdout", report["base"], flush=True)
    out_root = paths.MODELS / "bge-small-bird-schema"
    best, best_epoch = report["base"]["recall@10"], 0
    for epoch in range(1, args.epochs + 1):
        targs = SentenceTransformerTrainingArguments(
            output_dir=str(out_root / "tmp"), num_train_epochs=1, per_device_train_batch_size=args.batch,
            learning_rate=args.lr, warmup_ratio=0.1 if epoch == 1 else 0.0, fp16=True,
            batch_sampler=BatchSamplers.NO_DUPLICATES, logging_steps=50, save_strategy="no",
            report_to=[], seed=epoch)
        trainer = SentenceTransformerTrainer(model=model, args=targs, train_dataset=ds.shuffle(seed=epoch),
                                             loss=MultipleNegativesRankingLoss(model))
        trainer.train()
        r = recall_at_k(model, holdout, docs_by_db)
        report[f"epoch{epoch}"] = r
        print(f"epoch {epoch} holdout", r, flush=True)
        model.save(str(out_root / f"epoch{epoch}"))
        if r["recall@10"] > best:
            best, best_epoch = r["recall@10"], epoch
    report["best_epoch"] = best_epoch
    (out_root / "train_report.json").write_text(json.dumps(report, indent=2))
    if best_epoch:
        import shutil

        shutil.copytree(out_root / f"epoch{best_epoch}", out_root / "best", dirs_exist_ok=True)
    print("best epoch", best_epoch, report, flush=True)


if __name__ == "__main__":
    main()
