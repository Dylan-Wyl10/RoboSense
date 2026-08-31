"""
Batch runner for the segment-popularity re-experiment.

Runs Table 3 settings (30 normal + 10 no-budget, total 40 cases) with the
new per-CAV cell-entry event logging enabled in simulation.py.

Modes:
  --mode probe    Sequential, runs just the first setting (for resource probe).
  --mode full     Sequential, runs all 40 settings (use only for tiny machines).
  --mode parallel Phase-serial / case-parallel: 4 phases (one per MPR config),
                  within each phase all alpha cases run concurrently via
                  ProcessPoolExecutor. Each worker gets an isolated sumocfg +
                  additional-file that direct SUMO XML outputs to a unique
                  scratch dir, so the otherwise-shared `result/tmpnet/CTMTEST/`
                  paths don't race.

Read-only with respect to existing result directories: writes only to
`result/ctmResult/logs/ctm_test1/20260607_test/...`.

Notes
-----
- OD switching: `od.rou.xml` in each per-MPR folder is already mixed at
  the right CAV ratio. We copy it to `5x5net/od_mixed.rou.xml`. The 10%
  folder has an explicit `od_mixed.rou.xml` we prefer.
- Budget: `Config().budget = 2` for normal runs, `0` for no-budget runs.
- Seed: not overridden (SUMO default). The user explicitly approved.
- Parallel safety: OD file is installed once per phase (no concurrent
  rewriting). Each worker reads it read-only; SUMO outputs are per-worker
  isolated.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

# Make both the project root and src/ importable (PyCharm-style).
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT_FOR_IMPORTS = os.path.dirname(SRC_DIR)
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PROJECT_ROOT_FOR_IMPORTS)

if 'SUMO_HOME' not in os.environ:
    os.environ['SUMO_HOME'] = '/usr/share/sumo'
sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))

import traci  # noqa: E402

from config import Config  # noqa: E402
from simulation import Simulation  # noqa: E402


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(SRC_DIR)
NET_DIR = os.path.join(PROJECT_ROOT, 'sumo_cfg', '5x5net')
OD_BASE = os.path.join(NET_DIR, 'od')

# (mpr_label, src_folder, has_explicit_od_mixed)
OD_SOURCES = {
    '2percent':       (os.path.join(OD_BASE, 'flow350(7)_7200s_2percent'),       False),
    '5percent':       (os.path.join(OD_BASE, 'flow350(17)_7200s_5percent_new'),  False),
    '10percent':      (os.path.join(OD_BASE, 'flow350(35)_7200s_10percent_new'), True),
}

ALPHAS = [10, 100, 1000, 1500, 2000, 2500, 3000, 5000, 10000, 100000]

OUT_TAG = '20260607_test'

# Hard-coded SUMO tripinfo location (per sumocfg)
SUMO_TMP_LOG = os.path.join(PROJECT_ROOT, 'result', 'tmpnet', 'CTMTEST', 'sumolog_tmp')


@dataclass
class RunSetting:
    mpr_label: str       # '2percent' / '5percent' / '10percent' / '10percent_nobgt'
    od_key: str          # which OD folder to source (always one of OD_SOURCES keys)
    alpha: int
    budget: int          # 2 for normal, 0 for no-budget

    @property
    def case_subdir(self) -> str:
        return f'{OUT_TAG}/350_5400s_{self.mpr_label}_new_normVeh'

    @property
    def senario_str(self) -> str:
        return f'{self.alpha}_cover'


def build_settings(include_nobgt: bool = True) -> List[RunSetting]:
    settings: List[RunSetting] = []
    for mpr_label in ['2percent', '5percent', '10percent']:
        for a in ALPHAS:
            settings.append(RunSetting(mpr_label, mpr_label, a, budget=2))
    if include_nobgt:
        for a in ALPHAS:
            settings.append(RunSetting('10percent_nobgt', '10percent', a, budget=0))
    return settings


# ---------------------------------------------------------------------------
# OD file switching
# ---------------------------------------------------------------------------

def install_od_for(mpr_key: str) -> None:
    """Copy the per-MPR OD + turn-ratios files into 5x5net/.

    For 10%: source has an explicit od_mixed.rou.xml.
    For 2%/5%: source's od.rou.xml is already mixed at the right rate.
    """
    src_dir, has_explicit_mixed = OD_SOURCES[mpr_key]
    if not os.path.isdir(src_dir):
        raise FileNotFoundError(f'OD source not found: {src_dir}')

    if has_explicit_mixed:
        src_rou = os.path.join(src_dir, 'od_mixed.rou.xml')
    else:
        src_rou = os.path.join(src_dir, 'od.rou.xml')

    src_turn = os.path.join(src_dir, 'turnRatios.add.xml')
    if not (os.path.isfile(src_rou) and os.path.isfile(src_turn)):
        raise FileNotFoundError(f'Missing OD or turnRatios in {src_dir}')

    dst_rou = os.path.join(NET_DIR, 'od_mixed.rou.xml')
    dst_turn = os.path.join(NET_DIR, 'turnRatios.add.xml')
    shutil.copy2(src_rou, dst_rou)
    shutil.copy2(src_turn, dst_turn)
    print(f'  [OD] installed {mpr_key} -> {dst_rou} + {dst_turn}')


# ---------------------------------------------------------------------------
# Per-run config + execution
# ---------------------------------------------------------------------------

def make_config_for(setting: RunSetting) -> Config:
    cfg = Config()
    # alpha-2 is the second value in cfg.param tuple
    cfg.param = (1, setting.alpha, 999999)
    # this script reproduces the cell-coverage results of "Grid Network
    # Analysis" (paper Sec. 4.2)
    cfg.coverage_objective = 'cell'
    cfg.budget = setting.budget
    cfg.case_str = setting.case_subdir
    cfg.senario_str = setting.senario_str
    # Rebuild saving_dir + saving_path after patching
    cfg.saving_dir = (f'../result/ctmResult/logs/{cfg.test_str}/'
                      f'{cfg.case_str}/{cfg.senario_str}')
    cfg.saving_path = {
        'occupation':       f'{cfg.saving_dir}/occupation.npy',
        'od_route':         f'{cfg.saving_dir}/od_route.json',
        'ctm_demand_gt':    f'../result/ctmResult/logs/{cfg.test_str}/{cfg.case_str}/bench/ctm_gt.npy',
        'ctm':              f'{cfg.saving_dir}',
        'time_optim':       f'{cfg.saving_dir}/time_optim.pkl',
        'cav_cell_events':  f'{cfg.saving_dir}/cav_cell_events.pkl',
        'num_cav':          f'{cfg.saving_dir}/num_cav.pkl',
    }
    return cfg


def copy_sumolog_to_case_dir(saving_dir_relative: str, src_dir: str = SUMO_TMP_LOG) -> None:
    """Copy SUMO XML outputs from `src_dir` into the per-case `sumolog_tmp/` dir."""
    case_dir_abs = os.path.abspath(saving_dir_relative)
    dst = os.path.join(case_dir_abs, 'sumolog_tmp')
    if not os.path.isdir(src_dir):
        print(f'  [warn] no sumolog_tmp at {src_dir}, skipping copy')
        return
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src_dir):
        sf = os.path.join(src_dir, f)
        if os.path.isfile(sf):
            shutil.copy2(sf, os.path.join(dst, f))
    print(f'  [SUMO logs] copied {src_dir} -> {dst}')


# ---------------------------------------------------------------------------
# Per-worker sumocfg + additional-file isolation (for parallel mode)
# ---------------------------------------------------------------------------

_BASE_SUMOCFG = os.path.join(NET_DIR, 'simcfg', 'case0ctm.sumocfg')


def make_isolated_sumocfg(worker_tag: str) -> tuple[str, str, str]:
    """Build a per-worker sumocfg + per-worker edge_output.add.xml.

    Each worker writes SUMO XML outputs into a unique scratch dir
    `result/tmpnet/CTMTEST_<worker_tag>/sumolog_tmp/` so concurrent
    workers don't overwrite each other.

    Returns (sumocfg_path, scratch_tmpnet_dir, edge_add_path).
    The two temp files live next to the originals so relative paths inside
    still resolve. Caller is responsible for cleanup.
    """
    scratch_tmpnet = os.path.join(PROJECT_ROOT, 'result', f'tmpnet_w_{worker_tag}',
                                  'CTMTEST', 'sumolog_tmp')
    os.makedirs(scratch_tmpnet, exist_ok=True)
    # rel path FROM 5x5net/simcfg/ TO scratch_tmpnet:
    rel_out = os.path.relpath(scratch_tmpnet, os.path.dirname(_BASE_SUMOCFG))
    # rel path FROM 5x5net/ TO scratch_tmpnet (for edge_output additional):
    rel_out_from_net = os.path.relpath(scratch_tmpnet, NET_DIR)

    # 1) per-worker edge_output additional file
    edge_add_path = os.path.join(NET_DIR, f'edge_output_w_{worker_tag}.add.xml')
    with open(edge_add_path, 'w') as f:
        f.write('<additional>\n')
        f.write(f'        <edgeData id="edge1" file="{rel_out_from_net}/edge_data.xml" '
                'begin="0" end="20000" freq="1000"/>\n')
        f.write('</additional>\n')

    # 2) per-worker sumocfg (loads per-worker additional + writes outputs to scratch)
    sumocfg_path = os.path.join(NET_DIR, 'simcfg', f'case0ctm_w_{worker_tag}.sumocfg')
    cfg_xml = f'''<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="../5x5net.net.xml"/>
        <route-files value="../od_mixed.rou.xml"/>
        <additional-files value="../v_type.add.xml, ../edge_output_w_{worker_tag}.add.xml"/>
    </input>
    <processing>
        <ignore-route-errors value="true"/>
        <route-steps value="200"/>
        <no-internal-links value="False"/>
        <time-to-teleport value="200"/>
        <time-to-teleport.highways value="0"/>
        <eager-insert value="False"/>
    </processing>
    <output>
        <summary-output value="{rel_out}/summary0.xml"/>
        <tripinfo-output value="{rel_out}/tripinfo0.xml"/>
        <statistic-output value="{rel_out}/overall0.xml"/>
        <lanedata-output value="{rel_out}/lane_data.xml"/>
    </output>
    <time>
        <begin value="0"/>
        <end value="5400"/>
        <step-length value="0.1"/>
    </time>
    <routing>
        <device.rerouting.adaptation-steps value="18"/>
        <device.rerouting.adaptation-interval value="10"/>
    </routing>
    <report>
        <verbose value="true"/>
        <duration-log.statistics value="true"/>
        <no-step-log value="true"/>
    </report>
</configuration>
'''
    with open(sumocfg_path, 'w') as f:
        f.write(cfg_xml)
    return sumocfg_path, os.path.dirname(scratch_tmpnet), edge_add_path


def remove_isolated_sumocfg(sumocfg_path: str, edge_add_path: str) -> None:
    for p in (sumocfg_path, edge_add_path):
        try:
            os.remove(p)
        except OSError:
            pass


def run_one(setting: RunSetting, current_od_key_holder: list) -> dict:
    """Sequential run (no isolation). Used by --mode probe / --mode full."""
    print('\n' + '=' * 70)
    print(f'RUN: MPR={setting.mpr_label}  alpha={setting.alpha}  budget={setting.budget}')
    print('=' * 70)

    if current_od_key_holder[0] != setting.od_key:
        install_od_for(setting.od_key)
        current_od_key_holder[0] = setting.od_key
    else:
        print(f'  [OD] reuse {setting.od_key}')

    # Critical: simulation.py reads Config().budget via fresh Config() instances
    # inside its main loop. Use SIM_BUDGET env override (read by Config.__init__)
    # to actually thread the per-setting budget through.
    os.environ['SIM_BUDGET'] = str(setting.budget)
    cfg = make_config_for(setting)

    # Ensure case dir exists
    os.makedirs(os.path.abspath(cfg.saving_dir), exist_ok=True)
    os.makedirs(SUMO_TMP_LOG, exist_ok=True)

    t0 = time.time()
    sim = Simulation(
        start_time=600,
        max_time=cfg.sumo_maxtime,
        link_num=40,
        resolution=0.1,
        net_file=cfg.net_file,
        time_interval=5,
        sizeX=5,
        sizeY=5,
        link_dirct_file=cfg.link_node_dirct_file,
        demand_file=cfg.demand_file,
        turn_rate=cfg.turn_rate,
    )
    sim.simCTM(
        config=cfg.sumo_cfg, param=cfg.param, ctm_fd=cfg.ctm_fd,
        ctm_interval=cfg.ctm_interval, ctm_time_opt=cfg.ctm_time_opt,
        ctm_time_norm=cfg.ctm_time_normal, ctm_demand_mode=cfg.is_real_demand,
        optim_interval=cfg.opt_interval, saving_path=cfg.saving_path,
        GUImode=cfg.sumo_gui, route=cfg.is_route, bench_mode=cfg.is_bench,
        coverage_objective=cfg.coverage_objective,
    )
    wall = time.time() - t0

    try:
        traci.close()
    except Exception:
        pass

    copy_sumolog_to_case_dir(cfg.saving_dir)
    return {'wall_seconds': wall, 'case_dir': os.path.abspath(cfg.saving_dir)}


def run_one_isolated(setting_kwargs: dict) -> dict:
    """Worker entry-point for parallel mode. Each call runs in its own
    subprocess with an isolated sumocfg + scratch tmpnet dir.

    setting_kwargs has keys: mpr_label, od_key, alpha, budget, worker_tag.
    Returns a dict with timing + path info (and exception trace on failure).
    """
    # Re-build the setting from kwargs (can't pickle dataclass to subprocess in
    # all envs, so we pass kwargs and reconstruct).
    s = RunSetting(setting_kwargs['mpr_label'], setting_kwargs['od_key'],
                   setting_kwargs['alpha'], setting_kwargs['budget'])
    tag = setting_kwargs['worker_tag']

    # Re-import inside subprocess (each ProcessPoolExecutor worker is a fresh process).
    # The top-of-module imports already cover this, but `os.chdir(SRC_DIR)` is run in
    # the parent; sub-procs inherit cwd from spawn context, so set explicitly.
    os.chdir(SRC_DIR)
    # Critical: thread budget through to simulation.py via env var; each
    # subprocess has its own os.environ, so workers don't race on this.
    os.environ['SIM_BUDGET'] = str(s.budget)
    t0 = time.time()
    sumocfg_path, scratch_dir, edge_add_path = make_isolated_sumocfg(tag)
    try:
        cfg = make_config_for(s)
        # Point this run to the per-worker sumocfg.
        cfg.sumo_cfg = sumocfg_path
        os.makedirs(os.path.abspath(cfg.saving_dir), exist_ok=True)

        sim = Simulation(
            start_time=600, max_time=cfg.sumo_maxtime, link_num=40, resolution=0.1,
            net_file=cfg.net_file, time_interval=5, sizeX=5, sizeY=5,
            link_dirct_file=cfg.link_node_dirct_file,
            demand_file=cfg.demand_file, turn_rate=cfg.turn_rate,
        )
        sim.simCTM(
            config=cfg.sumo_cfg, param=cfg.param, ctm_fd=cfg.ctm_fd,
            ctm_interval=cfg.ctm_interval, ctm_time_opt=cfg.ctm_time_opt,
            ctm_time_norm=cfg.ctm_time_normal, ctm_demand_mode=cfg.is_real_demand,
            optim_interval=cfg.opt_interval, saving_path=cfg.saving_path,
            GUImode=cfg.sumo_gui, route=cfg.is_route, bench_mode=cfg.is_bench,
            coverage_objective=cfg.coverage_objective,
        )
        wall = time.time() - t0
        try:
            traci.close()
        except Exception:
            pass

        # Copy this worker's sumolog (per-worker scratch) into the per-case dir.
        per_worker_sumolog = os.path.join(scratch_dir, 'sumolog_tmp')
        copy_sumolog_to_case_dir(cfg.saving_dir, src_dir=per_worker_sumolog)
        return {
            'ok': True, 'mpr': s.mpr_label, 'alpha': s.alpha, 'budget': s.budget,
            'wall_seconds': wall, 'case_dir': os.path.abspath(cfg.saving_dir),
        }
    except Exception as e:
        import traceback
        return {
            'ok': False, 'mpr': s.mpr_label, 'alpha': s.alpha, 'budget': s.budget,
            'error': repr(e), 'traceback': traceback.format_exc(),
        }
    finally:
        remove_isolated_sumocfg(sumocfg_path, edge_add_path)
        # Clean up per-worker scratch tmpnet (we already copied what we need).
        # scratch_dir is .../tmpnet_w_<tag>/CTMTEST; remove the WHOLE
        # tmpnet_w_<tag>/ parent so no empty shell is left behind.
        try:
            shutil.rmtree(os.path.dirname(scratch_dir), ignore_errors=True)
        except Exception:
            pass


def run_phase_parallel(phase_settings: List[RunSetting], workers: int) -> List[dict]:
    """Install OD once for the phase, then run all settings in parallel."""
    print('\n' + '#' * 70)
    print(f'# PHASE: {phase_settings[0].mpr_label}  ({len(phase_settings)} cases, '
          f'{workers} workers)')
    print('#' * 70)
    install_od_for(phase_settings[0].od_key)
    print(f'  [OD] installed once for phase ({phase_settings[0].od_key})')

    payloads = [
        {'mpr_label': s.mpr_label, 'od_key': s.od_key,
         'alpha': s.alpha, 'budget': s.budget,
         'worker_tag': f'{s.mpr_label}_a{s.alpha}'}
        for s in phase_settings
    ]

    results = []
    t_phase = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one_isolated, p): p for p in payloads}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {'ok': False, 'mpr': p['mpr_label'], 'alpha': p['alpha'],
                     'budget': p['budget'], 'error': repr(e)}
            if r.get('ok'):
                print(f"  [done] {r['mpr']:18s} a={r['alpha']:>6d} b={r['budget']}  "
                      f"wall={r['wall_seconds']:.1f}s")
            else:
                print(f"  [FAIL] {r.get('mpr')} a={r.get('alpha')} b={r.get('budget')}: "
                      f"{r.get('error')}")
                tb = r.get('traceback')
                if tb:
                    print(tb)
            results.append(r)
    print(f'  [phase wall] {time.time() - t_phase:.1f}s')
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['probe', 'full', 'parallel'], default='probe',
                   help='probe = 1 setting; full = all sequential; parallel = phase-serial / case-parallel')
    p.add_argument('--workers', type=int, default=12,
                   help='workers per phase (parallel mode only)')
    p.add_argument('--no-nobgt', action='store_true',
                   help='skip no-budget runs (only 30 normal cases)')
    p.add_argument('--phases', type=str, default='all',
                   help='comma-separated subset: 2percent,5percent,10percent,10percent_nobgt')
    p.add_argument('--skip-existing', action='store_true',
                   help='skip cases whose cav_cell_events.pkl already exists (resume mode)')
    args = p.parse_args()

    all_settings = build_settings(include_nobgt=not args.no_nobgt)

    if args.mode == 'probe':
        settings = all_settings[:1]
        print(f'PROBE: 1 setting of {len(all_settings)} total')
    elif args.mode == 'full':
        settings = all_settings
        print(f'FULL: {len(settings)} settings sequentially')
    else:  # parallel
        settings = all_settings
        if args.phases != 'all':
            wanted = set(args.phases.split(','))
            settings = [s for s in settings if s.mpr_label in wanted]
        print(f'PARALLEL: {len(settings)} settings, {args.workers} workers per phase')

    # Filter out finished cases if resuming.
    if args.skip_existing:
        kept = []
        for s in settings:
            ev = (f'../result/ctmResult/logs/ctm_test1/{OUT_TAG}/'
                  f'350_5400s_{s.mpr_label}_new_normVeh/{s.alpha}_cover/cav_cell_events.pkl')
            if not os.path.isfile(os.path.join(SRC_DIR, ev)):
                kept.append(s)
            else:
                print(f'  [skip-existing] {s.mpr_label} a={s.alpha}')
        settings = kept
        print(f'  remaining after skip: {len(settings)}')

    os.chdir(SRC_DIR)
    grand_start = time.time()

    if args.mode in ('probe', 'full'):
        current_od = [None]
        results = []
        for s in settings:
            try:
                r = run_one(s, current_od)
                r.update({'mpr': s.mpr_label, 'alpha': s.alpha, 'budget': s.budget,
                          'ok': True})
                results.append(r)
                print(f'  [done] wall={r["wall_seconds"]:.1f}s  -> {r["case_dir"]}')
            except Exception as e:
                print(f'  [FAIL] {s}: {e}')
                try:
                    traci.close()
                except Exception:
                    pass
    else:
        # parallel mode: group by mpr_label, run each phase concurrently.
        phases: dict[str, List[RunSetting]] = {}
        for s in settings:
            phases.setdefault(s.mpr_label, []).append(s)
        results = []
        for mpr_label, phase_settings in phases.items():
            phase_results = run_phase_parallel(phase_settings, workers=args.workers)
            results.extend(phase_results)

    print('\n' + '=' * 70)
    print(f'GRAND TOTAL wall = {time.time() - grand_start:.1f} s '
          f'for {sum(1 for r in results if r.get("ok"))} ok / {len(results)} total')
    for r in results:
        ok = '✓' if r.get('ok') else '✗'
        print(f'  {ok} {r.get("mpr","?"):18s} alpha={r.get("alpha","?")} '
              f'bgt={r.get("budget","?")}  wall={r.get("wall_seconds", 0):.1f}s')

    # End-of-run cleanup: sweep any per-worker scratch dirs that survived a crash,
    # the probe's sumolog (in legacy tmpnet/CTMTEST/sumolog_tmp/), and any
    # leftover per-worker sumocfg / additional files. We DO NOT touch the
    # legacy tmpnet/PR2*/PR5*/flextable/ subdirs -- those are unrelated user data.
    print('\n[cleanup] removing per-worker scratch + probe sumolog leftovers')
    import glob
    project_root_abs = os.path.abspath(os.path.join(SRC_DIR, '..'))
    # Per-worker tmpnet_w_*/ scratch (mostly auto-cleaned, but sweep stragglers).
    for d in glob.glob(os.path.join(project_root_abs, 'result', 'tmpnet_w_*')):
        try:
            shutil.rmtree(d, ignore_errors=True)
            print(f'  rm {d}')
        except Exception as e:
            print(f'  [warn] {d}: {e}')
    # Probe's SUMO scratch under tmpnet/CTMTEST/sumolog_tmp/ (data is already
    # copied into the per-case dir by copy_sumolog_to_case_dir).
    probe_sumolog = os.path.join(project_root_abs, 'result', 'tmpnet', 'CTMTEST',
                                 'sumolog_tmp')
    if os.path.isdir(probe_sumolog):
        for f in os.listdir(probe_sumolog):
            try:
                os.remove(os.path.join(probe_sumolog, f))
            except OSError:
                pass
        print(f'  cleaned {probe_sumolog}/*')
    # Per-worker temp sumocfg / additional files (in case a worker crashed
    # before its `finally` ran).
    for p in glob.glob(os.path.join(NET_DIR, 'simcfg', 'case0ctm_w_*.sumocfg')):
        try: os.remove(p); print(f'  rm {p}')
        except OSError: pass
    for p in glob.glob(os.path.join(NET_DIR, 'edge_output_w_*.add.xml')):
        try: os.remove(p); print(f'  rm {p}')
        except OSError: pass
    print('[cleanup] done')


if __name__ == '__main__':
    main()
