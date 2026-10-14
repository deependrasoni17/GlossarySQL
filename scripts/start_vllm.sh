#!/bin/bash
# Start a vLLM OpenAI-compatible server inside an existing GPU allocation:
#   srun --jobid=<id> --overlap -n1 scripts/start_vllm.sh <model> <gpus> <port> <tp> [mem_util]
P=/scratch/m25csa016/glossarysql
MODEL=${1:-Qwen/Qwen2.5-Coder-7B-Instruct}
GPUS=${2:-0}
PORT=${3:-8000}
TP=${4:-1}
MEM=${5:-0.60}
export PYTHONNOUSERSITE=1 HF_HOME=/scratch/m25csa016/hf_cache HF_HUB_OFFLINE=1 VLLM_NO_USAGE_STATS=1
export CUDA_VISIBLE_DEVICES=$GPUS
echo "$(hostname):$PORT $MODEL" > $P/logs/vllm_server_$PORT.txt
exec $P/envs/serve2/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --served-model-name "$MODEL" --host 0.0.0.0 --port "$PORT" \
  --tensor-parallel-size "$TP" --dtype auto --max-model-len 32768 \
  --gpu-memory-utilization "$MEM" --enable-prefix-caching --max-num-seqs 256 --seed 0
