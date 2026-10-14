#!/bin/bash
#SBATCH --job-name=gsql-vllm
#SBATCH --partition=mtech
#SBATCH --qos=mtech
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH --time=08:00:00
#SBATCH --output=/scratch/m25csa016/glossarysql/logs/vllm_%j.log
# Holds 2 GPUs for the whole session: GPU0 serves the LLM through vLLM's
# OpenAI-compatible API; GPU1 is free for embedding fine-tuning (Extension A).
# Evaluation runs inside this allocation with `srun --jobid=<id> --overlap`.
# MODEL / TP / GPUS can be overridden at submit time with --export.

P=/scratch/m25csa016/glossarysql
MODEL=${MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}
TP=${TP:-1}
GPUS=${GPUS:-0}
PORT=${PORT:-8000}
export PYTHONNOUSERSITE=1 HF_HOME=/scratch/m25csa016/hf_cache HF_HUB_OFFLINE=1 VLLM_NO_USAGE_STATS=1
nvidia-smi --query-gpu=index,name,memory.total --format=csv
echo "$(hostname):$PORT $MODEL" > $P/logs/vllm_server.txt
CUDA_VISIBLE_DEVICES=$GPUS $P/envs/serve/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --served-model-name "$MODEL" --host 0.0.0.0 --port $PORT \
  --tensor-parallel-size $TP --dtype auto --max-model-len 16384 \
  --gpu-memory-utilization 0.90 --enable-prefix-caching --max-num-seqs 128 --seed 0 \
  --disable-log-requests &
VLLM_PID=$!
# Keep the allocation alive even if the server is restarted by hand.
wait $VLLM_PID
sleep infinity
