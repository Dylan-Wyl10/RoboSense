"""Gurobi label machine for the bidirectional grid — multi-commodity
time-expanded flow (extension 1: per-vehicle (o, d, t0) tasks).

Commodity = group of vehicles sharing the same (o, d, t0); each commodity is
an integer flow of value n_k from (o, t0) to gate d on the time-expanded
graph (a DAG even though the spatial graph is cyclic, because travel times
are >= 1 so t strictly increases). Coverage y[i, tau] is shared across
commodities exactly as in the single-OD model:

  min  a1/(V*H) * total_travel_cost  -  a2/(n_links*H) * sum(y)

Validation (cyclic graph => no brute-force reference): after solving we
decompose flows into explicit routes and recompute the objective with
BiInstance.objective() — the two numbers must agree to 1e-9; we also check
the MILP is never worse than the all-min-time-routes heuristic.
"""

from collections import Counter, defaultdict

import numpy as np
from gurobipy import GRB, Model, quicksum

from .bigrid import BiInstance


def _time_graph(inst, o, d, t0):
    """Forward-reachable time-expanded arcs for one commodity."""
    g, H = inst.grid, inst.horizon
    arcs, seen = defaultdict(list), set()
    frontier = [(l, t0) for l in g.gate_out[o]]
    seen.update(frontier)
    exit_links = set(g.gate_in[d])
    while frontier:
        l, t = frontier.pop()
        s = t + inst.cost(l, t)
        if s > H:
            continue
        if l in exit_links:
            arcs[(l, t)].append(("DST", s))
        for nxt in g.con[l]:
            arcs[(l, t)].append((nxt, s))
            if (nxt, s) not in seen:
                seen.add((nxt, s))
                frontier.append((nxt, s))
    return arcs, seen


def solve_milp(inst, time_limit=120, mip_gap=None, verbose=False):
    """Returns (routes aligned with inst.tasks order, obj, cost, cov)."""
    g, H = inst.grid, inst.horizon
    V = len(inst.tasks)
    groups = Counter(tuple(t) for t in inst.tasks)     # (o,d,t0) -> count

    m = Model("bigrid_fleet")
    m.Params.OutputFlag = 1 if verbose else 0
    m.Params.TimeLimit = time_limit
    if mip_gap is not None:
        m.Params.MIPGap = mip_gap

    F, SRC, cover, costsum = {}, {}, defaultdict(list), []
    for k, ((o, d, t0), nk) in enumerate(groups.items()):
        arcs, nodes = _time_graph(inst, o, d, t0)
        inflow = defaultdict(list)
        for (l, t), succs in arcs.items():
            for (j, s) in succs:
                v = m.addVar(vtype=GRB.INTEGER, lb=0, ub=nk,
                             name=f"f{k}_{l}_{t}_{j}_{s}")
                F[(k, l, t, j, s)] = v
                if j != "DST":
                    inflow[(j, s)].append(v)
        for l in g.gate_out[o]:
            if (l, t0) in nodes:
                v = m.addVar(vtype=GRB.INTEGER, lb=0, ub=nk, name=f"s{k}_{l}")
                SRC[(k, l)] = v
                inflow[(l, t0)].append(v)
        m.addConstr(quicksum(SRC[(k, l)] for l in g.gate_out[o]
                             if (k, l) in SRC) == nk)
        for (l, t) in nodes:
            out = [F[(k, l, t, j, s)] for (j, s) in arcs.get((l, t), [])]
            m.addConstr(quicksum(inflow[(l, t)]) == quicksum(out),
                        name=f"c{k}_{l}_{t}")
        for (l, t) in nodes:                          # cost + coverage terms
            entry = quicksum(inflow[(l, t)])
            c = inst.cost(l, t)
            costsum.append(c * entry)
            for tau in range(t, min(t + c, H)):
                cover[(l, tau)].append(entry)

    y = {}
    for (l, tau), terms in cover.items():
        y[(l, tau)] = m.addVar(vtype=GRB.BINARY, name=f"y_{l}_{tau}")
        m.addConstr(y[(l, tau)] <= quicksum(terms))

    m.setObjective((inst.alpha1 * quicksum(costsum)
                    - inst.alpha2 * quicksum(y.values())) / (V * H),
                   GRB.MINIMIZE)
    m.optimize()
    if m.SolCount == 0:
        return None

    # decompose each commodity's flow into explicit routes
    fval = {key: round(v.X) for key, v in F.items() if v.X > 0.5}
    sval = {key: round(v.X) for key, v in SRC.items() if v.X > 0.5}
    routes_by_group = defaultdict(list)
    for k, ((o, d, t0), nk) in enumerate(groups.items()):
        for _ in range(nk):
            l = next(lk for (kk, lk), v in sval.items() if kk == k and v > 0)
            sval[(k, l)] -= 1
            t, route = t0, [l]
            while True:
                key = next(kk for kk in fval
                           if kk[0] == k and kk[1] == l and kk[2] == t
                           and fval[kk] > 0)
                fval[key] -= 1
                if fval[key] == 0:
                    del fval[key]
                j, s = key[3], key[4]
                if j == "DST":
                    break
                route.append(j)
                l, t = j, s
            routes_by_group[(o, d, t0)].append(route)

    routes = [routes_by_group[tuple(t)].pop(0) for t in inst.tasks]
    obj, tot, cov = inst.objective(routes)
    assert abs(obj - m.ObjVal) < 1e-6, \
        f"decomposed obj {obj} != MILP obj {m.ObjVal}"
    return routes, obj, tot, cov


