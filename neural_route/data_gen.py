"""Offline (instance -> exact-optimal solution) dataset for the toy spike.

FM-MCVRP-style: labels are computed OFFLINE before training (here by the
provably-exact enumeration solver — no Gurobi calls during training).

Token scheme (vocab 28):
    0 PAD | 1..24 link/node ids | 25 SEP (end of one vehicle's route,
    emitted where the route reaches END via node 12 or 24) | 26 BOS | 27 EOS
Target sequence for a 4-vehicle solution (canonical: routes sorted):
    BOS v1_links... SEP v2_links... SEP v3_links... SEP v4_links... SEP EOS
"""

import numpy as np

from . import toy_env as te

PAD, SEP, BOS, EOS = 0, 25, 26, 27
VOCAB = 28
SEQ_LEN = 1 + te.N_VEH * 7 + 1          # BOS + 4*(6 links + SEP) + EOS = 30


def solution_to_tokens(assignment):
    toks = [BOS]
    for k in sorted(assignment):
        toks.extend(te.ROUTES[k][1:-1])  # 6 link ids (drop 25/26)
        toks.append(SEP)
    toks.append(EOS)
    return np.array(toks, dtype=np.int64)


def tokens_to_assignment(toks):
    """Inverse: token list -> route indices (None if any route invalid)."""
    route_lookup = {tuple(r[1:-1]): k for k, r in enumerate(te.ROUTES)}
    routes, cur = [], []
    for tk in toks:
        if tk in (BOS, PAD):
            continue
        if tk == EOS:
            break
        if tk == SEP:
            k = route_lookup.get(tuple(cur))
            if k is None:
                return None
            routes.append(k)
            cur = []
        else:
            cur.append(int(tk))
    return routes if len(routes) == te.N_VEH and not cur else None


def generate(n, seed=0):
    """Returns features (n, 24) float32 = per-node delta, targets (n, SEQ_LEN)."""
    rng = np.random.default_rng(seed)
    X = np.zeros((n, te.N_LINKS), dtype=np.float32)
    Y = np.full((n, SEQ_LEN), PAD, dtype=np.int64)
    objs = np.zeros(n)
    for i in range(n):
        inst = te.sample_instance(rng)
        assign, obj, _, _ = inst.solve_exact()
        toks = solution_to_tokens(assign)
        X[i] = inst.delta
        Y[i, :len(toks)] = toks
        objs[i] = obj
    return X, Y, objs


if __name__ == "__main__":
    import sys, time
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    t0 = time.time()
    X, Y, objs = generate(n)
    out = f"neural_route/data/toy_{n}.npz"
    import os
    os.makedirs("neural_route/data", exist_ok=True)
    np.savez_compressed(out, X=X, Y=Y, objs=objs)
    print(f"saved {out}: {n} instances in {time.time()-t0:.1f}s "
          f"(mean exact obj {objs.mean():.4f})")
