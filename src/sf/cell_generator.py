"""CTM cells of the Sioux Falls network, generated from the SUMO network (YIL-231).

Cell layout of a link with n positions (n = length / cell length, cell length = vf x dt):
- m = lane_change_zone / cell length lane-level positions at each end (m = 1 at dt = 12 s, 2 at dt = 6 s); they match
  the SUMO pieces where lane changes are forbidden;
- internal link: m x lane_in, merge, full..., diverge, m x lane_out;
- entry (zone) link: source C0, full..., diverge, m x lane_out;
- exit (zone) link: m x lane_in, merge, full..., sink C0.

Numbering (author, 2026-10-27): along the link from upstream, a lane-level position takes two numbers (left lane first,
as in the 5x5: C1 = left lane, C2 = right lane), a full-width position one number; source and sink are C0. A 5-position
5x5 link gives C1/C2, C3, C4, C5, C6/C7, i.e. the current 5x5 names. Roles are stored in the table: code must not infer
a role from a name. Cell ids keep the 5x5 format: A0.<link>.C<k> for internal links, A1.<link>.C<k> for zone links.

Run from src/:  python -m sf.cell_generator [dt]      (default: both 12 and 6)
Writes sumo_cfg/siouxfalls/CTMcfg/dt<dt>/: cells.csv, Cells.csv (id, x, y in km, for the plotting tools), links.csv,
signals.json, cell_index.json, summary.json.
"""
import csv
import json
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CFG = os.path.join(ROOT, 'sumo_cfg', 'siouxfalls')
SPEC_FILE = os.path.join(CFG, 'network_spec.json')
NET_FILE = os.path.join(CFG, 'siouxfalls.net.xml')
LEFT, RIGHT = 1, 0                      # SUMO lane index of the left and the right lane


def layout(role, n, m):
    """roles of the n positions of a link"""
    if role == 'internal':
        roles = ['lane_in'] * m + ['merge'] + ['full'] * (n - 2 * m - 2) + ['diverge'] + ['lane_out'] * m
    elif role == 'entry':
        roles = ['full'] * (n - m - 1) + ['diverge'] + ['lane_out'] * m
    else:
        roles = ['lane_in'] * m + ['merge'] + ['full'] * (n - m - 1)
    if len(roles) != n or min(roles.count('lane_in') + roles.count('lane_out'), 1) < 0:
        raise ValueError(f'{role} link with {n} positions cannot hold the template')
    return roles


def cells_of_link(lk, cell, m):
    """cells of one link: list of dicts (id, role, position, number, lane, start, end, pieces)"""
    n = int(round(lk['length'] / cell))
    roles = layout(lk['role'], n, m)
    pre = 'A0' if lk['role'] == 'internal' else 'A1'
    out, k = [], 1
    if lk['role'] == 'entry':
        out.append({'id': f'{pre}.{lk["id"]}.C0', 'role': 'source', 'position': 0, 'number': 0, 'lanes': [0, 1],
                    'start': 0.0, 'end': 0.0})
    for p, r in enumerate(roles, start=1):
        s, e = (p - 1) * cell, p * cell
        if r in ('lane_in', 'lane_out'):
            for ln in (LEFT, RIGHT):
                out.append({'id': f'{pre}.{lk["id"]}.C{k}', 'role': r, 'position': p, 'number': k, 'lanes': [ln],
                            'start': s, 'end': e})
                k += 1
        else:
            out.append({'id': f'{pre}.{lk["id"]}.C{k}', 'role': r, 'position': p, 'number': k, 'lanes': [0, 1],
                        'start': s, 'end': e})
            k += 1
    if lk['role'] == 'exit':
        out.append({'id': f'{pre}.{lk["id"]}.C0', 'role': 'sink', 'position': n + 1, 'number': 0, 'lanes': [0, 1],
                    'start': lk['length'], 'end': lk['length']})
    for c in out:                       # SUMO pieces (edge, from, to on that edge) covered by the cell
        c['pieces'] = []
        for pc in lk['pieces']:
            a, b = max(c['start'], pc['start']), min(c['end'], pc['end'])
            if b > a + 1e-6:
                c['pieces'].append([pc['edge'], round(a - pc['start'], 3), round(b - pc['start'], 3)])
        c['link'] = lk['id']
        c['n_positions'] = n
    return out


