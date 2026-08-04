#!/bin/bash
# End-to-end budget-conditioned pipeline, YIL-113.
#
#   ./run_pipeline.sh            full run: farm -> train(3 seeds) -> eval -> curve -> figs -> deck
#   ./run_pipeline.sh farm       labels only (resumable; safe to interrupt and re-run)
#   ./run_pipeline.sh train      training only
#   ./run_pipeline.sh eval       3-seed eval + response curve
#   ./run_pipeline.sh report     figures + deck v2
#
# Every stage is idempotent: the farm skips existing records, training overwrites its
# own checkpoints, eval/figs/deck are pure functions of what is on disk.
# Nothing here writes outside this experiment directory.

cd "$(dirname "$0")" || exit 1
source ~/anaconda3/etc/profile.d/conda.sh
conda activate torchnn
set -e

STAGE="${1:-all}"
SEEDS="0 1 2"
EPOCHS=60

farm() {
  echo "=== [1/4] label farm (resumable) ==="
  until ./run_farm.sh | tee /dev/stderr | grep -q "FARM COMPLETE"; do
    echo "--- farm interrupted, resuming ---"
  done
}

train() {
  echo "=== [2/4] training ${EPOCHS} epochs x seeds ${SEEDS} ==="
  for s in $SEEDS; do
    python budget_train.py train $EPOCHS results/budget_model_seed$s.pt $s
  done
}

evaluate() {
  echo "=== [3/4] 3-seed five-layer eval + response curve ==="
  python aggregate.py
  python budget_train.py curve results/budget_model_seed0.pt
}

report() {
  echo "=== [4/4] figures + deck ==="
  python build_figs.py
  python build_method_figs.py
  python build_deck_final.py
}

case "$STAGE" in
  farm)   farm ;;
  train)  train ;;
  eval)   evaluate ;;
  report) report ;;
  all)    farm; train; evaluate; report ;;
  *)      echo "unknown stage: $STAGE"; exit 1 ;;
esac
echo "PIPELINE STAGE '$STAGE' DONE"
