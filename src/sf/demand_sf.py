"""Demand of the Sioux Falls network (YIL-231), following the 5x5 procedure (sumo_cfg/5x5net/od/flow350_7200s_odfix).

1. OD between the 17 zone nodes, fitted so that the link flows reproduce the TNTP equilibrium flows
   (SiouxFalls_flow.tntp): path flows on the 3 shortest paths (by link length) of every OD pair, non-negative least
   squares; OD = sum over the paths of each pair.
2. Scale: one factor for the whole OD so that the busiest signal approach runs at V/C = TARGET_VC (author,
   2026-10-28): capacity of an approach = 2 lanes x q_max x 20 s / cycle (cycle = 25 s x approaches at the node),
   q_max = 1920 veh/h/lane (5x5 FD).
3. SUMO files, as the 5x5: TAZ file (<node>_in = first piece of the zone's entry links, <node>_out = last piece of
   its exit links), O-format OD file over 2 h, od2trips (vType bgv, prefix bgv, default seed).
DUE (duaIterate, 50 iterations, the 5x5 options) is started separately: see run_dua().

Run from src/:  python -m sf.demand_sf fit|files|dua --name <folder under sumo_cfg/siouxfalls/od/>
"""
import argparse
import itertools
import json
import os
import shutil
import subprocess
import sys

import networkx as nx
import numpy as np
from scipy.optimize import lsq_linear

from sf.ctm_sf import CFG

SPEC = os.path.join(CFG, 'network_spec.json')
SRC = os.path.join(CFG, 'source')
NET = os.path.join(CFG, 'siouxfalls.net.xml')
VTYPES = os.path.join(CFG, 'v_type.add.xml')
TARGET_VC = 0.85
Q_LANE = 1920.0           # veh/h/lane, 5x5 FD
GREEN = 20.0              # s per approach
PHASE = 25.0              # s per approach (20 + 2 + 3)
HOURS = 2.0               # departures spread over 0-7200 s
K_PATHS = 3


def tntp_flows():
    v = {}
    for line in open(os.path.join(SRC, 'SiouxFalls_flow.tntp')):
        p = line.split()
        if len(p) >= 3 and p[0].isdigit():
            v[(int(p[0]), int(p[1]))] = float(p[2])
    return v


def fit_od():
    spec = json.load(open(SPEC))
    zones = sorted({z['node'] for z in spec['zones']})
    G = nx.DiGraph()
    for lk in spec['links']:
        if lk['role'] == 'internal':
            G.add_edge(int(lk['from']), int(lk['to']), w=lk['length'])
    v = tntp_flows()
    links = sorted(v)
    lidx = {l: i for i, l in enumerate(links)}
    target = np.array([v[l] for l in links])
    cols, meta = [], []
    for o, d in itertools.permutations(zones, 2):
        for m, p in enumerate(nx.shortest_simple_paths(G, o, d, weight='w')):
            if m >= K_PATHS:
                break
            col = np.zeros(len(links))
            for a, b in zip(p[:-1], p[1:]):
                col[lidx[(a, b)]] = 1.0
            cols.append(col)
            meta.append((o, d))
    A = np.array(cols).T
    h = lsq_linear(A, target, bounds=(0, np.inf), method='bvls', max_iter=20000).x
    fit = A @ h
    rel = np.abs(fit - target) / target
    od = {}
    for x, (o, d) in zip(h, meta):
        od[(o, d)] = od.get((o, d), 0.0) + float(x)
    stats = {'R2': float(1 - ((fit - target) ** 2).sum() / ((target - target.mean()) ** 2).sum()),
             'max_rel_err': float(rel.max()), 'links_within_5pct': int((rel <= 0.05).sum()),
             'od_pairs': len(zones) * (len(zones) - 1), 'od_pairs_positive': int(sum(1 for x in od.values() if x > 1e-6)),
             'total_tntp_units': float(sum(od.values()))}
    return zones, od, {l: float(f) for l, f in zip(links, fit)}, stats