def intra_links(cells):
    """connections inside one link"""
    by_pos = {}
    for c in cells:
        if c['role'] in ('source', 'sink'):        # their arcs are added separately (types 'source' and 'sink')
            continue
        by_pos.setdefault(c['position'], []).append(c)
    out = []
    for p in sorted(by_pos)[:-1]:
        here, nxt = by_pos[p], by_pos[p + 1] if p + 1 in by_pos else None
        if nxt is None:
            continue
        for a in here:
            for b in nxt:
                if len(a['lanes']) == 1 and len(b['lanes']) == 1 and a['lanes'] != b['lanes']:
                    continue            # lane cell -> lane cell only within the same lane
                kind = ('merge' if len(a['lanes']) == 1 and len(b['lanes']) == 2 else
                        'diverge' if len(a['lanes']) == 2 and len(b['lanes']) == 1 else 'straight')
                out.append({'from': a['id'], 'to': b['id'], 'type': kind, 'tl': '', 'link_index': -1})
    return out


def signals(root):
    sig = {}
    for t in root.findall('tlLogic'):
        phases = [(float(p.get('duration')), p.get('state')) for p in t.findall('phase')]
        cycle = sum(d for d, _ in phases)
        green = {}
        t0 = 0.0
        for d, s in phases:
            for i, ch in enumerate(s):
                if ch in 'Gg':
                    green.setdefault(i, []).append([t0, t0 + d])
            t0 += d
        sig[t.get('id')] = {'offset': float(t.get('offset')), 'cycle': cycle, 'phases': phases,
                            'green': {str(i): w for i, w in sorted(green.items())}}
    return sig


