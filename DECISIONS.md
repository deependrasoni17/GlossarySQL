# Decisions log

What was chosen, what failed, and why. Times are from the build session (15 Oct 2026, IST).

## Infrastructure

- **Everything on `/scratch`, not home.** Home has ~26 GB free under a 70 GB quota and the
  filesystem is 96% full; scratch has ~127 GB free under a 200 GB quota. `~/glossarysql` is a
  symlink to `/scratch/m25csa016/glossarysql`.
- **Local open-weight LLM instead of an API.** No API keys were available and the cluster has GPUs,
  so the LLM is served by vLLM (OpenAI-compatible API) and called through LangChain's `ChatOpenAI`.
  Swapping to a hosted API is a config change (`base_url`, `model`). Cost is therefore reported in
  tokens and LLM calls, not dollars.
- **One Slurm job holds 2 GPUs for the whole session** (`scripts/serve_vllm.sbatch`): GPU0 serves the
  LLM, GPU1 trains Extension A. Evaluation runs inside the same allocation with
  `srun --jobid --overlap`, because the QOS allows only 2 jobs.
- **Failed: vLLM 0.7.3 on the allocated node.** The job landed on `cn07` (2x RTX PRO 6000
  Blackwell, 96 GB), not the A30 nodes. vLLM 0.7.3 / torch 2.5 has no sm_120 kernels
  ("no kernel image is available"). Fixed by a second env with vLLM 0.10.2 / torch 2.8 cu128.
- **Failed: environment builds.** Conda's default channels need a ToS acceptance in
  non-interactive mode (switched to `conda-forge`); two parallel `conda create` runs raced on the
  same package cache; packages in `~/.local` leaked into the envs and broke torch
  (fixed with `PYTHONNOUSERSITE=1`); unpinned `transformers` 5.x needs a newer torch (pinned 4.48
  in the app env and 4.56 in the vLLM env).
- **Data mirrors.** The official Aliyun download URLs time out from this network. Mini-Dev
  questions come from `birdsql/bird_mini_dev` (HF), the dev databases + description CSVs from the
  official `dev.zip` mirrored at `HAL-9001/bird-dev`, and BIRD train from `mayurisp279/birdbench_1.0`
  (official `train.zip`; only `train.json`, `train_tables.json` and the description CSVs are
  extracted - the 33 GB of training databases are not needed).

## Data and evaluation protocol

- **Two-fold split instead of one 250/250 split.** Each database's questions are split in half,
  stratified by difficulty (seed 42, saved in `data/split.json`). Fold 0 uses half A as knowledge and
  evaluates half B; fold 1 swaps them. Every one of the 500 questions is evaluated exactly once, which
  narrows confidence intervals; a question never sees its own hint or SQL.
- **Gold sanity check.** All 500 gold queries execute and score 100% against themselves. Question
  701 takes ~4 minutes in SQLite, so the gold cache uses a 10-minute timeout; predictions use the
  official 30 s timeout.
- **Metrics re-implemented from the official scripts** (`evaluation_ex.py`, `evaluation_f1.py`), so
  per-question scores can be stored for bootstrap and McNemar tests.

## Retrieval

- **Hybrid BM25 + dense with reciprocal rank fusion everywhere.** Measured on Mini-Dev column
  recall@15: hybrid 66.6%, dense 63.0%, BM25 61.7%.
- **Retrieval text has no sample values**, so the same document format exists for BIRD-train
  databases (whose SQLite files were not downloaded) and Extension A trains on what it is tested on.
  Samples are still shown to the LLM in the prompt.
- **Key expansion.** After the top-15 columns, primary keys, foreign keys and the columns they
  join to are added for every involved table, plus columns from value matches.
- **Glossary entries are the hint split on semicolons outside quotes**, de-duplicated, with
  pointers to the source questions. No LLM rewriting: it costs calls and risks changing meaning.
- **Value matching**: exact n-gram lookup, then `rapidfuzz` ratio >= 90 for phrases of 5+ chars;
  numeric/date-like values and long free-text columns are excluded.

## Agent

- **Context placement is identical for E and F.** Retrieved definitions (E) and the gold hint (F)
  go into the same "Business definitions" prompt section, so the comparison isolates the knowledge
  source.
- **Voting compares result sets** (sorted, de-duplicated, floats rounded to 4 places), the same
  notion of equality as BIRD's EX. Ties prefer non-empty results, then the earliest candidate.
- **Repair** fixes errors and guard rejections only (not empty results), at temperature 0, at most 2
  rounds; identical failing queries are repaired once.
