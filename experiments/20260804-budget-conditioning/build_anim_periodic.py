"""Periodic link-cost exploration figures (YIL-125 round 2, 2026-08-05).

User request: the current cost c(i,t) = (base(i)+t)//4 + 1 + delta_i grows
without bound in t; add a modulo to the FIRST TERM so link cost stays bounded
for every t0, and re-render the animation with step 1. Figures only, no deck.

Variants (both == current cost at t=0 because base(i) <= 60 < 96):
  MOD  (as asked)   first = ((base(i)+t) %  96) // 4          bounded 0..23
                    sawtooth: NOT FIFO — at the wrap, entering 1 step later
                    can arrive ~22 steps earlier, so the repo's single-label
                    TD-Dijkstra (earliest_arrival / min_finish) is no longer
                    exact. Matrices here are computed with an exact
                    time-expanded search; the TD-vs-exact gap is quantified.
  TRI  (FIFO-safe)  u = (base(i)+t) % 192; first = min(u, 192-u) // 4
                    bounded 0..24, rise 96 / fall 96; c(t+1)-c(t) >= -1 so
                    FIFO holds and ALL existing machinery stays exact.

Outputs (results/): figB_current_step1.gif, figB_mod96_step1.gif,
figB_tri192_step1.gif, figB_cost_profiles.png.  Deck files untouched.
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
from neural_route.bigrid import BiGrid, BiInstance, calibrate_horizon  # noqa: E402

R = f"{HERE}/results"
INK, INK2, SURF = "#0B0B0B", "#52514E", "#FCFCFB"
ORANGE, GREY = "#EB6834", "#B9B7B0"
CM_BLUE = LinearSegmentedColormap.from_list(
    "seqblue", ["#FCFCFB", "#CFE0F5", "#7FA8E0", "#2A78D6", "#16406F"])

P_MOD, P_TRI = 96, 192          # sawtooth period / triangle period (rise 96, fall 96)
DPI = 78
COST_VMAX = 56                  # shared left-panel scale = current cost's max at t=160

g = BiGrid(4, 4)
H = calibrate_horizon(g)
GATE_IDS = list(g.gates.values())
GATE_LBL = [n.split("_")[0] for n in g.gates]
LINK_GATES = {lid: [gid for gid, ins in g.gate_in.items() if lid in ins]
              for lid in g.ends}


class ModInstance(BiInstance):
    """First term wrapped by % P_MOD, exactly as asked (sawtooth)."""

    def cost(self, i, t):
        if i > self.grid.n_links:
            return 0
        return ((self.grid.base[i] + t) % P_MOD) // 4 + 1 + int(self.delta[i - 1])


class TriInstance(BiInstance):
    """Triangle fold, period P_TRI: bounded AND FIFO-preserving."""

    def cost(self, i, t):
        if i > self.grid.n_links:
            return 0
        u = (self.grid.base[i] + t) % P_TRI
        return min(u, P_TRI - u) // 4 + 1 + int(self.delta[i - 1])


def exact_arrivals(inst, o_gate, t0, cut=1400):
    """Earliest arrival at every gate, EXACT for arbitrary (non-FIFO) costs:
    Dijkstra over time-expanded states (link, entry time), no waiting."""
    seen = set()
    arrive = {}
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


def matrix(inst, t0, exact=False):
    M = np.full((8, 8), np.nan)
    for a, o in enumerate(GATE_IDS):
        arr = (exact_arrivals(inst, o, t0) if exact
               else inst.earliest_arrival(o, t0=t0)[1])
        for b, d in enumerate(GATE_IDS):
            if d != o:
                M[a, b] = arr.get(d, np.inf) - t0
    return M


def xy(node):
    i, j = node
    return float(j), float(g.R - i)


def draw_network(ax, title):
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
        fa = FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=9, lw=2.4,
                             color=GREY, zorder=2, shrinkA=0, shrinkB=0)
        ax.add_patch(fa)
        patches[lid] = fa
    return patches


def render_gif(name, inst, t0s, mats, sup_fmt, foot, dur_vmax, star_H=None,
               frame_ms=100):
    fig = plt.figure(figsize=(15.6, 6.5), dpi=DPI)
    fig.patch.set_facecolor(SURF)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.18], left=0.015,
                          right=0.97, top=0.82, bottom=0.06, wspace=0.12)
    axL, axR = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    norm_c = Normalize(1, COST_VMAX)
    pat = draw_network(
        axL, "cost of ENTERING each directed link at t = t₀\n(colour scale "
             f"shared with the current-cost animation, max {COST_VMAX})")
    sm = plt.cm.ScalarMappable(norm=norm_c, cmap=CM_BLUE)
    cbL = fig.colorbar(sm, ax=axL, fraction=0.042, pad=0.01)
    cbL.set_label("entry cost (time steps)", fontsize=9, color=INK2)
    cbL.ax.tick_params(labelsize=8, colors=INK2)
    norm_d = Normalize(0, dur_vmax)
    im = axR.imshow(np.zeros((8, 8)), cmap=CM_BLUE, norm=norm_d)
    axR.set_xticks(range(8), GATE_LBL, fontsize=9)
    axR.set_yticks(range(8), GATE_LBL, fontsize=9)
    axR.tick_params(colors=INK2, length=0)
    for spn in axR.spines.values():
        spn.set_visible(False)
    axR.set_xlabel("destination gate", fontsize=10, color=INK)
    axR.set_ylabel("origin gate", fontsize=10, color=INK)
    cbR = fig.colorbar(im, ax=axR, fraction=0.042, pad=0.02,
                       extend="max" if star_H else "neither")
    cbR.set_label("travel time (steps)", fontsize=9, color=INK2)
    cbR.ax.tick_params(labelsize=8, colors=INK2)
    txt = [[axR.text(b, a, "", ha="center", va="center", fontsize=8)
            for b in range(8)] for a in range(8)]
    titleR = axR.set_title("", fontsize=10.5, color=INK, pad=8)
    sup = fig.suptitle("", fontsize=13, color=INK, y=0.965)
    ft = fig.text(0.5, 0.905, foot, ha="center", fontsize=9.5, color=INK2)
    imgs = []
    for t0 in t0s:
        cols = CM_BLUE(norm_c(np.array([inst.cost(l, t0)
                                        for l in range(1, g.n_links + 1)])))
        for lid, fa in pat.items():
            fa.set_color(cols[lid - 1])
        M = mats[t0]
        im.set_data(np.ma.masked_invalid(M))
        for a in range(8):
            for b in range(8):
                if a == b:
                    continue
                v = M[a, b]
                star = "*" if (star_H and t0 + v > star_H) else ""
                txt[a][b].set_text(f"{v:.0f}{star}")
                txt[a][b].set_color(
                    "white" if norm_d(min(v, dur_vmax)) > 0.55 else INK)
        titleR.set_text(f"gate-to-gate travel time DEPARTING at t₀ = {t0}"
                        + ("\n(* = would arrive after H = 338)" if star_H
                           else "\n(exact time-expanded search)"))
        sup.set_text(sup_fmt.format(t0=t0))
        fig.canvas.draw()
        imgs.append(Image.fromarray(
            np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()))
    plt.close(fig)
    out = f"{R}/{name}"
    durs = [frame_ms] * len(imgs)
    if star_H:                       # non-periodic: hold first & last frame
        durs[0], durs[-1] = 1400, 2000
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durs,
                 loop=0, optimize=True)
    print(f"wrote {out}  ({os.path.getsize(out)/1e6:.1f} MB, "
          f"{len(imgs)} frames @ {frame_ms} ms)")


# ------------------------------------------------------------ compute + checks
zero = np.zeros(g.n_links)
cur, mod, tri = (BiInstance(g, zero, [], horizon=H),
                 ModInstance(g, zero, [], horizon=H),
                 TriInstance(g, zero, [], horizon=H))

T0_CUR = list(range(0, 161))
T0_MOD = list(range(0, P_MOD))
T0_TRI = list(range(0, P_TRI))

print("computing matrices: current (TD-Dijkstra, FIFO exact) ...")
M_CUR = {t0: matrix(cur, t0) for t0 in T0_CUR}
print("triangle (TD-Dijkstra; FIFO holds) ...")
M_TRI = {t0: matrix(tri, t0) for t0 in T0_TRI}
print("sawtooth mod (exact time-expanded search) ...")
M_MOD = {t0: matrix(mod, t0, exact=True) for t0 in T0_MOD}

# checks: dominance + short-trip anchor at t0=0, periodicity, FIFO effects.
# (Full matrix equality at t0=0 CANNOT hold: wrapped costs are pointwise <=
# current, so trips still en route when the wrap arrives get cheaper — only
# trips finishing before base+t reaches 96 (arrival <= 36) are unchanged.)
def le_nan(A, B):
    return bool(np.all((A <= B + 1e-9) | np.isnan(A)))

assert le_nan(M_MOD[0], M_CUR[0]), "mod pointwise <= current"
assert le_nan(M_TRI[0], M_CUR[0]), "tri pointwise <= current"
short = M_CUR[0] <= 36
assert np.allclose(M_MOD[0][short], M_CUR[0][short]), "short-trip anchor (mod)"
assert np.allclose(M_TRI[0][short], M_CUR[0][short]), "short-trip anchor (tri)"
print(f"t0=0 far-OD effect: G7->G3 current {M_CUR[0][6,2]:.0f} -> "
      f"mod {M_MOD[0][6,2]:.0f} / tri {M_TRI[0][6,2]:.0f};  G1->G5 "
      f"{M_CUR[0][0,4]:.0f} -> {M_MOD[0][0,4]:.0f} / {M_TRI[0][0,4]:.0f}")
assert np.allclose(M_MOD[0], matrix(mod, P_MOD, exact=True) , equal_nan=True), \
    "mod periodicity"
assert np.allclose(M_TRI[0], matrix(tri, P_TRI), equal_nan=True), \
    "tri periodicity"
for t0 in (0, 37, 91, 150):
    assert np.allclose(matrix(tri, t0 % P_TRI), matrix(tri, t0 % P_TRI, exact=True),
                       equal_nan=True), "tri TD==exact (FIFO)"
bad, worst = 0, 0
for t0 in T0_MOD:
    td = matrix(mod, t0)                     # single-label TD-Dijkstra (invalid)
    d = td - M_MOD[t0]
    bad += int(np.nansum(d > 0))
    worst = max(worst, np.nanmax(d))
n_cells = len(T0_MOD) * 56
print(f"CHECKS OK. sawtooth: single-label TD-Dijkstra wrong on {bad}/{n_cells} "
      f"cells ({100*bad/n_cells:.1f}%), overestimates by up to {worst:.0f} steps")
mx_mod = max(np.nanmax(M) for M in M_MOD.values())
mx_tri = max(np.nanmax(M) for M in M_TRI.values())
print(f"duration ranges: mod max {mx_mod:.0f}, tri max {mx_tri:.0f}, "
      f"current max {max(np.nanmax(M) for M in M_CUR.values()):.0f}")
tw = P_MOD - 1      # wrap for the base-1 link (id 1): (1+95) % 96 == 0
print(f"wrap example (link base=1): enter t={tw-1}: c={mod.cost(1, tw-1)}, "
      f"exit {tw-1+mod.cost(1, tw-1)};  enter t={tw}: c={mod.cost(1, tw)}, "
      f"exit {tw+mod.cost(1, tw)}")

# ------------------------------------------------------------------- render
vmax_mod = int(np.ceil(mx_mod / 50) * 50)
vmax_tri = int(np.ceil(mx_tri / 50) * 50)
render_gif("figB_current_step1.gif", cur, T0_CUR, M_CUR,
           "CURRENT cost (unbounded) — departure t₀ = {t0:>3d}   (H = 338)",
           "c(i,t) = (base(i)+t)//4 + 1 + δᵢ · grows forever ·   "
           "G1→G2: 2 → 92 · G7→G3: 159 → 955   (t₀: 0 → 160, step 1)",
           500, star_H=H, frame_ms=90)
render_gif("figB_mod96_step1.gif", mod, T0_MOD, M_MOD,
           "MOD cost (as asked): first term = ((base+t) mod 96)//4 — "
           "departure t₀ = {t0:>2d} of one full period 0..95",
           f"bounded: entry cost ≤ 24, trips ≤ {mx_mod:.0f} steps at every t₀ "
           "· matrix is PERIODIC in t₀ (loop repeats seamlessly) · "
           "⚠ sawtooth wrap breaks FIFO (see reply)",
           vmax_mod, frame_ms=110)
render_gif("figB_tri192_step1.gif", tri, T0_TRI, M_TRI,
           "TRIANGLE cost (FIFO-safe alternative): rise 96 / fall 96 — "
           "departure t₀ = {t0:>3d} of one full period 0..191",
           f"bounded: entry cost ≤ 25, trips ≤ {mx_tri:.0f} steps at every t₀ "
           "· periodic, seamless loop · FIFO preserved ⇒ existing TD-Dijkstra/"
           "mask/Bᵥ machinery stays exact",
           vmax_tri, frame_ms=80)

# --------------------------------------------------------------- profiles png
fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.4), dpi=110, sharex=True)
fig.patch.set_facecolor(SURF)
TT = np.arange(0, 385)
for ax, inst_, ttl, mx in (
        (axes[0], cur, "CURRENT: (base+t)//4 + 1 — unbounded", None),
        (axes[1], mod, f"MOD (as asked): ((base+t) mod {P_MOD})//4 + 1 — "
                       "bounded, sawtooth (breaks FIFO)", 24),
        (axes[2], tri, f"TRIANGLE: fold of period {P_TRI} — bounded, "
                       "FIFO-safe", 25)):
    ax.set_facecolor(SURF)
    for lid, col, lbl in ((1, "#2A78D6", "E/W street, base 1"),
                          (60, ORANGE, "N/S street, base 60")):
        ax.plot(TT, [inst_.cost(lid, int(t)) for t in TT],
                color=col, lw=2, label=lbl)
    ax.set_title(ttl, fontsize=10.5, color=INK)
    ax.set_xlabel("time t", fontsize=9.5, color=INK2)
    ax.grid(alpha=0.25, lw=0.6)
    ax.tick_params(labelsize=8.5, colors=INK2)
    for spn in ("top", "right"):
        ax.spines[spn].set_visible(False)
    if mx:
        ax.axhline(mx, color="#8A8880", lw=1, ls=":")
        ax.text(378, mx + 1.5, f"max {mx}", ha="right", fontsize=8.5,
                color=INK2)
axes[0].set_ylabel("link entry cost c(i,t)   (δ = 0)", fontsize=9.5, color=INK)
axes[0].legend(fontsize=9, loc="upper left", frameon=False)
fig.suptitle("Three cost laws on the same two streets — what the modulo does",
             fontsize=13, color=INK, y=0.99)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(f"{R}/figB_cost_profiles.png", facecolor=SURF)
plt.close(fig)
print(f"wrote {R}/figB_cost_profiles.png")
