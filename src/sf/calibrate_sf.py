"""Fundamental-diagram calibration of the Sioux Falls CTM (YIL-231), following the 5x5 procedure
(Simulation.calibrateCTM, src/simulation.py:342-528):
- v_f and k_jam fixed (16 m/s = 57.6 km/h; 1000 / 7.5 m = 133.3 veh/km/lane, vehicle length + minGap);
- trapezoidal FD: grid over q_max and delta_kc, w = q_max / (k_jam - q_max / v_f - delta_kc);
- the CTM starts from the bench state at START s (all cells = ground truth) and runs open-loop for DURATION s, fed
  only with the observed first cell of every entry link (dynamic mode, as the 5x5 C40);
- score: mean absolute error of the vehicles per cell against the bench. The 5x5 scores only the cells of the entry
  links; here both are reported and the choice is made on all inner cells (every cell except sources and sinks),
  with the 5x5 score alongside.
The q_max grid is wider than the 5x5 one (1875-1920 there; its best, 1920, sat on the edge).

Run from src/:  python -m sf.calibrate_sf --bench <bench dir> [--dt 12]
Writes <bench dir>/dt<dt>/CTMcali.json (all grid points, best by both scores) and errors per link of the best.
"""
import argparse
import json
import os

import numpy as np

from sf.bench_sf import load_gt
from sf.ctm_sf import SFCTM

V_F = 57.6
K_JAM = 1000 / 7.5
START, DURATION = 1800.0, 3600.0
Q_GRID = list(range(1500, 2501, 50))
DKC_GRID = list(range(0, 41, 2))


def run_once(ctm, gt, q_max, w, dt):
    ctm.set_fd({'v_f': V_F, 'k_jam': K_JAM, 'q_max': q_max, 'w': w})
    k0 = int(START // dt)
    steps = min(int(DURATION // dt), gt.shape[1] - k0)
    ctm.n = gt[:, k0].copy()
    pred = np.zeros((gt.shape[0], steps))
    for k in range(steps):
        t = (k0 + k) * dt
        ctm._apply_dynamic_demand(t)
        pred[:, k] = ctm.n                    # state at the start of the step, as runCTM's 'number'
        ctm.step(t)
    return pred, gt[:, k0:k0 + steps]


def calibrate(bench, dt):
    gt = load_gt(bench, dt)
    tc = {(a, b): c for a, b, c in json.load(open(os.path.join(bench, 'turn_counts.json')))}
    ctm = SFCTM({'v_f': V_F, 'k_jam': K_JAM, 'q_max': 1900, 'w': 20}, dt, demand_mode='dynamic', demand_gt=gt)
    ctm.init()
    ctm.set_turn_counts(tc)
    inner = np.array([r not in ('source', 'sink') for r in ctm.role])
    entry = np.array([c.startswith('A1.E') and r not in ('source', 'sink') for c, r in zip(ctm.cell_idx, ctm.role)])
    grid, best_all, best_entry = [], None, None
    for qm in Q_GRID:
        for dkc in DKC_GRID:
            room = K_JAM - qm / V_F - dkc
            if room <= 0:
                continue
            w = qm / room
            pred, truth = run_once(ctm, gt, qm, w, dt)
            mae_all = float(np.abs(pred[inner] - truth[inner]).mean())
            mae_entry = float(np.abs(pred[entry] - truth[entry]).mean())
            row = {'q_max': qm, 'delta_kc': dkc, 'w': round(w, 3), 'mae_inner_cells': mae_all, 'mae_entry_cells': mae_entry}
            grid.append(row)
            if best_all is None or mae_all < best_all['mae_inner_cells']:
                best_all = row
            if best_entry is None or mae_entry < best_entry['mae_entry_cells']:
                best_entry = row
    # error per link of the chosen FD
    pred, truth = run_once(ctm, gt, best_all['q_max'], best_all['w'], dt)
    per_link = {}
    for i in np.where(inner)[0]:
        per_link.setdefault(ctm.link_of[i], []).append(i)
    link_err = {L: {'mae_per_cell': round(float(np.abs(pred[ix] - truth[ix]).mean()), 3),
                    'mean_veh_truth': round(float(truth[ix].sum(axis=0).mean()), 2),
                    'mean_veh_ctm': round(float(pred[ix].sum(axis=0).mean()), 2)} for L, ix in per_link.items()}
    tot_t, tot_p = truth[inner].sum(axis=0), pred[inner].sum(axis=0)
    out = {'dt': dt, 'v_f': V_F, 'k_jam': K_JAM, 'start': START, 'duration': DURATION,
           'best_inner_cells': best_all, 'best_entry_cells_5x5_score': best_entry,
           'network_vehicles_truth_mean': float(tot_t.mean()), 'network_vehicles_ctm_mean': float(tot_p.mean()),
           'network_vehicles_rel_err_mean': float(np.mean(np.abs(tot_p - tot_t) / np.maximum(tot_t, 1))),
           'grid': grid, 'per_link_best': link_err}
    d = os.path.join(bench, f'dt{dt:g}')
    os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, 'CTMcali.json'), 'w'), indent=1)
    np.save(os.path.join(d, 'ctm_pred_best.npy'), pred)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--bench', required=True)
    ap.add_argument('--dt', type=float, default=12.0)
    a = ap.parse_args()
    r = calibrate(a.bench, a.dt)
    print(json.dumps({k: r[k] for k in ('dt', 'best_inner_cells', 'best_entry_cells_5x5_score', 'network_vehicles_truth_mean',
                                         'network_vehicles_ctm_mean', 'network_vehicles_rel_err_mean')}, indent=1))
