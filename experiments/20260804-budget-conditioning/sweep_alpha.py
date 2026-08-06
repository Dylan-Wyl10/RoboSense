"""Alpha sweep on the SAME instance as sweep_budget.py (seed 7), so the two
panels of the comparison figure share one instance.

alpha varies, budget fixed at the global horizon H  ->  the 2026-08-03 result
(binary regime switch) reproduced under controlled conditions.
"""

import csv
import os
import sys
import time

sys.path.insert(0, "/home/yilin/Research/Route_TSC_CART")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neural_route.bigrid_milp import solve_milp  # noqa: E402

from sweep_budget import fixed_instance  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
ALPHAS = [0.10, 0.20, 0.30, 0.40, 0.45, 0.48, 0.50, 0.52, 0.55, 0.60,
          0.70, 0.80, 0.90]


def main():
    rows = []
    for a2 in ALPHAS:
        inst = fixed_instance()
        inst.alpha1, inst.alpha2 = round(1 - a2, 3), a2
        t0 = time.time()
        res = solve_milp(inst, time_limit=180, mip_gap=0.005)
        dt = time.time() - t0
        routes, obj, cost, cov = res
        rows.append(dict(alpha2=a2, alpha1=inst.alpha1, obj=round(obj, 6),
                         cost=cost, cov=cov, overlap=cost - cov,
                         route_lens=[len(r) for r in routes],
                         solve_s=round(dt, 1)))
        print(f"a2={a2:4} cost={cost:5} cov={cov:5} lens="
              f"{[len(r) for r in routes]} obj={obj:.5f} {dt:.1f}s", flush=True)
    with open(f"{OUT}/results_alpha_mod.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("wrote results_alpha_mod.csv")


if __name__ == "__main__":
    main()
