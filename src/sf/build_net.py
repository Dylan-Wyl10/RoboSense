"""Sioux Falls SUMO network for the CTM experiments (YIL-231).

Design agreed with the author on YIL-231 (2026-10-26/27):
- topology of the TNTP Sioux Falls network, shape of the real map: node positions are the TNTP lon/lat projected to
  metres and scaled by SCALE, then moved as little as possible so that every link is straight and its length is a
  whole number of CELL metres, with at least MIN_CELLS cells (the CTM link template: lane cells, merge, ..., diverge,
  lane cells);
- 2 lanes and VF m/s on every link; zone (entry/exit) links of ZONE_CELLS cells at every node with at most 3 links;
- every link is three SUMO edges (suffix a, b, c): the first and the last LC_ZONE metres forbid lane changes (they are
  the CTM's lane-level cells), only the middle part allows them;
- connections by rule: the right lane takes the right turns and the through movement, the left lane the through
  movement and the left turns; no U-turns;
- signals: one phase per approach, 20 s green + 2 s yellow + 3 s all-red (the 5x5 timing), offset 0.

Run from src/:  python -m sf.build_net
Writes sumo_cfg/siouxfalls/net/ (plain XML, netconvert log, siouxfalls.net.xml) and sumo_cfg/siouxfalls/network_spec.json.
"""
import json
import math
import os
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CFG = os.path.join(ROOT, 'sumo_cfg', 'siouxfalls')
SRC = os.path.join(CFG, 'source')
NETDIR = os.path.join(CFG, 'net')
NET_FILE = os.path.join(CFG, 'siouxfalls.net.xml')
SPEC_FILE = os.path.join(CFG, 'network_spec.json')

VF = 16.0               # m/s, free-flow speed (speed limit of every lane)
DT = 12.0               # s, CTM step of the main version
DT_FINE = 6.0           # s, finer version on the same network
CELL = VF * DT          # 192 m: every link is a whole number of these (and so of 96 m cells)
MIN_CELLS = 4           # every link has at least 4 cells at DT
SCALE = 1.03            # real map x 1.03 (smallest node moves near the real size, YIL-231 2026-10-27)
ZONE_CELLS = 3          # zone links: 3 cells (576 m), as the 5x5 entry/exit links
LC_ZONE = CELL          # no lane changes in the first and the last cell of every link
LANES = 2
EARTH_R = 6371000.0
TLS = dict(green=20, yellow=2, allred=3)
NO_LC = 'emergency'     # lane-change permission on the end pieces: only emergency vehicles (i.e. nobody here)


# ---------------------------------------------------------------- input
def read_tntp():
    lonlat = {}
    for line in open(os.path.join(SRC, 'SiouxFalls_node.tntp')):
        p = line.split()
        if p and p[0].isdigit():
            lonlat[int(p[0])] = (float(p[1]), float(p[2]))
    pairs = set()
    for line in open(os.path.join(SRC, 'SiouxFalls_net.tntp')):
        p = line.split()
        if len(p) >= 3 and p[0].isdigit():
            a, b = int(p[0]), int(p[1])
            pairs.add((min(a, b), max(a, b)))
    return lonlat, sorted(pairs)


def project(lonlat):
    """equirectangular projection around the centroid (error < 0.1% over the 14 km of the network)"""
    lon0 = np.mean([v[0] for v in lonlat.values()])
    lat0 = np.mean([v[1] for v in lonlat.values()])
    k = math.cos(math.radians(lat0))
    return {n: np.array([math.radians(lo - lon0) * EARTH_R * k, math.radians(la - lat0) * EARTH_R])
            for n, (lo, la) in lonlat.items()}


# ---------------------------------------------------------------- geometry
def snap(P0, pairs):
    """move the nodes as little as possible so that every straight link is a whole number of cells (>= MIN_CELLS)"""
    nodes = sorted(P0)
    idx = {n: a for a, n in enumerate(nodes)}
    I = np.array([idx[i] for i, j in pairs]); J = np.array([idx[j] for i, j in pairs])
    X0 = np.array([P0[n] for n in nodes])
    d0 = np.linalg.norm(X0[I] - X0[J], axis=1)
    ncell = np.maximum(MIN_CELLS, np.round(d0 / CELL)).astype(int)
    L = ncell * CELL

    def res(x):
        X = x.reshape(-1, 2)
        return np.concatenate([100.0 * (np.linalg.norm(X[I] - X[J], axis=1) - L), (X - X0).ravel()])

    sol = least_squares(res, X0.ravel(), xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=20000)
    X = sol.x.reshape(-1, 2)
    P = {n: X[idx[n]] for n in nodes}
    return P, {e: int(c) for e, c in zip(pairs, ncell)}, {e: float(d) for e, d in zip(pairs, d0)}


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * ab)))


