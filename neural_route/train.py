"""Train + evaluate the toy model. Usage:
    python -m neural_route.train [n_train] [n_test] [epochs]

Pipeline (FM-MCVRP recipe, miniature):
  1. data_gen.generate(): sample instances, EXACT labels (offline; no solver
     calls during training).
  2. Teacher-forced cross-entropy on next-token prediction.
  3. Eval: masked greedy decode -> objective via toy_env -> gap vs exact.
Gap definition: (obj_model - obj_exact) on the normalized objective; both
terms are in [0,1] so gaps are directly interpretable.
"""

import sys
import time

import numpy as np
import torch
import torch.nn as nn

from . import toy_env as te
from .data_gen import PAD, generate, tokens_to_assignment
from .model import ToyRouteModel, greedy_decode


def main(n_train=2000, n_test=200, epochs=30, d=96, seed=0):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)

    t0 = time.time()
    Xtr, Ytr, _ = generate(n_train, seed=seed)
    Xte, Yte, obj_te = generate(n_test, seed=seed + 10_000)
    print(f"data: {n_train}+{n_test} instances, {time.time()-t0:.0f}s")

    model = ToyRouteModel(d=d).to(dev)
    n_par = sum(p.numel() for p in model.parameters())
    print(f"model params: {n_par/1e6:.2f}M (d={d})")

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

    # --- evaluation: greedy decode, objective gap vs exact ---
    model.eval()
    Xte_t = torch.tensor(Xte, device=dev)
    tok_lists = greedy_decode(model, Xte_t)
    gaps, n_valid, n_opt = [], 0, 0
    for i in range(n_test):
        inst = te.Instance(delta=Xte[i].astype(np.int64))   # delta defines the instance
        assign = tokens_to_assignment(tok_lists[i])
        if assign is None:
            continue
        res = inst.objective(assign)
        if res is None:
            continue
        n_valid += 1
        gap = res[0] - obj_te[i]
        gaps.append(gap)
        if gap < 1e-9:
            n_opt += 1
    gaps = np.array(gaps)
    print(f"\neval on {n_test} held-out instances:")
    print(f"  valid solutions : {n_valid}/{n_test} "
          f"(decode mask enforces graph-legality only; invalid = model chose a "
          f"route busting the {te.HORIZON}-step horizon under this instance's "
          f"deltas — horizon/budget mask at decode is the known next step)")
    if n_valid:
        print(f"  optimal found   : {n_opt}/{n_valid} "
              f"({100*n_opt/max(n_valid,1):.1f}%)")
        print(f"  mean obj gap    : {gaps.mean():.5f}  (exact obj mean "
              f"{obj_te.mean():.4f}; both terms normalized to [0,1])")
        print(f"  max obj gap     : {gaps.max():.5f}")
    return n_valid, n_opt, gaps


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:4]]
    main(*args)
