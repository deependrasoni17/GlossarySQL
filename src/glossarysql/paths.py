"""Central file locations. Everything lives under the project root on scratch."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("GLOSSARYSQL_ROOT", Path(__file__).resolve().parents[2]))

DATA = ROOT / "data"
RAW = DATA / "raw"
MINIDEV_JSON = RAW / "minidev_hf" / "data" / "mini_dev_sqlite-00000-of-00001.json"
DB_DIR = RAW / "bird_dev" / "dev_20240627" / "dev_databases"
TRAIN_DIR = RAW / "bird_train" / "train"
SPLIT_FILE = DATA / "split.json"
INDEX_DIR = DATA / "index"

CACHE = ROOT / "cache"
LLM_CACHE = CACHE / "llm_cache.sqlite"
MODELS = ROOT / "models"
RESULTS = ROOT / "results"
RUNS = RESULTS / "runs"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"
CONFIGS = ROOT / "configs"
SERVER_FILE = ROOT / "logs" / "vllm_server.txt"  # "host:port model" written by the server job


def db_path(db_id: str) -> Path:
    return DB_DIR / db_id / f"{db_id}.sqlite"


def description_dir(db_id: str) -> Path:
    return DB_DIR / db_id / "database_description"
