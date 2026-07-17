"""Gurobi MILP label generator — time-expanded arc-flow formulation.

This is THE label machine for training (user directive 2026-07-17: no brute
force in the pipeline; Gurobi generates training info so the pipeline shape
survives on large networks). It never enumerates routes:

  time-nodes  (i, t) = "a vehicle enters link i at time t", built by forward
              reachability from (START, t0) through arcs (i,t) -> (j, t+c(i,t));
  flow        identical vehicles (same OD + departure) => one aggregated
              integer commodity: source pushes n_veh units, sink absorbs them;
              an integer flow of value V on a DAG decomposes into V paths
              (extracted greedily after solve) — exact for symmetric fleets.
  coverage    entering i at t occupies (i, t .. t+c-1): y[i,tau] <= total flow
              entering i at any t that covers tau; y binary, pushed up by the
              (maximized) coverage term.
  objective   min a1*cost/cost_norm - a2*sum(y)/(n_links*horizon)  (normalized).

Model size ~ O(n_links * horizon) variables — polynomial, no 20^V anywhere.
Validated == brute-force optimum on the 3x3 grid (validate()); on larger
grids brute force is impossible, which is exactly the point.
"""

from collections import defaultdict

import numpy as np
from gurobipy import GRB, Model, quicksum

from . import toy_env as te


def build_time_graph(inst):
    """Forward-reachable time-expanded graph.

    Returns arcs: dict (i, t) -> list of (j, s) successors  (j may be END with
    s = completion time), plus the set of reachable entry time-nodes.
    """
    g, H = inst.grid, inst.horizon
    t0 = inst.depart
    arcs, seen = defaultdict(list), set()
    frontier = [(j, t0) for j in g.con[g.START]]
    for node in frontier:
        seen.add(node)
    while frontier:
        i, t = frontier.pop()
        c = inst.cost(i, t)
        s = t + c
        if s > H:
            continue                       # cannot finish traversing i in time
        for j in g.con[i]:
            if j == g.END:
                arcs[(i, t)].append((g.END, s))
            else:
                arcs[(i, t)].append((j, s))
                if (j, s) not in seen:
                    seen.add((j, s))
                    frontier.append((j, s))
    return arcs, seen


def solve_milp(inst, time_limit=60, verbose=False, mip_gap=None):
    """Solve one Instance with Gurobi. Returns (routes, obj, cost, coverage).

    routes = n_veh explicit node lists (decomposed from the aggregated flow),
    canonically sorted. obj/cost/cov recomputed via inst.objective (single
    source of truth). Returns None if infeasible/timeout without solution.
    """
    g, H, V = inst.grid, inst.horizon, inst.n_veh
    arcs, nodes = build_time_graph(inst)

    m = Model("flow_coverage")
    m.Params.OutputFlag = 1 if verbose else 0
    m.Params.TimeLimit = time_limit
    if mip_gap is not None:
        m.Params.MIPGap = mip_gap

    # integer flow on every time-arc; entry arcs from virtual source
    f = {}
    for (i, t), succs in arcs.items():
        for (j, s) in succs:
            f[(i, t, j, s)] = m.addVar(vtype=GRB.INTEGER, lb=0, ub=V,
                                       name=f"f_{i}_{t}_{j}_{s}")
    src = {}
    for j in g.con[g.START]:
        if (j, inst.depart) in nodes:
            src[j] = m.addVar(vtype=GRB.INTEGER, lb=0, ub=V, name=f"src_{j}")
    y = m.addVars(g.n_links, H, vtype=GRB.BINARY, name="y")

    # source pushes exactly V vehicles
    m.addConstr(quicksum(src.values()) == V)

    # conservation at every entry time-node
    inflow = defaultdict(list)
    for (i, t, j, s), var in f.items():
        if j != g.END:
            inflow[(j, s)].append(var)
    for j, var in src.items():
        inflow[(j, inst.depart)].append(var)
    for (i, t) in nodes:
        out = [f[(i, t, j, s)] for (j, s) in arcs.get((i, t), [])]
        m.addConstr(quicksum(inflow[(i, t)]) == quicksum(out),
                    name=f"cons_{i}_{t}")

    # coverage linking: entering i at t covers (i, t .. t+c-1)
    cover_terms = defaultdict(list)
    for (i, t) in nodes:
        entry = quicksum(inflow[(i, t)])
        for tau in range(t, min(t + inst.cost(i, t), H)):
            cover_terms[(i, tau)].append(entry)
    for i in range(1, g.n_links + 1):
        for tau in range(H):
            terms = cover_terms.get((i, tau))
            if terms:
                m.addConstr(y[i - 1, tau] <= quicksum(terms))
            else:
                m.addConstr(y[i - 1, tau] == 0)

    total_cost = quicksum(inst.cost(i, t) * quicksum(inflow[(i, t)])
                          for (i, t) in nodes)
    m.setObjective(inst.alpha1 / inst.cost_norm * total_cost
                   - inst.alpha2 / (g.n_links * H) * y.sum(),
                   GRB.MINIMIZE)
    m.optimize()
    if m.SolCount == 0:
        return None

    # decompose aggregated flow into V explicit routes
    fval = {k: round(v.X) for k, v in f.items() if v.X > 0.5}
    sval = {j: round(v.X) for j, v in src.items() if v.X > 0.5}
    routes = []
    for _ in range(V):
        j = next(k for k, v in sval.items() if v > 0)
        sval[j] -= 1
        route, cur = [g.START, j], (j, inst.depart)
        while True:
            key = next(k for k in fval
                       if k[:2] == cur and fval[k] > 0)
            fval[key] -= 1
            if fval[key] == 0:
                del fval[key]
            nxt, s = key[2], key[3]
            route.append(nxt)
            if nxt == g.END:
                break
            cur = (nxt, s)
        routes.append(route)
    routes.sort()
    obj, tot, cov = inst.objective(routes)
    return routes, obj, tot, cov


def validate(n_instances=5, seed=0, atol=1e-9):
    """3x3 only: MILP must match the brute-force optimum objective."""
    rng = np.random.default_rng(seed)
    ok = True
    for n in range(n_instances):
        inst = te.sample_instance(rng)
        _, o_bf, t_bf, c_bf = inst.solve_exact()
        _, o_mp, t_mp, c_mp = solve_milp(inst)
        match = abs(o_bf - o_mp) < atol
        ok &= match
        print(f"[{n}] brute obj={o_bf:.6f} (cost {t_bf}, cov {c_bf}) | "
              f"milp obj={o_mp:.6f} (cost {t_mp}, cov {c_mp}) | "
              f"{'MATCH' if match else 'MISMATCH'}")
    print("validation:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    validate()
