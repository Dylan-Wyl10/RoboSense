#!/bin/bash
# Budget label farm — resumable. Re-run until it prints "FARM COMPLETE".
# Every mode skips already-written records, so interrupting is safe.
cd "$(dirname "$0")"
source ~/anaconda3/etc/profile.d/conda.sh
conda activate torchnn
D=data_mod
W=15

run() {  # mode n seed
  python budget_datagen.py --mode "$1" --n "$2" --seed "$3" --out "$D" --workers $W \
    2>&1 | grep -vE "Set parameter|Academic license"
}

run train      8000 0      || exit 1
run test        800 10000  || exit 1
run zeroshot    400 20000  || exit 1
run vextrap     400 30000  || exit 1
run rhointerp   400 40000  || exit 1
run rhoextrap   300 50000  || exit 1
run curve        60 60000  || exit 1
echo "FARM COMPLETE $(date)"
