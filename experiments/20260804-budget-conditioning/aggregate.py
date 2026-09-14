"""Evaluate all seeds on all five layers, aggregate to mean +- std, and write
results.csv + agg_3seed.json."""

import csv
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from budget_train import (LAYERS, OUTD, BudgetRouteModel, eval_split)  # noqa: E402

SEEDS = [0, 1, 2]


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    per_seed = {}
    for s in SEEDS:
        model = BudgetRouteModel().to(dev)
        model.load_state_dict(torch.load(f"{OUTD}/budget_model_seed{s}.pt",
                                         weights_only=True))
        per_seed[s] = {}
        for k, (f, lab) in LAYERS.items():
            pc = f"{OUTD}/percase_{k}_seed{s}.csv" if s == 0 else None
            per_seed[s][k] = eval_split(model, f, dev, per_case=pc)
            print(f"seed{s} {k} {json.dumps(per_seed[s][k])}", flush=True)
        with open(f"{OUTD}/eval_layers_seed{s}.json", "w") as fh:
            json.dump(per_seed[s], fh, indent=1)

    agg, rows = {}, []
    for k, (f, lab) in LAYERS.items():
        g = np.array([per_seed[s][k]["mean_gap"] for s in SEEDS])
        rg = np.array([per_seed[s][k]["rel_gap"] for s in SEEDS])
        mb = np.array([per_seed[s][k]["match_or_better"] for s in SEEDS])
        ms = np.array([per_seed[s][k]["ms_per_case"] for s in SEEDS])
        feas = [per_seed[s][k]["feasible"] for s in SEEDS]
        n = per_seed[SEEDS[0]][k]["n"]
        agg[k] = dict(label=lab, n=n, feasible=min(feas),
                      feasible_all_seeds=(min(feas) == n),
                      gap_mean=float(g.mean()), gap_std=float(g.std()),
                      rel_gap_mean=float(rg.mean()), rel_gap_std=float(rg.std()),
                      match_mean=float(mb.mean()), match_std=float(mb.std()),
                      ms_per_case=float(ms.mean()))
        rows.append(dict(layer=k, description=lab, n=n,
                         feasible_min_over_seeds=min(feas),
                         gap_mean=round(float(g.mean()), 5),
                         gap_std=round(float(g.std()), 5),
                         rel_gap_pct_mean=round(100 * float(rg.mean()), 2),
                         rel_gap_pct_std=round(100 * float(rg.std()), 2),
                         match_or_better_mean=round(float(mb.mean()), 1),
                         ms_per_case=round(float(ms.mean()), 1)))
    with open(f"{OUTD}/agg_3seed.json", "w") as fh:
        json.dump(agg, fh, indent=1)
    with open(f"{os.path.dirname(OUTD)}/results_mod24.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    for r in rows:
        print(f"{r['layer']:12} n={r['n']:4} feas={r['feasible_min_over_seeds']:4} "
              f"gap={r['gap_mean']:.4f}+-{r['gap_std']:.4f} "
              f"rel={r['rel_gap_pct_mean']:.1f}%+-{r['rel_gap_pct_std']:.1f} "
              f"match={r['match_or_better_mean']}")
    print("wrote results.csv + agg_3seed.json")


if __name__ == "__main__":
    main()
