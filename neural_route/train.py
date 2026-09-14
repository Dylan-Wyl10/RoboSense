"""Train + evaluate on a parametric grid, labels from Gurobi. Usage:
    python -m neural_route.train [R] [C] [n_train] [n_test] [epochs]

Pipeline: data_gen.generate() -> Gurobi-labelled instances (offline; the
training loop makes no solver calls) -> teacher-forced CE -> masked greedy
decode -> objective gap vs the Gurobi reference on held-out instances.
"""

import sys
import time

import numpy as np
import torch
import torch.nn as nn

from . import toy_env as te
from .data_gen import PAD, generate, tokens_to_routes
from .model import RouteModel, greedy_decode


def main(R=3, C=3, n_train=2000, n_test=200, epochs=40, d=96, seed=0,
         out_dir=None):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)
    grid = te.Grid(R, C)
    print(f"grid {R}x{C}: {grid.n_links} links, route_len {grid.route_len}, "
          f"horizon {te.default_horizon(grid)}")

    t0 = time.time()
    Xtr, Ytr, _ = generate(n_train, grid=grid, seed=seed)
    Xte, Yte, obj_te = generate(n_test, grid=grid, seed=seed + 10_000)
    print(f"data (Gurobi labels): {n_train}+{n_test} instances, "
          f"{time.time()-t0:.0f}s total")

    model = RouteModel(grid, d=d).to(dev)
    print(f"model params: {sum(p.numel() for p in model.parameters())/1e6:.2f}M")

    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    lossf = nn.CrossEntropyLoss(ignore_index=PAD)
    Xtr_t = torch.tensor(Xtr, device=dev)
    Ytr_t = torch.tensor(Ytr, device=dev)

    B = 64
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n_train, device=dev)
        tot = 0.0
        for i in range(0, n_train, B):
            idx = perm[i:i + B]
            logits = model(Xtr_t[idx], Ytr_t[idx])
            loss = lossf(logits.reshape(-1, logits.size(-1)),
                         Ytr_t[idx][:, 1:].reshape(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        if ep % 5 == 4 or ep == 0:
            print(f"epoch {ep+1:3d}  CE {tot/n_train:.4f}")

    # --- eval: masked greedy decode vs Gurobi reference objective ---
    insts = [te.Instance(grid, delta=Xte[i].astype(np.int64))
             for i in range(n_test)]
    Xte_t = torch.tensor(Xte, device=dev)
    t0 = time.time()
    tok_lists = greedy_decode(model, insts, Xte_t)
    t_dec = (time.time() - t0) / n_test
    gaps, n_valid, n_le = [], 0, 0
    cases = []                       # per-instance model-vs-Gurobi comparison
    for i in range(n_test):
        routes = tokens_to_routes(grid, tok_lists[i], insts[i].n_veh)
        if routes is None:
            continue
        res = insts[i].objective(routes)
        if res is None:
            continue
        n_valid += 1
        gap = res[0] - obj_te[i]
        gaps.append(gap)
        if gap < 1e-9:
            n_le += 1
        g_routes = tokens_to_routes(grid, Yte[i], insts[i].n_veh)
        g_res = insts[i].objective(g_routes)
        cases.append({
            "idx": i, "gap": gap,
            "model_obj": res[0], "gurobi_obj": obj_te[i],
            "model_cost": res[1], "gurobi_cost": g_res[1],
            "model_cov": res[2], "gurobi_cov": g_res[2],
            "same_routes": sorted(routes) == sorted(g_routes),
            "model_routes": "|".join("-".join(map(str, r[1:-1]))
                                     for r in sorted(routes)),
            "gurobi_routes": "|".join("-".join(map(str, r[1:-1]))
                                      for r in sorted(g_routes)),
        })
    gaps = np.array(gaps)
    if out_dir and cases:
        import csv, os
        os.makedirs(out_dir, exist_ok=True)
        path = f"{out_dir}/eval_cases_{R}x{C}_seed{seed}.csv"
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cases[0].keys()))
            w.writeheader()
            w.writerows(cases)
        torch.save(model.state_dict(), f"{out_dir}/model_{R}x{C}_seed{seed}.pt")
        n_same = sum(c["same_routes"] for c in cases)
        print(f"  identical route sets   : {n_same}/{len(cases)}")
        print(f"  per-case CSV -> {path}")
    print(f"\neval on {n_test} held-out instances "
          f"({t_dec*1000:.0f} ms/instance decode):")
    print(f"  valid solutions          : {n_valid}/{n_test}")
    if n_valid:
        print(f"  matches/beats Gurobi ref : {n_le}/{n_valid} "
              f"({100*n_le/n_valid:.1f}%)")
        print(f"  mean obj gap vs Gurobi   : {gaps.mean():.5f} "
              f"(ref obj mean {obj_te.mean():.4f}; normalized units)")
        print(f"  max obj gap              : {gaps.max():.5f}")
    return n_valid, n_le, gaps


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:6]]
    out = sys.argv[6] if len(sys.argv) > 6 else None
    main(*args, out_dir=out)
