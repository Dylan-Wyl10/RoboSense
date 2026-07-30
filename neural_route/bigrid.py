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

Cost: c(i,t) = (i+t)//4 + 1 + delta[i]  (same family as before; i = link id,
so the two directions of one street have different base costs — interpreted
as direction-dependent congestion). FIFO holds (t + c(i,t) nondecreasing in
t), so earliest-arrival is computed with time-dependent Dijkstra — this also
replaces route enumeration (impossible on a cyclic graph) for horizon
calibration and for the decoder's budget mask.
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
    """delta offsets + per-vehicle (o, d) gate tasks; costs as before."""

    def __init__(self, grid, delta, tasks, depart=0, horizon=None,
                 alpha1=0.5, alpha2=0.5):
        self.grid = grid
        self.delta = np.asarray(delta, dtype=np.int64)
        assert self.delta.shape == (grid.n_links,)
        self.tasks = list(tasks)          # [(o_gate_id, d_gate_id), ...]
        self.depart = depart
        self.horizon = horizon
        self.alpha1, self.alpha2 = alpha1, alpha2

    def cost(self, i, t):
        if i > self.grid.n_links:         # gate nodes are free
            return 0
        return (i + t) // 4 + 1 + int(self.delta[i - 1])

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


def calibrate_horizon(grid, max_delta=1, slack=1.6):
    """Horizon = slack * max over ordered ODs of earliest arrival under the
    worst congestion (all deltas at max)."""
    inst = BiInstance(grid, np.full(grid.n_links, max_delta), tasks=[])
    worst = 0
    for o in grid.gates.values():
        _, arrive = inst.earliest_arrival(o)
        for d in grid.gates.values():
            if d != o:
                if d not in arrive:
                    raise RuntimeError(f"gate {d} unreachable from {o}")
                worst = max(worst, arrive[d])
    return int(np.ceil(worst * slack))
