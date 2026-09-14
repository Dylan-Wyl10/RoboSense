"""Extension-1 model + training on the bidirectional grid (YIL-113).

Usage:
  python -m neural_route.bigrid_train train  [epochs] [ckpt_out]
  python -m neural_route.bigrid_train eval   <ckpt>   [layer: test|zeroshot|vextrap|all]

Encoder tokens: 80 link tokens (Emb(link) + W*delta_i) + V task tokens
(Emb_o(gate) + Emb_d(gate) + W*t0). Decoder: joint fleet sequence
[BOS v1links SEP v2links SEP ... EOS]; masked greedy decoding uses
BiInstance.min_finish (time-dependent Dijkstra) for the budget mask.
Model selection: per-epoch masked-greedy objective gap on a validation
slice — NOT cross-entropy.
"""

import json
import sys
import time

import numpy as np
import torch
import torch.nn as nn

from .bigrid import BiGrid, BiInstance, calibrate_horizon

DATA = "/home/yilin/Research/Route_TSC_CART/experiments/20260716-fm-mcvrp-local/data"
OUTD = "/home/yilin/Research/Route_TSC_CART/experiments/20260716-fm-mcvrp-local/results"
PAD, SEP, BOS, EOS = 0, 81, 82, 83
VOCAB = 84
MAX_LEN = 140
MAX_V = 8

GRID = BiGrid(4, 4)
HORIZON = calibrate_horizon(GRID)
GATE_IDS = sorted(GRID.gates.values())          # 81..88 -> index 0..7
GIDX = {g: i for i, g in enumerate(GATE_IDS)}


def load(split):
    recs = [json.loads(l) for l in open(f"{DATA}/{split}.jsonl")]
    recs = [r for r in recs if "error" not in r]
    X = np.zeros((len(recs), GRID.n_links), dtype=np.float32)
    TASK = np.zeros((len(recs), MAX_V, 3), dtype=np.int64)   # (o_idx, d_idx, t0)
    NV = np.zeros(len(recs), dtype=np.int64)
    Y = np.full((len(recs), MAX_LEN), PAD, dtype=np.int64)
    OBJ = np.zeros(len(recs))
    for i, r in enumerate(recs):
        X[i] = r["delta"]
        NV[i] = len(r["tasks"])
        for k, (o, d, t0) in enumerate(r["tasks"]):
            TASK[i, k] = (GIDX[o], GIDX[d], t0)
        toks = [BOS]
        for rt in r["routes"]:
            toks.extend(rt)
            toks.append(SEP)
        toks.append(EOS)
        assert len(toks) <= MAX_LEN, len(toks)
        Y[i, :len(toks)] = toks
        OBJ[i] = r["obj"]
    return recs, X, TASK, NV, Y, OBJ


class BiRouteModel(nn.Module):
    def __init__(self, d=128, nhead=4, enc_layers=3, dec_layers=3, ff=256):
        super().__init__()
        self.link_emb = nn.Embedding(GRID.n_links, d)
        self.delta_proj = nn.Linear(1, d)
        self.gate_o = nn.Embedding(8, d)
        self.gate_d = nn.Embedding(8, d)
        self.t0_proj = nn.Linear(1, d)
        self.tok_emb = nn.Embedding(VOCAB, d, padding_idx=PAD)
        self.pos_emb = nn.Embedding(MAX_LEN, d)
        enc = nn.TransformerEncoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        dec = nn.TransformerDecoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.encoder = nn.TransformerEncoder(enc, enc_layers)
        self.decoder = nn.TransformerDecoder(dec, dec_layers)
        self.head = nn.Linear(d, VOCAB)

    def encode(self, delta, task, nv):
        B = delta.size(0)
        ids = torch.arange(GRID.n_links, device=delta.device)
        link_tok = self.link_emb(ids)[None].expand(B, -1, -1) \
            + self.delta_proj(delta[..., None])
        task_tok = (self.gate_o(task[..., 0]) + self.gate_d(task[..., 1])
                    + self.t0_proj(task[..., 2:3].float()))
        mem = torch.cat([link_tok, task_tok], 1)
        pad = torch.zeros(B, GRID.n_links + MAX_V, dtype=torch.bool,
                          device=delta.device)
        for b in range(B):
            pad[b, GRID.n_links + nv[b]:] = True
        return self.encoder(mem, src_key_padding_mask=pad), pad

    def forward(self, delta, task, nv, tokens):
        mem, mem_pad = self.encode(delta, task, nv)
        inp = tokens[:, :-1]
        pos = torch.arange(inp.size(1), device=inp.device)
        h = self.tok_emb(inp) + self.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            inp.size(1), device=inp.device)
        out = self.decoder(h, mem, tgt_mask=causal,
                           tgt_key_padding_mask=(inp == PAD),
                           memory_key_padding_mask=mem_pad)
        return self.head(out)


def legal_next(inst, prev_tok, veh_i, t_now):
    g = inst.grid
    if veh_i >= len(inst.tasks):
        return [EOS]
    o, d, t0 = inst.tasks[veh_i]
    if prev_tok in (BOS, SEP):
        cands, t = g.gate_out[o], t0
    else:
        if prev_tok in g.gate_in[d]:
            allowed = [SEP]
            allowed += [j for j in g.con[prev_tok]
                        if inst.min_finish(j, t_now, d) <= inst.horizon]
            return allowed
        cands, t = g.con[prev_tok], t_now
    out = [j for j in cands if inst.min_finish(j, t, d) <= inst.horizon]
    return out or [cands[0]]


