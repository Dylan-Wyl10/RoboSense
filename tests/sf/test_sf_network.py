"""Checks of the Sioux Falls network and its CTM cells (YIL-231). Run from the repository root:
    python -m pytest tests/sf -q        (or: python tests/sf/test_sf_network.py)
Needs sumo_cfg/siouxfalls/ built by `python -m sf.build_net` and `python -m sf.cell_generator` (run from src/)."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from sf.cell_generator import cells_of_link, layout          # noqa: E402

CFG = os.path.join(ROOT, 'sumo_cfg', 'siouxfalls')


def test_5x5_names_are_reproduced():
    """a 400 m link at 80 m cells gets exactly the 5x5 names and roles"""
    lk = {'id': 'E1', 'role': 'internal', 'length': 400.0,
          'pieces': [{'edge': 'E1', 'start': 0.0, 'end': 400.0, 'lane_change': True}]}
    cs = cells_of_link(lk, 80.0, 1)
    got = [(c['id'], c['role'], c['lanes']) for c in cs]
    assert got == [('A0.E1.C1', 'lane_in', [1]), ('A0.E1.C2', 'lane_in', [0]), ('A0.E1.C3', 'merge', [0, 1]),
                   ('A0.E1.C4', 'full', [0, 1]), ('A0.E1.C5', 'diverge', [0, 1]),
                   ('A0.E1.C6', 'lane_out', [1]), ('A0.E1.C7', 'lane_out', [0])]


def test_template_needs_four_positions():
    assert layout('internal', 4, 1) == ['lane_in', 'merge', 'diverge', 'lane_out']
    try:
        layout('internal', 3, 1)
    except ValueError:
        return
    raise AssertionError('a 3-position internal link must be rejected')


def test_network_checks():
    ch = json.load(open(os.path.join(CFG, 'network_spec.json')))['checks']
    assert ch['pieces_with_wrong_length'] == []
    assert ch['max_gap_junction_distance_vs_length_m'] < 0.1
    assert ch['min_cells_per_link'] >= 4
    assert ch['lanes_with_wrong_lane_change_rule'] == []
    assert ch['connections_rule_vs_net']['missing'] == [] and ch['connections_rule_vs_net']['extra'] == []
    assert ch['u_turns'] == 0
    assert ch['approach_lanes_without_connection'] == []
    assert ch['phases_with_more_than_one_approach'] == []


def test_cells_checks():
    for dt in ('12', '6'):
        s = json.load(open(os.path.join(CFG, 'CTMcfg', f'dt{dt}', 'summary.json')))
        assert s['unique_ids']
        for key in ('cells_without_input', 'cells_without_output', 'cells_not_covered_by_pieces',
                    'lane_cells_on_lane_change_pieces', 'full_cells_on_no_lane_change_pieces'):
            assert s[key] == [], (dt, key)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
