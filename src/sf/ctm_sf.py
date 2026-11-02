"""CTM of the Sioux Falls network (YIL-231), built from the generated cell tables (sf.cell_generator).

Same model as the 5x5 CTM (src/utili/ctm/ctmcomponent.py), written for any number of inputs and outputs per cell and
vectorised over cells:
- sending S = min(n, Q dt), receiving R = min(Q dt, w/vf (N - n)); full-width cells have 2 lanes (Q and N doubled), as
  C3/C4/C5 in the 5x5; the source cell of an entry link is unbounded, the sink of an exit link absorbs everything;
- link diverge (full-width diverge cell -> left / right lane cell): each lane takes min(R_lane, p_lane S), as C5;
- intersection diverge (stop-line lane cell -> receiving lane cells of the downstream links): first-in-first-out, as
  C6/C7: the outflow is limited by the most restrictive branch, times the green share of the movement in the step;
- merges (several inputs into one cell, incl. receiving lane cells fed by up to 3 approaches): when the inputs exceed
  R, R is shared in proportion to what each input sends;
- turning: counts per movement (approach link -> downstream link); a movement served by both lanes (the through
  movement) is split over the lanes by their free space, the 5x5 'compromise' rule (Cell.updateConnection);
- signals: green share of each SUMO connection in each step, from the static programme (signals.json) and the cycle
  position of each signal; yellow and red count as red, as in the 5x5;
- boundary: 'static' feeds each entry link's source at the rate in a demand table; 'dynamic' writes the observed
  number of vehicles into the first cell of each entry link every step (the bench ground truth), as the 5x5 does
  with C40.
The interface follows the 5x5 CTM where the simulation and the route optimiser use it: init() -> cell_idx,
cells_dic[cid].n, runCTM(time_current, time_range) -> (snapshot, outflow, inflow, number, sigflag),
connection_matrix, demand_cell_list.
"""
import csv
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CFG = os.path.join(ROOT, 'sumo_cfg', 'siouxfalls')
BIG = 1e12


class CellView:
    """the attributes of one cell that the 5x5 simulation code reads or writes (n, get/load_state)"""

    def __init__(self, ctm, i, cid):
        self._ctm, self._i, self.cellid_full = ctm, i, cid

    @property
    def n(self):
        return self._ctm.n[self._i]

    @n.setter
    def n(self, v):
        self._ctm.n[self._i] = v

    def get_state(self):
        return {'n': float(self._ctm.n[self._i])}

    def load_state(self, state):
        self._ctm.n[self._i] = state['n']

    def get_state_num(self, cell_len=None):
        return self._ctm.n[self._i]