def scale(zones, od, link_flow):
    """factor f so that the busiest approach has V/C = TARGET_VC"""
    spec = json.load(open(SPEC))
    approaches = {}
    for lk in spec['links']:
        if lk['role'] in ('internal', 'entry'):
            approaches.setdefault(lk['to'], []).append(lk)
    rows = []
    entry_links = {}
    for lk in spec['links']:
        if lk['role'] == 'entry':
            entry_links.setdefault(lk['zone'], []).append(lk['id'])
    for node, aps in approaches.items():
        cap = 2 * Q_LANE * GREEN / (PHASE * len(aps))
        for lk in aps:
            if lk['role'] == 'internal':
                flow = link_flow[(int(lk['from']), int(lk['to']))]
            else:
                z = lk['zone']
                flow = sum(x for (o, d), x in od.items() if o == z) / len(entry_links[z])
            rows.append({'approach': lk['id'], 'node': node, 'cap_vph': cap, 'flow_tntp': flow})
    f = TARGET_VC / max(r['flow_tntp'] / r['cap_vph'] for r in rows)
    for r in rows:
        r['flow_vph'] = r['flow_tntp'] * f
        r['vc'] = r['flow_vph'] / r['cap_vph']
    return f, sorted(rows, key=lambda r: -r['vc'])


def integer_counts(od_vph):
    """vehicles per OD over HOURS, rounded with the total kept (largest remainder)"""
    raw = {k: v * HOURS for k, v in od_vph.items() if v > 0}
    base = {k: int(np.floor(v)) for k, v in raw.items()}
    rest = int(round(sum(raw.values()))) - sum(base.values())
    for k in sorted(raw, key=lambda k: raw[k] - base[k], reverse=True)[:max(rest, 0)]:
        base[k] += 1
    return {k: c for k, c in base.items() if c > 0}


