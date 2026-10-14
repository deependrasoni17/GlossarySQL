#!/bin/bash
# Run an experiment config inside the GPU job allocation (CPU side):
#   srun --jobid=<id> --overlap -n1 scripts/run_eval.sh configs/E.yaml [extra args]
P=/scratch/m25csa016/glossarysql
export PYTHONNOUSERSITE=1 HF_HOME=/scratch/m25csa016/hf_cache HF_HUB_OFFLINE=1 PYTHONPATH=$P/src
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
cd $P && exec $P/envs/app/bin/python -m glossarysql.eval.run --config "$@"
