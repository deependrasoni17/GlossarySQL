#!/bin/bash
# Launch the Gradio demo inside the allocation: srun --jobid=<id> --overlap -n1 scripts/run_app.sh
P=/scratch/m25csa016/glossarysql
export PYTHONNOUSERSITE=1 HF_HOME=/scratch/m25csa016/hf_cache HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4
export GRADIO_SERVER_PORT=${GRADIO_SERVER_PORT:-7860} GRADIO_ANALYTICS_ENABLED=False
cd $P && exec $P/envs/app/bin/python app/app.py
