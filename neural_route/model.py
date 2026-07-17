"""Small encoder-decoder Transformer for the toy spike (FM-MCVRP recipe, mini).

Encoder input : the instance = 24 node tokens; each token embeds its node id
                plus a linear projection of that node's cost offset delta.
Decoder       : autoregressive over solution tokens (data_gen scheme),
                cross-attending the encoded instance — predicts the NEXT node
                of the joint 4-vehicle route sequence.
Feasibility at inference is enforced by masking logits to graph-legal moves
(see legal_next()): successors of the current node; SEP only from 12/24;
after SEP a new route starts from START's successors {1, 13}; EOS after 4 SEPs.
"""

import torch
import torch.nn as nn

from . import toy_env as te
from .data_gen import BOS, EOS, PAD, SEP, VOCAB


class ToyRouteModel(nn.Module):
    def __init__(self, d=96, nhead=4, enc_layers=2, dec_layers=3, ff=192):
        super().__init__()
        self.node_emb = nn.Embedding(te.N_LINKS, d)      # encoder side: nodes 1..24
        self.delta_proj = nn.Linear(1, d)
        self.tok_emb = nn.Embedding(VOCAB, d, padding_idx=PAD)
        self.pos_emb = nn.Embedding(64, d)
        enc = nn.TransformerEncoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        dec = nn.TransformerDecoderLayer(d, nhead, ff, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.encoder = nn.TransformerEncoder(enc, enc_layers)
        self.decoder = nn.TransformerDecoder(dec, dec_layers)
        self.head = nn.Linear(d, VOCAB)

    def encode(self, delta):                              # delta: (B, 24)
        ids = torch.arange(te.N_LINKS, device=delta.device)
        h = self.node_emb(ids)[None] + self.delta_proj(delta[..., None])
        return self.encoder(h)

    def forward(self, delta, tokens):
        """Teacher-forced logits for tokens[:, 1:] given tokens[:, :-1]."""
        mem = self.encode(delta)
        inp = tokens[:, :-1]
        pos = torch.arange(inp.size(1), device=inp.device)
        h = self.tok_emb(inp) + self.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            inp.size(1), device=inp.device)
        out = self.decoder(h, mem, tgt_mask=causal,
                           tgt_key_padding_mask=(inp == PAD))
        return self.head(out)                             # (B, L-1, VOCAB)


def legal_next(prev_tok, n_sep):
    """Graph-legal next tokens given previous token and #routes completed."""
    if n_sep >= te.N_VEH:
        return [EOS]
    if prev_tok in (BOS, SEP):
        return te.CON[te.START]                           # {1, 13}
    succ = [s for s in te.CON[prev_tok] if s != te.END]
    if te.END in te.CON[prev_tok]:
        succ = succ + [SEP]                               # 12/24 -> end of route
    return succ


@torch.no_grad()
def greedy_decode(model, delta, max_len=32):
    """Masked greedy decoding. delta: (B, 24). Returns token lists per sample."""
    model.eval()
    B = delta.size(0)
    mem = model.encode(delta)
    toks = torch.full((B, 1), BOS, dtype=torch.long, device=delta.device)
    n_sep = [0] * B
    done = [False] * B
    for _ in range(max_len - 1):
        pos = torch.arange(toks.size(1), device=delta.device)
        h = model.tok_emb(toks) + model.pos_emb(pos)[None]
        causal = nn.Transformer.generate_square_subsequent_mask(
            toks.size(1), device=delta.device)
        out = model.decoder(h, mem, tgt_mask=causal)
        logits = model.head(out[:, -1])                   # (B, VOCAB)
        mask = torch.full_like(logits, float("-inf"))
        for b in range(B):
            allowed = [EOS] if done[b] else legal_next(int(toks[b, -1]), n_sep[b])
            mask[b, allowed] = 0.0
        nxt = (logits + mask).argmax(-1)
        for b in range(B):
            if nxt[b] == SEP:
                n_sep[b] += 1
            if nxt[b] == EOS:
                done[b] = True
        toks = torch.cat([toks, nxt[:, None]], dim=1)
        if all(done):
            break
    return [t.tolist() for t in toks]
