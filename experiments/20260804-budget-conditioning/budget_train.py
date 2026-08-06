"""Budget-conditioned model + training + 5-layer eval (option (a), YIL-113).

Deltas vs `neural_route/bigrid_train.py` (which stays untouched):

  1. TASK TOKEN gains the budget attribute:
        Emb_o(o) + Emb_d(d) + Proj(t0)  ->  ... + Proj([rho_v, B_v/H])
     (same recipe that put t0 in for extension 1; RouteFinder-style global
     attribute embedding.)
  2. DECODER MASK switches from the global horizon to the vehicle's own
     deadline:
        min_finish(j, t, d) <= H   ->   min_finish(j, t, d) <= t0_v + B_v
     Feasibility is therefore ENFORCED, not learned: an unseen budget still
     yields a feasible route by construction.
  3. Objective / gap use the budget normalizer sum_v B_v (`objective_budget`).

Usage:
  python budget_train.py train [epochs] [ckpt] [seed]
  python budget_train.py eval  <ckpt> [layer|all]
  python budget_train.py curve <ckpt>          # coverage-vs-rho response curve
"""

import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, "/home/yilin/Research/Route_TSC_CART")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from neural_route.bigrid import BiGrid  # noqa: E402
from modenv import ModInstance as BiInstance, calibrate_horizon  # noqa: E402

from budget_milp import objective_budget  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = f"{HERE}/data_mod24"
OUTD = f"{HERE}/results_mod24"
PAD, SEP, BOS, EOS = 0, 81, 82, 83
VOCAB = 84
MAX_LEN = 128                   # bounded periodic costs -> longer routes
                                # (pre-mod max 72; mod-96 farm hit 88)
MAX_V = 8

GRID = BiGrid(4, 4)
HORIZON = calibrate_horizon(GRID)
GATE_IDS = sorted(GRID.gates.values())
GIDX = {g: i for i, g in enumerate(GATE_IDS)}

LAYERS = {                      # name -> (file, human label)
    "L1_same":     ("test_seed10000",      "L1 same-distribution"),
    "L2_odzero":   ("zeroshot_seed20000",  "L2 OD zero-shot"),
    "L3_vextrap":  ("vextrap_seed30000",   "L3 fleet extrapolation V in {5,8}"),
    "L4a_rhoint":  ("rhointerp_seed40000", "L4a UNSEEN rho (interp 1.25/1.75)"),
    "L4b_rhoext":  ("rhoextrap_seed50000", "L4b UNSEEN rho (extrap 4.0)"),
}


# --------------------------------------------------------------- data


def load(split):
    recs = [json.loads(l) for l in open(f"{DATA}/{split}.jsonl")]
    recs = [r for r in recs if "error" not in r]
    n = len(recs)
    X = np.zeros((n, GRID.n_links), dtype=np.float32)
    TASK = np.zeros((n, MAX_V, 3), dtype=np.int64)      # o_idx, d_idx, t0
    BUD = np.zeros((n, MAX_V, 2), dtype=np.float32)     # rho_norm, B/H
    NV = np.zeros(n, dtype=np.int64)
    Y = np.full((n, MAX_LEN), PAD, dtype=np.int64)
    OBJ = np.zeros(n)
    for i, r in enumerate(recs):
        X[i] = r["delta"]
        NV[i] = len(r["tasks"])
        for k, ((o, d, t0), rho, B) in enumerate(
                zip(r["tasks"], r["rhos"], r["budgets"])):
            TASK[i, k] = (GIDX[o], GIDX[d], t0)
            BUD[i, k] = ((rho - 1.0) / 3.0, B / HORIZON)
        toks = [BOS]
        for rt in r["routes"]:
            toks.extend(rt)
            toks.append(SEP)
        toks.append(EOS)
        assert len(toks) <= MAX_LEN, len(toks)
        Y[i, :len(toks)] = toks
        OBJ[i] = r["obj"]
    return recs, X, TASK, BUD, NV, Y, OBJ


def make_insts(rs):
    out = []
    for r in rs:
        inst = BiInstance(GRID, np.array(r["delta"]),
                          [tuple(t) for t in r["tasks"]], horizon=HORIZON)
        inst.budgets = list(r["budgets"])
        out.append(inst)
    return out


# --------------------------------------------------------------- model


