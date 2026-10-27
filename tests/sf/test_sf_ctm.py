"""Checks of the Sioux Falls CTM (YIL-231): signals, free-flow travel, conservation. Run from the repository root:
    python -m pytest tests/sf -q"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from sf.ctm_sf import SFCTM                                    # noqa: E402

FD = {'v_f': 57.6, 'k_jam': 1000 / 7.5, 'q_max': 1920, 'w': 19.59}   # 5x5 values, until SF is calibrated


def make(dt=12.0, demand=None, mode='static'):
    c = SFCTM(FD, dt, demand_mode=mode, demand_table=demand)
    c.init()
    return c


def test_green_share_matches_programme():
    c = make()
    # over one full cycle every intersection arc gets its programme's green time (20 s per approach)
    for q, a in enumerate(c.int_arcs):
        cyc = c.ia_cycle[q]
        tot = sum(c.green_share(t)[q] * c.dt for t in np.arange(0, cyc * 12, c.dt)) / 12   # 12 cycles, any alignment
        assert abs(tot - 20.0) < 1e-6, (c.a_tl[a], tot)


def test_free_flow_one_cell_per_step():
    """one vehicle at the start of a link moves one cell per step when the road is empty (vf dt = cell length)"""
    c = make()
    i = c.idx['A0.E15.C3']                       # merge cell of link E15 (position 2)
    c.n[:] = 0.0
    c.n[i] = 1.0
    seen = []
    for k in range(4):
        c.step(k * c.dt)
        seen.append(c.cell_idx[int(np.argmax(c.n))])
    assert seen[0] == 'A0.E15.C4', seen          # next position after one step


def test_conservation_and_no_negative():
    links = [l for l in pd.read_csv(os.path.join(ROOT, 'sumo_cfg/siouxfalls/CTMcfg/dt12/links.csv'))['from']
             if str(l).startswith('A1.E1') and str(l).endswith('.C0')]
    dem = pd.DataFrame({'time': 0, 'link_id': [l.split('.')[1] for l in links], 'demand': 600.0})
    c = make(demand=dem)
    entered, left = 0.0, 0.0
    sink = c.role == 'sink'
    for k in range(600):                         # 2 h
        before = c.n.sum()
        flow, g = c.step(k * c.dt)
        entered += c.arr_rate[c.role == 'source'].sum() * c.dt / 3600.0
        left += c._last_in[sink].sum()
        assert c.n.min() >= -1e-9
    inside = c.n.sum()
    assert abs(entered - inside - left) < 1e-6 * max(1.0, entered), (entered, inside, left)
    assert left > 0.5 * entered                  # traffic flows through the network


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
