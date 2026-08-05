"""Time-dependence figures for the deck (YIL-125 round 1, 2026-08-05).

User questions on slide 4's static figure: (i) the 8x8 "earliest arrival" matrix
is a single (t0=0, delta=0) slice of a time-VARYING quantity — show that; (ii)
delta_i was not visible anywhere — show what a day's congestion pattern looks
like on the network.

Outputs (results/):
  figA_td_travel.gif   two-panel animation, delta=0 day, departure t0 sweeps
                       0..160: left = network with every directed link coloured
                       by its entry cost c(i,t0); right = 8x8 gate-to-gate
                       travel time (TD-Dijkstra earliest arrival - t0) departing
                       at t0.  '*' marks trips that would arrive after H.
                       GIF animates in PowerPoint slideshow mode; PDF export
                       shows the first frame (t0=0 == slide 4's heatmap).
  figA_delta_day.png   left = one sampled day's delta (Bernoulli(1/2) per
                       DIRECTED link, the farm's sampler) drawn on the network;
                       right = extra travel time that day adds vs delta=0,
                       departing t0=0.

Colour: sequential single-hue ramps only (magnitude); deck blue #2A78D6 for
cost/duration, deck orange #EB6834 for the congestion-increment panel. The
horizon flag is a symbol (*) + caption, never colour alone.
"""

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
from neural_route.bigrid import BiGrid, BiInstance, calibrate_horizon  # noqa: E402

R = f"{HERE}/results"
INK, INK2, SURF = "#0B0B0B", "#52514E", "#FCFCFB"
BLUE, ORANGE, GREY = "#2A78D6", "#EB6834", "#B9B7B0"
CM_BLUE = LinearSegmentedColormap.from_list(
    "seqblue", ["#FCFCFB", "#CFE0F5", "#7FA8E0", "#2A78D6", "#16406F"])
CM_ORAN = LinearSegmentedColormap.from_list(
    "seqoran", ["#FCFCFB", "#FAD9C9", "#F0975C", "#EB6834", "#8F3213"])

T0_MAX, T0_STEP = 160, 5
DAY_SEED = 7                     # same Bernoulli(1/2) sampler as the farm

g = BiGrid(4, 4)
H = calibrate_horizon(g)
GATE_IDS = list(g.gates.values())
GATE_LBL = [n.split("_")[0] for n in g.gates]          # G1..G8


def xy(node):
    """intersection (i,j) -> plot coords (x right, y up)."""
    i, j = node
    return float(j), float(g.R - i)


def duration_matrix(inst, t0):
    """8x8 travel time o->d departing at t0 (nan diagonal)."""
    M = np.full((8, 8), np.nan)
    for a, o in enumerate(GATE_IDS):
        _, arr = inst.earliest_arrival(o, t0=t0)
        for b, d in enumerate(GATE_IDS):
            if d != o:
                M[a, b] = arr[d] - t0
    return M


def draw_network(ax, title, title_color=INK):
    """Static scaffolding: intersections, gates, one FancyArrowPatch per
    directed link (colour set by the caller). Returns {link_id: patch}."""
    ax.set_facecolor(SURF)
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, g.C + 1.15)
    ax.set_ylim(-1.15, g.R + 1.15)
    ax.axis("off")
    ax.set_title(title, fontsize=10.5, color=title_color, pad=8)
    for i in range(g.R + 1):
        for j in range(g.C + 1):
            x, y = xy((i, j))
            ax.add_patch(Circle((x, y), 0.045, color="#C9C8C2", zorder=3))
    ctr = np.array([g.C / 2, g.R / 2])
    for name, gid in g.gates.items():
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
        p = np.array([-u[1], u[0]])          # left of travel direction
        s = np.array([x1, y1]) + 0.16 * u + 0.058 * p
        e = np.array([x2, y2]) - 0.16 * u + 0.058 * p
        # grey underlay keeps near-white (cheap) links visible
        ax.add_patch(FancyArrowPatch(s, e, arrowstyle="-|>",
                                     mutation_scale=10.5, lw=3.6,
                                     color="#DEDCD6", zorder=1.8,
                                     shrinkA=0, shrinkB=0))
        fa = FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=9,
                             lw=2.4, color=GREY, zorder=2,
                             shrinkA=0, shrinkB=0)
        ax.add_patch(fa)
        patches[lid] = fa
    return patches


