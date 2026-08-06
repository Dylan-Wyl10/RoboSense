#!/bin/bash
# Post-farm chain for the mod-96 re-run (YIL-125 r4): train 3 seeds ->
# aggregate + curve -> sweeps -> label stats. Idempotent like run_pipeline.
cd "$(dirname "$0")" || exit 1
source ~/anaconda3/etc/profile.d/conda.sh
conda activate torchnn
set -e
./run_pipeline.sh train
./run_pipeline.sh eval
python sweep_budget.py 2>&1 | grep -vE "Set parameter|Academic license" | tee sweep_budget_mod.log
python sweep_alpha.py  2>&1 | grep -vE "Set parameter|Academic license" | tee sweep_alpha_mod.log
python kc_stats.py
echo "AFTER-FARM CHAIN COMPLETE $(date)"