def generate(dt):
    spec = json.load(open(SPEC_FILE))
    vf = spec['params']['vf']
    cell = vf * dt
    m = int(round(spec['params']['lane_change_zone'] / cell))
    root = ET.parse(NET_FILE).getroot()
    edge_link = {pc['edge']: lk['id'] for lk in spec['links'] for pc in lk['pieces']}
    all_cells, links = [], []
    first_lane_cell, last_lane_cell = {}, {}
    for lk in spec['links']:
        cs = cells_of_link(lk, cell, m)
        all_cells += cs
        links += intra_links(cs)
        for c in cs:
            if c['role'] == 'lane_in' and c['position'] == 1:
                first_lane_cell[(lk['id'], c['lanes'][0])] = c['id']
            if c['role'] == 'lane_out' and c['position'] == c['n_positions']:
                last_lane_cell[(lk['id'], c['lanes'][0])] = c['id']
        if lk['role'] == 'entry':
            links.append({'from': cs[0]['id'], 'to': cs[1]['id'], 'type': 'source', 'tl': '', 'link_index': -1})
        if lk['role'] == 'exit':
            links.append({'from': cs[-2]['id'], 'to': cs[-1]['id'], 'type': 'sink', 'tl': '', 'link_index': -1})
    for c in root.findall('connection'):                       # intersections: one CTM link per SUMO connection
        if not c.get('tl'):
            continue
        fl, tl_ = edge_link[c.get('from')], edge_link[c.get('to')]
        links.append({'from': last_lane_cell[(fl, int(c.get('fromLane')))],
                      'to': first_lane_cell[(tl_, int(c.get('toLane')))],
                      'type': 'intersection', 'tl': c.get('tl'), 'link_index': int(c.get('linkIndex')),
                      'dir': c.get('dir')})
    out = os.path.join(CFG, 'CTMcfg', f'dt{dt:g}')
    os.makedirs(out, exist_ok=True)
    xy = {n: np.array([v['x'], v['y']]) for n, v in spec['nodes'].items()}
    link_by_id = {lk['id']: lk for lk in spec['links']}
    with open(os.path.join(out, 'cells.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cell_id', 'link', 'role', 'position', 'number', 'lanes', 'start_m', 'end_m', 'length_m', 'n_lanes', 'pieces'])
        for c in all_cells:
            w.writerow([c['id'], c['link'], c['role'], c['position'], c['number'], ' '.join(map(str, c['lanes'])),
                        c['start'], c['end'], c['end'] - c['start'], len(c['lanes']),
                        ';'.join(f'{e}:{a}:{b}' for e, a, b in c['pieces'])])
    with open(os.path.join(out, 'Cells.csv'), 'w', newline='') as f:   # plotting coordinates (km), as the 5x5 file
        w = csv.writer(f)
        w.writerow(['cell_id', 'x', 'y'])
        for c in all_cells:
            lk = link_by_id[c['link']]
            a, b = xy[lk['from']], xy[lk['to']]
            u = (b - a) / np.linalg.norm(b - a)
            right = np.array([u[1], -u[0]])
            s = 0.5 * (c['start'] + c['end'])
            off = 30.0 if len(c['lanes']) == 2 else (15.0 if c['lanes'][0] == LEFT else 45.0)
            x, y = (a + s * u + off * right) / 1000.0
            w.writerow([c['id'], round(float(x), 4), round(float(y), 4)])
    with open(os.path.join(out, 'links.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['from', 'to', 'type', 'tl', 'link_index', 'dir'])
        for l in links:
            w.writerow([l['from'], l['to'], l['type'], l['tl'], l['link_index'], l.get('dir', '')])
    json.dump(signals(root), open(os.path.join(out, 'signals.json'), 'w'), indent=1)
    json.dump([c['id'] for c in all_cells], open(os.path.join(out, 'cell_index.json'), 'w'))
    summary = check(all_cells, links, spec, cell, m)
    summary.update({'dt': dt, 'cell_m': cell, 'lane_zone_positions': m})
    json.dump(summary, open(os.path.join(out, 'summary.json'), 'w'), indent=1)
    return summary


def check(cells, links, spec, cell, m):
    roles = {}
    for c in cells:
        roles[c['role']] = roles.get(c['role'], 0) + 1
    ids = [c['id'] for c in cells]
    inp, outp = {}, {}
    for l in links:
        outp[l['from']] = outp.get(l['from'], 0) + 1
        inp.setdefault(l['to'], set()).add(l['from'] if l['type'] != 'intersection' else l['from'].split('.')[1])
    no_in = [c['id'] for c in cells if c['role'] != 'source' and c['id'] not in inp]
    no_out = [c['id'] for c in cells if c['role'] != 'sink' and c['id'] not in outp]
    # every cell's pieces cover exactly its length; lane cells lie on pieces without lane changes and vice versa
    cover = [c['id'] for c in cells if c['role'] not in ('source', 'sink')
             and abs(sum(b - a for _, a, b in c['pieces']) - (c['end'] - c['start'])) > 1e-6]
    lc = {pc['edge']: pc['lane_change'] for lk in spec['links'] for pc in lk['pieces']}
    lane_on_lc = [c['id'] for c in cells if len(c['lanes']) == 1 and any(lc[e] for e, _, _ in c['pieces'])]
    full_on_nolc = [c['id'] for c in cells if c['role'] in ('merge', 'full', 'diverge') and any(not lc[e] for e, _, _ in c['pieces'])]
    rec_inputs = {}
    for l in links:
        if l['type'] == 'intersection':
            rec_inputs.setdefault(l['to'], set()).add(l['from'].split('.')[1])
    dist = {}
    for v in rec_inputs.values():
        dist[len(v)] = dist.get(len(v), 0) + 1
    return {'cells': len(cells), 'by_role': roles, 'unique_ids': len(set(ids)) == len(ids), 'links': len(links),
            'intersection_links': sum(1 for l in links if l['type'] == 'intersection'),
            'cells_without_input': no_in, 'cells_without_output': no_out, 'cells_not_covered_by_pieces': cover,
            'lane_cells_on_lane_change_pieces': lane_on_lc, 'full_cells_on_no_lane_change_pieces': full_on_nolc,
            'receiving_cells_by_upstream_approaches': {str(k): v for k, v in sorted(dist.items())}}


if __name__ == '__main__':
    for dt in ([float(a) for a in sys.argv[1:]] or [12.0, 6.0]):
        print(json.dumps(generate(dt), indent=1))
