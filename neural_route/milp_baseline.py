"""Gurobi MILP for the toy fleet-coverage problem, with a NORMALIZED objective.

Route-based formulation (exact on the toy: the 20 DAG routes are enumerable, so
route selection is the only decision). The legacy arc-time MILP
(build_model_smallexample) is left untouched as the general-case reference;
this model must agree with toy_env.Instance.solve_exact() — cross-validated
in validate().

    min  alpha1/cost_norm * sum_a sum_k cost[k] r[a,k]
       - alpha2/(n_links*horizon) * sum_{i,t} y[i,t]
    s.t. sum_k r[a,k] = 1  for each vehicle a          (one route per vehicle)
         y[i,t] <= sum_{a,k: (i,t) in occ[k]} r[a,k]   (coverage only if visited)
         r, y binary

Normalization (user request 2026-07-17): both objective terms live in [0,1];
cost_norm = n_veh * max feasible single-route cost (precomputed constant, so
the objective stays linear — normalization in a MILP is just constant scaling).
"""

import numpy as np
from gurobipy import GRB, Model, quicksum

from . import toy_env as te


def solve_milp(inst, time_limit=30, verbose=False):
    """Solve one toy_env.Instance. Returns (assignment, obj, cost, coverage)."""
    costs, occs, feas = inst.route_table()
    K = np.flatnonzero(feas)
    A = range(inst.n_veh)
    cells = te.N_LINKS * inst.horizon

    m = Model("toy_fleet_coverage")
    m.Params.OutputFlag = 1 if verbose else 0
    m.Params.TimeLimit = time_limit

    r = m.addVars(inst.n_veh, len(K), vtype=GRB.BINARY, name="r")
    y = m.addVars(cells, vtype=GRB.BINARY, name="y")

    for a in A:
        m.addConstr(quicksum(r[a, j] for j in range(len(K))) == 1)
    cell_routes = [np.flatnonzero(occs[K][:, c]) for c in range(cells)]
    for c in range(cells):
        if len(cell_routes[c]) == 0:
            m.addConstr(y[c] == 0)
        else:
            m.addConstr(y[c] <= quicksum(r[a, j] for a in A for j in cell_routes[c]))

    m.setObjective(
        inst.alpha1 / inst.cost_norm
        * quicksum(int(costs[K[j]]) * r[a, j] for a in A for j in range(len(K)))
        - inst.alpha2 / cells * quicksum(y[c] for c in range(cells)),
        GRB.MINIMIZE)
    m.optimize()

    assign = sorted(int(K[j]) for a in A for j in range(len(K))
                    if r[a, j].X > 0.5)
    obj, tot, cov = inst.objective(assign)
    return assign, obj, tot, cov


def validate(n_instances=5, seed=0, atol=1e-9):
    """Cross-check MILP vs brute-force exact optimum on random instances."""
    rng = np.random.default_rng(seed)
    ok = True
    for n in range(n_instances):
        inst = te.sample_instance(rng)
        a_bf, o_bf, t_bf, c_bf = inst.solve_exact()
        a_mp, o_mp, t_mp, c_mp = solve_milp(inst)
        match = abs(o_bf - o_mp) < atol
        ok &= match
        print(f"[{n}] brute obj={o_bf:.6f} (cost {t_bf}, cov {c_bf}) | "
              f"milp obj={o_mp:.6f} (cost {t_mp}, cov {c_mp}) | "
              f"{'MATCH' if match else 'MISMATCH'}")
    print("validation:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    validate()
