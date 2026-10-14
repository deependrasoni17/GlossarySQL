# GlossarySQL - working notes for Claude Code sessions

Agentic text-to-SQL on BIRD Mini-Dev that *retrieves* business definitions from a glossary
instead of using the benchmark's hand-written hints. README.md has the results; DECISIONS.md has
the design log (read it before changing anything structural).

## Layout
- `src/glossarysql/` - `sql/` (guard, read-only executor, normalisation), `ingest/` (schema, values,
  glossary), `retrieval/` (hybrid BM25+FAISS+RRF, value matching, KnowledgeBase), `agent/`
  (LangGraph graph + prompts), `calibration/ltt.py`, `eval/` (run, metrics, stats, report),
  `training/` (Extension A fine-tuning, Extension B confidence model), `llm.py` (cached LLM client).
- `configs/*.yaml` - one per experiment, `extends:` a parent. A-F are the planned ablation;
  `*_full` use the full schema; `*_32b` use Qwen2.5-Coder-32B-AWQ; `E_ft` uses the fine-tuned retriever.
- `app/app.py` - Gradio demo. `tests/` - pytest. `results/` - tables/figures (runs/*.jsonl are gitignored).

## Environment (IITJ HPC, user m25csa016)
- Project lives on scratch: `/scratch/m25csa016/glossarysql` (`~/glossarysql` is a symlink). Home quota is nearly full.
- Always `export PYTHONNOUSERSITE=1` (packages in `~/.local` break the envs) and `HF_HOME=/scratch/m25csa016/hf_cache`.
- `envs/app` (py3.11, torch 2.5 CPU use, LangChain/LangGraph, faiss, gradio) runs the agent, eval and app.
- `envs/serve2` (py3.12, vLLM 0.10.2, torch 2.8 cu128, sentence-transformers 5) serves LLMs and trains on GPU.
  `envs/serve` (vLLM 0.7.3) only works on the A30 nodes (cn01-05), not on Blackwell cn07.
- Slurm: partition/QOS `mtech`, max 2 GPUs and 2 jobs. Hold one 2-GPU job (`scripts/serve_vllm.sbatch`)
  and run work inside it: `srun --jobid=<id> --overlap -n1 scripts/start_vllm.sh <model> <gpu> <port>`,
  `scripts/run_eval.sh configs/E.yaml`, `scripts/chain.sh <id> <workers> A B C`.
- The LLM endpoint is read from `logs/vllm_server.txt` ("host:port model") or
  `GLOSSARYSQL_LLM_BASE_URL` + `GLOSSARYSQL_LLM_MODEL`. All LLM calls are cached in `cache/llm_cache.sqlite`.

## Commands
- Tests: `envs/app/bin/python -m pytest -q`
- Rebuild schema/value indexes: `python -m glossarysql.ingest.schema`
- One experiment: `python -m glossarysql.eval.run --config configs/E.yaml [--limit 20]`
- Retrieval metrics: `python -m glossarysql.eval.retrieval_metrics --schema-embedder models/bge-small-bird-schema/best`
- Extension B: `python -m glossarysql.training.confidence --run E_full`
- All tables/figures: `python -m glossarysql.eval.report`
