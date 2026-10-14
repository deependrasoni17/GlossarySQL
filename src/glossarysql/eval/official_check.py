"""Score a run with BIRD Mini-Dev's *official* evaluation_ex.py and compare with our EX.

    python -m glossarysql.eval.official_check --run E2_full --num-cpus 16
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from glossarysql import paths
from glossarysql.data import load_minidev

OFFICIAL = paths.RAW / "bird_mini_dev_repo" / "evaluation"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="E2_full")
    ap.add_argument("--num-cpus", type=int, default=16)
    args = ap.parse_args()
    exs = load_minidev()
    rows = {json.loads(line)["question_id"]: json.loads(line)
            for line in (paths.RUNS / f"{args.run}.jsonl").read_text().splitlines()}
    tmp = Path(tempfile.mkdtemp(prefix="bird_official_"))
    # Official formats: predictions as {idx: "SQL\t----- bird -----\tdb"}, gold as "SQL\tdb" lines.
    pred = {str(i): " ".join(rows[e.question_id]["pred_sql"].split()) + f"\t----- bird -----\t{e.db_id}"
            for i, e in enumerate(exs)}
    (tmp / "pred.json").write_text(json.dumps(pred))
    (tmp / "gold.sql").write_text("\n".join(f"{' '.join(e.sql.split())}\t{e.db_id}" for e in exs) + "\n")
    (tmp / "diff.jsonl").write_text("\n".join(json.dumps({"difficulty": e.difficulty}) for e in exs) + "\n")
    cmd = [sys.executable, str(OFFICIAL / "evaluation_ex.py"), "--predicted_sql_path", str(tmp / "pred.json"),
           "--ground_truth_path", str(tmp / "gold.sql"), "--db_root_path", str(paths.DB_DIR) + "/",
           "--num_cpus", str(args.num_cpus), "--meta_time_out", "30.0", "--diff_json_path",
           str(tmp / "diff.jsonl"), "--sql_dialect", "SQLite", "--output_log_path", str(tmp / "log.txt")]
    proc = subprocess.run(cmd, cwd=OFFICIAL, capture_output=True, text=True)
    out = proc.stdout
    if proc.returncode:
        print(proc.stderr[-2000:])
    print(out[-1200:])
    ours = 100 * sum(rows[e.question_id]["ex"] for e in exs) / len(exs)
    m = re.findall(r"\nEX\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", out)
    official = float(m[-1][-1]) if m else float("nan")
    result = {"run": args.run, "our_ex": round(ours, 2), "official_ex": official}
    (paths.TABLES / f"official_check_{args.run}.json").write_text(json.dumps(result, indent=2))
    print(result)


if __name__ == "__main__":
    main()
