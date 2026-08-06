"""Deck figures for the mod-24 link cost (YIL-125 r5, 2026-08-06).

Cost law (user simplification, r5): c(i,t) = (base(i)+t) mod 24 + 1 + delta_i
— single source of truth in modenv.py (ModInstance / PERIOD / H). All
matrices computed with modenv's exact (link, entry-time) search (the wrap
breaks FIFO; single-label TD-Dijkstra is wrong on 28% of queries here).

This revision also makes the animation CLEARER (user ask): plainer titles,
bigger annotations, slower loop (24 frames, one full congestion cycle).

Outputs (results/):
  figA_network_mod.png   slide 4: link-id network + t0=0 heatmap
  figA_td_travel_mod.gif slide 5: one full cycle t0 = 0..23, step 1
  figA_delta_day_mod.png slide 6: sampled day's delta + change matrix
                         (diverging: congestion can SPEED trips up)
Prints the deck-text numbers at the end.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
from matplotlib.patches import Circle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.expanduser("~/Research/Route_TSC_CART"))
from neural_route.bigrid import BiGrid  # noqa: E402
from modenv import ModInstance, PERIOD, calibrate_horizon  # noqa: E402

R = f"{HERE}/results"
INK, INK2, SURF = "#0B0B0B", "#52514E", "#FCFCFB"
ORANGE, GREY = "#EB6834", "#B9B7B0"
CM_BLUE = LinearSegmentedColormap.from_list(
    "seqblue", ["#FCFCFB", "#CFE0F5", "#7FA8E0", "#2A78D6", "#16406F"])
CM_DIV = LinearSegmentedColormap.from_list(
    "div", ["#16406F", "#7FA8E0", "#FCFCFB", "#F0975C", "#8F3213"])
DIR_COL = {"E": "#2A78D6", "W": "#E578B4", "S": "#3F9C4E", "N": "#E8A21A"}
DAY_SEED = 7

g = BiGrid(4, 4)
H = calibrate_horizon(g)
GATE_IDS = list(g.gates.values())
GATE_LBL = [n.split("_")[0] for n in g.gates]
nE = (g.R + 1) * g.C
nS = (g.C + 1) * g.R


def link_dir(lid):
    if lid <= nE:
        return "E"
    if lid <= 2 * nE:
        return "W"
    if lid <= 2 * nE + nS:
        return "S"
    return "N"


def matrix(inst, t0):
    M = np.full((8, 8), np.nan)
    for a, o in enumerate(GATE_IDS):
        _, arr = inst.earliest_arrival(o, t0=t0)
        for b, d in enumerate(GATE_IDS):
            if d != o:
                M[a, b] = arr[d] - t0
    return M


def xy(node):
    i, j = node
    return float(j), float(g.R - i)


def draw_network(ax, title, ids=False, by_direction=False, title_size=11.5):
    ax.set_facecolor(SURF)
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, g.C + 1.15)
    ax.set_ylim(-1.15, g.R + 1.15)
    ax.axis("off")
    ax.set_title(title, fontsize=title_size, color=INK, pad=10)
    for i in range(g.R + 1):
        for j in range(g.C + 1):
            ax.add_patch(Circle(xy((i, j)), 0.045, color="#C9C8C2", zorder=3))
    ctr = np.array([g.C / 2, g.R / 2])
    for name in g.gates:
        x, y = xy(g.gate_pos[name])
        v = np.array([x, y]) - ctr
        v = v / (np.linalg.norm(v) + 1e-9)
        gx, gy = x + 0.62 * v[0], y + 0.62 * v[1]
        ax.plot([x, gx], [y, gy], ls=":", lw=1.0, color="#8A8880", zorder=2)
        ax.add_patch(Circle((gx, gy), 0.23, facecolor="#F5C142",
                            edgecolor=INK, lw=1.2, zorder=4))
        ax.text(gx, gy, name.split("_")[0], ha="center", va="center",
                fontsize=9.5, fontweight="bold", color=INK, zorder=5)
    patches = {}
    for lid, (a, b) in g.ends.items():
        (x1, y1), (x2, y2) = xy(a), xy(b)
        u = np.array([x2 - x1, y2 - y1])
        u = u / np.linalg.norm(u)
        p = np.array([-u[1], u[0]])
        s = np.array([x1, y1]) + 0.16 * u + 0.058 * p
        e = np.array([x2, y2]) - 0.16 * u + 0.058 * p
        ax.add_patch(FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=11,
                                     lw=4.0, color="#DEDCD6", zorder=1.8,
                                     shrinkA=0, shrinkB=0))
        col = DIR_COL[link_dir(lid)] if by_direction else GREY
        fa = FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=9.5,
                             lw=2.8, color=col, zorder=2, shrinkA=0, shrinkB=0)
        ax.add_patch(fa)
        patches[lid] = fa
        if ids:
            m = (s + e) / 2 + 0.115 * p
            ax.text(m[0], m[1], str(lid), ha="center", va="center",
                    fontsize=5.4, color=INK2, zorder=3)
    return patches


def heat_axes(ax):
    ax.set_xticks(range(8), GATE_LBL, fontsize=10)
    ax.set_yticks(range(8), GATE_LBL, fontsize=10)
    ax.tick_params(colors=INK2, length=0)
    for spn in ax.spines.values():
        spn.set_visible(False)
    ax.set_xlabel("TO gate", fontsize=11, color=INK)
    ax.set_ylabel("FROM gate", fontsize=11, color=INK)


# ------------------------------------------------------------------- compute
zero = np.zeros(g.n_links)
mod0 = ModInstance(g, zero, [], horizon=H)
T0S = list(range(0, PERIOD))
MATS = {t0: matrix(mod0, t0) for t0 in T0S}
assert np.allclose(MATS[0], matrix(mod0, PERIOD), equal_nan=True), "period"
mx = max(np.nanmax(M) for M in MATS.values())
rng_g12 = (min(M[0, 1] for M in MATS.values()), max(M[0, 1] for M in MATS.values()))
rng_g73 = (min(M[6, 2] for M in MATS.values()), max(M[6, 2] for M in MATS.values()))
print(f"mod-{PERIOD}: H={H}; trips max {mx:.0f}; G1->G2 {rng_g12[0]:.0f}..{rng_g12[1]:.0f}; "
      f"G7->G3 {rng_g73[0]:.0f}..{rng_g73[1]:.0f}; t0=0: G1G2={MATS[0][0,1]:.0f} "
      f"G1G5={MATS[0][0,4]:.0f} G7G3={MATS[0][6,2]:.0f}")

# ------------------------------------------------- figA_network_mod (slide 4)
fig = plt.figure(figsize=(15.6, 6.8), dpi=110)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.14], left=0.015, right=0.97,
                      top=0.84, bottom=0.07, wspace=0.10)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
draw_network(axL, "fixed bidirectional 4×4 — 80 directed links, ids 1–80\n"
                  "E 1–20 (blue) · W 21–40 (pink) · S 41–60 (green) · "
                  "N 61–80 (amber) · no U-turns · 8 gates",
             ids=True, by_direction=True, title_size=10.5)
normR = Normalize(0, 70)
imR = axR.imshow(np.ma.masked_invalid(MATS[0]), cmap=CM_BLUE, norm=normR)
heat_axes(axR)
axR.set_title("earliest arrival departing t₀ = 0, δ = 0 — mod-24 cost\n"
              "(exact search; all 56 ordered ODs; PERIODIC in t₀, period 24)",
              fontsize=10.5, color=INK, pad=8)
for a in range(8):
    for b in range(8):
        if a != b:
            v = MATS[0][a, b]
            axR.text(b, a, f"{v:.0f}", ha="center", va="center", fontsize=8,
                     color="white" if normR(v) > 0.55 else INK)
cb = fig.colorbar(imR, ax=axR, fraction=0.042, pad=0.02)
cb.set_label("time steps", fontsize=9, color=INK2)
cb.ax.tick_params(labelsize=8, colors=INK2)
fig.suptitle("Network & instances — cost law "
             "c(i,t) = (base(i)+t) mod 24 + 1 + δᵢ", fontsize=13,
             color=INK, y=0.97)
fig.savefig(f"{R}/figA_network_mod.png", facecolor=SURF)
plt.close(fig)
print(f"wrote {R}/figA_network_mod.png")

# ----------------------------------------------- figA_td_travel_mod (slide 5)
fig = plt.figure(figsize=(15.6, 6.9), dpi=84)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.16], left=0.015, right=0.965,
                      top=0.775, bottom=0.075, wspace=0.13)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
norm_c = Normalize(1, PERIOD)
pat = draw_network(
    axL, "LEFT — how slow is each road RIGHT NOW?\n"
         "colour = time to drive one road segment if you enter it at t₀\n"
         "(light = fast, dark = jammed; the jam wave sweeps every road)",
    title_size=11.5)
sm = plt.cm.ScalarMappable(norm=norm_c, cmap=CM_BLUE)
cbL = fig.colorbar(sm, ax=axL, fraction=0.042, pad=0.01)
cbL.set_label("steps to drive one segment", fontsize=10, color=INK2)
cbL.ax.tick_params(labelsize=9, colors=INK2)
norm_d = Normalize(0, 80)
imR = axR.imshow(np.zeros((8, 8)), cmap=CM_BLUE, norm=norm_d)
heat_axes(axR)
axR.set_title("RIGHT — fastest possible trip between gates,\n"
              "if you DEPART at this moment t₀ (numbers = total steps)",
              fontsize=11.5, color=INK, pad=10)
cbR = fig.colorbar(imR, ax=axR, fraction=0.042, pad=0.02)
cbR.set_label("fastest trip (steps)", fontsize=10, color=INK2)
cbR.ax.tick_params(labelsize=9, colors=INK2)
txt = [[axR.text(b, a, "", ha="center", va="center", fontsize=9.5)
        for b in range(8)] for a in range(8)]
sup = fig.suptitle("", fontsize=15, color=INK, y=0.975)
foot = fig.text(0.5, 0.895,
                f"one full congestion cycle = {PERIOD} steps · same trip, "
                f"different clock: G1→G2 swings {rng_g12[0]:.0f} → "
                f"{rng_g12[1]:.0f} steps, G7→G3 swings {rng_g73[0]:.0f} → "
                f"{rng_g73[1]:.0f} · then it all repeats",
                ha="center", fontsize=11, color=INK2)
imgs = []
for t0 in T0S:
    cols = CM_BLUE(norm_c(np.array([mod0.cost(l, t0)
                                    for l in range(1, g.n_links + 1)])))
    for lid, fa in pat.items():
        fa.set_color(cols[lid - 1])
    M = MATS[t0]
    imR.set_data(np.ma.masked_invalid(M))
    for a in range(8):
        for b in range(8):
            if a != b:
                txt[a][b].set_text(f"{M[a, b]:.0f}")
                txt[a][b].set_color(
                    "white" if norm_d(min(M[a, b], 80)) > 0.55 else INK)
    sup.set_text(f"The network is time-dependent — clock:  t₀ = {t0:>2d} / "
                 f"{PERIOD - 1}")
    fig.canvas.draw()
    imgs.append(Image.fromarray(
        np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()))
plt.close(fig)
out = f"{R}/figA_td_travel_mod.gif"
imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=280,
             loop=0, optimize=True)
print(f"wrote {out}  ({os.path.getsize(out)/1e6:.1f} MB, {len(imgs)} frames)")

# ----------------------------------------------- figA_delta_day_mod (slide 6)
rng = np.random.default_rng(DAY_SEED)
delta = rng.integers(0, 2, g.n_links)
modd = ModInstance(g, delta, [], horizon=H)
INC = matrix(modd, 0) - MATS[0]
k = int(delta.sum())
n_neg = int(np.nansum(INC < 0))
print(f"delta-day: increments {np.nanmin(INC):+.0f}..{np.nanmax(INC):+.0f}; "
      f"{n_neg}/56 ODs FASTER on the congested day")
fig = plt.figure(figsize=(15.6, 6.2), dpi=100)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18], left=0.015, right=0.97,
                      top=0.80, bottom=0.07, wspace=0.12)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
pat = draw_network(axL, f"one sampled operating day (farm sampler, seed "
                        f"{DAY_SEED}):  δᵢ = 1 on {k}/80 directed links\n"
                        "orange = congested (+1/traversal) · grey = clear · "
                        "directions can differ", title_size=10.5)
for lid, fa in pat.items():
    if delta[lid - 1]:
        fa.set_color(ORANGE)
        fa.set_linewidth(3.4)
    else:
        fa.set_color(GREY)
        fa.set_linewidth(1.6)
lo = min(-1, int(np.floor(np.nanmin(INC))))
hi = max(1, int(np.ceil(np.nanmax(INC))))
normI = TwoSlopeNorm(vcenter=0, vmin=lo, vmax=hi)
imI = axR.imshow(np.ma.masked_invalid(INC), cmap=CM_DIV, norm=normI)
heat_axes(axR)
axR.set_title("CHANGE in travel time vs the δ = 0 day, departing t₀ = 0\n"
              "(orange = slower, blue = FASTER — the wrap can turn delay "
              "into a shortcut)", fontsize=10.5, color=INK, pad=8)
for a in range(8):
    for b in range(8):
        if a != b:
            v = INC[a, b]
            axR.text(b, a, f"{v:+.0f}", ha="center", va="center", fontsize=8,
                     color="white" if (normI(v) > 0.82 or normI(v) < 0.18)
                     else INK)
cb = fig.colorbar(imI, ax=axR, fraction=0.042, pad=0.02)
cb.set_label("Δ steps vs δ = 0", fontsize=9, color=INK2)
cb.ax.tick_params(labelsize=8, colors=INK2)
fig.suptitle("Day-to-day variation: the congestion pattern δ ∈ {0,1}⁸⁰ is an "
             "instance property, not a vehicle property", fontsize=13,
             color=INK, y=0.95)
fig.savefig(f"{R}/figA_delta_day_mod.png", facecolor=SURF)
plt.close(fig)
print(f"wrote {R}/figA_delta_day_mod.png  (day seed {DAY_SEED}: {k}/80 "
      f"congested)")