class SFCTM:
    def __init__(self, ctm_fd, dt, demand_mode='static', demand_table=None, demand_gt=None, cfg_dir=None):
        """ctm_fd: v_f, k_jam (per lane), q_max (per lane), w; dt in s; demand_table: DataFrame time, link_id,
        demand (veh/h); demand_gt: array [cells, steps] of the bench (dynamic mode)"""
        self.fd = dict(ctm_fd)
        self.dt = float(dt)
        self.tick = int(dt)
        self.demand_mode = demand_mode
        self.demand = demand_table
        self.demand_gt = np.load(demand_gt) if isinstance(demand_gt, str) else demand_gt
        self.cfg_dir = cfg_dir or os.path.join(CFG, 'CTMcfg', f'dt{self.dt:g}')

    # ------------------------------------------------------------ build
    def init(self, max_flow=None):
        rows = list(csv.DictReader(open(os.path.join(self.cfg_dir, 'cells.csv'))))
        self.cell_idx = [r['cell_id'] for r in rows]
        self.idx = {c: i for i, c in enumerate(self.cell_idx)}
        self.role = np.array([r['role'] for r in rows])
        self.link_of = np.array([r['link'] for r in rows])
        self.lanes = [list(map(int, r['lanes'].split())) for r in rows]
        self.n_lanes = np.array([int(r['n_lanes']) for r in rows], dtype=float)
        self.length_km = np.array([float(r['length_m']) for r in rows]) / 1000.0
        self.position = np.array([int(r['position']) for r in rows])
        self.pieces = [[(p.split(':')[0], float(p.split(':')[1]), float(p.split(':')[2])) for p in r['pieces'].split(';') if p]
                       for r in rows]
        self.set_fd(self.fd)
        arcs = list(csv.DictReader(open(os.path.join(self.cfg_dir, 'links.csv'))))
        self.a_from = np.array([self.idx[a['from']] for a in arcs])
        self.a_to = np.array([self.idx[a['to']] for a in arcs])
        self.a_type = np.array([a['type'] for a in arcs])
        self.a_tl = np.array([a['tl'] for a in arcs])
        self.a_li = np.array([int(a['link_index']) for a in arcs])
        N, A = len(self.cell_idx), len(arcs)
        self.N, self.A = N, A
        self.connection_matrix = np.zeros((N, N))
        self.connection_matrix[self.a_from, self.a_to] = 1
        self.n = np.zeros(N)
        self.cells_dic = {c: CellView(self, i, c) for i, c in enumerate(self.cell_idx)}
        # first cell of every entry link (the cell fed by its source), as C40 in the 5x5
        self.demand_cell_list = [self.cell_idx[j] for j in sorted(set(self.a_to[self.a_type == 'source']))]
        self._build_turning()
        self._build_signals()
        self.set_turn_counts({})
        self.arr_rate = np.zeros(N)            # veh/h at source cells
        if self.demand is not None:
            self._apply_static_demand(0.0)
        return self.cell_idx

    def set_fd(self, fd):
        """q_max and k_jam are per lane; full-width cells have two lanes"""
        self.fd = dict(fd)
        dt_h = self.dt / 3600.0
        self.Q = self.fd['q_max'] * self.n_lanes * dt_h
        self.Njam = self.fd['k_jam'] * self.length_km * self.n_lanes
        self.wv = self.fd['w'] / self.fd['v_f']
        src, snk = self.role == 'source', self.role == 'sink'
        self.Q = np.where(src, 2 * self.fd['q_max'] * dt_h, self.Q)
        self.Q = np.where(snk, BIG, self.Q)
        self.Njam = np.where(src | snk, BIG, self.Njam)

    def _build_turning(self):
        """approaches (links that end at a signal) with their left/right first stop-line cells, movements and the arcs
        of each movement"""
        inter = np.where(self.a_type == 'intersection')[0]
        div = np.where(self.a_type == 'diverge')[0]
        self.int_arcs, self.div_arcs = inter, div
        # stop-line lane cells where the intersection arcs start (last position) and where the diverge arcs end
        lane_first = {}                                          # (link, lane) -> first stop-line cell
        for a in div:
            j = self.a_to[a]
            lane_first[(self.link_of[j], self.lanes[j][0])] = j
        self.approaches = sorted({self.link_of[self.a_from[a]] for a in inter})
        ap_idx = {L: k for k, L in enumerate(self.approaches)}
        K = len(self.approaches)
        self.ap_left = np.array([lane_first[(L, 1)] for L in self.approaches])
        self.ap_right = np.array([lane_first[(L, 0)] for L in self.approaches])
        # movements: (approach, downstream link) and the lanes that serve it
        mov = {}
        for a in inter:
            L, M = self.link_of[self.a_from[a]], self.link_of[self.a_to[a]]
            mov.setdefault((L, M), set()).add(self.lanes[self.a_from[a]][0])
        self.movements = sorted(mov)
        mv_idx = {m: q for q, m in enumerate(self.movements)}
        self.mv_ap = np.array([ap_idx[L] for L, M in self.movements])
        self.mv_both = np.array([len(mov[m]) == 2 for m in self.movements])
        self.mv_lane = np.array([min(mov[m]) if len(mov[m]) == 1 else -1 for m in self.movements])
        self.ia_mv = np.array([mv_idx[(self.link_of[self.a_from[a]], self.link_of[self.a_to[a]])] for a in inter])
        self.ia_lane = np.array([self.lanes[self.a_from[a]][0] for a in inter])
        self.ia_ap = self.mv_ap[self.ia_mv]
        # link-diverge arcs: approach and lane of the target
        self.da_ap = np.array([ap_idx.get(self.link_of[self.a_from[a]], -1) for a in div])
        self.da_lane = np.array([self.lanes[self.a_to[a]][0] for a in div])
        self.K = K

    def set_turn_counts(self, counts):
        """counts: {(approach link, downstream link): vehicles}; movements without a count get 1 (equal shares)"""
        self.turn_counts = dict(counts)
        self.mv_count = np.array([float(counts.get(m, 1.0)) for m in self.movements])

    def _build_signals(self):
        sig = json.load(open(os.path.join(self.cfg_dir, 'signals.json')))
        self.signals = sig
        inter = self.int_arcs
        self.cycle_of = {t: int(round(v['cycle'])) for t, v in sig.items()}
        cmax = max(self.cycle_of.values())
        self.g_cum = np.zeros((len(inter), 2 * cmax + 1))
        self.ia_cycle = np.zeros(len(inter), dtype=int)
        self.ia_tl = self.a_tl[inter]
        for q, a in enumerate(inter):
            t = self.a_tl[a]
            c = self.cycle_of[t]
            g = np.zeros(c)
            for s, e in sig[t]['green'].get(str(self.a_li[a]), []):
                g[int(round(s)):int(round(e))] = 1.0
            g2 = np.concatenate([g, g])
            self.g_cum[q, 1:2 * c + 1] = np.cumsum(g2)
            self.ia_cycle[q] = c
        self.tl_shift = {t: 0 for t in sig}                     # cycle position = (time + shift) mod cycle
        self.ia_shift = np.zeros(len(inter), dtype=int)

    def sync_signals(self, time_now, positions):
        """positions: {tl: cycle position (s) at time_now}, e.g. from TraCI; sets the shift used by green_share"""
        for t, pos in positions.items():
            self.tl_shift[t] = int(round(pos - time_now)) % self.cycle_of[t]
        self.ia_shift = np.array([self.tl_shift[t] for t in self.ia_tl])

    def green_share(self, t):
        """green share of every intersection arc over [t, t + dt)"""
        pos = (int(round(t)) + self.ia_shift) % self.ia_cycle
        d = int(round(self.dt))
        r = np.arange(len(pos))
        return (self.g_cum[r, pos + d] - self.g_cum[r, pos]) / d

    # ------------------------------------------------------------ boundary
    def _apply_static_demand(self, t):
        df = self.demand[self.demand['time'] <= t]
        if len(df) == 0:
            return
        last = df.sort_values('time').groupby('link_id').tail(1)
        for _, r in last.iterrows():
            src = f'A1.{r["link_id"]}.C0'
            if src in self.idx:
                self.arr_rate[self.idx[src]] = float(r['demand'])

    def _apply_dynamic_demand(self, t):
        k = int(t // self.dt)
        if self.demand_gt is None or k >= self.demand_gt.shape[1]:
            if self.demand is not None:
                self._apply_static_demand(t)
            return
        for cid in self.demand_cell_list:
            i = self.idx[cid]
            self.n[i] = self.demand_gt[i, k]

    # ------------------------------------------------------------ dynamics
    def step(self, t):
        """advance one step starting at time t; returns (arc flows, green share of the intersection arcs)"""
        n = self.n
        dt_h = self.dt / 3600.0
        src = self.role == 'source'
        n[src] += self.arr_rate[src] * dt_h                     # arrivals into the source cells
        S = np.minimum(n, self.Q)
        R = np.maximum(0.0, np.minimum(self.Q, self.wv * (self.Njam - n)))
        g = self.green_share(t)
        # through split by free space of the two first stop-line cells (5x5 compromise rule)
        fl = np.maximum(self.Njam[self.ap_left] - n[self.ap_left], 0.0)
        fr = np.maximum(self.Njam[self.ap_right] - n[self.ap_right], 0.0)
        phi = np.where(fl + fr > 0, fl / np.maximum(fl + fr, 1e-12), 0.5)          # share of through to the left
        c = self.mv_count
        both = self.mv_both
        TL = np.bincount(self.mv_ap, weights=np.where(both, phi[self.mv_ap] * c, np.where(self.mv_lane == 1, c, 0.0)), minlength=self.K)
        TR = np.bincount(self.mv_ap, weights=np.where(both, (1 - phi[self.mv_ap]) * c, np.where(self.mv_lane == 0, c, 0.0)), minlength=self.K)
        # demand of every arc
        d = S[self.a_from].copy()
        p_div = np.where(TL + TR > 0, TL / np.maximum(TL + TR, 1e-12), 0.5)
        div_share = np.where(self.da_lane == 1, p_div[self.da_ap], 1 - p_div[self.da_ap])
        d[self.div_arcs] = S[self.a_from[self.div_arcs]] * div_share
        cm = c[self.ia_mv]
        lane_tot = np.where(self.ia_lane == 1, TL[self.ia_ap], TR[self.ia_ap])
        w_lane = np.where(both[self.ia_mv], np.where(self.ia_lane == 1, phi[self.ia_ap], 1 - phi[self.ia_ap]), 1.0)
        p_int = np.where(lane_tot > 0, cm * w_lane / np.maximum(lane_tot, 1e-12), 0.0)
        d[self.int_arcs] = S[self.a_from[self.int_arcs]] * p_int * g
        # receiving: shared in proportion to the demands when they exceed R
        D = np.bincount(self.a_to, weights=d, minlength=self.N)
        scale = np.where(D > R, R / np.maximum(D, 1e-12), 1.0)
        alloc = d * scale[self.a_to]
        flow = alloc.copy()
        # FIFO at the stop line: the lane's outflow is limited by its most restrictive branch
        ia = self.int_arcs
        lim = np.where(p_int > 0, alloc[ia] / np.maximum(p_int, 1e-12), BIG)
        f_cell = np.full(self.N, BIG)
        np.minimum.at(f_cell, self.a_from[ia], lim)
        f_lane = np.minimum(f_cell[self.a_from[ia]], S[self.a_from[ia]] * g)
        flow[ia] = p_int * f_lane
        out = np.bincount(self.a_from, weights=flow, minlength=self.N)
        inn = np.bincount(self.a_to, weights=flow, minlength=self.N)
        self.n = np.maximum(n + inn - out, 0.0)
        self.n[self.role == 'sink'] = 0.0                      # vehicles leave the network
        self._last_in, self._last_out, self._last_flow = inn, out, flow
        return flow, g

    def sigflag(self, g):
        """green share per cell (stop-line lane cells that feed intersection arcs; 1 elsewhere)"""
        s = np.ones(self.N)
        if len(self.int_arcs):
            val = np.zeros(self.N)
            np.maximum.at(val, self.a_from[self.int_arcs], g)
            has = np.zeros(self.N, dtype=bool)
            has[self.a_from[self.int_arcs]] = True
            s[has] = val[has]
        return s

    def runCTM(self, time_current, time_range):
        """predict from the current state; returns (snapshot after one step, outflow, inflow, number, sigflag) with
        cells as rows and steps as columns, like the 5x5 CTM; the state is left after the last step (the caller reloads
        the snapshot)"""
        steps = int(time_range // self.dt)
        number, outflow, inflow, sig = [], [], [], []
        snapshot = None
        for k in range(steps + 1):
            t = time_current + k * self.dt
            if self.demand_mode == 'static' and self.demand is not None:
                self._apply_static_demand(t)
            elif self.demand_mode == 'dynamic':
                self._apply_dynamic_demand(t)
            if k == 1:
                snapshot = {c: {'n': float(v)} for c, v in zip(self.cell_idx, self.n)}
            number.append(self.n.copy())
            flow, g = self.step(t)
            outflow.append(self._last_out)
            inflow.append(self._last_in)
            sig.append(self.sigflag(g))
        if snapshot is None:
            snapshot = {c: {'n': float(v)} for c, v in zip(self.cell_idx, self.n)}
        mk = lambda rows: pd.DataFrame(np.array(rows).T, index=self.cell_idx)
        return snapshot, mk(outflow), mk(inflow), mk(number), mk(sig)

    def load_snapshot(self, snapshot):
        self.n = np.array([snapshot[c]['n'] for c in self.cell_idx], dtype=float)

    def ctm_fd_for_optimizer(self):
        """FD dictionary in the form the route optimiser reads (cell length in km, step in h)"""
        fd = dict(self.fd)
        fd['length'] = float(np.median(self.length_km[(self.role != 'source') & (self.role != 'sink')]))
        fd['delta_t'] = self.dt / 3600.0
        return fd


# ---------------------------------------------------------------- vehicle -> cell
class CellMapper:
    """vehicle position (SUMO edge piece, lane, position on the piece) -> CTM cell"""

    def __init__(self, ctm):
        self.ctm = ctm
        self.by_piece = {}                                      # edge -> list of (from, to, lanes, cell index)
        for i, ps in enumerate(ctm.pieces):
            if ctm.role[i] in ('source', 'sink'):
                continue
            for e, a, b in ps:
                self.by_piece.setdefault(e, []).append((a, b, ctm.lanes[i], i))
        for e in self.by_piece:
            self.by_piece[e].sort()

    def cell(self, edge, lane, pos):
        """cell index of a vehicle, or None (e.g. not on a CTM piece)"""
        segs = self.by_piece.get(edge)
        if not segs:
            return None
        best = None
        for a, b, lanes, i in segs:
            if a - 1e-6 <= pos < b + 1e-6 and lane in lanes:
                return i
            if lane in lanes:
                best = i if best is None or pos >= a else best
        return best                                              # beyond the end (rounding): the last cell of the lane
