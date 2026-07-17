"""Toy 3x3 one-way network environment for the FM-MCVRP-style SL spike (YIL-113).

Standalone (no SUMO). Objective mirrors the legacy small-example MILP
(src/utili/routeOptimGurobi.py::build_model_smallexample) but with BOTH terms
normalized to [0, 1] (user request, 2026-07-17):

    min  alpha1 * total_cost / cost_norm  -  alpha2 * coverage / (n_links * horizon)

where coverage = |union over fleet of occupied (link, time) cells| and
cost_norm = fleet_size * (max single-route cost over the instance) — a tight,
precomputable constant, so the MILP objective stays linear.

Graph: link-node form of a 3x3 street grid. Nodes 1-12 horizontal (east),
13-24 vertical (south), 25 = start, 26 = end (both cost-free). Topology
identical to the legacy `con` dict and the user's figure. DAG: 20 routes,
each visiting exactly 6 links.

Cost (user formula, t = node ENTRY time) plus per-instance perturbation:
    c_inst(i, t) = (i + t) // 4 + 1 + delta[i]
delta[i] >= 0 are per-instance node offsets ("today's congestion") — the
instance-variability axis, analogous to FM-MCVRP's daily demand subsets.
delta = 0 recovers the user's exact formula.
"""

from itertools import combinations_with_replacement

import numpy as np

CON = {1: [2, 16], 2: [3, 19], 3: [22], 4: [5, 17], 5: [6, 20], 6: [23],
       7: [8, 18], 8: [9, 21], 9: [24], 10: [11], 11: [12], 12: [26],
       13: [4, 14], 14: [7, 15], 15: [10], 16: [5, 17], 17: [18, 8], 18: [11],
       19: [6, 20], 20: [9, 21], 21: [12], 22: [23], 23: [24], 24: [26],
       25: [1, 13], 26: []}

START, END = 25, 26
LINKS = list(range(1, 25))
N_LINKS = len(LINKS)
HORIZON = 45          # legacy time_step
N_VEH = 4             # user setting 2026-07-17: 4 vehicles, same departure
DEPART = 0


def enumerate_routes(start=START, end=END):
    routes, stack = [], [(start, [start])]
    while stack:
        node, path = stack.pop()
        if node == end:
            routes.append(path)
            continue
        for nxt in CON[node]:
            stack.append((nxt, path + [nxt]))
    return sorted(routes)


ROUTES = enumerate_routes()          # 20 routes, len 8 incl. 25/26
N_ROUTES = len(ROUTES)


class Instance:
    """One problem instance = per-node cost offsets (+ fleet config)."""

    def __init__(self, delta=None, n_veh=N_VEH, depart=DEPART, horizon=HORIZON,
                 alpha1=0.5, alpha2=0.5):
        self.delta = np.zeros(N_LINKS, dtype=np.int64) if delta is None \
            else np.asarray(delta, dtype=np.int64)
        assert self.delta.shape == (N_LINKS,) and (self.delta >= 0).all()
        self.n_veh, self.depart, self.horizon = n_veh, depart, horizon
        self.alpha1, self.alpha2 = alpha1, alpha2
        self._route_cache = None

    def cost(self, i, t):
        if i in (START, END):
            return 0
        return (i + t) // 4 + 1 + int(self.delta[i - 1])

    def simulate(self, route, t0=None):
        """(total_cost, occupied-cell bool[N_LINKS*HORIZON]) or (None, None)."""
        t0 = self.depart if t0 is None else t0
        t, total = t0, 0
        occ = np.zeros(N_LINKS * self.horizon, dtype=bool)
        for node in route:
            if node == END:
                return (total, occ) if t <= self.horizon else (None, None)
            if node == START:
                continue
            c = self.cost(node, t)
            if t + c > self.horizon:
                return None, None
            occ[(node - 1) * self.horizon + t:(node - 1) * self.horizon + t + c] = True
            total += c
            t += c
        raise ValueError("route did not reach END")

    def route_table(self):
        """Simulate all 20 routes once: (costs[k], occ[k] bool matrix, feas[k])."""
        if self._route_cache is None:
            costs = np.full(N_ROUTES, -1, dtype=np.int64)
            occs = np.zeros((N_ROUTES, N_LINKS * self.horizon), dtype=bool)
            for k, r in enumerate(ROUTES):
                c, o = self.simulate(r)
                if c is not None:
                    costs[k], occs[k] = c, o
            self._route_cache = (costs, occs, costs >= 0)
        return self._route_cache

    @property
    def cost_norm(self):
        costs, _, feas = self.route_table()
        return self.n_veh * int(costs[feas].max())

    def objective(self, assignment):
        """Normalized MILP objective for a route-index assignment (len n_veh)."""
        costs, occs, feas = self.route_table()
        idx = np.asarray(assignment)
        if not feas[idx].all():
            return None
        total = int(costs[idx].sum())
        cov = int(np.logical_or.reduce(occs[idx]).sum())
        obj = (self.alpha1 * total / self.cost_norm
               - self.alpha2 * cov / (N_LINKS * self.horizon))
        return obj, total, cov

    def solve_exact(self):
        """Provably-optimal joint assignment by vectorized enumeration.

        Same departure time => vehicles interchangeable => enumerate multisets
        (C(20+V-1, V) = 8855 for V=4 instead of 20^4).
        Returns (assignment, obj, total_cost, coverage).
        """
        costs, occs, feas = self.route_table()
        combos = np.array(list(combinations_with_replacement(
            np.flatnonzero(feas), self.n_veh)))            # (M, V)
        tot = costs[combos].sum(axis=1)                     # (M,)
        cov = np.logical_or.reduce(occs[combos], axis=1).sum(axis=1)
        obj = (self.alpha1 * tot / self.cost_norm
               - self.alpha2 * cov / (N_LINKS * self.horizon))
        b = int(np.argmin(obj))
        return list(combos[b]), float(obj[b]), int(tot[b]), int(cov[b])


def sample_instance(rng, max_delta=1, min_feasible=4, **kw):
    """Random instance: iid per-node offsets in {0..max_delta} ('daily traffic').

    max_delta=1 keeps all instances solvable within HORIZON (base route costs
    are 32-44 vs horizon 45, so larger offsets kill feasibility). Resamples
    until at least `min_feasible` of the 20 routes are feasible.
    """
    while True:
        inst = Instance(delta=rng.integers(0, max_delta + 1, size=N_LINKS), **kw)
        if int(inst.route_table()[2].sum()) >= min_feasible:
            return inst
