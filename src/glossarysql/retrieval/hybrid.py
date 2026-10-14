"""Hybrid retrieval: BM25 (exact names, codes) + dense embeddings (paraphrases),
merged with reciprocal rank fusion (RRF), which needs no weight tuning."""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from glossarysql import paths

DEFAULT_EMBEDDER = "BAAI/bge-small-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    # Split snake_case and CamelCase so "Free Meal Count" matches "FreeMealCount".
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return _TOKEN.findall(text.lower().replace("_", " "))


class Embedder:
    """sentence-transformers model with an on-disk cache keyed by text."""

    _lock = threading.Lock()

    def __init__(self, model_name: str = DEFAULT_EMBEDDER, device: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        tag = hashlib.md5(model_name.encode()).hexdigest()[:8]
        self.cache_file = paths.CACHE / f"emb_{Path(model_name).name}_{tag}.npz"
        self._cache: dict[str, np.ndarray] = {}
        if self.cache_file.exists():
            z = np.load(self.cache_file, allow_pickle=True)
            self._cache = dict(zip(z["texts"].tolist(), z["vecs"]))
        self._dirty = False

    def encode(self, texts: list[str]) -> np.ndarray:
        with self._lock:
            missing = list(dict.fromkeys(t for t in texts if t not in self._cache))
            if missing:
                vecs = self.model.encode(missing, batch_size=128, normalize_embeddings=True,
                                         show_progress_bar=False, convert_to_numpy=True)
                self._cache.update(zip(missing, vecs.astype(np.float32)))
                self._dirty = True
            return np.stack([self._cache[t] for t in texts]) if texts else np.zeros((0, 384), np.float32)

    def save(self) -> None:
        with self._lock:
            if self._dirty:
                paths.CACHE.mkdir(parents=True, exist_ok=True)
                texts = list(self._cache)
                np.savez(self.cache_file, texts=np.array(texts, dtype=object),
                         vecs=np.stack([self._cache[t] for t in texts]))
                self._dirty = False


@dataclass
class Hit:
    idx: int
    score: float  # fused RRF score
    dense: float  # cosine similarity (useful as a confidence feature)
    bm25: float


class HybridIndex:
    def __init__(self, texts: list[str], embedder: Embedder, query_prefix: str = ""):
        self.texts = texts
        self.embedder = embedder
        self.query_prefix = query_prefix
        self.bm25 = BM25Okapi([tokenize(t) or ["_"] for t in texts]) if texts else None
        vecs = embedder.encode(texts)
        self.faiss = faiss.IndexFlatIP(vecs.shape[1]) if len(texts) else None
        if self.faiss is not None:
            self.faiss.add(vecs)

    def search(self, query: str, k: int, pool: int = 50, rrf_k: int = 60) -> list[Hit]:
        if not self.texts:
            return []
        pool = min(pool, len(self.texts))
        bm = self.bm25.get_scores(tokenize(query) or ["_"])
        bm_rank = np.argsort(-bm)[:pool]
        qv = self.embedder.encode([self.query_prefix + query])
        dense_scores, dense_idx = self.faiss.search(qv, pool)
        dense_scores, dense_idx = dense_scores[0], dense_idx[0]
        dense_of = dict(zip(dense_idx.tolist(), dense_scores.tolist()))
        fused: dict[int, float] = {}
        for r, i in enumerate(bm_rank.tolist()):
            if bm[i] > 0:
                fused[i] = fused.get(i, 0) + 1 / (rrf_k + r + 1)
        for r, i in enumerate(dense_idx.tolist()):
            fused[i] = fused.get(i, 0) + 1 / (rrf_k + r + 1)
        top = sorted(fused.items(), key=lambda x: -x[1])[:k]
        out = []
        for i, s in top:
            d = dense_of.get(i)
            if d is None:
                d = float(qv[0] @ self.embedder.encode([self.texts[i]])[0])
            out.append(Hit(i, s, d, float(bm[i])))
        return out
