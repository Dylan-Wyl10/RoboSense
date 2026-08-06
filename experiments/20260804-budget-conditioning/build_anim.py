"""Deck figures for the mod-96 link cost (YIL-125 round 3, 2026-08-05).

User decision: adopt the sawtooth modulo cost
    c(i,t) = ((base(i)+t) mod 96)//4 + 1 + delta_i        (bounded <= 24 + delta)
for the environment; this round regenerates ONLY the deck pages/figures that
depend on the cost law. Labels / model / H are still the pre-mod benchmark
until the re-run (the Step-0 slide carries that transition note).

The wrap breaks FIFO, so every matrix here is computed with an EXACT search
over time-expanded (link, entry-time) states — not the single-label
TD-Dijkstra (which is wrong on 18.1% of cells under this cost, see
build_anim_periodic.py, YIL-125 r2).

Outputs (results/):
  figA_network_mod.png   slide 4: link-id network (colour = direction) +
                         8x8 earliest-arrival heatmap at t0=0, delta=0, mod-96
  figA_td_travel_mod.gif slide 5: t0 sweeps one FULL period 0..95 step 1,
                         seamless loop; left = links coloured by entry cost
                         (scale 1..24), right = exact 8x8 duration matrix
  figA_delta_day_mod.png slide 6: sampled day's delta on the network + extra
                         steps vs the delta=0 day (t0=0, exact)
Pre-mod figA files from r1 stay on disk (history); the deck no longer uses
them. Prints the deck-text numbers (per-OD ranges, delta increments, the
would-be re-calibrated H) at the end.
"""

import heapq
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Circle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/Research/Route_TSC_CART"))
from neural_route.bigrid import BiGrid, BiInstance  # noqa: E402

R = f"{HERE}/results"
INK, INK2, SURF = "#0B0B0B", "#52514E", "#FCFCFB"
ORANGE, GREY = "#EB6834", "#B9B7B0"
CM_BLUE = LinearSegmentedColormap.from_list(
    "seqblue", ["#FCFCFB", "#CFE0F5", "#7FA8E0", "#2A78D6", "#16406F"])
CM_ORAN = LinearSegmentedColormap.from_list(
    "seqoran", ["#FCFCFB", "#FAD9C9", "#F0975C", "#EB6834", "#8F3213"])
DIR_COL = {"E": "#2A78D6", "W": "#E578B4", "S": "#3F9C4E", "N": "#E8A21A"}

P = 96                          # congestion period (user decision: mod)
DAY_SEED = 7                    # same sampled day as the r1 delta figure
DPI = 80

g = BiGrid(4, 4)
GATE_IDS = list(g.gates.values())
GATE_LBL = [n.split("_")[0] for n in g.gates]
LINK_GATES = {lid: [gid for gid, ins in g.gate_in.items() if lid in ins]
              for lid in g.ends}
nE = (g.R + 1) * g.C            # id ranges: E 1..20, W 21..40, S 41..60, N 61..80
nS = (g.C + 1) * g.R


def link_dir(lid):
    if lid <= nE:
        return "E"
    if lid <= 2 * nE:
        return "W"
    if lid <= 2 * nE + nS:
        return "S"
    return "N"


class ModInstance(BiInstance):
    """The adopted cost: first term wraps mod P (sawtooth, bounded)."""

    def cost(self, i, t):
        if i > self.grid.n_links:
            return 0
        return ((self.grid.base[i] + t) % P) // 4 + 1 + int(self.delta[i - 1])


