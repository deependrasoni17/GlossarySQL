#!/bin/bash
# Run several configs one after another inside the allocation: scripts/chain.sh <jobid> <workers> A B C ...
P=/scratch/m25csa016/glossarysql
JOB=$1; W=$2; shift 2
for c in "$@"; do
  srun --jobid=$JOB --overlap -n1 $P/scripts/run_eval.sh configs/$c.yaml --workers $W > $P/logs/run_$c.log 2>&1
done
