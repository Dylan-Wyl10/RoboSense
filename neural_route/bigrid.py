"""Bidirectional 4x4 grid with 8 gates — extension 1 environment (YIL-113).

User directive 2026-07-29: make the network bidirectional so every gate pair
is a feasible OD (28 unordered pairs / 56 ordered tasks from 8 gates).

Structure (R x C blocks, default 4x4 => 5x5 intersections):
  directed link-nodes, one per street segment per direction:
    eastbound  E(i,j): (i,j)->(i,j+1)   ids 1  .. RpC       (Rp=R+1 rows, C cols)
    westbound  W(i,j): (i,j+1)->(i,j)   ids RpC+1 .. 2RpC
    southbound S(i,j): (i,j)->(i+1,j)   ids 2RpC+1 .. 2RpC+CpR   (Cp=C+1)
    northbound N(i,j): (i+1,j)->(i,j)   ids 2RpC+CpR+1 .. 2RpC+2CpR
  4x4 => 40 + 40 = 80 link-nodes.
  Connections at each intersection: incoming link -> every outgoing link
  EXCEPT its own reverse twin (no U-turn).
  Gates 2 per side at symmetric boundary intersections; every gate is both
  entry (gate -> outgoing links) and exit (incoming links -> gate).

Cost (OPTION B, user decision 2026-08-02): symmetric base cost per street —
    c(i,t) = (base(i)+t)//4 + 1 + delta[i],   base(i) = min(i, reverse(i))
both directions of one street share the base cost; direction-dependent
variation enters ONLY through the per-directed-link delta. FIFO holds
(t + c(i,t) nondecreasing in t), so earliest-arrival is computed with
time-dependent Dijkstra — replaces route enumeration (impossible on a cyclic
graph) for horizon calibration and the decoder's budget mask.

Tasks (extension-1 spec): per-vehicle (o_gate, d_gate, t0) — departure time
is part of the instance.
"""

import heapq

import numpy as np


