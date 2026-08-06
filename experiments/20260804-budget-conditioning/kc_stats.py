"""Label-set statistics for the mod-96 farm (YIL-125 r4).

Prints per-shard and aggregate: solve times, cap hits, the K/C (coverage vs
cost) accounting the proof-I slide quotes, and the maximum token-sequence
length (sum of route lens + V SEPs + EOS + BOS) the model must fit
(budget_train.MAX_LEN). Writes results_mod/kc_stats.json.
"""

import glob
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
out = {}
all_ratio, all_zero, all_seq, all_solve = [], 0, [], []
n_tot = 0
for path in sorted(glob.glob(f"{HERE}/data_mod/*.jsonl")):
    name = os.path.basename(path).replace(".jsonl", "")
    ratios, zeros, seqs, solves, errors = [], 0, [], [], 0
    for line in open(path):
        r = json.loads(line)
        if "error" in r:
            errors += 1
            continue
        cost, cov = r["cost"], r["cov"]
        ratios.append(cov / cost)
        zeros += int(cov == cost)
        seqs.append(sum(len(rt) for rt in r["routes"]) + len(r["routes"]) + 2)
        solves.append(r["solve_s"])
    n = len(ratios)
    n_tot += n
    all_ratio.extend(ratios)
    all_zero += zeros
    all_seq.extend(seqs)
    all_solve.extend(solves)
    out[name] = dict(n=n, errors=errors,
                     kc_median=round(float(np.median(ratios)), 4),
                     zero_overlap_pct=round(100 * zeros / n, 1),
                     max_seq=int(max(seqs)),
                     solve_mean=round(float(np.mean(solves)), 2),
                     solve_max=round(float(np.max(solves)), 1))
out["ALL"] = dict(n=n_tot,
                  kc_median=round(float(np.median(all_ratio)), 4),
                  zero_overlap_pct=round(100 * all_zero / n_tot, 1),
                  max_seq=int(max(all_seq)),
                  solve_mean=round(float(np.mean(all_solve)), 2),
                  solve_max=round(float(np.max(all_solve)), 1),
                  cap_hits=int(sum(s >= 60 for s in all_solve)))
os.makedirs(f"{HERE}/results_mod", exist_ok=True)
with open(f"{HERE}/results_mod/kc_stats.json", "w") as fh:
    json.dump(out, fh, indent=1)
for k, v in out.items():
    print(k, json.dumps(v))
