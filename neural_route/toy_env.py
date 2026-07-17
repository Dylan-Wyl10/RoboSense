"""Toy 3x3 one-way network environment for the FM-MCVRP-style SL spike (YIL-113).

Standalone (no SUMO). Mirrors the legacy small-example MILP in
src/utili/routeOptimGurobi.py::build_model_smallexample:
  min  alpha1 * total_travel_cost - alpha2 * coverage / (n_links * horizon)
where coverage = |union over fleet of occupied (link, time) cells| (y[i,t]).

Graph: link-node representation of a 3x3 street grid. Nodes 1-12 horizontal
(eastbound), 13-24 vertical (southbound), 25 = start, 26 = end (both cost-free).
Topology identical to get_small_net_param()'s `con` and the user's figure.

Travel cost (user-specified, 2026-07-16): node i entered at time t costs
    c(i, t) = (i + t) // 4 + 1
interpreted as the travel time spent traversing node i; the vehicle occupies
(i, t) .. (i, t + c - 1) for coverage purposes.
"""

from itertools import product

# node -> list of successor nodes (verbatim from legacy get_small_net_param)
CON = {1: [2, 16], 2: [3, 19], 3: [22], 4: [5, 17], 5: [6, 20], 6: [23],
       7: [8, 18], 8: [9, 21], 9: [24], 10: [11], 11: [12], 12: [26],
       13: [4, 14], 14: [7, 15], 15: [10], 16: [5, 17], 17: [18, 8], 18: [11],
       19: [6, 20], 20: [9, 21], 21: [12], 22: [23], 23: [24], 24: [26],
       25: [1, 13], 26: []}

START, END = 25, 26
LINKS = [i for i in range(1, 25)]          # cost/coverage-bearing nodes
N_LINKS = len(LINKS)


def cost(i, t):
    """Travel time through node i when entered at time t (start/end are free)."""
    if i in (START, END):
        return 0
    return (i + t) // 4 + 1


def enumerate_routes(start=START, end=END):
    """All simple start->end paths. The one-way grid is a DAG: expect 20."""
    routes, stack = [], [(start, [start])]
    while stack:
        node, path = stack.pop()
        if node == end:
            routes.append(path)
            continue
        for nxt in CON[node]:
            stack.append((nxt, path + [nxt]))
    return sorted(routes)


ROUTES = enumerate_routes()


def simulate(route, t0, horizon=None):
    """Drive one route departing at t0.

    Returns (total_cost, occupied) where occupied = {(i, t), ...} link-time
    cells (the omega/y cells of the MILP). Start/end nodes add no cost and no
    occupation. If horizon is given and the vehicle cannot finish (enter END)
    strictly within it, returns (None, None) = infeasible.
    """
    t, total, occupied = t0, 0, set()
    for node in route:
        if node == END:
            return (total, occupied) if horizon is None or t <= horizon else (None, None)
        if node == START:
            continue
        c = cost(node, t)
        if horizon is not None and t + c > horizon:
            return None, None
        occupied.update((node, s) for s in range(t, t + c))
        total += c
        t += c
    raise ValueError("route did not reach END")


def fleet_objective(assignment, departures, alpha1=0.5, alpha2=0.5, horizon=45):
    """MILP-equivalent objective (minimize) for a joint fleet assignment.

    assignment: list of route indices (into ROUTES), one per vehicle.
    departures: list of departure times t0, one per vehicle.
    Returns (obj, total_cost, coverage) or None if any vehicle is infeasible.
    """
    total_cost, union = 0, set()
    for ridx, t0 in zip(assignment, departures):
        c, occ = simulate(ROUTES[ridx], t0, horizon)
        if c is None:
            return None
        total_cost += c
        union |= occ
    cov = len(union)
    obj = alpha1 * total_cost - alpha2 * cov / (N_LINKS * horizon)
    return obj, total_cost, cov


def solve_exact(departures, alpha1=0.5, alpha2=0.5, horizon=45):
    """Brute-force exact optimum over all 20^V joint assignments (V small).

    Returns (best_assignment, best_obj, best_cost, best_cov).
    """
    best = None
    for assign in product(range(len(ROUTES)), repeat=len(departures)):
        res = fleet_objective(list(assign), departures, alpha1, alpha2, horizon)
        if res is None:
            continue
        if best is None or res[0] < best[1]:
            best = (list(assign), *res)
    return best
