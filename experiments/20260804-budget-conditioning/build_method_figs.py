"""Method figures for the consolidated deck (current benchmark only).

figM1  end-to-end pipeline (offline label farm + training / online inference)
figM2  model architecture, with the two redesign points marked

Palette: documented categorical slots 1 (blue) / 2 (orange) from the dataviz
reference palette.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
R = f"{HERE}/results"

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
SURF, FILL, EDGE = "#fcfcfb", "#f2f4f7", "#c9c8c2"

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})


def box(ax, x, y, w, h, title, body="", fill=FILL, edge=EDGE, tc=INK,
        ts=10.5, bs=8.8, lw=1.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                fc=fill, ec=edge, lw=lw, zorder=2))
    if body:
        ax.text(x + w / 2, y + h * 0.72, title, ha="center", va="center",
                fontsize=ts, fontweight="bold", color=tc, zorder=3)
        ax.text(x + w / 2, y + h * 0.33, body, ha="center", va="center",
                fontsize=bs, color=INK2, zorder=3, linespacing=1.45)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=ts, color=tc, zorder=3, linespacing=1.45)


def arrow(ax, p0, p1, color=MUTED, lw=1.6, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, color=color, lw=lw,
                                 linestyle=ls, mutation_scale=13,
                                 shrinkA=2, shrinkB=2, zorder=4))


def blank(figsize):
    fig, ax = plt.subplots(figsize=figsize, dpi=200)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


# ------------------------------------------------------------------ figM1
def fig_pipeline():
    fig, ax = blank((13.0, 5.4))

    ax.add_patch(FancyBboxPatch((1.2, 52), 97.4, 42,
                                boxstyle="round,pad=0,rounding_size=0.05",
                                fc="none", ec=EDGE, lw=1.2, ls=(0, (5, 4))))
    ax.text(2.2, 96.0, "OFFLINE  —  run once", fontsize=12.5,
            fontweight="bold", color=INK)
    ax.add_patch(FancyBboxPatch((1.2, 3), 97.4, 38,
                                boxstyle="round,pad=0,rounding_size=0.05",
                                fc="none", ec=EDGE, lw=1.2, ls=(0, (5, 4))))
    ax.text(2.2, 44.5, "ONLINE  —  every new case, 6–9 ms, no solver",
            fontsize=12.5, fontweight="bold", color=INK)

    w, h, y = 17.2, 27, 58
    xs = [3.2, 22.4, 41.6, 60.8, 80.0]
    box(ax, xs[0], y, w, h, "Environment",
        "fixed 4×4 bidirectional\nnetwork · 80 links · 8 gates\ntime-dependent cost c(i,t)\nTD-Dijkstra oracle")
    box(ax, xs[1], y, w, h, "Case sampler",
        "δ ~ congestion\nV vehicles, each with\n(o, d, t₀, ρ) → budget B\nstratified ODs + holdouts")
    box(ax, xs[2], y, w, h, "Gurobi MILP", "multi-commodity\ntime-expanded flow\nper-vehicle deadline t₀+B\n→ reference routes",
        edge=BLUE, tc=BLUE, lw=1.8)
    box(ax, xs[3], y, w, h, "Label set",
        "10 780 (case, routes) pairs\n0 errors · 0 hit the cap\n0.90 s mean per solve\ntokenised sequences")
    box(ax, xs[4], y, w, h, "Training",
        "teacher forcing,\nnext-link cross-entropy\nno solver in the loop\nselect on masked-greedy gap")
    for a, b in zip(xs, xs[1:]):
        arrow(ax, (a + w, y + h / 2), (b, y + h / 2))

    y2, h2 = 8, 27
    box(ax, xs[0], y2, w, h2, "New case",
        "today's δ  +  V tasks\n(o, d, t₀, B)")
    box(ax, xs[1], y2, w, h2, "Encoder",
        "link tokens + task tokens\n→ case memory\n(runs once)")
    box(ax, xs[2], y2, w, h2, "Masked decoder",
        "autoregressive next link\nlogits + (−∞) feasibility mask\nover the joint fleet sequence",
        edge=ORANGE, tc=ORANGE, lw=1.8)
    box(ax, xs[3], y2, w, h2, "Routes",
        "V routes, feasibility\nGUARANTEED by the mask")
    box(ax, xs[4], y2, w, h2, "Evaluation",
        "objective gap vs Gurobi\non held-out cases\n(eval only)", fill="#f7f7f5")
    for a, b in zip(xs, xs[1:]):
        arrow(ax, (a + w, y2 + h2 / 2), (b, y2 + h2 / 2))

    arrow(ax, (xs[4] + w / 2, y), (xs[1] + w / 2, y2 + h2), color=BLUE, lw=1.8)
    ax.text(97.0, 48.8, "trained weights", fontsize=9.5, color=BLUE,
            style="italic", ha="right")
    arrow(ax, (xs[0] + w / 2, y), (xs[2] + w / 2, y2 + h2), color=MUTED,
          lw=1.3, ls=(0, (4, 3)))
    ax.text(2.6, 48.8, "environment supplies the mask", fontsize=9.5,
            color=MUTED, ha="left")

    fig.tight_layout(pad=0.2)
    fig.savefig(f"{R}/figM1_pipeline.png", facecolor=SURF, bbox_inches="tight")
    print("figM1 ok")


# ------------------------------------------------------------------ figM2
def fig_architecture():
    fig, ax = blank((13.0, 6.0))

    ax.text(2.0, 96.5, "Encoder  (runs once per case)", fontsize=12.5,
            fontweight="bold", color=INK)
    ax.text(44.0, 96.5, "Decoder  (autoregressive; one step shown)",
            fontsize=12.5, fontweight="bold", color=INK)

    # ---- encoder tokens
    for i, lab in enumerate(["link\n1", "link\n2", "link\n3", "link\n80"]):
        x = 2.0 + i * 7.6 + (3.0 if i == 3 else 0)
        box(ax, x, 79, 6.6, 11, lab, ts=8.6)
    ax.text(24.8, 84.5, "· · ·", fontsize=12, color=MUTED, ha="center")
    for i, lab in enumerate(["task\n1", "task\n2", "task\nV"]):
        x = 2.0 + i * 7.6 + (3.0 if i == 2 else 0)
        box(ax, x, 65, 6.6, 11, lab, ts=8.6, fill="#fdf1e9", edge=ORANGE, lw=1.6)
    ax.text(17.2, 70.5, "· ·", fontsize=12, color=MUTED, ha="center")

    ax.text(2.0, 60.8, "link token  =  Emb(link id)  +  W·δᵢ", fontsize=9.6,
            color=INK2)
    ax.text(2.0, 56.4, "task token  =  Emb_o(o) + Emb_d(d)", fontsize=9.6,
            color=ORANGE, fontweight="bold")
    ax.text(9.3, 52.4, "+ Proj(t₀) + Proj([ρ, B/H])", fontsize=9.6,
            color=ORANGE, fontweight="bold")

    box(ax, 2.0, 36.5, 33.0, 12.0, "Transformer encoder",
        "self-attention + FFN,  ×3 layers,  d = 128,  4 heads", ts=10.5, bs=8.6)
    arrow(ax, (18.5, 51.3), (18.5, 48.5))
    box(ax, 2.0, 22.5, 33.0, 10.0, "case memory   (80 + V) × d",
        fill="#eaf1fb", edge=BLUE, tc=BLUE, ts=10.5)
    arrow(ax, (18.5, 36.5), (18.5, 32.5))

    # ---- decoder
    toks = ["BOS", "l₁", "l₂", "SEP", "l₁", "…"]
    for i, t in enumerate(toks):
        f, e = ("#fdf1e9", ORANGE) if t == "SEP" else (FILL, EDGE)
        box(ax, 45.0 + i * 6.4, 84, 6.0, 8, t, ts=9, fill=f, edge=e)
    ax.text(45.0, 93.2, "partial JOINT fleet sequence   "
                        "[ BOS · veh1 · SEP · veh2 · SEP · … · EOS ]",
            fontsize=9.4, color=INK2)

    box(ax, 45.0, 68, 38.0, 9.5, "masked self-attention  (causal)", ts=10)
    arrow(ax, (64.0, 84), (64.0, 77.5))
    box(ax, 45.0, 55.5, 38.0, 9.5, "cross-attention  →  case memory", ts=10)
    arrow(ax, (64.0, 68), (64.0, 65.0))
    box(ax, 45.0, 43, 38.0, 9.5, "FFN      —   decoder block × 3", ts=10)
    arrow(ax, (64.0, 55.5), (64.0, 52.5))
    box(ax, 45.0, 30.5, 38.0, 9.5, "linear head  →  logits over vocab (84)", ts=10)
    arrow(ax, (64.0, 43), (64.0, 40.0))
    box(ax, 45.0, 15, 38.0, 9.5, "softmax  →  next link   (argmax / sample)", ts=10)
    arrow(ax, (64.0, 30.5), (64.0, 24.5))
    arrow(ax, (35.0, 27.5), (45.0, 60.3), color=BLUE, lw=1.6)
    ax.add_patch(FancyArrowPatch((45.0, 19.7), (41.8, 19.7), arrowstyle="-",
                                 color=MUTED, lw=1.4))
    ax.add_patch(FancyArrowPatch((41.8, 19.7), (41.8, 88.0), arrowstyle="-",
                                 color=MUTED, lw=1.4))
    arrow(ax, (41.8, 88.0), (45.0, 88.0))
    ax.text(40.4, 52.0, "append token, advance clock  t += c(link, t)",
            fontsize=8.4, color=MUTED, ha="center", va="center", rotation=90)

    # ---- mask
    box(ax, 86.0, 24.0, 13.0, 46.0,
        "feasibility mask\n(no parameters)\n\nlogits[illegal] = −∞\n\n"
        "① not a successor\n     / U-turn\n\n② cannot reach own\n     dest within t₀+B\n\n"
        "③ SEP only next to\n     own dest gate",
        fill="#fdf1e9", edge=ORANGE, tc=ORANGE, ts=8.4, lw=1.8)
    arrow(ax, (83.0, 35.2), (86.0, 40.0), color=ORANGE)
    arrow(ax, (86.0, 30.0), (83.0, 19.7), color=ORANGE)

    # ---- redesign callouts
    ax.add_patch(FancyBboxPatch((2.0, 3.0), 33.0, 17.0,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                fc="#fdf1e9", ec=ORANGE, lw=1.8, zorder=2))
    ax.text(3.3, 17.5, "The two redesign points", fontsize=10.2,
            fontweight="bold", color=ORANGE, zorder=3)
    ax.text(3.3, 9.8, "①  instance attributes (o, d, t₀, B) moved OUT of the\n"
                      "     weights and INTO the input  →  one model, all cases\n"
                      "②  the mask threshold is the vehicle's OWN budget t₀+B\n"
                      "     →  unseen budgets stay feasible by construction",
            fontsize=8.9, color=INK2, va="center", zorder=3, linespacing=1.55)

    ax.text(2.0, 1.0, "1.04 M parameters  ·  vocab = 80 links + BOS/SEP/EOS/PAD  ·  "
                      "joint sequence ≈ Σᵥ(route len + 1) + 2 tokens  ·  training: teacher forcing + "
                      "cross-entropy on Gurobi sequences  ·  inference: masked greedy",
            fontsize=8.8, color=MUTED)

    fig.tight_layout(pad=0.2)
    fig.savefig(f"{R}/figM2_architecture.png", facecolor=SURF,
                bbox_inches="tight")
    print("figM2 ok")


if __name__ == "__main__":
    fig_pipeline()
    fig_architecture()
