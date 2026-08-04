"""Budget sweep on ONE fixed instance — the direct counterpart of the alpha
sweep posted 2026-08-03 (which showed alpha is a binary regime switch).

Question: with alpha FROZEN at 0.3 / 0.7, does the per-vehicle budget B
produce a CONTINUOUS response in route shape / coverage?

Output: results.csv + a printed table.
"""

import csv
import os
import sys
import time

import numpy as np

sys.path.insert(0, "/home/yilin/Research/Route_TSC_CART")
from neural_route.bigrid import BiGrid, BiInstance, calibrate_horizon  # noqa: E402

from budget_milp import (budgets_from_slack, min_travel_time,  # noqa: E402
                         solve_budget_milp)

OUT = os.path.dirname(os.path.abspath(__file__))
RHOS = [1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 6.0, 99.0]


def fixed_instance(seed=7):
    """Same recipe as the label farm's training sampler, V=3, fixed seed."""
    g = BiGrid(4, 4)
    H = calibrate_horizon(g)
    rng = np.random.default_rng(seed)
    delta = rng.integers(0, 2, g.n_links)
    gates = sorted(g.gates.values())
    tasks = []
    for _ in range(3):
        o, d = rng.choice(gates, 2, replace=False)
        tasks.append((int(o), int(d), int(rng.integers(0, 6))))
    return BiInstance(g, delta, tasks, horizon=H)


def main():
    inst = fixed_instance()
    H = inst.horizon
    tmins = [min_travel_time(inst, o, d, t0) for (o, d, t0) in inst.tasks]
    print(f"grid 4x4, H={H}, alpha=({inst.alpha1}, {inst.alpha2})")
    print(f"tasks (o,d,t0) = {inst.tasks}")
    print(f"tau_min per vehicle = {tmins}  (sum {sum(tmins)})\n")

    rows = []
    for rho in RHOS:
        B = budgets_from_slack(inst, rho)
        t0 = time.time()
        res = solve_budget_milp(inst, B, time_limit=120, mip_gap=0.005)
        dt = time.time() - t0
        if res is None:
            print(f"rho={rho}: NO SOLUTION")
            continue
        routes, obj, cost, cov = res
        overlap = cost - cov
        lens = [len(r) for r in routes]
        used = [sum(1 for _ in r) for r in routes]      # segments per vehicle
        rows.append(dict(rho=rho, budgets=B, sumB=sum(B), obj=round(obj, 6),
                         cost=cost, cov=cov, overlap=overlap,
                         cost_frac=round(cost / sum(B), 4),
                         cov_frac=round(cov / sum(B), 4),
                         route_lens=lens, solve_s=round(dt, 1)))
        print(f"rho={rho:5} B={B} sumB={sum(B):5} | cost={cost:5} cov={cov:5} "
              f"overlap={overlap:4} | lens={lens} | obj={obj:.5f} | {dt:.1f}s")

    with open(f"{OUT}/results_sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nwrote {OUT}/results_sweep.csv")


if __name__ == "__main__":
    main()