def exact_arrivals(inst, o_gate, t0, cut=1400):
    """Earliest arrival at every gate — exact for non-FIFO costs (Dijkstra
    over time-expanded (link, entry-time) states, no waiting)."""
    seen, arrive = set(), {}
    pq = [(t0, lid) for lid in inst.grid.gate_out[o_gate]]
    heapq.heapify(pq)
    while pq:
        t, lid = heapq.heappop(pq)
        if len(arrive) == 8 and t >= max(arrive.values()):
            break
        if (lid, t) in seen or t > cut:
            continue
        seen.add((lid, t))
        s = t + inst.cost(lid, t)
        for gid in LINK_GATES[lid]:
            if gid not in arrive or s < arrive[gid]:
                arrive[gid] = s
        for nxt in inst.grid.con[lid]:
            if (nxt, s) not in seen:
                heapq.heappush(pq, (s, nxt))
    return arrive


def matrix(inst, t0):
    M = np.full((8, 8), np.nan)
    for a, o in enumerate(GATE_IDS):
        arr = exact_arrivals(inst, o, t0)
        for b, d in enumerate(GATE_IDS):
            if d != o:
                M[a, b] = arr.get(d, np.inf) - t0
    return M


def xy(node):
    i, j = node
    return float(j), float(g.R - i)


def draw_network(ax, title, ids=False, by_direction=False):
    ax.set_facecolor(SURF)
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, g.C + 1.15)
    ax.set_ylim(-1.15, g.R + 1.15)
    ax.axis("off")
    ax.set_title(title, fontsize=10.5, color=INK, pad=8)
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
        ax.add_patch(Circle((gx, gy), 0.21, facecolor="#F5C142",
                            edgecolor=INK, lw=1.2, zorder=4))
        ax.text(gx, gy, name.split("_")[0], ha="center", va="center",
                fontsize=8.5, fontweight="bold", color=INK, zorder=5)
    patches = {}
    for lid, (a, b) in g.ends.items():
        (x1, y1), (x2, y2) = xy(a), xy(b)
        u = np.array([x2 - x1, y2 - y1])
        u = u / np.linalg.norm(u)
        p = np.array([-u[1], u[0]])
        s = np.array([x1, y1]) + 0.16 * u + 0.058 * p
        e = np.array([x2, y2]) - 0.16 * u + 0.058 * p
        ax.add_patch(FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=10.5,
                                     lw=3.6, color="#DEDCD6", zorder=1.8,
                                     shrinkA=0, shrinkB=0))
        col = DIR_COL[link_dir(lid)] if by_direction else GREY
        fa = FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=9, lw=2.4,
                             color=col, zorder=2, shrinkA=0, shrinkB=0)
        ax.add_patch(fa)
        patches[lid] = fa
        if ids:
            m = (s + e) / 2 + 0.115 * p
            ax.text(m[0], m[1], str(lid), ha="center", va="center",
                    fontsize=5.4, color=INK2, zorder=3)
    return patches


def heat(ax, M, vmax, title, cmap=CM_BLUE, fmt="{:.0f}"):
    norm = Normalize(0, vmax)
    im = ax.imshow(np.ma.masked_invalid(M), cmap=cmap, norm=norm)
    ax.set_xticks(range(8), GATE_LBL, fontsize=9)
    ax.set_yticks(range(8), GATE_LBL, fontsize=9)
    ax.tick_params(colors=INK2, length=0)
    for spn in ax.spines.values():
        spn.set_visible(False)
    ax.set_xlabel("destination gate", fontsize=10, color=INK)
    ax.set_ylabel("origin gate", fontsize=10, color=INK)
    ax.set_title(title, fontsize=10.5, color=INK, pad=8)
    txt = [[ax.text(b, a, "" if a == b else fmt.format(M[a, b]),
                    ha="center", va="center", fontsize=8,
                    color="white" if (a != b and norm(min(M[a, b], vmax)) > 0.55)
                    else INK)
            for b in range(8)] for a in range(8)]
    return im, norm, txt


