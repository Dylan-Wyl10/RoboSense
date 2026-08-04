"""Parallel Gurobi label farm for the BUDGET-conditioned bigrid (option (a)).

Same instance sampler as `neural_route.bigrid_datagen` (delta, V, OD terciles,
t0) plus ONE new per-vehicle attribute: the slack ratio rho_v, from which the
budget B_v = ceil(rho_v * tau_min_v) is derived.  Utility weights stay uniform
(user decision 2026-08-04: "选 A 选 B 都无所谓" — keep w_i = 1 for now).

rho anchors
  TRAIN  {1.0, 1.5, 2.0, 3.0}      seen during training
  INTERP {1.25, 1.75}              never trained -> L4a interpolation exam
  EXTRAP {4.0}                     never trained -> L4b extrapolation exam
Each vehicle draws its own rho (heterogeneous fleet); with prob P_HOMO the
whole fleet shares one rho (homogeneous fleet) so the two regimes are
separable at eval time.

Modes
  train / test        trained ODs, V in {2,3,4,6}, TRAIN anchors
  zeroshot            4 held-out ODs,               TRAIN anchors
  vextrap             V in {5,8},                   TRAIN anchors
  rhointerp           trained ODs,                  INTERP anchors  (homogeneous)
  rhoextrap           trained ODs,                  EXTRAP anchors  (homogeneous)
  curve               FIXED instances re-solved at EVERY rho in RHO_CURVE
                      (homogeneous) -> the coverage-vs-rho response curve

Usage:
  python budget_datagen.py --n 4000 --out DIR --seed 0    --mode train --workers 15
  python budget_datagen.py --n 400  --out DIR --seed 10000 --mode test  --workers 15
  ...
Resumable: existing (idx, rho_tag) records are skipped.
"""

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, "/home/yilin/Research/Route_TSC_CART")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neural_route.bigrid import BiGrid, BiInstance, calibrate_horizon  # noqa: E402
from neural_route.bigrid_datagen import HOLDOUT_ODS  # noqa: E402

from budget_milp import budgets_from_slack, solve_budget_milp  # noqa: E402

RHO_TRAIN = [1.0, 1.5, 2.0, 3.0]
RHO_INTERP = [1.25, 1.75]
RHO_EXTRAP = [4.0]
RHO_CURVE = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]
P_HOMO = 0.35

_G = None


def _init():
    global _G
    g = BiGrid(4, 4)
    H = calibrate_horizon(g)
    inst0 = BiInstance(g, np.zeros(g.n_links), tasks=[], horizon=H)
    ids = list(g.gates.values())
    arr = {}
    for o in ids:
        _, a = inst0.earliest_arrival(o)
        for d in ids:
            if d != o:
                arr[(o, d)] = a[d]
    hold = {(g.gates[a], g.gates[b]) for a, b in HOLDOUT_ODS}
    train_ods = [od for od in arr if od not in hold]
    order = sorted(train_ods, key=lambda od: arr[od])
    k = len(order) // 3
    _G = dict(g=g, H=H, terciles=[order[:k], order[k:2 * k], order[2 * k:]],
              hold=sorted(hold))


def _sample_tasks(rng, mode):
    g = _G["g"]
    if mode in ("train", "test", "rhointerp", "rhoextrap", "curve"):
        V = int(rng.choice([2, 3, 4, 6]))
        pool = _G["terciles"]
    elif mode == "zeroshot":
        V = int(rng.choice([2, 3, 4]))
        pool = None
    elif mode == "vextrap":
        V = int(rng.choice([5, 8]))
        pool = _G["terciles"]
    tasks = []
    for j in range(V):
        if pool is None:
            o, d = _G["hold"][int(rng.integers(len(_G["hold"])))]
        else:
            terc = pool[j % 3]
            o, d = terc[int(rng.integers(len(terc)))]
        tasks.append((int(o), int(d), int(rng.integers(0, 6))))
    return tasks


def _sample_rhos(rng, mode, V):
    if mode in ("train", "test", "zeroshot", "vextrap"):
        anchors = RHO_TRAIN
        if rng.random() < P_HOMO:                     # homogeneous fleet
            return [float(rng.choice(anchors))] * V
        return [float(rng.choice(anchors)) for _ in range(V)]
    if mode == "rhointerp":
        return [float(rng.choice(RHO_INTERP))] * V
    if mode == "rhoextrap":
        return [float(rng.choice(RHO_EXTRAP))] * V
    raise ValueError(mode)


def _one(args):
    idx, seed, mode, rho_fixed = args
    rng = np.random.default_rng(seed + idx)
    delta = rng.integers(0, 2, _G["g"].n_links)
    tasks = _sample_tasks(rng, "curve" if mode == "curve" else mode)
    inst = BiInstance(_G["g"], delta, tasks, horizon=_G["H"])
    rhos = ([float(rho_fixed)] * len(tasks) if mode == "curve"
            else _sample_rhos(rng, mode, len(tasks)))
    try:
        B = budgets_from_slack(inst, rhos)
    except Exception as e:                                    # pragma: no cover
        return json.dumps({"idx": idx, "rho_tag": rho_fixed, "error": str(e)[:200]})
    t0 = time.time()
    try:
        res = solve_budget_milp(inst, B, time_limit=60, mip_gap=0.02)
    except Exception as e:                                    # pragma: no cover
        return json.dumps({"idx": idx, "rho_tag": rho_fixed, "error": str(e)[:200]})
    if res is None:
        return json.dumps({"idx": idx, "rho_tag": rho_fixed, "error": "no solution"})
    routes, obj, tot, cov = res
    return json.dumps({
        "idx": idx, "rho_tag": rho_fixed, "delta": delta.tolist(),
        "tasks": tasks, "rhos": rhos, "budgets": B, "routes": routes,
        "obj": obj, "cost": tot, "cov": cov,
        "solve_s": round(time.time() - t0, 2)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=15)
    ap.add_argument("--mode", default="train",
                    choices=["train", "test", "zeroshot", "vextrap",
                             "rhointerp", "rhoextrap", "curve"])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{a.mode}_seed{a.seed}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    done.add((r["idx"], r.get("rho_tag")))
                except Exception:
                    pass
    if a.mode == "curve":
        todo = [(i, a.seed, a.mode, rho) for rho in RHO_CURVE
                for i in range(a.n) if (i, rho) not in done]
    else:
        todo = [(i, a.seed, a.mode, None) for i in range(a.n)
                if (i, None) not in done]
    print(f"{a.mode}: {len(done)} done, {len(todo)} to go -> {path}", flush=True)
    if not todo:
        print("DONE", flush=True)
        return
    t0 = time.time()
    with Pool(a.workers, initializer=_init) as pool, open(path, "a") as fh:
        for k, rec in enumerate(pool.imap_unordered(_one, todo, chunksize=2)):
            fh.write(rec + "\n")
            fh.flush()
            if (k + 1) % 100 == 0:
                rate = (k + 1) / (time.time() - t0)
                print(f"{k+1}/{len(todo)} ({rate:.2f} inst/s, "
                      f"eta {(len(todo)-k-1)/rate/60:.0f} min)", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
