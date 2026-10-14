#!/bin/bash
# Extension A: fine-tune the schema retriever on GPU1 of the allocation.
P=/scratch/m25csa016/glossarysql
export PYTHONNOUSERSITE=1 HF_HOME=/scratch/m25csa016/hf_cache HF_HUB_OFFLINE=1 PYTHONPATH=$P/src
export CUDA_VISIBLE_DEVICES=1 TOKENIZERS_PARALLELISM=false WANDB_DISABLED=true
cd $P && exec $P/envs/serve2/bin/python -m glossarysql.training.finetune "$@"
