"""Bench run on the Sioux Falls network (YIL-231): SUMO without routing, recording the CTM ground truth.

Every dt seconds every vehicle is mapped to its CTM cell (sf.ctm_sf.CellMapper: edge piece, lane, position), giving
ctm_gt [cells x steps] as in the 5x5 bench (all vehicles per cell). Also written: the turn counts of the route file
(approach link -> downstream link, used by the CTM's turning shares) and the number of vehicles entering each entry
link per step (the external flows the CTM is given in 'dynamic' mode).

`compare()` runs the CTM open-loop on the same period, fed only with the observed first cells of the entry links
(dynamic mode), and reports how far its cell counts are from the ground truth.

Run from src/:
  python -m sf.bench_sf --routes <rou.xml> --out <dir> [--dt 12] [--end 7200] [--vtypes <add.xml>]
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

if 'SUMO_HOME' not in os.environ:
    os.environ['SUMO_HOME'] = '/usr/share/sumo'
sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
import traci                                                     # noqa: E402

from sf.ctm_sf import SFCTM, CellMapper, CFG                     # noqa: E402

NET = os.path.join(CFG, 'siouxfalls.net.xml')
SPEC = os.path.join(CFG, 'network_spec.json')
FD_5X5 = {'v_f': 57.6, 'k_jam': 1000 / 7.5, 'q_max': 1920, 'w': 19.59}


def piece_to_link():
    spec = json.load(open(SPEC))
    return {p['edge']: lk['id'] for lk in spec['links'] for p in lk['pieces']}


def turn_counts_from_routes(route_file):
    """{(approach link, downstream link): vehicles} from the routes of a route file"""
    p2l = piece_to_link()
    counts = {}
    for v in ET.parse(route_file).getroot().iter('vehicle'):
        r = v.find('route')
        if r is None:
            continue
        links = []
        for e in r.get('edges').split():
            L = p2l.get(e)
            if L is not None and (not links or links[-1] != L):
                links.append(L)
        for a, b in zip(links[:-1], links[1:]):
            counts[(a, b)] = counts.get((a, b), 0) + 1
    return counts


def run_bench(route_file, out_dir, dt=12.0, end=7200.0, resolution=0.1, vtypes=None, seed=42):
    os.makedirs(out_dir, exist_ok=True)
    ctm = SFCTM(FD_5X5, dt)
    ctm.init()
    mapper = CellMapper(ctm)
    entry_first = {ctm.link_of[ctm.idx[c]]: ctm.idx[c] for c in ctm.demand_cell_list}
    files = [route_file] + ([vtypes] if vtypes else [])
    cmd = ['sumo', '-n', NET, '-r', ','.join(files), '--step-length', str(resolution), '--no-step-log', 'true',
           '--seed', str(seed), '--end', str(end), '--duration-log.statistics', 'true',
           '--tripinfo-output', os.path.join(out_dir, 'tripinfo.xml')]
    traci.start(cmd)
    steps = int(end // dt) + 1
    gt = np.zeros((len(ctm.cell_idx), steps), dtype=np.int32)
    unmapped = 0
    every = int(round(dt / resolution))
    k_step = 0
    tick = 0
    while True:
        if tick % every == 0 and k_step < steps:
            for v in traci.vehicle.getIDList():
                i = mapper.cell(traci.vehicle.getRoadID(v), traci.vehicle.getLaneIndex(v), traci.vehicle.getLanePosition(v))
                if i is None:
                    unmapped += 1
                else:
                    gt[i, k_step] += 1
            k_step += 1
        if traci.simulation.getTime() >= end or (traci.simulation.getMinExpectedNumber() == 0 and tick > 0):
            break
        traci.simulationStep()
        tick += 1
    traci.close()
    gt = gt[:, :k_step]
    np.save(os.path.join(out_dir, 'ctm_gt.npy'), gt)
    json.dump(ctm.cell_idx, open(os.path.join(out_dir, 'cell_index.json'), 'w'))
    tc = turn_counts_from_routes(route_file)
    json.dump([[a, b, c] for (a, b), c in sorted(tc.items())], open(os.path.join(out_dir, 'turn_counts.json'), 'w'))
    info = {'route_file': os.path.abspath(route_file), 'dt': dt, 'end': end, 'resolution': resolution, 'seed': seed,
            'steps': int(k_step), 'unmapped_vehicle_samples': int(unmapped), 'max_in_network': int(gt.sum(axis=0).max()),
            'entry_cells': {L: ctm.cell_idx[i] for L, i in entry_first.items()}}
    json.dump(info, open(os.path.join(out_dir, 'bench_info.json'), 'w'), indent=1)
    return info


def compare(out_dir, fd=None, dt=12.0, start=0, steps=None):
    """open-loop CTM fed with the observed first cells of the entry links; error against the ground truth"""
    gt = np.load(os.path.join(out_dir, 'ctm_gt.npy')).astype(float)
    tc = {(a, b): c for a, b, c in json.load(open(os.path.join(out_dir, 'turn_counts.json')))}
    ctm = SFCTM(fd or FD_5X5, dt, demand_mode='dynamic', demand_gt=gt)
    ctm.init()
    ctm.set_turn_counts(tc)
    steps = steps or gt.shape[1] - start - 1
    ctm.n = gt[:, start].copy()
    pred = np.zeros((len(ctm.cell_idx), steps + 1))
    pred[:, 0] = ctm.n
    for k in range(steps):
        t = (start + k) * dt
        ctm._apply_dynamic_demand(t)
        ctm.step(t)
        pred[:, k + 1] = ctm.n
    truth = gt[:, start:start + steps + 1]
    inner = np.array([r not in ('source', 'sink') for r in ctm.role])
    err = np.abs(pred[inner] - truth[inner])
    tot_p, tot_t = pred[inner].sum(axis=0), truth[inner].sum(axis=0)
    by_link = {}
    for i in np.where(inner)[0]:
        by_link.setdefault(ctm.link_of[i], []).append(i)
    lp = np.array([pred[ix].sum(axis=0) for ix in by_link.values()])
    lt = np.array([truth[ix].sum(axis=0) for ix in by_link.values()])
    return {'steps': int(steps), 'cell_MAE': float(err.mean()), 'cell_MAE_when_occupied': float(err[truth[inner] > 0].mean()),
            'link_MAE': float(np.abs(lp - lt).mean()), 'network_total_truth_max': float(tot_t.max()),
            'network_total_pred_max': float(tot_p.max()),
            'network_total_rel_err_mean': float(np.mean(np.abs(tot_p - tot_t) / np.maximum(tot_t, 1)))}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--routes', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dt', type=float, default=12.0)
    ap.add_argument('--end', type=float, default=7200.0)
    ap.add_argument('--vtypes', default=None)
    a = ap.parse_args()
    print(json.dumps(run_bench(a.routes, a.out, a.dt, a.end, vtypes=a.vtypes), indent=1))
    print(json.dumps(compare(a.out, dt=a.dt), indent=1))
