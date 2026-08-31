# RoboSense

**Leveraging robotaxi fleets as drive-by sensors for urban traffic monitoring.**

Robotaxis are dispatched to carry passengers, but a centrally controlled fleet can
do a second job at the same time: while driving, it collects traffic data. RoboSense
is a dynamic routing framework that makes that second job an explicit objective —
routes are chosen to trade off passenger travel time against how much of the network
the fleet observes, in space and in time.

The framework has three parts:

1. **A cell-based network representation** aligned with what a vehicle can actually
   sense as it drives.
2. **A cell-level monitoring metric** that quantifies spatiotemporal fleet coverage.
3. **A rolling-horizon MILP** that jointly minimizes time-dependent travel time and
   maximizes monitoring performance, on top of a Cell Transmission Model (CTM) that
   predicts the time-varying traffic state.

Evaluated in SUMO on a 5x5 urban grid at robotaxi market penetration rates (MPR) of
2%, 5%, and 10%. A notable finding: with well-chosen objective weights, monitoring
performance and robotaxi average speed improve *together* — better coverage feeds
better traffic state prediction, which feeds better routing.

> **Status.** This repository accompanies a manuscript that is not yet published.
> The code and the full case-study configuration are here; raw experiment output is
> not distributed (see [Data](#data)).

---

## Repository layout

```
src/
  config.py                 # all run settings live here (see Configuration)
  main_ctm.py               # single simulation run entry point
  simulation.py             # SUMO/TraCI loop, CTM stepping, routing calls
  utili/
    routeOptimGurobi.py     # the MILP: variables, constraints, objective
    ctm/                    # cell transmission model
    network.py, tools.py    # network handling and helpers
  od_generator/             # demand / OD generation scripts
  turn-defs/                # turn ratio generation
  data_analysis/
    popularity_rerun.py     # batch runner: cell-coverage objective (Sec. 4.2)
    nweight_rerun.py        # batch runner: vehicle-weighted objective (Sec. 4.3)
    FdCalibrator.py         # fundamental diagram calibration
sumo_cfg/
  5x5net/                   # the 5x5 grid network, signals, detectors, CTM config
    od/flow*/               # per-MPR demand scenarios (2% / 5% / 10%)
  toy_net/                  # small network used for the illustrative example
analysis/                   # result analysis and plotting
result/                     # aggregated results only -- see Data
```

## Requirements

| | Version tested | Notes |
|---|---|---|
| Python | 3.12 | |
| SUMO | 1.19+ | `sumo` on PATH; `SUMO_HOME` set |
| Gurobi | 11.0.3 | **license required**, see below |

Python packages: numpy, pandas, scipy, networkx, matplotlib, seaborn,
scikit-learn, gurobipy, traci, sumolib.

### Gurobi license

The routing model is a MILP solved with Gurobi, so you need a license.

- **Academic users**: Gurobi issues free named-user academic licenses.
- **Everyone else**: the free size-limited license is enough for the **toy
  network** example, but *not* for the 5x5 grid case study — those models exceed
  its variable/constraint limits. Plan on a full license to reproduce the paper.

## Installation

```bash
# 1. SUMO (Ubuntu; see sumo.dlr.de for other platforms)
sudo apt install sumo sumo-tools
export SUMO_HOME=/usr/share/sumo        # add to your shell profile

# 2. Python environment
conda env create -f environment.yml
conda activate robosense

# 3. Gurobi license
grbgetkey <your-license-key>            # or place gurobi.lic per Gurobi's docs
```

Verify:

```bash
sumo --version
python -c "import gurobipy; gurobipy.Model('ok'); print('gurobi ok')"
```

## Quickstart

All scripts resolve paths relative to `src/`, so run them from there.

> **Before your first routing run** you need to generate the CTM ground truth
> once — see [First-time setup](#first-time-setup-ctm-ground-truth). Without it
> every routing run stops immediately with a `FileNotFoundError` on
> `bench/ctm_gt.npy`.

The fastest way to confirm a working setup is one case of the batch runner. It
installs the demand scenario, runs the simulation, and cleans up after itself:

```bash
cd src
python data_analysis/popularity_rerun.py --mode probe
```

To run `main_ctm.py` directly instead, first install one of the per-MPR demand
scenarios, since the simulation config reads `od_mixed.rou.xml`:

```bash
cd sumo_cfg/5x5net
cp "od/flow350(7)_7200s_2percent/od.rou.xml" od_mixed.rou.xml       # 2% MPR
cp "od/flow350(7)_7200s_2percent/turnRatios.add.xml" turnRatios.add.xml
cd ../../src
python main_ctm.py
```

Both write to the `saving_dir` configured in `config.py`. For the 10% scenario
use its `od_mixed.rou.xml` rather than `od.rou.xml`.

## First-time setup: CTM ground truth

The CTM runs in `dynamic` demand mode, which reads a per-scenario ground-truth
occupancy array `bench/ctm_gt.npy`. These arrays are simulation output (~6 MB
each) and are **not** distributed with the repository, so you generate them once
before the first routing run. Without them you will see:

```
FileNotFoundError: .../result/ctmResult/logs/ctm_test1/<tag>/<case>/bench/ctm_gt.npy
```

A benchmark run is just the same simulation with routing switched off, so it
needs no ground truth to produce one.

**Step 1 — install the demand scenario you are generating for.** From
`sumo_cfg/5x5net/`, for the 2% case:

```bash
cp "od/flow350(7)_7200s_2percent/od.rou.xml" od_mixed.rou.xml
cp "od/flow350(7)_7200s_2percent/turnRatios.add.xml" turnRatios.add.xml
```

**Step 2 — switch `src/config.py` into benchmark mode.** The batch runners look
for the ground truth under the `1215test` tag (`BENCH_SRC_TAG` in
`nweight_rerun.py`), so write it there:

```python
self.is_real_demand = 'static'   # static demand needs no ground truth
self.is_bench       = True       # disable the routing optimization
self.is_route       = False
self.test_str       = 'ctm_test1'
self.case_str       = '1215test/350_5400s_2percent_new_normVeh'
self.senario_str    = 'bench'    # writes <case_str>/bench/ctm_gt.npy
```

**Step 3 — run it.**

```bash
cd src && python main_ctm.py
```

This writes `result/ctmResult/logs/ctm_test1/1215test/350_5400s_2percent_new_normVeh/bench/ctm_gt.npy`,
which is exactly where the routing runs look for it.

**Step 4 — repeat** for each scenario you intend to run, changing both the OD
files in step 1 and `case_str` in step 2:

| Scenario | OD folder | `case_str` suffix |
|---|---|---|
| 2% | `flow350(7)_7200s_2percent` | `350_5400s_2percent_new_normVeh` |
| 5% | `flow350(17)_7200s_5percent_new` | `350_5400s_5percent_new_normVeh` |
| 10% | `flow350(35)_7200s_10percent_new` | `350_5400s_10percent_new_normVeh` |
| 10%, no budget | `flow350(35)_7200s_10percent_new` | `350_5400s_10percent_nobgt_new_normVeh` |

The 10% folder has an explicit `od_mixed.rou.xml`; use that instead of
`od.rou.xml`. The no-budget case uses the same demand as 10%, so if you already
generated that one you can simply copy its `ctm_gt.npy` across.

**Step 5 — restore** `is_real_demand = 'dynamic'`, `is_bench = False`,
`is_route = True` before doing any routing runs.

You only need the scenarios you actually plan to run. `provision_bench_gt()` in
the batch runners copies these from `1215test` into their own output tree and
never overwrites an existing file.

## Reproducing the paper

Two batch runners, one per objective formulation. Each pins its own
`coverage_objective`, so you do not need to edit `config.py` to switch between them.

```bash
cd src

# Grid Network Analysis (Sec. 4.2) -- cell-coverage objective
python data_analysis/popularity_rerun.py --mode probe          # 1 case, smoke test
python data_analysis/popularity_rerun.py --mode parallel --workers 12

# Vehicle Number Weighted Monitoring Objective (Sec. 4.3)
python data_analysis/nweight_rerun.py --mode probe
python data_analysis/nweight_rerun.py --mode parallel --workers 12
```

Useful flags: `--phases 2percent,5percent` to run a subset of MPRs,
`--skip-existing` to resume an interrupted sweep, `--no-nobgt` to skip the
no-budget cases.

**Start with `--mode probe`.** A full sweep is large: `nweight_rerun.py` runs 52
cases (3 MPRs x 13 `alpha_2` values, plus 13 no-budget cases) and
`popularity_rerun.py` runs 40. Each case is a 5400-second SUMO simulation with a
MILP re-solved on a rolling horizon, so a full sweep is hours of compute on a
many-core machine, and `--workers 12` will use substantial RAM.

## Configuration

Everything is in `src/config.py`. The settings that matter most:

| Setting | Meaning |
|---|---|
| `coverage_objective` | `'cell'` = coverage term `sum(y_i^t)`; `'vehicle_count'` = `sum(n_i^t * y_i^t)` |
| `param` | `(alpha_1, alpha_2, M)` — travel-time weight, coverage weight, big-M |
| `budget` | de-routing budget per robotaxi; `0` restricts to shortest paths |
| `opt_interval` | re-optimization interval in seconds |
| `sumo_maxtime` | simulation horizon |
| `is_route` | `False` disables routing control (benchmark runs) |

### The two objectives

Both minimize the same expression, differing only in how the coverage term is
weighted:

```
min  (alpha_1/|A|) * sum_a sum_{i,t} c_i^t x_{i,t}^a  -  alpha_2 * COVERAGE / (|I|*|T|)
```

- `coverage_objective = 'cell'` → `COVERAGE = sum_{i,t} y_i^t`. Every covered cell
  counts once. This is the formulation in the Methodology section.
- `coverage_objective = 'vehicle_count'` → `COVERAGE = sum_{i,t} n_i^t * y_i^t`,
  where `n_i^t` is the CTM-predicted vehicle count in cell `i` at step `t`. Covering
  a busy cell is worth more than covering an empty one, so the fleet is pulled toward
  congested links.

Because `n_i^t` comes from the CTM and enters as a **constant** coefficient on the
existing binary `y_i^t`, the model stays an MILP — same variables, same constraints.

Raising `alpha_2` buys coverage at the cost of travel time. The paper sweeps
`alpha_2` from 10 to 3000.

## Data

This repository tracks **code, network definitions, and case-study
configuration** — everything needed to *re-run* the experiments. Raw SUMO output
(per-vehicle, per-step dumps) is not tracked: it is hundreds of megabytes and fully
regenerable from the configuration here. Aggregated results are kept.

See [`DATA.md`](DATA.md) for the exact tracked/untracked breakdown.

## Citation

The manuscript is not yet published. Until it is, please cite the software entry in
[`CITATION.cff`](CITATION.cff). Citation details will be updated here on publication.

## License

MIT — see [`LICENSE`](LICENSE).

Note that the dependencies carry their own terms: SUMO is EPL-2.0, and **Gurobi is
commercial software requiring a separate license**. Neither is redistributed here.

## Authors

Yilin Wang (<wang4517@purdue.edu>), Yiheng Feng (<feng333@purdue.edu>)
Lyles School of Civil and Construction Engineering, Purdue University
