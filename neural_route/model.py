"""Grid-parametric encoder-decoder Transformer (FM-MCVRP recipe, mini).

Encoder : n_links node tokens (id embedding + delta projection).
Decoder : autoregressive joint fleet sequence (data_gen token scheme),
          cross-attending the encoded instance.
Decoding masks enforce graph-legality AND horizon feasibility: a successor is
allowed only if entering it now still permits finishing the route within the
instance horizon along its cheapest remaining path (budget mask — the OP/TOP
delta; with the calibrated default horizon it rarely binds, but it is exact).
"""

import torch
import torch.nn as nn

from .data_gen import PAD, vocab_of


class RouteModel(nn.Module):
    def __init__(self, grid, d=96, nhead=4, enc_layers=2, dec_layers=3, ff=192,
                 max_len=128):
        super().__init__()
        self.grid = grid
        vb = vocab_of(grid)
        self.vocab = vb["size"]
        self.node_emb = nn.Embedding(grid.n_links, d)
        self.delta_proj = nn.Linear(1, d)
        self.tok_emb = nn.Embedding(self.vocab, d, padding_idx=PAD)
        self.pos_emb = nn.Embedding(max_len, d)
        enc = nn.TransformerEncoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        dec = nn.TransformerDecoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.encoder = nn.TransformerEncoder(enc, enc_layers)
        self.decoder = nn.TransformerDecoder(dec, dec_layers)
        self.head = nn.Linear(d, self.vocab)

    def encode(self, delta):
        ids = torch.arange(self.grid.n_links, device=delta.device)
        h = self.node_emb(ids)[None] + self.delta_proj(delta[..., None])
        return self.encoder(h)

    def forward(self, delta, tokens):
        mem = self.encode(delta)
        inp = tokens[:, :-1]
        pos = torch.arange(inp.size(1), device=inp.device)
        h = self.tok_emb(inp) + self.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            inp.size(1), device=inp.device)
        out = self.decoder(h, mem, tgt_mask=causal,
                           tgt_key_padding_mask=(inp == PAD))
        return self.head(out)


def _min_finish_time(inst, node, t):
    """Earliest possible completion time entering `node` at time t (cheapest
    successor chain in the DAG, exact by memo-free recursion on route_len)."""
    g = inst.grid
    c = inst.cost(node, t)
    s = t + c
    succ = g.con[node]
    if g.END in succ:
        return s
    return min(_min_finish_time(inst, j, s) for j in succ if j != g.END)


def legal_next(inst, prev_tok, n_sep, t_now):
    """(allowed tokens, entry time for link tokens). Applies graph mask +
    horizon/budget mask ('can I still finish in time via j?')."""
    g = inst.grid
    vb = vocab_of(g)
    if n_sep >= inst.n_veh:
        return [vb["EOS"]]
    if prev_tok in (vb["BOS"], vb["SEP"]):
        cands, t_entry = g.con[g.START], inst.depart
    else:
        succ = g.con[prev_tok]
        t_entry = t_now
        if g.END in succ:
            return [vb["SEP"]] if all(s == g.END for s in succ) else \
                [vb["SEP"]] + [j for j in succ if j != g.END
                               and _min_finish_time(inst, j, t_entry) <= inst.horizon]
        cands = succ
    allowed = [j for j in cands
               if _min_finish_time(inst, j, t_entry) <= inst.horizon]
    return allowed or cands[:1]           # degenerate fallback (never hit with calibrated horizon)


@torch.no_grad()
def greedy_decode(model, instances, delta, max_len=None):
    """Masked greedy decoding. instances: list of Instance (per sample, for
    time tracking); delta: (B, n_links) tensor. Returns token lists."""
    model.eval()
    g = model.grid
    vb = vocab_of(g)
    if max_len is None:
        max_len = 2 + max(i.n_veh for i in instances) * (g.route_len + 1) + 2
    B = delta.size(0)
    mem = model.encode(delta)
    toks = torch.full((B, 1), vb["BOS"], dtype=torch.long, device=delta.device)
    n_sep = [0] * B
    t_now = [instances[b].depart for b in range(B)]
    done = [False] * B
    for _ in range(max_len - 1):
        pos = torch.arange(toks.size(1), device=delta.device)
        h = model.tok_emb(toks) + model.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            toks.size(1), device=delta.device)
        out = model.decoder(h, mem, tgt_mask=causal)
        logits = model.head(out[:, -1])
        mask = torch.full_like(logits, float("-inf"))
        for b in range(B):
            allowed = [vb["EOS"]] if done[b] else \
                legal_next(instances[b], int(toks[b, -1]), n_sep[b], t_now[b])
            mask[b, allowed] = 0.0
        nxt = (logits + mask).argmax(-1)
        for b in range(B):
            tk = int(nxt[b])
            if done[b]:
                continue
            if tk == vb["SEP"]:
                n_sep[b] += 1
                t_now[b] = instances[b].depart
            elif tk == vb["EOS"]:
                done[b] = True
            elif 1 <= tk <= g.n_links:
                t_now[b] += instances[b].cost(tk, t_now[b])
        toks = torch.cat([toks, nxt[:, None]], dim=1)
        if all(done):
            break
    return [t.tolist() for t in toks]