def write_files(outdir, zones, counts):
    spec = json.load(open(SPEC))
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, 'taz.xml'), 'w') as f:
        f.write('<additional>\n    <tazs>\n')
        for z in zones:
            ins = [lk['pieces'][0]['edge'] for lk in spec['links'] if lk['role'] == 'entry' and lk['zone'] == z]
            outs = [lk['pieces'][-1]['edge'] for lk in spec['links'] if lk['role'] == 'exit' and lk['zone'] == z]
            f.write(f'        <taz id="{z}_in" edges="{" ".join(ins)}"/>\n')
            f.write(f'        <taz id="{z}_out" edges="{" ".join(outs)}"/>\n')
        f.write('    </tazs>\n</additional>\n')
    with open(os.path.join(outdir, 'od_file_bgv.od'), 'w') as f:
        f.write(f'$O;D2\n0.00 {HOURS:.1f}\n1.00\n')
        for (o, d), c in sorted(counts.items()):
            f.write(f'{o}_in {d}_out {c}\n')
    r = subprocess.run(['od2trips', '-n', 'taz.xml', '-d', 'od_file_bgv.od', '-o', 'od_file_bgv.odtrips.xml',
                        '--vtype', 'bgv', '--prefix', 'bgv'], cwd=outdir, capture_output=True, text=True)
    open(os.path.join(outdir, 'od2trips.log'), 'w').write(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit('od2trips failed: ' + r.stderr[-500:])


def run_dua(outdir, iterations=50):
    """duaIterate with the options of the 5x5 (gen_odfix.sh step 3), in <outdir>/dualogs"""
    dl = os.path.join(outdir, 'dualogs')
    if os.path.exists(dl):
        raise SystemExit(f'refusing to overwrite {dl}')
    os.makedirs(dl)
    env = dict(os.environ, SUMO_HOME='/usr/share/sumo', PYTHONPATH='/usr/share/sumo/tools')
    cmd = [sys.executable, '/usr/share/sumo/tools/assign/duaIterate.py', '-n', NET, '-t', '../od_file_bgv.odtrips.xml',
           '--additional', VTYPES, '--no-gzip', '-l', str(iterations),
           'duarouter--vtype-output', 'dummy.xml', 'duarouter--additional-files', VTYPES]
    with open(os.path.join(dl, 'stdout.log'), 'w') as out:
        r = subprocess.run(cmd, cwd=dl, stdout=out, stderr=subprocess.STDOUT, env=env)
    return r.returncode


def due_check(outdir):
    """per DUE iteration: end of the DUE simulation, teleports, arrivals, mean travel time (last step of
    summary_NNN.xml), as the 5x5 checks (od/flow350_7200s_odfix/checks/demand_checks.md)"""
    import xml.etree.ElementTree as ET
    dl = os.path.join(outdir, 'dualogs')
    rows = []
    for it in sorted(d for d in os.listdir(dl) if d.isdigit()):
        f = os.path.join(dl, it, f'summary_{it}.xml')
        if not os.path.exists(f):
            continue
        last = None
        try:
            for _, el in ET.iterparse(f):
                if el.tag == 'step':
                    last = dict(el.attrib)
                el.clear()
        except ET.ParseError:                 # iteration still running
            continue
        if last:
            rows.append({'iteration': int(it), 'end_s': float(last['time']), 'teleports': int(last['teleports']),
                         'arrived': int(last['arrived']), 'loaded': int(last['loaded']),
                         'mean_travel_time_s': float(last['meanTravelTime'])})
    ok = [r for r in rows if r['arrived'] == r['loaded'] and r['teleports'] <= 10]
    best = min(ok or rows, key=lambda r: r['mean_travel_time_s'])
    json.dump({'iterations': rows, 'lowest_mean_travel_time_without_jams': best}, open(os.path.join(outdir, 'due_iterations.json'), 'w'), indent=1)
    lines = ['| iteration | end (s) | teleports | arrived / loaded | mean travel time (s) |', '|---|---|---|---|---|']
    lines += [f"| {r['iteration']:03d} | {r['end_s']:.0f} | {r['teleports']} | {r['arrived']} / {r['loaded']} | {r['mean_travel_time_s']:.0f} |" for r in rows]
    open(os.path.join(outdir, 'due_iterations.md'), 'w').write('\n'.join(lines) + '\n')
    return rows, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['fit', 'files', 'dua', 'due_check'])
    ap.add_argument('--name', default='vc085_7200s')
    a = ap.parse_args()
    outdir = os.path.join(CFG, 'od', a.name)
    if a.step in ('fit', 'files'):
        zones, od, link_flow, stats = fit_od()
        f, rows = scale(zones, od, link_flow)
        od_vph = {k: v * f for k, v in od.items()}
        counts = integer_counts(od_vph)
        summary = {'fit': stats, 'factor': f, 'target_vc': TARGET_VC, 'q_lane': Q_LANE,
                   'total_veh_per_h': float(sum(od_vph.values())), 'vehicles_2h': int(sum(counts.values())),
                   'od_pairs_with_vehicles': len(counts), 'busiest_approaches': rows[:8],
                   'zone_productions_vph': {z: round(sum(v for (o, d), v in od_vph.items() if o == z), 1) for z in zones},
                   'zone_attractions_vph': {z: round(sum(v for (o, d), v in od_vph.items() if d == z), 1) for z in zones}}
        print(json.dumps({k: summary[k] for k in ('fit', 'factor', 'total_veh_per_h', 'vehicles_2h', 'od_pairs_with_vehicles')}, indent=1))
        print('busiest approaches:', [(r['approach'], r['node'], round(r['flow_vph']), round(r['cap_vph']), round(r['vc'], 2)) for r in rows[:6]])
        if a.step == 'files':
            if os.path.exists(os.path.join(outdir, 'od_file_bgv.od')):
                raise SystemExit(f'refusing to overwrite {outdir}')
            write_files(outdir, zones, counts)
            json.dump(summary, open(os.path.join(outdir, 'demand_summary.json'), 'w'), indent=1)
            json.dump([[o, d, round(v, 3)] for (o, d), v in sorted(od_vph.items()) if v > 0],
                      open(os.path.join(outdir, 'od_vph.json'), 'w'))
            print('written to', outdir)
    elif a.step == 'dua':
        print('duaIterate exit code', run_dua(outdir))
    else:
        rows, best = due_check(outdir)
        for r in rows:
            print(r)
        print('lowest mean travel time without jams:', best)


if __name__ == '__main__':
    main()
