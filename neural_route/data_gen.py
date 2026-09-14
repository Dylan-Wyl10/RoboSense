"""Offline (instance -> solution) dataset, labels from the GUROBI MILP.

User directive 2026-07-17: no brute force in the pipeline — Gurobi generates
the training labels (time-expanded flow MILP, milp_baseline.solve_milp), the
same code path that will run on large networks. FM-MCVRP-style: all labels
computed offline; the training loop makes zero solver calls.

Token scheme for a grid with L links (vocab L+4):
    0 PAD | 1..L link ids | L+1 SEP (route reached END) | L+2 BOS | L+3 EOS
Target: BOS v1_links... SEP v2... SEP v3... SEP v4... SEP EOS
(routes canonically sorted; every route has exactly grid.route_len links).
"""

import numpy as np

from . import toy_env as te
from .milp_baseline import solve_milp

PAD = 0


def vocab_of(grid):
    L = grid.n_links
    return {"SEP": L + 1, "BOS": L + 2, "EOS": L + 3, "size": L + 4}


def seq_len_of(grid, n_veh=4):
    return 1 + n_veh * (grid.route_len + 1) + 1


def solution_to_tokens(grid, routes):
    vb = vocab_of(grid)
    toks = [vb["BOS"]]
    for r in sorted(routes):
        toks.extend(r[1:-1])
        toks.append(vb["SEP"])
    toks.append(vb["EOS"])
    return np.array(toks, dtype=np.int64)


def tokens_to_routes(grid, toks, n_veh=4):
    """Token list -> explicit routes (None if malformed)."""
    vb = vocab_of(grid)
    routes, cur = [], []
    for tk in toks:
        tk = int(tk)
        if tk in (vb["BOS"], PAD):
            continue
        if tk == vb["EOS"]:
            break
        if tk == vb["SEP"]:
            if len(cur) != grid.route_len:
                return None
            routes.append([grid.START] + cur + [grid.END])
            cur = []
        else:
            cur.append(tk)
    return routes if len(routes) == n_veh and not cur else None


def generate(n, grid=te.GRID3, seed=0, n_veh=4, time_limit=60, log_every=200):
    """Returns X (n, n_links) float32 deltas, Y (n, seq_len) tokens, objs (n,)."""
    rng = np.random.default_rng(seed)
    SL = seq_len_of(grid, n_veh)
    X = np.zeros((n, grid.n_links), dtype=np.float32)
    Y = np.full((n, SL), PAD, dtype=np.int64)
    objs = np.zeros(n)
    for i in range(n):
        inst = te.sample_instance(rng, grid=grid, n_veh=n_veh)
        res = solve_milp(inst, time_limit=time_limit)
        if res is None:
            raise RuntimeError(f"MILP produced no solution for instance {i}")
        routes, obj, _, _ = res
        toks = solution_to_tokens(grid, routes)
        X[i] = inst.delta
        Y[i, :len(toks)] = toks
        objs[i] = obj
        if log_every and (i + 1) % log_every == 0:
            print(f"  labelled {i+1}/{n}")
    return X, Y, objs
