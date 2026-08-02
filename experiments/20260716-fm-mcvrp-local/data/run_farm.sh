#!/bin/bash
source ~/anaconda3/etc/profile.d/conda.sh && conda activate torchnn
cd ~/Research/Route_TSC_CART
D=experiments/20260716-fm-mcvrp-local/data
python3 -m neural_route.bigrid_datagen --n 5000 --out $D --seed 0     --workers 12 --mode train
python3 -m neural_route.bigrid_datagen --n 500  --out $D --seed 10000 --workers 12 --mode test
python3 -m neural_route.bigrid_datagen --n 300  --out $D --seed 20000 --workers 12 --mode zeroshot
python3 -m neural_route.bigrid_datagen --n 300  --out $D --seed 30000 --workers 12 --mode vextrap
echo "FARM COMPLETE $(date)"