class BudgetRouteModel(nn.Module):
    def __init__(self, d=128, nhead=4, enc_layers=3, dec_layers=3, ff=256):
        super().__init__()
        self.link_emb = nn.Embedding(GRID.n_links, d)
        self.delta_proj = nn.Linear(1, d)
        self.gate_o = nn.Embedding(8, d)
        self.gate_d = nn.Embedding(8, d)
        self.t0_proj = nn.Linear(1, d)
        self.bud_proj = nn.Linear(2, d)                 # <-- NEW: [rho, B/H]
        self.tok_emb = nn.Embedding(VOCAB, d, padding_idx=PAD)
        self.pos_emb = nn.Embedding(MAX_LEN, d)
        enc = nn.TransformerEncoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        dec = nn.TransformerDecoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.encoder = nn.TransformerEncoder(enc, enc_layers)
        self.decoder = nn.TransformerDecoder(dec, dec_layers)
        self.head = nn.Linear(d, VOCAB)

    def encode(self, delta, task, bud, nv):
        B = delta.size(0)
        ids = torch.arange(GRID.n_links, device=delta.device)
        link_tok = self.link_emb(ids)[None].expand(B, -1, -1) \
            + self.delta_proj(delta[..., None])
        task_tok = (self.gate_o(task[..., 0]) + self.gate_d(task[..., 1])
                    + self.t0_proj(task[..., 2:3].float())
                    + self.bud_proj(bud))
        mem = torch.cat([link_tok, task_tok], 1)
        pad = torch.zeros(B, GRID.n_links + MAX_V, dtype=torch.bool,
                          device=delta.device)
        for b in range(B):
            pad[b, GRID.n_links + nv[b]:] = True
        return self.encoder(mem, src_key_padding_mask=pad), pad

    def forward(self, delta, task, bud, nv, tokens):
        mem, mem_pad = self.encode(delta, task, bud, nv)
        inp = tokens[:, :-1]
        pos = torch.arange(inp.size(1), device=inp.device)
        h = self.tok_emb(inp) + self.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            inp.size(1), device=inp.device)
        out = self.decoder(h, mem, tgt_mask=causal,
                           tgt_key_padding_mask=(inp == PAD),
                           memory_key_padding_mask=mem_pad)
        return self.head(out)


# --------------------------------------------------------- budget mask


def legal_next(inst, prev_tok, veh_i, t_now):
    """Identical in structure to the ext-1 mask, EXCEPT the reachability
    threshold is this vehicle's own deadline instead of the global horizon."""
    g = inst.grid
    if veh_i >= len(inst.tasks):
        return [EOS]
    o, d, t0 = inst.tasks[veh_i]
    dl = min(inst.horizon, t0 + inst.budgets[veh_i])     # <-- budget deadline
    if prev_tok in (BOS, SEP):
        cands, t = g.gate_out[o], t0
    else:
        if prev_tok in g.gate_in[d]:
            allowed = [SEP]
            allowed += [j for j in g.con[prev_tok]
                        if inst.min_finish(j, t_now, d) <= dl]
            return allowed
        cands, t = g.con[prev_tok], t_now
    out = [j for j in cands if inst.min_finish(j, t, d) <= dl]
    return out or [cands[0]]


@torch.no_grad()
def greedy_decode(model, insts, delta, task, bud, nv, dev):
    model.eval()
    B = delta.size(0)
    mem, mem_pad = model.encode(delta, task, bud, nv)
    toks = torch.full((B, 1), BOS, dtype=torch.long, device=dev)
    veh = [0] * B
    t_now = [insts[b].tasks[0][2] if insts[b].tasks else 0 for b in range(B)]
    done = [False] * B
    for _ in range(MAX_LEN - 1):
        pos = torch.arange(toks.size(1), device=dev)
        h = model.tok_emb(toks) + model.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            toks.size(1), device=dev)
        out = model.decoder(h, mem, tgt_mask=causal,
                            memory_key_padding_mask=mem_pad)
        logits = model.head(out[:, -1])
        mask = torch.full_like(logits, float("-inf"))
        for b in range(B):
            allowed = [EOS] if done[b] else \
                legal_next(insts[b], int(toks[b, -1]), veh[b], t_now[b])
            mask[b, allowed] = 0.0
        nxt = (logits + mask).argmax(-1)
        for b in range(B):
            tk = int(nxt[b])
            if done[b]:
                continue
            if tk == SEP:
                veh[b] += 1
                if veh[b] < len(insts[b].tasks):
                    t_now[b] = insts[b].tasks[veh[b]][2]
            elif tk == EOS:
                done[b] = True
            elif 1 <= tk <= GRID.n_links:
                t_now[b] += insts[b].cost(tk, t_now[b])
        toks = torch.cat([toks, nxt[:, None]], 1)
        if all(done):
            break
    return [t.tolist() for t in toks]


