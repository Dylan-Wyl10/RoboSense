"""Parametric one-way grid environment for the FM-MCVRP-style SL spike (YIL-113).

2026-07-17 user directives: (1) labels come from GUROBI (the scalable path —
see milp_baseline.py's time-expanded flow MILP; enumeration survives only as a
small-grid VALIDATOR, never in the training pipeline); (2) the grid is now
parametric (R x C blocks) so the choice space can grow beyond 3x3.

Grid(R, C): link-node form of an R x C one-way street grid (east/south).
  horizontal links 1 .. R'*C        (R' = R+1 rows, C per row)
  vertical links   R'*C+1 .. n_links (C' = C+1 cols, R per col)
  START = n_links+1 (top-left in), END = n_links+2 (bottom-right out)
Grid(3, 3) reproduces the user's figure / legacy `con` topology exactly
(verified in tests): 12+12 links, 20 routes, every route = R+C = 6 links.

Objective (normalized, both terms in [0, 1]):
  min alpha1 * cost/cost_norm - alpha2 * coverage/(n_links*horizon),
  coverage = |union of occupied (link, time) cells|,
  cost_norm = n_veh * max feasible single-route cost.

Cost: c(i, t) = (i + t) // 4 + 1 + delta[i], t = node entry time; START/END
free. delta = per-instance node offsets (the instance-variability axis).
"""

from itertools import combinations_with_replacement

import numpy as np


class Grid:
    def __init__(self, R=3, C=3):
        self.R, self.C = R, C
        Rp, Cp = R + 1, C + 1
        self.n_links = Rp * C + Cp * R
        self.START, self.END = self.n_links + 1, self.n_links + 2

        def h(i, j):                      # horizontal link at row i (0..R), col j (0..C-1)
            return i * C + j + 1

        def v(i, j):                      # vertical link at col j (0..C), row i (0..R-1)
            return Rp * C + j * R + i + 1

        con = {}
        for i in range(Rp):
            for j in range(C):
                succ = []
                if j + 1 < C:
                    succ.append(h(i, j + 1))
                if i < R:
                    succ.append(v(i, j + 1))
                if j + 1 == C and i == R:
                    succ.append(self.END)
                con[h(i, j)] = succ
        for j in range(Cp):
            for i in range(R):
                succ = []
                if i + 1 < R:
                    succ.append(v(i + 1, j))
                if j < C:
                    succ.append(h(i + 1, j))
                if i + 1 == R and j == C:
                    succ.append(self.END)
                con[v(i, j)] = succ
        con[self.START] = [h(0, 0), v(0, 0)]
        con[self.END] = []
        self.con = con
        self.route_len = R + C            # every monotone route visits R+C links
        self._routes = None

    def enumerate_routes(self):
        """All START->END paths. VALIDATION/calibration only — the training
        pipeline never calls this (labels come from the Gurobi MILP)."""
        if self._routes is None:
            routes, stack = [], [(self.START, [self.START])]
            while stack:
                node, path = stack.pop()
                if node == self.END:
                    routes.append(path)
                    continue
                for nxt in self.con[node]:
                    stack.append((nxt, path + [nxt]))
            self._routes = sorted(routes)
        return self._routes


GRID3 = Grid(3, 3)


class Instance:
    """One problem instance on a grid: per-node cost offsets + fleet config."""

    def __init__(self, grid=GRID3, delta=None, n_veh=4, depart=0,
                 horizon=None, alpha1=0.5, alpha2=0.5):
        self.grid = grid
        self.delta = np.zeros(grid.n_links, dtype=np.int64) if delta is None \
            else np.asarray(delta, dtype=np.int64)
        assert self.delta.shape == (grid.n_links,) and (self.delta >= 0).all()
        self.n_veh, self.depart = n_veh, depart
        self.horizon = default_horizon(grid) if horizon is None else horizon
        self.alpha1, self.alpha2 = alpha1, alpha2
        self._route_cache = None

    def cost(self, i, t):
        if i in (self.grid.START, self.grid.END):
            return 0
        return (i + t) // 4 + 1 + int(self.delta[i - 1])

    def simulate(self, route, t0=None):
        """(total_cost, occupied bool[n_links*horizon]) or (None, None)."""
        g, H = self.grid, self.horizon
        t = self.depart if t0 is None else t0
        total = 0
        occ = np.zeros(g.n_links * H, dtype=bool)
        for node in route:
            if node == g.END:
                return (total, occ) if t <= H else (None, None)
            if node == g.START:
                continue
            c = self.cost(node, t)
            if t + c > H:
                return None, None
            base = (node - 1) * H
            occ[base + t:base + t + c] = True
            total += c
            t += c
        raise ValueError("route did not reach END")

    # ---- enumeration-based paths below are for VALIDATION on small grids only

    def route_table(self):
        routes = self.grid.enumerate_routes()
        if self._route_cache is None:
            costs = np.full(len(routes), -1, dtype=np.int64)
            occs = np.zeros((len(routes), self.grid.n_links * self.horizon), bool)
            for k, r in enumerate(routes):
                c, o = self.simulate(r)
                if c is not None:
                    costs[k], occs[k] = c, o
            self._route_cache = (costs, occs, costs >= 0)
        return self._route_cache

    @property
    def cost_norm(self):
        costs, _, feas = self.route_table()
        return self.n_veh * int(costs[feas].max())

    def objective(self, routes):
        """Normalized objective for explicit routes (lists of node ids)."""
        total, union = 0, np.zeros(self.grid.n_links * self.horizon, bool)
        for r in routes:
            c, o = self.simulate(r)
            if c is None:
                return None
            total += c
            union |= o
        cov = int(union.sum())
        obj = (self.alpha1 * total / self.cost_norm
               - self.alpha2 * cov / (self.grid.n_links * self.horizon))
        return obj, total, cov

    def solve_exact(self):
        """Brute-force optimum (multiset enumeration). SMALL GRIDS ONLY —
        used to validate the Gurobi MILP, never to produce training labels."""
        costs, occs, feas = self.route_table()
        combos = np.array(list(combinations_with_replacement(
            np.flatnonzero(feas).tolist(), self.n_veh)), dtype=np.int64)
        tot = costs[combos].sum(axis=1)
        cov = np.logical_or.reduce(occs[combos], axis=1).sum(axis=1)
        obj = (self.alpha1 * tot / self.cost_norm
               - self.alpha2 * cov / (self.grid.n_links * self.horizon))
        b = int(np.argmin(obj))
        routes = [self.grid.enumerate_routes()[k] for k in combos[b]]
        return routes, float(obj[b]), int(tot[b]), int(cov[b])


def default_horizon(grid, max_delta=1, slack=1.15):
    """Horizon calibrated so every route stays feasible at delta = max_delta:
    simulate the worst route under worst offsets, add slack."""
    worst = 0
    probe = Instance.__new__(Instance)          # lightweight cost-only probe
    probe.grid = grid
    probe.delta = np.full(grid.n_links, max_delta, dtype=np.int64)
    probe.depart = 0
    for route in grid.enumerate_routes():
        t = 0
        for node in route[1:-1]:
            t += (node + t) // 4 + 1 + max_delta
        worst = max(worst, t)
    return int(np.ceil(worst * slack))


def sample_instance(rng, grid=GRID3, max_delta=1, **kw):
    """Random instance: iid per-node offsets in {0..max_delta}. With the
    calibrated horizon all routes stay feasible."""
    return Instance(grid, delta=rng.integers(0, max_delta + 1,
                                             size=grid.n_links), **kw)
