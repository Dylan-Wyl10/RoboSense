"""Parallel Gurobi label farm for the bidirectional 4x4 (extension 1).

Usage:
  python -m neural_route.bigrid_datagen --n 5000 --out DIR --seed 0 --workers 12
  python -m neural_route.bigrid_datagen --n 500 --out DIR --seed 10000 --workers 12          # same-dist test
  python -m neural_route.bigrid_datagen --n 300 --out DIR --seed 20000 --mode zeroshot ...   # held-out ODs
  python -m neural_route.bigrid_datagen --n 300 --out DIR --seed 30000 --mode vextrap ...    # V in {5,8}

Sampling (training mode):
  delta ~ iid {0,1}^80; V ~ {2,3,4,6}; per vehicle: OD from the 52 TRAINING
  ordered pairs, drawn by difficulty tercile round-robin (terciles from the
  delta=0 earliest-arrival matrix); t0 ~ {0..5}.
  HOLDOUT_ODS (never in training) are reserved for the zero-shot test set.

Each instance index i is solved with its own derived seed, so shards are
deterministic and the farm is resumable (existing records are skipped).
Labels: multi-commodity MILP, MIPGap 2%, 60 s cap. Output: JSONL shards
(one per worker) with delta/tasks/routes/obj/cost/cov/solve metadata.
"""

import argparse
import json
import os
import time
from multiprocessing import Pool

import numpy as np

from .bigrid import BiGrid, BiInstance, calibrate_horizon
from .bigrid_milp import solve_milp

# fixed across the project: 4 held-out ODs spanning difficulty (never trained)
HOLDOUT_ODS = [("G1_NW", "G5_SE"), ("G6_S", "G2_N"),
               ("G4_E", "G8_W"), ("G7_SW", "G3_NE")]

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
    terciles = [order[:k], order[k:2 * k], order[2 * k:]]
    _G = dict(g=g, H=H, terciles=terciles, hold=sorted(hold),
              all_ods=sorted(arr))


def _sample_tasks(rng, mode):
    g = _G["g"]
    if mode == "train" or mode == "test":
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


def _one(args):
    idx, seed, mode = args
    rng = np.random.default_rng(seed + idx)
    delta = rng.integers(0, 2, _G["g"].n_links)
    tasks = _sample_tasks(rng, mode)
    inst = BiInstance(_G["g"], delta, tasks, horizon=_G["H"])
    t0 = time.time()
    try:
        res = solve_milp(inst, time_limit=60, mip_gap=0.02)
    except Exception as e:                                    # pragma: no cover
        return json.dumps({"idx": idx, "error": str(e)[:200]})
    if res is None:
        return json.dumps({"idx": idx, "error": "no solution"})
    routes, obj, tot, cov = res
    return json.dumps({
        "idx": idx, "delta": delta.tolist(), "tasks": tasks,
        "routes": routes, "obj": obj, "cost": tot, "cov": cov,
        "solve_s": round(time.time() - t0, 2)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--mode", default="train",
                    choices=["train", "test", "zeroshot", "vextrap"])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{a.mode}_seed{a.seed}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["idx"])
                except Exception:
                    pass
    todo = [(i, a.seed, a.mode) for i in range(a.n) if i not in done]
    print(f"{a.mode}: {len(done)} done, {len(todo)} to go -> {path}", flush=True)
    t0 = time.time()
    with Pool(a.workers, initializer=_init) as pool, open(path, "a") as fh:
        for k, rec in enumerate(pool.imap_unordered(_one, todo, chunksize=4)):
            fh.write(rec + "\n")
            fh.flush()
            if (k + 1) % 100 == 0:
                rate = (k + 1) / (time.time() - t0)
                print(f"{k+1}/{len(todo)} ({rate:.1f} inst/s, "
                      f"eta {(len(todo)-k-1)/rate/60:.0f} min)", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