class BiGrid:
    def __init__(self, R=4, C=4):
        self.R, self.C = R, C
        Rp, Cp = R + 1, C + 1
        nE = Rp * C
        nS = Cp * R
        self.n_links = 2 * nE + 2 * nS

        def E(i, j):
            return i * C + j + 1

        def W(i, j):
            return nE + i * C + j + 1

        def S(i, j):
            return 2 * nE + j * R + i + 1

        def N(i, j):
            return 2 * nE + nS + j * R + i + 1

        self._E, self._W, self._S, self._N = E, W, S, N
        # geometry: link id -> (from_intersection, to_intersection)
        self.ends = {}
        for i in range(Rp):
            for j in range(C):
                self.ends[E(i, j)] = ((i, j), (i, j + 1))
                self.ends[W(i, j)] = ((i, j + 1), (i, j))
        for j in range(Cp):
            for i in range(R):
                self.ends[S(i, j)] = ((i, j), (i + 1, j))
                self.ends[N(i, j)] = ((i + 1, j), (i, j))
        self.reverse = {}
        for i in range(Rp):
            for j in range(C):
                self.reverse[E(i, j)] = W(i, j)
                self.reverse[W(i, j)] = E(i, j)
        for j in range(Cp):
            for i in range(R):
                self.reverse[S(i, j)] = N(i, j)
                self.reverse[N(i, j)] = S(i, j)

        # option (b): base cost id = the lower id of the two directions
        self.base = {lid: min(lid, self.reverse[lid]) for lid in self.ends}

        out_of = {}                       # intersection -> outgoing link ids
        into = {}                         # intersection -> incoming link ids
        for lid, (a, b) in self.ends.items():
            out_of.setdefault(a, []).append(lid)
            into.setdefault(b, []).append(lid)
        self.out_of, self.into = out_of, into

        # link -> successor links (no U-turn)
        self.con = {}
        for lid, (a, b) in self.ends.items():
            self.con[lid] = [nxt for nxt in out_of.get(b, [])
                             if nxt != self.reverse[lid]]

        # 8 gates (user spec 2026-07-30): 4 corners + 4 edge midpoints
        self.gate_pos = {
            "G1_NW": (0, 0), "G2_N": (0, C // 2), "G3_NE": (0, C),
            "G4_E": (R // 2, C), "G5_SE": (R, C), "G6_S": (R, C // 2),
            "G7_SW": (R, 0), "G8_W": (R // 2, 0),
        }
        self.gates = {}                   # gate name -> gate node id (n_links+1..)
        for k, name in enumerate(self.gate_pos, start=1):
            self.gates[name] = self.n_links + k
        self.gate_of_id = {v: k for k, v in self.gates.items()}
        # entry arcs: gate -> outgoing links of its intersection
        self.gate_out = {g: list(self.out_of[self.gate_pos[name]])
                         for name, g in self.gates.items()}
        # exit arcs: incoming links of its intersection -> gate
        self.gate_in = {g: list(self.into[self.gate_pos[name]])
                        for name, g in self.gates.items()}

    def od_pairs(self):
        """All ordered OD tasks (o != d): 8*7 = 56; 28 unordered pairs."""
        ids = list(self.gates.values())
        return [(o, d) for o in ids for d in ids if o != d]


class BiInstance:
    """delta offsets + per-vehicle (o_gate, d_gate, t0) tasks."""

    def __init__(self, grid, delta, tasks, depart=0, horizon=None,
                 alpha1=0.3, alpha2=0.7):
        self.grid = grid
        self.delta = np.asarray(delta, dtype=np.int64)
        assert self.delta.shape == (grid.n_links,)
        # tasks: [(o, d, t0), ...]; (o, d) pairs are padded with t0=depart
        self.tasks = [t if len(t) == 3 else (*t, depart) for t in tasks]
        self.depart = depart
        self.horizon = horizon
        self.alpha1, self.alpha2 = alpha1, alpha2

    def cost(self, i, t):
        if i > self.grid.n_links:         # gate nodes are free
            return 0
        return (self.grid.base[i] + t) // 4 + 1 + int(self.delta[i - 1])

    def earliest_arrival(self, o_gate, t0=None):
        """Time-dependent Dijkstra from gate o (FIFO costs): returns
        dict link -> earliest ENTRY time, and dict gate_id -> earliest
        arrival time at that gate."""
        g = self.grid
        t0 = self.depart if t0 is None else t0
        entry = {}                        # link -> earliest entry time
        arrive = {}                       # gate id -> earliest arrival
        pq = [(t0, -lid) for lid in g.gate_out[o_gate]]
        heapq.heapify(pq)
        while pq:
            t, neg = heapq.heappop(pq)
            lid = -neg
            if lid in entry and entry[lid] <= t:
                continue
            entry[lid] = t
            s = t + self.cost(lid, t)     # exit time of this link
            for gid, ins in g.gate_in.items():
                if lid in ins and (gid not in arrive or s < arrive[gid]):
                    arrive[gid] = s
            for nxt in g.con[lid]:
                if nxt not in entry or entry[nxt] > s:
                    heapq.heappush(pq, (s, -nxt))
        return entry, arrive

    def min_finish(self, lid, t, d_gate):
        """Earliest arrival at gate d if we ENTER link lid at time t (exact,
        memoised per (lid, t, d) — the decoder budget-mask query)."""
        key = (lid, t, d_gate)
        if not hasattr(self, "_mf"):
            self._mf = {}
        if key in self._mf:
            return self._mf[key]
        g = self.grid
        best = np.inf
        entry = {}
        pq = [(t, -lid)]
        while pq:
            tt, neg = heapq.heappop(pq)
            l = -neg
            if tt >= best:
                break                      # labels are popped in order
            if l in entry and entry[l] <= tt:
                continue
            entry[l] = tt
            s = tt + self.cost(l, tt)
            if l in g.gate_in[d_gate]:
                best = min(best, s)
            for nxt in g.con[l]:
                if nxt not in entry or entry[nxt] > s:
                    heapq.heappush(pq, (s, -nxt))
        self._mf[key] = best
        return best

    def simulate(self, route, t0):
        """Drive one explicit route (list of link ids, no gates) from t0.
        Returns (total_cost, occupied bool[n_links*horizon], finish_time)
        or (None, None, None) if the horizon is busted."""
        H = self.horizon
        t, total = t0, 0
        occ = np.zeros(self.grid.n_links * H, dtype=bool)
        for lid in route:
            c = self.cost(lid, t)
            if t + c > H:
                return None, None, None
            base = (lid - 1) * H
            occ[base + t:base + t + c] = True
            total += c
            t += c
        return total, occ, t

    def objective(self, routes):
        """Normalized objective for explicit per-vehicle routes (aligned with
        self.tasks order; route k departs at tasks[k][2]).

        BOTH terms are normalized by V*H (2026-08-02 design decision):
        max achievable fleet coverage ~= total travel time <= V*H, so this
        puts cost and coverage on the same scale; with alpha 0.3/0.7 the
        optimum makes real sensing detours instead of collapsing to
        min-time routing (validated vs the min-time heuristic).
            min (a1*cost - a2*coverage) / (V*H)
        """
        g, H = self.grid, self.horizon
        total, union = 0, np.zeros(g.n_links * H, dtype=bool)
        for (o, d, t0), route in zip(self.tasks, routes):
            if not route or route[0] not in g.gate_out[o] \
               or route[-1] not in g.gate_in[d]:
                return None
            for a, b in zip(route, route[1:]):
                if b not in g.con[a]:
                    return None
            c, occ, _ = self.simulate(route, t0)
            if c is None:
                return None
            total += c
            union |= occ
        cov = int(union.sum())
        obj = (self.alpha1 * total - self.alpha2 * cov) / (len(self.tasks) * H)
        return obj, total, cov


def calibrate_horizon(grid, max_delta=1, slack=1.6, max_t0=5):
    """Horizon = slack * max over ordered ODs of earliest arrival under worst
    congestion, departing at the latest allowed t0 (FIFO => worst case)."""
    inst = BiInstance(grid, np.full(grid.n_links, max_delta), tasks=[])
    worst = 0
    for o in grid.gates.values():
        _, arrive = inst.earliest_arrival(o, t0=max_t0)
        for d in grid.gates.values():
            if d != o:
                if d not in arrive:
                    raise RuntimeError(f"gate {d} unreachable from {o}")
                worst = max(worst, arrive[d])
    return int(np.ceil(worst * slack))