def min_time_heuristic(inst):
    """All vehicles take their earliest-arrival route: an upper bound the
    MILP must beat or match (used as a validation guardrail)."""
    routes = []
    for (o, d, t0) in inst.tasks:
        g = inst.grid
        # rebuild the arg-min path via predecessor tracking
        import heapq
        entry, pred = {}, {}
        pq = [(t0, -l, 0) for l in g.gate_out[o]]
        heapq.heapify(pq)
        best, best_end = np.inf, None
        while pq:
            t, neg, p = heapq.heappop(pq)
            l = -neg
            if l in entry and entry[l] <= t:
                continue
            entry[l] = t
            pred[l] = p
            s = t + inst.cost(l, t)
            if l in g.gate_in[d] and s < best:
                best, best_end = s, l
            for nxt in g.con[l]:
                if nxt not in entry or entry[nxt] > s:
                    heapq.heappush(pq, (s, -nxt, l))
        route, l = [], best_end
        while l != 0:
            route.append(l)
            l = pred[l]
        routes.append(route[::-1])
    return routes, inst.objective(routes)


def validate(n_instances=4, seed=0):
    """Internal-consistency + heuristic-bound validation on random cases."""
    from .bigrid import BiGrid, calibrate_horizon
    g = BiGrid(4, 4)
    H = calibrate_horizon(g)
    rng = np.random.default_rng(seed)
    gates = list(g.gates.values())
    ok = True
    for n in range(n_instances):
        V = int(rng.integers(2, 5))
        tasks = []
        for _ in range(V):
            o, d = rng.choice(gates, 2, replace=False)
            tasks.append((int(o), int(d), int(rng.integers(0, 6))))
        inst = BiInstance(g, rng.integers(0, 2, g.n_links), tasks, horizon=H)
        import time
        t0 = time.time()
        res = solve_milp(inst)
        dt = time.time() - t0
        _, h = min_time_heuristic(inst)
        good = res is not None and res[1] <= h[0] + 1e-9
        ok &= good
        print(f"[{n}] V={V} milp obj={res[1]:.5f} (cost {res[2]}, cov {res[3]}) "
              f"| min-time heuristic {h[0]:.5f} | {dt:.1f}s | "
              f"{'OK' if good else 'VIOLATION'}")
    print("validation:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    validate()
