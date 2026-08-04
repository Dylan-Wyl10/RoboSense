"""Per-vehicle BUDGET variant of the bigrid MILP (option (a), YIL-113).

Design delta vs `neural_route.bigrid_milp`:

  * every vehicle v carries its own budget B_v (max travel time from its own
    t0); the hard deadline is  T_v = min(H, t0_v + B_v).  Semantically B_v is
    the robotaxi's shift length / remaining energy -- the real PartB
    constraint, not a tuning weight.
  * commodities are grouped by (o, d, t0, B) instead of (o, d, t0), because
    two vehicles with the same OD but different budgets live on different
    time-expanded DAGs.
  * normalizer V*H  ->  sum_v B_v  (= the fleet's actually available driving
    time).  The chain  cov <= cost <= sum_v B_v  still holds, so both terms
    stay in (0, 1] before being multiplied by alpha -- the property the user
    required on 2026-08-04.  The coverage GRID stays on [0, H) so cells are
    comparable across budgets.

Objective (alpha unchanged, defaults 0.3 / 0.7):

    min  ( a1 * sum cost  -  a2 * sum y[i,tau] ) / sum_v B_v

Nothing here edits existing project code; `neural_route` is imported.
"""

from collections import Counter, defaultdict

import numpy as np
from gurobipy import GRB, Model, quicksum


def min_travel_time(inst, o, d, t0):
    """Earliest arrival at gate d departing gate o at t0 = the feasibility
    floor for that vehicle's budget (B_v below this -> infeasible task)."""
    _, arrive = inst.earliest_arrival(o, t0=t0)
    if d not in arrive:
        return None
    return int(arrive[d] - t0)


def budgets_from_slack(inst, rho, cap=True):
    """B_v = ceil(rho * tau_min_v): budget expressed as a SLACK RATIO over the
    vehicle's own shortest feasible trip.  rho is scalar or per-vehicle.

    This is the parameterization that makes budgets comparable across OD
    pairs (a raw absolute B is infeasible for far pairs and vacuous for near
    ones), and rho is exactly the scalar the model gets conditioned on.
    """
    rhos = np.broadcast_to(np.asarray(rho, dtype=float), (len(inst.tasks),))
    out = []
    for (o, d, t0), r in zip(inst.tasks, rhos):
        tmin = min_travel_time(inst, o, d, t0)
        if tmin is None:
            raise ValueError(f"gate {d} unreachable from {o} at t0={t0}")
        b = int(np.ceil(r * tmin))
        if cap:
            b = min(b, inst.horizon - t0)      # never exceed the global grid
        out.append(max(b, tmin))               # never below feasibility floor
    return out


def _time_graph(inst, o, d, t0, deadline):
    """Forward-reachable time-expanded arcs, pruned at this vehicle's own
    deadline instead of the global horizon."""
    g = inst.grid
    arcs, seen = defaultdict(list), set()
    frontier = [(l, t0) for l in g.gate_out[o]]
    seen.update(frontier)
    exit_links = set(g.gate_in[d])
    while frontier:
        l, t = frontier.pop()
        s = t + inst.cost(l, t)
        if s > deadline:
            continue
        if l in exit_links:
            arcs[(l, t)].append(("DST", s))
        for nxt in g.con[l]:
            arcs[(l, t)].append((nxt, s))
            if (nxt, s) not in seen:
                seen.add((nxt, s))
                frontier.append((nxt, s))
    return arcs, seen


def objective_budget(inst, routes, budgets):
    """Recompute the budget-normalized objective from explicit routes and
    verify every per-vehicle deadline.  Returns (obj, cost, cov) or None."""
    g, H = inst.grid, inst.horizon
    total, union = 0, np.zeros(g.n_links * H, dtype=bool)
    for (o, d, t0), route, B in zip(inst.tasks, routes, budgets):
        if not route or route[0] not in g.gate_out[o] \
           or route[-1] not in g.gate_in[d]:
            return None
        for a, b in zip(route, route[1:]):
            if b not in g.con[a]:
                return None
        t = t0
        for lid in route:
            c = inst.cost(lid, t)
            if t + c > min(H, t0 + B):         # per-vehicle budget check
                return None
            base = (lid - 1) * H
            union[base + t:base + t + c] = True
            total += c
            t += c
    cov = int(union.sum())
    obj = (inst.alpha1 * total - inst.alpha2 * cov) / float(sum(budgets))
    return obj, total, cov


def solve_budget_milp(inst, budgets, time_limit=120, mip_gap=None,
                      verbose=False):
    """Multi-commodity time-expanded MILP with per-vehicle budgets.
    Returns (routes aligned with inst.tasks, obj, cost, cov) or None."""
    g, H = inst.grid, inst.horizon
    assert len(budgets) == len(inst.tasks)
    keys = [(int(o), int(d), int(t0), int(B))
            for (o, d, t0), B in zip(inst.tasks, budgets)]
    groups = Counter(keys)                     # (o,d,t0,B) -> count

    m = Model("bigrid_fleet_budget")
    m.Params.OutputFlag = 1 if verbose else 0
    m.Params.TimeLimit = time_limit
    if mip_gap is not None:
        m.Params.MIPGap = mip_gap

    F, SRC, cover, costsum = {}, {}, defaultdict(list), []
    for k, ((o, d, t0, B), nk) in enumerate(groups.items()):
        deadline = min(H, t0 + B)
        arcs, nodes = _time_graph(inst, o, d, t0, deadline)
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
            m.addConstr(quicksum(inflow[(l, t)]) == quicksum(out))
        for (l, t) in nodes:
            entry = quicksum(inflow[(l, t)])
            c = inst.cost(l, t)
            costsum.append(c * entry)
            for tau in range(t, min(t + c, H)):
                cover[(l, tau)].append(entry)

    y = {}
    for (l, tau), terms in cover.items():
        y[(l, tau)] = m.addVar(vtype=GRB.BINARY, name=f"y_{l}_{tau}")
        m.addConstr(y[(l, tau)] <= quicksum(terms))

    denom = float(sum(budgets))
    m.setObjective((inst.alpha1 * quicksum(costsum)
                    - inst.alpha2 * quicksum(y.values())) / denom,
                   GRB.MINIMIZE)
    m.optimize()
    if m.SolCount == 0:
        return None

    fval = {key: round(v.X) for key, v in F.items() if v.X > 0.5}
    sval = {key: round(v.X) for key, v in SRC.items() if v.X > 0.5}
    routes_by_group = defaultdict(list)
    for k, ((o, d, t0, B), nk) in enumerate(groups.items()):
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
            routes_by_group[(o, d, t0, B)].append(route)

    routes = [routes_by_group[key].pop(0) for key in keys]
    chk = objective_budget(inst, routes, budgets)
    assert chk is not None, "decomposed routes violate a budget"
    assert abs(chk[0] - m.ObjVal) < 1e-6, \
        f"decomposed obj {chk[0]} != MILP obj {m.ObjVal}"
    return routes, chk[0], chk[1], chk[2]
