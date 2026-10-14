"""Loading BIRD Mini-Dev and the fixed knowledge/evaluation split.

Each database's questions are split in half, stratified by difficulty, into
halves "A" and "B". Fold 0 uses A as the knowledge split (glossary + solved
examples) and evaluates on B; fold 1 swaps them, so every question is evaluated
exactly once and never sees its own hint or its own solved SQL.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass

from glossarysql import paths

SEED = 42


@dataclass(frozen=True)
class Example:
    question_id: int
    db_id: str
    question: str
    evidence: str
    sql: str
    difficulty: str


def load_minidev() -> list[Example]:
    raw = json.loads(paths.MINIDEV_JSON.read_text())
    return [
        Example(r["question_id"], r["db_id"], r["question"], r.get("evidence", "") or "",
                r["SQL"], r["difficulty"])
        for r in raw
    ]


def make_split(examples: list[Example], seed: int = SEED) -> dict[int, str]:
    rng = random.Random(seed)
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for ex in examples:
        groups[(ex.db_id, ex.difficulty)].append(ex.question_id)
    half: dict[int, str] = {}
    # Alternate the starting half per group so odd-sized groups do not all favour "A".
    flip = 0
    for key in sorted(groups):
        ids = sorted(groups[key])
        rng.shuffle(ids)
        for i, qid in enumerate(ids):
            half[qid] = "AB"[(i + flip) % 2]
        flip ^= len(ids) % 2
    return half


def load_split() -> dict[int, str]:
    if not paths.SPLIT_FILE.exists():
        half = make_split(load_minidev())
        paths.SPLIT_FILE.write_text(json.dumps(
            {"seed": SEED, "half": {str(k): v for k, v in sorted(half.items())}}, indent=0))
    data = json.loads(paths.SPLIT_FILE.read_text())
    return {int(k): v for k, v in data["half"].items()}


def fold_sets(fold: int, examples: list[Example] | None = None) -> tuple[list[Example], list[Example]]:
    """Return (knowledge, evaluation) examples for fold 0 or 1."""
    examples = examples or load_minidev()
    half = load_split()
    k_half = "A" if fold == 0 else "B"
    knowledge = [e for e in examples if half[e.question_id] == k_half]
    evaluation = [e for e in examples if half[e.question_id] != k_half]
    return knowledge, evaluation