def seg_seg(a, b, c, d):
    return min(seg_dist(a, c, d), seg_dist(b, c, d), seg_dist(c, a, b), seg_dist(d, a, b))


def angdiff(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def zone_stubs(P, pairs, zones, length):
    """direction of each zone link: the most clearance from other links, nodes and stubs, at least 35 deg from the
    node's links; degree-2 nodes get two zone links (as the corners of the 5x5)"""
    deg = {n: sum(1 for e in pairs if n in e) for n in P}
    stubs = []
    for n in zones:
        used = [math.atan2(*(P[j if i == n else i] - P[n])[::-1]) for i, j in pairs if n in (i, j)]
        for c in range(2 if deg[n] == 2 else 1):
            best = None
            for a10 in range(0, 360, 2):
                a = math.radians(a10)
                gap = min(angdiff(a, u) for u in used)
                if gap < math.radians(35):
                    continue
                u = np.array([math.cos(a), math.sin(a)])
                s0, s1 = P[n] + 150.0 * u, P[n] + (length + CELL) * u     # the stub plus its source/sink box
                cl = min([seg_seg(s0, s1, P[i], P[j]) for i, j in pairs if n not in (i, j)] +
                         [seg_dist(P[m], s0, s1) for m in P if m != n] +
                         [seg_seg(s0, s1, t0, t1) for t0, t1 in [(st['p0'], st['p1']) for st in stubs]] + [1e9])
                key = (min(cl, 450.0), gap)
                if best is None or key > best[0]:
                    best = (key, a, s0, s1)
            (cl, gap), a, s0, s1 = best
            used.append(a)
            stubs.append({'node': n, 'k': c + 1, 'angle': a, 'clearance': cl, 'p0': s0, 'p1': s1,
                          'end': P[n] + length * np.array([math.cos(a), math.sin(a)])})
    return stubs


# ---------------------------------------------------------------- network description
def build_spec():
    lonlat, pairs = read_tntp()
    P0 = {n: v * SCALE for n, v in project(lonlat).items()}
    P, ncell, dmap = snap(P0, pairs)
    deg = {n: sum(1 for e in pairs if n in e) for n in P}
    zones = [n for n in sorted(P) if deg[n] <= 3]
    zlen = ZONE_CELLS * CELL
    stubs = zone_stubs(P, pairs, zones, zlen)

    nodes = {str(n): {'x': float(P[n][0]), 'y': float(P[n][1]), 'type': 'traffic_light', 'tntp': n,
                      'lonlat': list(lonlat[n]), 'moved_m': float(np.linalg.norm(P[n] - P0[n]))} for n in sorted(P)}
    links = []

    def point(a, b, s):
        u = (P_[b] - P_[a]) / np.linalg.norm(P_[b] - P_[a])
        return P_[a] + s * u

    P_ = {str(n): P[n] for n in P}
    for e, (i, j) in enumerate(pairs, start=1):
        L = ncell[(i, j)] * CELL
        na, nb = f'n{e}a', f'n{e}b'                               # LC_ZONE from node i and from node j
        nodes[na] = dict(zip(('x', 'y'), map(float, point(str(i), str(j), LC_ZONE))), type='priority')
        nodes[nb] = dict(zip(('x', 'y'), map(float, point(str(j), str(i), LC_ZONE))), type='priority')
        for lid, fr, to, n1, n2 in ((f'E{e}', str(i), str(j), na, nb), (f'-E{e}', str(j), str(i), nb, na)):
            links.append({'id': lid, 'tntp': [int(fr), int(to)], 'from': fr, 'to': to, 'role': 'internal',
                          'length': L, 'map_length': round(dmap[(i, j)] / SCALE, 1),
                          'pieces': [{'edge': lid + 'a', 'from': fr, 'to': n1, 'start': 0.0, 'end': LC_ZONE, 'lane_change': False},
                                     {'edge': lid + 'b', 'from': n1, 'to': n2, 'start': LC_ZONE, 'end': L - LC_ZONE, 'lane_change': True},
                                     {'edge': lid + 'c', 'from': n2, 'to': to, 'start': L - LC_ZONE, 'end': L, 'lane_change': False}]})
    for k, st in enumerate(stubs, start=101):
        n, z, m = str(st['node']), f"{st['node']}_{st['k']}", f"{st['node']}_{st['k']}m"
        nodes[z] = {'x': float(st['end'][0]), 'y': float(st['end'][1]), 'type': 'dead_end'}
        u = (st['end'] - P_[n]) / np.linalg.norm(st['end'] - P_[n])
        pm = P_[n] + LC_ZONE * u                                   # LC_ZONE from the intersection
        nodes[m] = {'x': float(pm[0]), 'y': float(pm[1]), 'type': 'priority'}
        links.append({'id': f'E{k}', 'from': z, 'to': n, 'role': 'entry', 'zone': int(n), 'length': zlen,
                      'pieces': [{'edge': f'E{k}b', 'from': z, 'to': m, 'start': 0.0, 'end': zlen - LC_ZONE, 'lane_change': True},
                                 {'edge': f'E{k}c', 'from': m, 'to': n, 'start': zlen - LC_ZONE, 'end': zlen, 'lane_change': False}]})
        links.append({'id': f'-E{k}', 'from': n, 'to': z, 'role': 'exit', 'zone': int(n), 'length': zlen,
                      'pieces': [{'edge': f'-E{k}a', 'from': n, 'to': m, 'start': 0.0, 'end': LC_ZONE, 'lane_change': False},
                                 {'edge': f'-E{k}b', 'from': m, 'to': z, 'start': LC_ZONE, 'end': zlen, 'lane_change': True}]})
    for lk in links:
        lk['cells'] = {f'{DT:g}': int(round(lk['length'] / CELL)), f'{DT_FINE:g}': int(round(lk['length'] / (VF * DT_FINE)))}
    spec = {'params': {'vf': VF, 'dt': DT, 'dt_fine': DT_FINE, 'cell': CELL, 'cell_fine': VF * DT_FINE,
                       'min_cells': MIN_CELLS, 'scale': SCALE, 'zone_cells': ZONE_CELLS, 'lane_change_zone': LC_ZONE,
                       'lanes': LANES, 'tls': TLS, 'u_turns': False},
            'nodes': nodes, 'links': links,
            'zones': [{'node': st['node'], 'entry': f'E{k}', 'exit': f'-E{k}', 'end_node': f"{st['node']}_{st['k']}",
                       'clearance_m': round(st['clearance'], 1)} for k, st in enumerate(stubs, start=101)]}
    return spec


# ---------------------------------------------------------------- connections
def rule_connections(spec):
    """lane-to-lane connections at the signalised nodes (rule in the module docstring) and straight lane i -> lane i
    connections between the pieces of a link"""
    nodes = spec['nodes']
    xy = {n: np.array([v['x'], v['y']]) for n, v in nodes.items()}
    con = []
    for lk in spec['links']:                                    # piece -> piece, lane i -> lane i
        for p, q in zip(lk['pieces'][:-1], lk['pieces'][1:]):
            con += [(p['edge'], q['edge'], ln, ln) for ln in range(LANES)]
    incoming = {}
    outgoing = {}
    for lk in spec['links']:
        incoming.setdefault(lk['to'], []).append(lk)
        outgoing.setdefault(lk['from'], []).append(lk)
    moves = []
    for v, nd in nodes.items():
        if nd['type'] != 'traffic_light':
            continue
        for a in incoming.get(v, []):
            last = a['pieces'][-1]
            h_in = xy[v] - xy[last['from']]
            cands = []
            for b in outgoing.get(v, []):
                if b['to'] == a['from']:                          # U-turn: not allowed
                    continue
                first = b['pieces'][0]
                h_out = xy[first['to']] - xy[v]
                th = math.degrees(math.atan2(h_in[0] * h_out[1] - h_in[1] * h_out[0], h_in @ h_out))   # + = left
                cands.append((th, b['id'], first['edge']))
            cands.sort()
            thr = min(cands, key=lambda c: abs(c[0]))
            through = thr if abs(thr[0]) <= 45.0 else None
            for th, bid, edge in cands:
                if through is not None and bid == through[1]:
                    lanes = [0, 1]
                elif through is not None:
                    lanes = [0] if th < through[0] else [1]
                else:
                    right = [c for c in cands if c[0] < 0]
                    left = [c for c in cands if c[0] > 0]
                    if right and left:
                        lanes = [0] if th < 0 else [1]
                    else:                                       # all on one side: split the sorted list
                        lanes = [0] if cands.index((th, bid, edge)) < len(cands) / 2 else [1]
                for ln in lanes:
                    con.append((last['edge'], edge, ln, ln))
                    moves.append({'node': v, 'from_link': a['id'], 'to_link': bid, 'lane': ln, 'turn_deg': round(th, 1)})
    return con, moves


# ---------------------------------------------------------------- output
def write_plain(spec, con):
    os.makedirs(NETDIR, exist_ok=True)
    with open(os.path.join(NETDIR, 'sf.nod.xml'), 'w') as f:
        f.write('<nodes>\n')
        for n, v in spec['nodes'].items():
            f.write(f'    <node id="{n}" x="{v["x"]:.3f}" y="{v["y"]:.3f}" type="{v["type"]}"/>\n')
        f.write('</nodes>\n')
    with open(os.path.join(NETDIR, 'sf.edg.xml'), 'w') as f:
        f.write('<edges>\n')
        for lk in spec['links']:
            for p in lk['pieces']:
                head = (f'    <edge id="{p["edge"]}" from="{p["from"]}" to="{p["to"]}" numLanes="{LANES}" '
                        f'speed="{VF:.2f}" length="{p["end"] - p["start"]:.2f}"')
                if p['lane_change']:
                    f.write(head + '/>\n')
                else:
                    f.write(head + '>\n')
                    for ln in range(LANES):
                        f.write(f'        <lane index="{ln}" changeLeft="{NO_LC}" changeRight="{NO_LC}"/>\n')
                    f.write('    </edge>\n')
        f.write('</edges>\n')
    with open(os.path.join(NETDIR, 'sf.con.xml'), 'w') as f:
        f.write('<connections>\n')
        for a, b, la, lb in con:
            f.write(f'    <connection from="{a}" to="{b}" fromLane="{la}" toLane="{lb}"/>\n')
        f.write('</connections>\n')
    cfg = f"""<configuration>
    <input>
        <node-files value="sf.nod.xml"/>
        <edge-files value="sf.edg.xml"/>
        <connection-files value="sf.con.xml"/>
    </input>
    <output>
        <output-file value="../siouxfalls.net.xml"/>
    </output>
    <processing>
        <offset.disable-normalization value="true"/>
    </processing>
    <junctions>
        <no-internal-links value="true"/>
        <no-turnarounds value="true"/>
    </junctions>
    <tls_building>
        <tls.default-type value="static"/>
        <tls.layout value="incoming"/>
        <tls.green.time value="{TLS['green']}"/>
        <tls.yellow.time value="{TLS['yellow']}"/>
        <tls.allred.time value="{TLS['allred']}"/>
    </tls_building>
</configuration>
"""
    open(os.path.join(NETDIR, 'sf.netccfg'), 'w').write(cfg)


def netconvert():
    r = subprocess.run(['netconvert', '-c', 'sf.netccfg'], cwd=NETDIR, capture_output=True, text=True)
    open(os.path.join(NETDIR, 'netconvert.log'), 'w').write(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit('netconvert failed, see net/netconvert.log')


# ---------------------------------------------------------------- checks
def check(spec, moves):
    root = ET.parse(NET_FILE).getroot()
    out = {}
    lanes = {l.get('id'): l for e in root.findall('edge') if e.get('function') != 'internal' for l in e.findall('lane')}
    jxy = {j.get('id'): np.array([float(j.get('x')), float(j.get('y'))]) for j in root.findall('junction')}
    # 1. every piece has the set length; every link is a whole number of cells, >= MIN_CELLS; straight links close
    bad_len, gaps = [], []
    for lk in spec['links']:
        for p in lk['pieces']:
            for ln in range(LANES):
                L = float(lanes[f'{p["edge"]}_{ln}'].get('length'))
                if abs(L - (p['end'] - p['start'])) > 0.01:
                    bad_len.append(p['edge'])
        if lk['role'] == 'internal':
            gaps.append(abs(float(np.linalg.norm(jxy[lk['to']] - jxy[lk['from']])) - lk['length']))
    out['pieces_with_wrong_length'] = sorted(set(bad_len))
    out['max_gap_junction_distance_vs_length_m'] = round(max(gaps), 3)
    out['min_cells_per_link'] = min(lk['cells'][f'{DT:g}'] for lk in spec['links'] if lk['role'] == 'internal')
    # 2. lane changes forbidden exactly on the end pieces
    wrong_lc = []
    for lk in spec['links']:
        for p in lk['pieces']:
            for ln in range(LANES):
                l = lanes[f'{p["edge"]}_{ln}']
                banned = l.get('changeLeft') == NO_LC and l.get('changeRight') == NO_LC
                if banned == p['lane_change']:
                    wrong_lc.append(f'{p["edge"]}_{ln}')
    out['lanes_with_wrong_lane_change_rule'] = wrong_lc
    # 3. connections: what netconvert kept vs. the rule; no U-turns; every approach lane served
    want = {(m['from_link'], m['to_link'], m['lane']) for m in moves}
    edge_link = {p['edge']: lk['id'] for lk in spec['links'] for p in lk['pieces']}
    tls_con = [c for c in root.findall('connection') if c.get('tl')]
    got = {(edge_link[c.get('from')], edge_link[c.get('to')], int(c.get('fromLane'))) for c in tls_con}
    out['connections_rule_vs_net'] = {'rule': len(want), 'net': len(got), 'missing': sorted(want - got)[:5],
                                      'extra': sorted(got - want)[:5]}
    out['u_turns'] = sum(1 for c in tls_con if c.get('dir') == 't')
    served = {(c.get('from'), c.get('fromLane')) for c in tls_con}
    approach_lanes = {(lk['pieces'][-1]['edge'], str(ln)) for lk in spec['links'] if lk['role'] != 'exit' for ln in range(LANES)}
    out['approach_lanes_without_connection'] = sorted(approach_lanes - served)
    # 4. signals: one approach per phase, cycle = 25 s x approaches
    tl = {t.get('id'): t for t in root.findall('tlLogic')}
    multi, cyc = [], {}
    for tid, t in tl.items():
        st = [p.get('state') for p in t.findall('phase')]
        cyc[tid] = sum(int(float(p.get('duration'))) for p in t.findall('phase'))
        cons = [c for c in tls_con if c.get('tl') == tid]
        for s in st:
            apps = {c.get('from') for c in cons if s[int(c.get('linkIndex'))] in 'Gg'}
            if len(apps) > 1:
                multi.append(tid)
    out['phases_with_more_than_one_approach'] = sorted(set(multi))
    out['cycle_lengths'] = {str(k): v for k, v in sorted({c: list(cyc.values()).count(c) for c in set(cyc.values())}.items())}
    # 5. receiving lanes: number of upstream approaches
    rec = {}
    for c in tls_con:
        rec.setdefault((c.get('to'), c.get('toLane')), set()).add(c.get('from'))
    cnt = {}
    for v in rec.values():
        cnt[len(v)] = cnt.get(len(v), 0) + 1
    out['receiving_lanes_by_number_of_inputs'] = {str(k): v for k, v in sorted(cnt.items())}
    return out


def main():
    spec = build_spec()
    con, moves = rule_connections(spec)
    write_plain(spec, con)
    netconvert()
    spec['movements'] = moves
    spec['checks'] = check(spec, moves)
    moved = sorted(((v['moved_m'], n) for n, v in spec['nodes'].items() if 'moved_m' in v), reverse=True)
    spec['checks']['node_moves_m'] = {'median': round(float(np.median([m for m, _ in moved])), 1),
                                      'max': [round(moved[0][0], 1), moved[0][1]]}
    json.dump(spec, open(SPEC_FILE, 'w'), indent=1)
    print(json.dumps(spec['checks'], indent=1))


if __name__ == '__main__':
    main()