def toks_to_routes(toks, n_veh):
    routes, cur = [], []
    for tk in toks:
        tk = int(tk)
        if tk in (BOS, PAD):
            continue
        if tk == EOS:
            break
        if tk == SEP:
            routes.append(cur)
            cur = []
        else:
            cur.append(tk)
    return routes if len(routes) == n_veh and not cur else None


# --------------------------------------------------------------- eval


def _decode_batch(model, rs, X, TASK, BUD, NV, sl, dev):
    insts = make_insts(rs)
    outs = greedy_decode(model,
                         insts,
                         torch.tensor(X[sl], device=dev),
                         torch.tensor(TASK[sl], device=dev),
                         torch.tensor(BUD[sl], device=dev),
                         torch.tensor(NV[sl], device=dev), dev)
    res = []
    for b, r in enumerate(rs):
        routes = toks_to_routes(outs[b], len(r["tasks"]))
        val = objective_budget(insts[b], routes, r["budgets"]) if routes else None
        res.append((r, val))
    return res


def eval_split(model, split, dev, n=None, batch=25, per_case=None):
    recs, X, TASK, BUD, NV, Y, OBJ = load(split)
    if n:
        recs = recs[:n]
    gaps, feas, better = [], 0, 0
    rows = []
    t0 = time.time()
    for s in range(0, len(recs), batch):
        sl = slice(s, min(s + batch, len(recs)))
        for r, val in _decode_batch(model, recs[sl], X, TASK, BUD, NV, sl, dev):
            if val is None:
                rows.append(dict(idx=r["idx"], feasible=0))
                continue
            feas += 1
            gap = val[0] - r["obj"]
            gaps.append(gap)
            better += int(gap <= 1e-9)
            rows.append(dict(idx=r["idx"], feasible=1, V=len(r["tasks"]),
                             rho_mean=round(float(np.mean(r["rhos"])), 3),
                             ref_obj=round(r["obj"], 6),
                             model_obj=round(val[0], 6), gap=round(gap, 6),
                             ref_cost=r["cost"], model_cost=val[1],
                             ref_cov=r["cov"], model_cov=val[2]))
    if per_case:
        import csv
        with open(per_case, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(max(rows, key=len).keys()))
            w.writeheader()
            for row in rows:
                w.writerow(row)
    g = np.array(gaps) if gaps else np.array([np.inf])
    return dict(n=len(recs), feasible=feas, match_or_better=better,
                mean_gap=float(g.mean()), median_gap=float(np.median(g)),
                max_gap=float(g.max()), mean_ref_obj=float(np.mean(OBJ)),
                rel_gap=float(g.mean() / abs(np.mean(OBJ))),
                ms_per_case=round(1000 * (time.time() - t0) / len(recs), 1))


def curve(model, dev, split="curve_seed60000", batch=25):
    """Coverage / cost / objective vs rho — model against Gurobi."""
    recs, X, TASK, BUD, NV, Y, OBJ = load(split)
    by = {}
    for s in range(0, len(recs), batch):
        sl = slice(s, min(s + batch, len(recs)))
        for r, val in _decode_batch(model, recs[sl], X, TASK, BUD, NV, sl, dev):
            k = r["rho_tag"]
            e = by.setdefault(k, dict(n=0, feas=0, ref_cov=[], mdl_cov=[],
                                      ref_cost=[], mdl_cost=[], gaps=[]))
            e["n"] += 1
            e["ref_cov"].append(r["cov"])
            e["ref_cost"].append(r["cost"])
            if val is None:
                continue
            e["feas"] += 1
            e["mdl_cov"].append(val[2])
            e["mdl_cost"].append(val[1])
            e["gaps"].append(val[0] - r["obj"])
    out = []
    for k in sorted(by):
        e = by[k]
        out.append(dict(rho=k, n=e["n"], feasible=e["feas"],
                        gurobi_cov=float(np.mean(e["ref_cov"])),
                        model_cov=float(np.mean(e["mdl_cov"])),
                        gurobi_cost=float(np.mean(e["ref_cost"])),
                        model_cost=float(np.mean(e["mdl_cost"])),
                        mean_gap=float(np.mean(e["gaps"]))))
    return out