# ================================================================ animation
inst0 = BiInstance(g, np.zeros(g.n_links), tasks=[], horizon=H)
T0S = list(range(0, T0_MAX + 1, T0_STEP))
MATS = {t0: duration_matrix(inst0, t0) for t0 in T0S}
COSTS = {t0: np.array([inst0.cost(l, t0) for l in range(1, g.n_links + 1)])
         for t0 in T0S}
cmax = max(c.max() for c in COSTS.values())

fig = plt.figure(figsize=(15.6, 6.5), dpi=90)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18],
                      left=0.015, right=0.97, top=0.82, bottom=0.06,
                      wspace=0.12)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

norm_c = Normalize(1, cmax)
link_patches = draw_network(
    axL, "cost of ENTERING each directed link at t = t₀ (the departure "
         "instant)\nc(i,t) = (base(i)+t)//4 + 1 + δᵢ   (δ = 0 day; "
         "colour = cost, direction = arrowhead)")
sm = plt.cm.ScalarMappable(norm=norm_c, cmap=CM_BLUE)
cbL = fig.colorbar(sm, ax=axL, fraction=0.042, pad=0.01)
cbL.set_label("entry cost (time steps)", fontsize=9, color=INK2)
cbL.ax.tick_params(labelsize=8, colors=INK2)

norm_d = Normalize(0, 500)
im = axR.imshow(np.zeros((8, 8)), cmap=CM_BLUE, norm=norm_d)
axR.set_facecolor(SURF)
axR.set_xticks(range(8), GATE_LBL, fontsize=9)
axR.set_yticks(range(8), GATE_LBL, fontsize=9)
axR.tick_params(colors=INK2, length=0)
for sp in axR.spines.values():
    sp.set_visible(False)
axR.set_xlabel("destination gate", fontsize=10, color=INK)
axR.set_ylabel("origin gate", fontsize=10, color=INK)
cbR = fig.colorbar(im, ax=axR, fraction=0.042, pad=0.02, extend="max")
cbR.set_label("travel time (steps)", fontsize=9, color=INK2)
cbR.ax.tick_params(labelsize=8, colors=INK2)
cell_txt = [[axR.text(b, a, "", ha="center", va="center", fontsize=8)
             for b in range(8)] for a in range(8)]
titleR = axR.set_title("", fontsize=10.5, color=INK, pad=8)
sup = fig.suptitle("", fontsize=13, color=INK, y=0.965)
foot = fig.text(0.5, 0.955, "", ha="center", fontsize=9.5, color=INK2)
foot.set_y(0.905)


def update(t0):
    cols = CM_BLUE(norm_c(COSTS[t0]))
    for lid, fa in link_patches.items():
        fa.set_color(cols[lid - 1])
    M = MATS[t0]
    im.set_data(np.ma.masked_invalid(M))
    for a in range(8):
        for b in range(8):
            if a == b:
                continue
            v = M[a, b]
            bust = t0 + v > H
            cell_txt[a][b].set_text(f"{v:.0f}" + ("*" if bust else ""))
            cell_txt[a][b].set_color(
                "white" if norm_d(min(v, 500)) > 0.55 else INK)
    titleR.set_text(f"gate-to-gate travel time DEPARTING at t₀ = {t0}\n"
                    "(TD-Dijkstra earliest arrival − t₀; "
                    "* = would arrive after H)")
    sup.set_text(f"The network is time-dependent — departure time "
                 f"t₀ = {t0:>3d}   (horizon H = {H})")
    foot.set_text("same OD, later start ⇒ longer trip:  "
                  f"G1→G2  {MATS[0][0, 1]:.0f} → "
                  f"{MATS[T0_MAX][0, 1]:.0f}   ·   "
                  f"G7→G3  {MATS[0][6, 2]:.0f} → "
                  f"{MATS[T0_MAX][6, 2]:.0f}   (t₀: 0 → {T0_MAX})")
    return []