- **Two safety layers**: `sqlglot` + keyword guard (single SELECT/WITH, no write/DDL/PRAGMA/ATTACH),
  then a `mode=ro&immutable=1` SQLite connection with `PRAGMA query_only`, a progress-handler
  timeout and a row cap. When sqlglot cannot parse valid SQLite, the keyword checks plus the
  read-only connection decide (tested in `tests/test_sql.py`).
- **Extra ablations Cg and Cf** (single-shot + glossary / + gold hint) were added because they cost
  little with a local model and separate the glossary's effect from the agent loop's.
- **Latency** is measured after a warm-up that builds all indexes, under 64 concurrent questions
  sharing one vLLM server; cached LLM calls replay their original latency.

## Findings that changed the plan (made after the first A-F results)

- **Top-15 schema retrieval hurt (B 31.8% < A 37.6% EX).** In B, all gold columns were in the
  context for only 69% of questions. On those, B matched A (42.5% vs 41.3%); on the rest it
  collapsed (7.8% vs 29.2%). Offline, k=30 reaches 82% full coverage and two-stage table retrieval
  87%, but both still lose columns. Mini-Dev databases have 77 columns on average and fit easily in
  a 32k context, so instead of tuning k on the evaluation set I added a full-schema family
  (`D_full`, `E_full`, `F_full`). The pre-planned A-F (k=15) rows are kept and reported as-is.
- **Retrieved glossary at top-3 did not help (E 45.0% vs D 45.2%).** The needed definition exists
  for ~71% of questions, but the top-3 contained it for only 48%. Even then the gain was +1.7 points,
  and irrelevant definitions cost -1.9 points elsewhere.
- **Improved glossary retrieval (E2), chosen without the evaluation half.** Variants were compared by
  leave-one-out on the *knowledge* half (each knowledge question retrieves from the glossary minus
  its own entries; success = the retrieved entries match one of its own definitions at cosine >= 0.85).
  Indexing each definition together with the questions it was written for ("def+q") and
  retrieving 5 raised any-definition recall from 47% to 64% (share of definitions recovered: 28% to 42%).
  E (top-3, definition text only) remains the pre-registered row; E2 is reported separately as a
  post-hoc improvement.
- **Guard bug found during the runs:** sqlglot raises `TokenError` (not `ParseError`) on an
  unterminated identifier, which crashed the guard node for 1-2 questions per run. Fixed (catch
  `SqlglotError`, regression test added); affected runs were completed with `--resume`, which reruns
  only crashed questions (LLM calls come from the cache).
- **Learn-then-Test grid (bug found and fixed).** The first version used score quantiles as the grid
  for learned confidence scores. The strictest threshold then answered ~1 calibration question,
  its p-value was ~0.8, and fixed-sequence testing stopped at once, so the agent abstained on
  everything. Now the grid is fixed in advance (vote levels 1.0..0.2; probabilities 0.95..0.05 in
  steps of 0.05), and thresholds answering fewer than 20 calibration questions are skipped. The
  skip depends only on n; given n, errors are Binomial(n, risk), so each test run stays valid.
  Unit test added.
- **Calibration target.** Unanimous 5/5 votes of E2_full are right only 75.7% of the time (218
  questions), so alpha=0.1 and alpha=0.2 cannot be certified with ~250 calibration questions; this
  is reported as a finding. alpha=0.25 was added to the planned {0.1, 0.2, 0.3} to show the trade-off.
  Extension B scores are out-of-fold predictions from 5-fold CV over all 500 questions, so the
  model that scores a test question was trained partly on other test questions of that split (never
  on the question itself).
- **Oracle glossary retrieval (analysis only, `E_oracle_full`).** Picks the 5 glossary entries closest
  to the question's hidden hint. This splits the gap: F_full - E_oracle_full is the part the glossary
  cannot cover (coverage), and E_oracle_full - E2_full is the part a better retriever could still win.
- **Demo knowledge.** The demo indexes all 500 Mini-Dev questions as knowledge, but excludes a
  question's own glossary entries and solved example when that exact question is asked, so the
  example questions do not answer themselves.
- **Official-script cross-check.** BIRD's unmodified `evaluation_ex.py` scores E2_full at 50.00% vs our
  50.20%. The only difference is q701: our prediction is correct and runs in 0.1 s, but the official
  script runs gold and prediction under one 30 s limit, and the gold query alone needs ~4 minutes.
  Our gold results are cached with a 10-minute limit, so that question is scored on its merits.