# --------------------------------------------------------------- train


def train(epochs=60, out=f"{OUTD}/budget_model_seed0.pt", seed=0,
          n_train=None):
    os.makedirs(OUTD, exist_ok=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)
    np.random.seed(seed)
    recs, X, TASK, BUD, NV, Y, OBJ = load("train_seed0")
    if n_train:                                    # for the data-slope study
        recs, X, TASK, BUD, NV, Y, OBJ = (recs[:n_train], X[:n_train],
                                          TASK[:n_train], BUD[:n_train],
                                          NV[:n_train], Y[:n_train],
                                          OBJ[:n_train])
    n_val = 150
    model = BudgetRouteModel().to(dev)
    print(f"params {sum(p.numel() for p in model.parameters())/1e6:.2f}M | "
          f"train {len(recs)-n_val} | val {n_val} | H {HORIZON} | seed {seed}",
          flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    lossf = nn.CrossEntropyLoss(ignore_index=PAD)
    Xt = torch.tensor(X[:-n_val], device=dev)
    Tt = torch.tensor(TASK[:-n_val], device=dev)
    Ut = torch.tensor(BUD[:-n_val], device=dev)
    Nt = torch.tensor(NV[:-n_val], device=dev)
    Yt = torch.tensor(Y[:-n_val], device=dev)
    val_recs, vsl = recs[-n_val:], slice(len(recs) - n_val, len(recs))
    best, bs, N = np.inf, 32, Xt.size(0)
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(N, device=dev)
        tot, t0 = 0.0, time.time()
        for i in range(0, N, bs):
            idx = perm[i:i + bs]
            logits = model(Xt[idx], Tt[idx], Ut[idx], Nt[idx], Yt[idx])
            loss = lossf(logits.reshape(-1, VOCAB), Yt[idx][:, 1:].reshape(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        gaps, feas = [], 0
        for s in range(0, n_val, 25):
            sl = slice(vsl.start + s, min(vsl.start + s + 25, vsl.stop))
            for r, val in _decode_batch(model, recs[sl], X, TASK, BUD, NV,
                                        sl, dev):
                if val is not None:
                    feas += 1
                    gaps.append(val[0] - r["obj"])
        vgap = float(np.mean(gaps)) if gaps else np.inf
        mark = ""
        if vgap < best:
            best, mark = vgap, "  <- saved"
            torch.save(model.state_dict(), out)
        print(f"ep {ep+1:3d}  CE {tot/N:.4f}  val_gap {vgap:.5f} "
              f"(feas {feas}/{n_val})  [{time.time()-t0:.0f}s]{mark}", flush=True)
    print("best val_gap:", best, "->", out, flush=True)
    return best


if __name__ == "__main__":
    cmd = sys.argv[1]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    if cmd == "train":
        ep = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        ck = sys.argv[3] if len(sys.argv) > 3 else f"{OUTD}/budget_model_seed0.pt"
        sd = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        nt = int(sys.argv[5]) if len(sys.argv) > 5 else None
        train(ep, ck, sd, nt)
    elif cmd == "eval":
        model = BudgetRouteModel().to(dev)
        model.load_state_dict(torch.load(sys.argv[2], weights_only=True))
        keys = list(LAYERS) if (len(sys.argv) < 4 or sys.argv[3] == "all") \
            else [sys.argv[3]]
        allres = {}
        for k in keys:
            f, lab = LAYERS[k]
            r = eval_split(model, f, dev,
                           per_case=f"{OUTD}/percase_{k}.csv")
            allres[k] = dict(label=lab, **r)
            print(k, json.dumps(allres[k]), flush=True)
        with open(f"{OUTD}/eval_layers.json", "w") as fh:
            json.dump(allres, fh, indent=1)
    elif cmd == "curve":
        model = BudgetRouteModel().to(dev)
        model.load_state_dict(torch.load(sys.argv[2], weights_only=True))
        rows = curve(model, dev)
        with open(f"{OUTD}/curve.json", "w") as fh:
            json.dump(rows, fh, indent=1)
        for r in rows:
            print(json.dumps(r), flush=True)