imgs = []
for t0 in T0S:
    update(t0)
    fig.canvas.draw()
    # buffer_rgba is a live view of the canvas — copy, or every frame ends
    # up pointing at the last drawn state
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    imgs.append(Image.fromarray(buf))
plt.close(fig)
# explicit per-frame durations: hold the first and last frames
durs = [1400] + [260] * (len(imgs) - 2) + [2000]
gif = f"{R}/figA_td_travel.gif"
imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=durs,
             loop=0, optimize=True)
print(f"wrote {gif}  ({os.path.getsize(gif)/1e6:.1f} MB, "
      f"{len(imgs)} frames, t0 0..{T0_MAX} step {T0_STEP})")

# ============================================================= delta-day png
rng = np.random.default_rng(DAY_SEED)
delta = rng.integers(0, 2, g.n_links)
instd = BiInstance(g, delta, tasks=[], horizon=H)
Mday, M0 = duration_matrix(instd, 0), MATS[0]
INC = Mday - M0
k = int(delta.sum())

fig = plt.figure(figsize=(15.6, 6.2), dpi=100)
fig.patch.set_facecolor(SURF)
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18],
                      left=0.015, right=0.97, top=0.80, bottom=0.07,
                      wspace=0.12)
axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

pat = draw_network(
    axL, f"one sampled operating day (farm sampler, seed {DAY_SEED}):  "
         f"δᵢ = 1 on {k}/80 directed links\n"
         "orange = congested (+1/traversal) · grey = clear · "
         "directions can differ")
for lid, fa in pat.items():
    if delta[lid - 1]:
        fa.set_color(ORANGE)
        fa.set_linewidth(3.4)
    else:
        fa.set_color(GREY)
        fa.set_linewidth(1.6)

vmax = max(1, int(np.ceil(np.nanmax(INC))))
normI = Normalize(0, vmax)
imI = axR.imshow(np.ma.masked_invalid(INC), cmap=CM_ORAN, norm=normI)
axR.set_xticks(range(8), GATE_LBL, fontsize=9)
axR.set_yticks(range(8), GATE_LBL, fontsize=9)
axR.tick_params(colors=INK2, length=0)
for sp in axR.spines.values():
    sp.set_visible(False)
axR.set_xlabel("destination gate", fontsize=10, color=INK)
axR.set_ylabel("origin gate", fontsize=10, color=INK)
axR.set_title("EXTRA travel time this day adds vs the δ = 0 day, "
              "departing t₀ = 0\n(same TD-Dijkstra; all vehicles share "
              "the day's δ)", fontsize=10.5, color=INK, pad=8)
cb = fig.colorbar(imI, ax=axR, fraction=0.042, pad=0.02)
cb.set_label("extra steps", fontsize=9, color=INK2)
cb.ax.tick_params(labelsize=8, colors=INK2)
for a in range(8):
    for b in range(8):
        if a != b:
            v = INC[a, b]
            axR.text(b, a, f"+{v:.0f}", ha="center", va="center", fontsize=8,
                     color="white" if normI(v) > 0.55 else INK)
fig.suptitle("Day-to-day variation: the congestion pattern "
             "δ ∈ {0,1}⁸⁰ is an instance property, "
             "not a vehicle property", fontsize=13, color=INK, y=0.95)
png = f"{R}/figA_delta_day.png"
fig.savefig(png, facecolor=SURF)
plt.close(fig)
print(f"wrote {png}  (day seed {DAY_SEED}: {k}/80 congested, "
      f"max increment +{np.nanmax(INC):.0f}, "
      f"G1→G2 +{INC[0, 1]:.0f})")

print("checks:", f"H={H}", f"t0=0 G1G2={M0[0,1]:.0f} G7G3={M0[6,2]:.0f}",
      f"t0=80 G7G3={MATS[80][6,2]:.0f}", f"t0=160 G1G2={MATS[160][0,1]:.0f}")