# ------------------------------------------------------------------- compute
zero = np.zeros(g.n_links)
mod0 = ModInstance(g, zero, [], horizon=None)
T0S = list(range(0, P))
MATS = {t0: matrix(mod0, t0) for t0 in T0S}
assert np.allclose(MATS[0], matrix(mod0, P), equal_nan=True), "periodicity"
mx = max(np.nanmax(M) for M in MATS.values())
rng_g12 = (min(M[0, 1] for M in MATS.values()), max(M[0, 1] for M in MATS.values()))
rng_g73 = (min(M[6, 2] for M in MATS.values()), max(M[6, 2] for M in MATS.values()))
print(f"mod-96 durations: global max {mx:.0f}; G1->G2 {rng_g12[0]:.0f}..{rng_g12[1]:.0f}; "
      f"G7->G3 {rng_g73[0]:.0f}..{rng_g73[1]:.0f}; t0=0: G1->G2 {MATS[0][0,1]:.0f}, "
      f"G1->G5 {MATS[0][0,4]:.0f}, G7->G3 {MATS[0][6,2]:.0f}")

# would-be H under mod (worst congestion delta=1, latest depart t0=5, slack 1.6)
mod1 = ModInstance(g, np.ones(g.n_links), [], horizon=None)
worst = 0
for o in GATE_IDS:
    arr = exact_arrivals(mod1, o, 5)
    worst = max(worst, max(arr[d] for d in GATE_IDS if d != o))
H_mod = int(np.ceil(worst * 1.6))
print(f"would-be H under mod-96 (delta=1, t0=5, slack 1.6): {H_mod}  (was 338)")

# ------------------------------------------------- figA_network_mod (slide 4)
fig = plt.figure(figsize=(15.6, 6.8), dpi=110)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.14], left=0.015, right=0.97,
                      top=0.84, bottom=0.07, wspace=0.10)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
draw_network(axL, "fixed bidirectional 4×4 — 80 directed links, ids 1–80\n"
                  "E 1–20 (blue) · W 21–40 (pink) · S 41–60 (green) · "
                  "N 61–80 (amber) · no U-turns · 8 gates",
             ids=True, by_direction=True)
imR, normR, _ = heat(axR, MATS[0], 70,
                     "earliest arrival departing t₀ = 0, δ = 0 — mod-96 cost\n"
                     "(exact search; all 56 ordered ODs; PERIODIC in t₀, "
                     "period 96)")
cb = fig.colorbar(imR, ax=axR, fraction=0.042, pad=0.02)
cb.set_label("time steps", fontsize=9, color=INK2)
cb.ax.tick_params(labelsize=8, colors=INK2)
fig.suptitle("Network & instances — cost law "
             "c(i,t) = ((base(i)+t) mod 96)//4 + 1 + δᵢ", fontsize=13,
             color=INK, y=0.97)
fig.savefig(f"{R}/figA_network_mod.png", facecolor=SURF)
plt.close(fig)
print(f"wrote {R}/figA_network_mod.png")

# ----------------------------------------------- figA_td_travel_mod (slide 5)
fig = plt.figure(figsize=(15.6, 6.5), dpi=DPI)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18], left=0.015, right=0.97,
                      top=0.82, bottom=0.06, wspace=0.12)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
norm_c = Normalize(1, 24)
pat = draw_network(axL, "cost of ENTERING each directed link at t = t₀\n"
                        "c(i,t) = ((base(i)+t) mod 96)//4 + 1 + δᵢ   "
                        "(δ = 0 day; bounded ≤ 24)")
