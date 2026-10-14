"""Second safety layer: read-only SQLite execution with a time limit and a row cap."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExecResult:
    rows: list[tuple] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    error: str | None = None
    elapsed: float = 0.0
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


def connect_readonly(db_file: str | Path) -> sqlite3.Connection:
    # mode=ro refuses writes at the file level; immutable=1 skips locking because
    # nothing writes these files. query_only is a third, connection-level guard.
    uri = f"file:{Path(db_file).resolve()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("PRAGMA query_only = ON")
    conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
    return conn


def execute_sql(
    db_file: str | Path, sql: str, timeout_s: float = 30.0, max_rows: int = 100_000
) -> ExecResult:
    start = time.perf_counter()
    deadline = start + timeout_s
    conn = None
    try:
        conn = connect_readonly(db_file)
        # Returning non-zero from the progress handler aborts the running query.
        conn.set_progress_handler(lambda: int(time.perf_counter() > deadline), 200_000)
        cur = conn.execute(sql)
        rows = cur.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        cols = [d[0] for d in (cur.description or [])]
        return ExecResult(rows[:max_rows], cols, None, time.perf_counter() - start, truncated)
    except sqlite3.OperationalError as e:
        msg = str(e)
        if msg == "interrupted":
            msg = f"query timed out after {timeout_s:.0f}s"
        return ExecResult(error=msg, elapsed=time.perf_counter() - start)
    except Exception as e:  # noqa: BLE001 - any failure is reported back to the agent
        return ExecResult(error=f"{type(e).__name__}: {e}", elapsed=time.perf_counter() - start)
    finally:
        if conn is not None:
            conn.close()