@torch.no_grad()
def greedy_decode(model, insts, delta, task, nv, dev):
    model.eval()
    B = delta.size(0)
    mem, mem_pad = model.encode(delta, task, nv)
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


def eval_split(model, split, dev, n=None, batch=25):
    recs, X, TASK, NV, Y, OBJ = load(split)
    if n:
        recs, X, TASK, NV, OBJ = recs[:n], X[:n], TASK[:n], NV[:n], OBJ[:n]
    gaps, feas, better = [], 0, 0
    for s in range(0, len(recs), batch):
        rs = recs[s:s + batch]
        insts = [BiInstance(GRID, np.array(r["delta"]),
                            [tuple(t) for t in r["tasks"]], horizon=HORIZON)
                 for r in rs]
        d_t = torch.tensor(X[s:s + batch], device=dev)
        t_t = torch.tensor(TASK[s:s + batch], device=dev)
        n_t = torch.tensor(NV[s:s + batch], device=dev)
        outs = greedy_decode(model, insts, d_t, t_t, n_t, dev)
        for b, r in enumerate(rs):
            routes = toks_to_routes(outs[b], len(r["tasks"]))
            if routes is None:
                continue
            res = insts[b].objective(routes)
            if res is None:
                continue
            feas += 1
            gap = res[0] - r["obj"]
            gaps.append(gap)
            if gap <= 1e-9:
                better += 1
    gaps = np.array(gaps) if gaps else np.array([np.inf])
    return dict(n=len(recs), feasible=feas, match_or_better=better,
                mean_gap=float(gaps.mean()), max_gap=float(gaps.max()),
                mean_ref=float(np.mean(OBJ)))


def train(epochs=60, out=f"{OUTD}/bigrid_model_seed0.pt", seed=0):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(seed)
    recs, X, TASK, NV, Y, OBJ = load("train_seed0")
    n_val = 100                                   # tail of train as val slice
    model = BiRouteModel().to(dev)
    print(f"params: {sum(p.numel() for p in model.parameters())/1e6:.2f}M "
          f"| train {len(recs)-n_val} | horizon {HORIZON}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    lossf = nn.CrossEntropyLoss(ignore_index=PAD)
    Xt = torch.tensor(X[:-n_val], device=dev)
    Tt = torch.tensor(TASK[:-n_val], device=dev)
    Nt = torch.tensor(NV[:-n_val], device=dev)
    Yt = torch.tensor(Y[:-n_val], device=dev)
    val_recs = recs[-n_val:]
    best = np.inf
    B = 32
    N = Xt.size(0)
    for ep in range(epochs):
        model.train()
        perm = torch.randperm(N, device=dev)
        tot = 0.0
        t0 = time.time()
        for i in range(0, N, B):
            idx = perm[i:i + B]
            logits = model(Xt[idx], Tt[idx], Nt[idx], Yt[idx])
            loss = lossf(logits.reshape(-1, VOCAB),
                         Yt[idx][:, 1:].reshape(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
        # masked-greedy validation on the val slice
        insts = [BiInstance(GRID, np.array(r["delta"]),
                            [tuple(t) for t in r["tasks"]], horizon=HORIZON)
                 for r in val_recs]
        gaps, feas = [], 0
        for s in range(0, n_val, 25):
            rs = val_recs[s:s + 25]
            d_t = torch.tensor(X[-n_val + s:-n_val + s + 25] if s + 25 < n_val
                               else X[-n_val + s:], device=dev)
            t_t = torch.tensor(TASK[-n_val + s:-n_val + s + 25] if s + 25 < n_val
                               else TASK[-n_val + s:], device=dev)
            n_t = torch.tensor(NV[-n_val + s:-n_val + s + 25] if s + 25 < n_val
                               else NV[-n_val + s:], device=dev)
            outs = greedy_decode(model, insts[s:s + 25], d_t, t_t, n_t, dev)
            for b, r in enumerate(rs):
                routes = toks_to_routes(outs[b], len(r["tasks"]))
                res = insts[s + b].objective(routes) if routes else None
                if res:
                    feas += 1
                    gaps.append(res[0] - r["obj"])
        vgap = float(np.mean(gaps)) if gaps else np.inf
        marker = ""
        if vgap < best:
            best = vgap
            torch.save(model.state_dict(), out)
            marker = "  <- saved"
        print(f"ep {ep+1:3d}  CE {tot/N:.4f}  val_gap {vgap:.5f} "
              f"(feas {feas}/{n_val})  [{time.time()-t0:.0f}s]{marker}",
              flush=True)
    print("best val_gap:", best, "->", out, flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "train":
        ep = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        out = sys.argv[3] if len(sys.argv) > 3 else f"{OUTD}/bigrid_model_seed0.pt"
        train(ep, out)
    else:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        model = BiRouteModel().to(dev)
        model.load_state_dict(torch.load(sys.argv[2], weights_only=True))
        layers = ["test_seed10000", "zeroshot_seed20000", "vextrap_seed30000"] \
            if (len(sys.argv) < 4 or sys.argv[3] == "all") else [sys.argv[3]]
        for lay in layers:
            r = eval_split(model, lay, dev)
            print(lay, json.dumps(r), flush=True)