sm = plt.cm.ScalarMappable(norm=norm_c, cmap=CM_BLUE)
cbL = fig.colorbar(sm, ax=axL, fraction=0.042, pad=0.01)
cbL.set_label("entry cost (time steps)", fontsize=9, color=INK2)
cbL.ax.tick_params(labelsize=8, colors=INK2)
imR, norm_d, txt = heat(axR, MATS[0], 100, "")
cbR = fig.colorbar(imR, ax=axR, fraction=0.042, pad=0.02)
cbR.set_label("travel time (steps)", fontsize=9, color=INK2)
cbR.ax.tick_params(labelsize=8, colors=INK2)
titleR = axR.set_title("", fontsize=10.5, color=INK, pad=8)
sup = fig.suptitle("", fontsize=13, color=INK, y=0.965)
fig.text(0.5, 0.905,
         f"bounded: entry cost ≤ 24, every trip ≤ {mx:.0f} steps at every t₀ "
         f"· G1→G2 cycles {rng_g12[0]:.0f}…{rng_g12[1]:.0f} · G7→G3 cycles "
         f"{rng_g73[0]:.0f}…{rng_g73[1]:.0f} · loop repeats seamlessly",
         ha="center", fontsize=9.5, color=INK2)
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
                    "white" if norm_d(min(M[a, b], 100)) > 0.55 else INK)
    titleR.set_text(f"gate-to-gate travel time DEPARTING at t₀ = {t0}\n"
                    "(exact time-expanded search — the wrap breaks FIFO)")
    sup.set_text("The network is time-dependent AND periodic — departure "
                 f"t₀ = {t0:>2d} of one full period 0…95")
    fig.canvas.draw()
    imgs.append(Image.fromarray(
        np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()))
plt.close(fig)
out = f"{R}/figA_td_travel_mod.gif"
imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=110,
             loop=0, optimize=True)
print(f"wrote {out}  ({os.path.getsize(out)/1e6:.1f} MB, {len(imgs)} frames)")

# ----------------------------------------------- figA_delta_day_mod (slide 6)
rng = np.random.default_rng(DAY_SEED)
delta = rng.integers(0, 2, g.n_links)
modd = ModInstance(g, delta, [], horizon=None)
INC = matrix(modd, 0) - MATS[0]
k = int(delta.sum())
# NOTE: under the sawtooth, INC can be NEGATIVE — congestion delays early
# links, which can push a later link's entry past its wrap into the cheap
# zone, so a congested day can make some ODs FASTER. Report, don't hide.
n_neg = int(np.nansum(INC < 0))
print(f"delta-day increments: {np.nanmin(INC):+.0f}..{np.nanmax(INC):+.0f}; "
      f"{n_neg}/56 ODs FASTER on the congested day (sawtooth phase shift)")
fig = plt.figure(figsize=(15.6, 6.2), dpi=100)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18], left=0.015, right=0.97,
                      top=0.80, bottom=0.07, wspace=0.12)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
pat = draw_network(axL, f"one sampled operating day (farm sampler, seed "
                        f"{DAY_SEED}):  δᵢ = 1 on {k}/80 directed links\n"
                        "orange = congested (+1/traversal) · grey = clear · "
                        "directions can differ")
for lid, fa in pat.items():
    if delta[lid - 1]:
        fa.set_color(ORANGE)
        fa.set_linewidth(3.4)
    else:
        fa.set_color(GREY)
        fa.set_linewidth(1.6)
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
CM_DIV = LinearSegmentedColormap.from_list(
    "div", ["#16406F", "#7FA8E0", "#FCFCFB", "#F0975C", "#8F3213"])
lo = min(-1, int(np.floor(np.nanmin(INC))))
hi = max(1, int(np.ceil(np.nanmax(INC))))
normI = TwoSlopeNorm(vcenter=0, vmin=lo, vmax=hi)
imI = axR.imshow(np.ma.masked_invalid(INC), cmap=CM_DIV, norm=normI)
axR.set_xticks(range(8), GATE_LBL, fontsize=9)
axR.set_yticks(range(8), GATE_LBL, fontsize=9)
axR.tick_params(colors=INK2, length=0)
for spn in axR.spines.values():
    spn.set_visible(False)
axR.set_xlabel("destination gate", fontsize=10, color=INK)
axR.set_ylabel("origin gate", fontsize=10, color=INK)
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
      f"congested, increments {np.nanmin(INC):+.0f}..{np.nanmax(INC):+.0f}, "
      f"G1→G2 {INC[0, 1]:+.0f})")
