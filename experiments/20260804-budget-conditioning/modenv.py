"""Mod-24 environment (YIL-125 r5, 2026-08-06): the adopted cost law plus
EXACT earliest-arrival machinery that stays correct without FIFO.

    c(i,t) = (base(i)+t) mod 24 + 1 + delta_i           bounded <= 24 + delta

User simplification r5: drop the //4. Mathematically the r4 cost
((base+t) mod 96)//4 was identical to ((base+t)//4) mod 24 — a mod-24
sawtooth on a 4x-slowed clock — so this keeps the amplitude (0..23) and
removes the slow clock: the congestion cycle is now 24 steps.

The sawtooth wrap breaks FIFO (t + c can decrease in t), so the single-label
TD-Dijkstra in `neural_route.bigrid` is inexact here (wrong on 28.4% of
(OD, t0) cells under mod-24; 18.1% under the r4 mod-96 law). Every query below therefore runs Dijkstra over
time-expanded states (link, entry-time) — exact for arbitrary positive costs,
no waiting (the environment has no waiting).

Drop-in interface (same names/signatures as neural_route.bigrid):
    ModInstance(grid, delta, tasks, ...)  subclass of BiInstance overriding
        cost / earliest_arrival / min_finish;  simulate & objective inherit
        (they only call cost).
    calibrate_horizon(grid)               same rule as bigrid's, exact search.

`neural_route/` is NOT modified; pipeline scripts import from here instead.
Run `python modenv.py` for the self-checks (H, anchor values, min_finish
vs brute force, periodicity).
"""

import heapq
import os
import sys

import numpy as np

sys.path.insert(0, os.path.expanduser("~/Research/Route_TSC_CART"))
from neural_route.bigrid import BiGrid, BiInstance  # noqa: E402

PERIOD = 24


class ModInstance(BiInstance):

    def cost(self, i, t):
        if i > self.grid.n_links:
            return 0
        return ((self.grid.base[i] + t) % PERIOD
                + 1 + int(self.delta[i - 1]))

    def _link_gates(self):
        g = self.grid
        if not hasattr(self, "_lg"):
            self._lg = {lid: [gid for gid, ins in g.gate_in.items()
                              if lid in ins] for lid in g.ends}
        return self._lg

    def earliest_arrival(self, o_gate, t0=None):
        """Exact under non-FIFO costs: Dijkstra over (link, entry-time)
        states. Returns (entry, arrive) like the parent — `entry` maps each
        link to its EARLIEST entry time (informational; downstream code only
        uses `arrive`)."""
        g = self.grid
        t0 = self.depart if t0 is None else t0
        lg = self._link_gates()
        seen = set()
        entry, arrive = {}, {}
        n_gates = len(g.gates)
        pq = [(t0, lid) for lid in g.gate_out[o_gate]]
        heapq.heapify(pq)
        while pq:
            t, lid = heapq.heappop(pq)
            if len(arrive) == n_gates and t >= max(arrive.values()):
                break
            if (lid, t) in seen:
                continue
            seen.add((lid, t))
            if lid not in entry or t < entry[lid]:
                entry[lid] = t
            s = t + self.cost(lid, t)
            for gid in lg[lid]:
                if gid not in arrive or s < arrive[gid]:
                    arrive[gid] = s
            for nxt in g.con[lid]:
                if (nxt, s) not in seen:
                    heapq.heappush(pq, (s, nxt))
        return entry, arrive

    def min_finish(self, lid, t, d_gate):
        """Earliest arrival at gate d if we ENTER link lid at time t — exact
        (link, entry-time) search, memoised per (lid, t, d)."""
        key = (lid, t, d_gate)
        if not hasattr(self, "_mf"):
            self._mf = {}
        if key in self._mf:
            return self._mf[key]
        g = self.grid
        gate_in_d = set(g.gate_in[d_gate])
        best = np.inf
        seen = set()
        pq = [(t, lid)]
        while pq:
            tt, l = heapq.heappop(pq)
            if tt >= best:
                break                      # entry times only grow
            if (l, tt) in seen:
                continue
            seen.add((l, tt))
            s = tt + self.cost(l, tt)
            if l in gate_in_d:
                best = min(best, s)
            for nxt in g.con[l]:
                if (nxt, s) not in seen and s < best:
                    heapq.heappush(pq, (s, nxt))
        self._mf[key] = best
        return best


def calibrate_horizon(grid, max_delta=1, slack=1.6, max_t0=5):
    """Same rule as neural_route.bigrid.calibrate_horizon, exact search."""
    inst = ModInstance(grid, np.full(grid.n_links, max_delta), tasks=[])
    worst = 0
    for o in grid.gates.values():
        _, arrive = inst.earliest_arrival(o, t0=max_t0)
        for d in grid.gates.values():
            if d != o:
                if d not in arrive:
                    raise RuntimeError(f"gate {d} unreachable from {o}")
                worst = max(worst, arrive[d])
    return int(np.ceil(worst * slack))


if __name__ == "__main__":
    g = BiGrid(4, 4)
    H = calibrate_horizon(g)
    assert H == 128, f"H changed: {H}"            # r5 established value
    inst = ModInstance(g, np.zeros(g.n_links), tasks=[], horizon=H)
    ids = list(g.gates.values())
    _, a1 = inst.earliest_arrival(ids[0], t0=0)
    _, a7 = inst.earliest_arrival(ids[6], t0=0)
    assert a1[ids[1]] == 7 and a1[ids[4]] == 55, "G1 row anchor"
    assert a7[ids[2]] == 69, "G7->G3 anchor"      # r5 mod-24 value
    _, p0 = inst.earliest_arrival(ids[3], t0=11)
    _, p1 = inst.earliest_arrival(ids[3], t0=11 + PERIOD)
    assert all(p1[d] - p0[d] == PERIOD for d in ids if d != ids[3]), "period"

    # min_finish vs brute-force DP over the time-expanded graph
    rng = np.random.default_rng(0)
    inst_d = ModInstance(g, rng.integers(0, 2, g.n_links), tasks=[], horizon=H)

    def brute(lid, t, d, cut=400):
        best, seen = np.inf, set()
        stack = [(lid, t)]
        while stack:
            l, tt = stack.pop()
            if (l, tt) in seen or tt > cut:
                continue
            seen.add((l, tt))
            s = tt + inst_d.cost(l, tt)
            if l in g.gate_in[d]:
                best = min(best, s)
            stack.extend((nxt, s) for nxt in g.con[l])
        return best
    for lid in (1, 33, 60, 77):
        for t in (0, 40, 93):
            for d in (ids[2], ids[5]):
                assert inst_d.min_finish(lid, t, d) == brute(lid, t, d), \
                    (lid, t, d)
    print(f"modenv self-checks OK: H={H}, anchors match, "
          "min_finish == brute force, periodicity holds")
