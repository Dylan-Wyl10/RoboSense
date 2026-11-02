"""Bench run on the Sioux Falls network (YIL-231): SUMO without routing, recording the CTM ground truth.

Every dt seconds every vehicle is mapped to its CTM cell (sf.ctm_sf.CellMapper: edge piece, lane, position), giving
ctm_gt [cells x steps] as in the 5x5 bench (all vehicles per cell). Also written: the turn counts of the route file
(approach link -> downstream link, used by the CTM's turning shares) and the number of vehicles entering each entry
link per step (the external flows the CTM is given in 'dynamic' mode).

`compare()` runs the CTM open-loop on the same period, fed only with the observed first cells of the entry links
(dynamic mode), and reports how far its cell counts are from the ground truth.

Run from src/:
  python -m sf.bench_sf --routes <rou.xml> --out <dir> [--dts 12,6] [--end <s>] [--vtypes <add.xml>]
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


def run_bench(route_file, out_dir, dts=(12.0, 6.0), end=None, resolution=0.1, vtypes=None, seed=42):
    """one SUMO run (no routing); for every dt in dts: ctm_gt [cells x steps] of that cell layout in <out_dir>/dt<dt>/.
    Also: vehicles entering each entry link and leaving each exit link per step of the first dt (boundary flows),
    turn counts of the route file. end=None runs until the network is empty."""
    os.makedirs(out_dir, exist_ok=True)
    p2l = piece_to_link()
    lay = []
    for dt in dts:
        ctm = SFCTM(FD_5X5, dt)
        ctm.init()
        lay.append({'dt': dt, 'ctm': ctm, 'mapper': CellMapper(ctm), 'every': int(round(dt / resolution)), 'gt': [], 'unmapped': 0})
    cmd = ['sumo', '-n', NET, '-r', route_file] + (['--additional-files', vtypes] if vtypes else []) + [
           '--step-length', str(resolution), '--no-step-log', 'true',
           '--seed', str(seed), '--duration-log.statistics', 'true',
           '--tripinfo-output', os.path.join(out_dir, 'tripinfo.xml')] + (['--end', str(end)] if end else [])
    traci.start(cmd)
    spec = json.load(open(SPEC))
    entry_links = [lk['id'] for lk in spec['links'] if lk['role'] == 'entry']
    exit_links = [lk['id'] for lk in spec['links'] if lk['role'] == 'exit']
    e_idx, x_idx = {L: i for i, L in enumerate(entry_links)}, {L: i for i, L in enumerate(exit_links)}
    dep, arr = [np.zeros(len(entry_links))], [np.zeros(len(exit_links))]
    last_edge = {}
    tick = 0
    first_every = lay[0]['every']
    while True:
        for L in lay:
            if tick % L['every'] == 0:
                col = np.zeros(len(L['ctm'].cell_idx), dtype=np.int32)
                for v in traci.vehicle.getIDList():
                    i = L['mapper'].cell(traci.vehicle.getRoadID(v), traci.vehicle.getLaneIndex(v), traci.vehicle.getLanePosition(v))
                    if i is None:
                        L['unmapped'] += 1
                    else:
                        col[i] += 1
                L['gt'].append(col)
        if tick % first_every == 0 and tick > 0:
            dep.append(np.zeros(len(entry_links)))
            arr.append(np.zeros(len(exit_links)))
        for v in traci.simulation.getDepartedIDList():
            r = traci.vehicle.getRoute(v)
            last_edge[v] = r[-1]
            L = p2l.get(r[0])
            if L in e_idx:
                dep[-1][e_idx[L]] += 1
        for v in traci.simulation.getArrivedIDList():
            L = p2l.get(last_edge.pop(v, ''))
            if L in x_idx:
                arr[-1][x_idx[L]] += 1
        if (end and traci.simulation.getTime() >= end) or (traci.simulation.getMinExpectedNumber() == 0 and tick > 0):
            break
        traci.simulationStep()
        tick += 1
    traci.close()
    tc = turn_counts_from_routes(route_file)
    json.dump([[a, b, c] for (a, b), c in sorted(tc.items())], open(os.path.join(out_dir, 'turn_counts.json'), 'w'))
    np.save(os.path.join(out_dir, 'entry_departures.npy'), np.array(dep).T)    # [entry links x steps of dts[0]]
    np.save(os.path.join(out_dir, 'exit_arrivals.npy'), np.array(arr).T)
    json.dump({'entry_links': entry_links, 'exit_links': exit_links, 'dt': dts[0]},
              open(os.path.join(out_dir, 'boundary_index.json'), 'w'))
    info = {'route_file': os.path.abspath(route_file), 'end': end, 'resolution': resolution, 'seed': seed,
            'sim_end_s': tick * resolution, 'departed': int(sum(d.sum() for d in dep)), 'arrived': int(sum(a.sum() for a in arr)),
            'layouts': {}}
    for L in lay:
        d = os.path.join(out_dir, f'dt{L["dt"]:g}')
        os.makedirs(d, exist_ok=True)
        gt = np.array(L['gt']).T
        np.save(os.path.join(d, 'ctm_gt.npy'), gt)
        json.dump(L['ctm'].cell_idx, open(os.path.join(d, 'cell_index.json'), 'w'))
        info['layouts'][f'{L["dt"]:g}'] = {'steps': int(gt.shape[1]), 'unmapped_vehicle_samples': int(L['unmapped']),
                                          'max_in_network': int(gt.sum(axis=0).max()),
                                          'entry_cells': L['ctm'].demand_cell_list}
    json.dump(info, open(os.path.join(out_dir, 'bench_info.json'), 'w'), indent=1)
    return info


def load_gt(out_dir, dt):
    p = os.path.join(out_dir, f'dt{dt:g}', 'ctm_gt.npy')
    return np.load(p if os.path.exists(p) else os.path.join(out_dir, 'ctm_gt.npy')).astype(float)


def compare(out_dir, fd=None, dt=12.0, start=0, steps=None):
    """open-loop CTM fed with the observed first cells of the entry links; error against the ground truth"""
    gt = load_gt(out_dir, dt)
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
    ap.add_argument('--dts', default='12,6')
    ap.add_argument('--end', type=float, default=None)
    ap.add_argument('--vtypes', default=None)
    a = ap.parse_args()
    dts = tuple(float(x) for x in a.dts.split(','))
    print(json.dumps(run_bench(a.routes, a.out, dts, a.end, vtypes=a.vtypes), indent=1))
    for dt in dts:
        print(dt, json.dumps(compare(a.out, dt=dt), indent=1))
