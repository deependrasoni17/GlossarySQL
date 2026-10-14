"""LLM access through LangChain's OpenAI-compatible client, pointed at a local vLLM server.

Every call is cached on disk, keyed by the exact request (model, messages,
temperature, n, max_tokens, seed), so reruns cost nothing and are reproducible.
The cache also stores the original latency and token counts, so cost and
latency metrics stay honest when a run is replayed from cache.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from glossarysql import paths


@dataclass
class LLMResponse:
    texts: list[str]
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    cached: bool


class DiskCache:
    def __init__(self, path=paths.LLM_CACHE):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False, timeout=60)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS calls (key TEXT PRIMARY KEY, value TEXT)")
        self.lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT value FROM calls WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, value: dict) -> None:
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO calls VALUES (?,?)", (key, json.dumps(value)))
            self.conn.commit()


def server_endpoint() -> tuple[str, str]:
    """(base_url, model) from env vars or the file written by the vLLM Slurm job."""
    base = os.environ.get("GLOSSARYSQL_LLM_BASE_URL")
    model = os.environ.get("GLOSSARYSQL_LLM_MODEL")
    if base and model:
        return base, model
    hostport, served = paths.SERVER_FILE.read_text().split()[:2]
    return f"http://{hostport}/v1", served


class LLM:
    def __init__(self, base_url: str | None = None, model: str | None = None,
                 cache: DiskCache | None = None, timeout: float = 600):
        if base_url is None or model is None:
            base_url, model = server_endpoint()
        self.base_url, self.model = base_url, model
        self.cache = cache or DiskCache()
        self.timeout = timeout
        self._clients: dict[tuple, ChatOpenAI] = {}
        self._lock = threading.Lock()

    def _client(self, temperature: float, n: int, max_tokens: int, seed: int | None) -> ChatOpenAI:
        key = (temperature, n, max_tokens, seed)
        with self._lock:
            if key not in self._clients:
                self._clients[key] = ChatOpenAI(
                    base_url=self.base_url, api_key=os.environ.get("OPENAI_API_KEY", "EMPTY"),
                    model=self.model, temperature=temperature, n=n, max_tokens=max_tokens,
                    seed=seed, timeout=self.timeout, max_retries=3)
            return self._clients[key]

    def chat(self, system: str, user: str, temperature: float = 0.0, n: int = 1,
             max_tokens: int = 1024, seed: int | None = 0) -> LLMResponse:
        messages: list[BaseMessage] = [SystemMessage(system), HumanMessage(user)]
        key = hashlib.sha256(json.dumps(
            [self.model, system, user, temperature, n, max_tokens, seed]).encode()).hexdigest()
        hit = self.cache.get(key)
        if hit is not None:
            return LLMResponse(hit["texts"], hit["pt"], hit["ct"], hit["sec"], True)
        t0 = time.perf_counter()
        result = self._client(temperature, n, max_tokens, seed).generate([messages])
        sec = time.perf_counter() - t0
        texts = [g.text for g in result.generations[0]]
        usage = (result.llm_output or {}).get("token_usage", {}) or {}
        pt, ct = int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
        self.cache.put(key, {"texts": texts, "pt": pt, "ct": ct, "sec": sec})
        return LLMResponse(texts, pt, ct, sec, False)
