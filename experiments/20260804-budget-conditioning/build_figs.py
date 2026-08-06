"""Figures for the budget-conditioning deck pages (YIL-113).

figS1  alpha (step) vs budget (smooth) — same instance, same y axis
figS2  coverage-vs-rho response curve, model vs Gurobi
figS3  five-layer exam: relative gap + feasibility

Palette: documented categorical slots 1 (blue) / 2 (orange) from the dataviz
reference palette — pre-validated as a set; no re-stepping.
"""

import csv
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
R = f"{HERE}/results"
os.makedirs(R, exist_ok=True)

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
SURF = "#fcfcfb"
GRID = "#e4e3de"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "font.size": 11, "text.color": INK,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.linewidth": 1.0,
    "xtick.major.size": 0, "ytick.major.size": 0,
    "font.family": "DejaVu Sans",
})


def style(ax):
    ax.grid(True, axis="y", color=GRID, lw=1.0, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def read(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------ figS1
def fig_s1():
    a = read(f"{HERE}/results_alpha_mod.csv")
    b = read(f"{HERE}/results_sweep_mod.csv")
    b = [r for r in b if float(r["rho"]) <= 6.0]          # drop the rho=99 point
    ax2v = [float(r["alpha2"]) for r in a]
    acov = [int(r["cov"]) for r in a]
    rho = [float(r["rho"]) for r in b]
    bcov = [int(r["cov"]) for r in b]
    ymax = max(max(acov), max(bcov)) * 1.18

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.0, 4.5), dpi=200)

    axL.plot(ax2v, acov, "-o", color=BLUE, lw=2, ms=8,
             markerfacecolor=SURF, markeredgewidth=2, zorder=3)
    axL.set_xlim(0.05, 0.95)
    axL.set_ylim(0, ymax)
    axL.set_xlabel("coverage weight  $\\alpha_2$   (budget fixed at horizon H)")
    axL.set_ylabel("fleet coverage  (space–time cells)")
    axL.set_title("The weight is a SWITCH", color=INK, fontsize=13,
                  fontweight="bold", loc="left", pad=12)
    axL.axvline(0.5, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    axL.annotate("min-time routes\n(172 cells, flat over 0.10–0.48)",
                 xy=(0.28, 172), xytext=(0.10, 470), fontsize=10, color=INK2,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    axL.annotate("horizon-saturated roaming\n(999 cells, flat over 0.52–0.90)",
                 xy=(0.80, 999), xytext=(0.58, 620), fontsize=10, color=INK2,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    axL.text(0.485, ymax * 0.965, "knife-edge  $\\alpha_2/\\alpha_1 = 1$",
             fontsize=10, color=MUTED, ha="right", va="top")
    axL.text(0.06, ymax * 0.06, "13 values of $\\alpha_2$  →  2 distinct solutions",
             fontsize=10.5, color=INK, fontweight="bold")

    axR.plot(rho, bcov, "-o", color=ORANGE, lw=2, ms=8,
             markerfacecolor=SURF, markeredgewidth=2, zorder=3)
    axR.set_xlim(0.7, 6.3)
    axR.set_ylim(0, ymax)
    axR.set_xlabel("budget slack ratio  $\\rho$   "
                   "($B_v = \\rho\\,\\tau^{min}_v$;  $\\alpha$ fixed at 0.3 / 0.7)")
    axR.set_title("The budget is a DIAL", color=INK, fontsize=13,
                  fontweight="bold", loc="left", pad=12)
    for x, y in ((1.0, bcov[0]), (2.0, bcov[rho.index(2.0)]),
                 (6.0, bcov[-1])):
        axR.annotate(f"{y}", xy=(x, y), xytext=(0, 12), fontsize=10,
                     color=INK2, textcoords="offset points", ha="center")
    axR.text(0.85, ymax * 0.06,
             "10 values of $\\rho$  →  10 distinct solutions, monotone",
             fontsize=10.5, color=INK, fontweight="bold")

    for ax in (axL, axR):
        style(ax)
        ax.yaxis.set_major_locator(MaxNLocator(5))
    fig.suptitle("Same instance (V=3, 4×4 bidirectional grid), same MILP, "
                 "same solver — only the control variable differs",
                 fontsize=11, color=INK2, y=1.005, x=0.011, ha="left")
    fig.tight_layout()
    fig.savefig(f"{R}/figS1_knob_vs_switch.png", bbox_inches="tight",
                facecolor=SURF)
    print("figS1 ok")


# ------------------------------------------------------------ figS2
def fig_s2():
    rows = json.load(open(f"{HERE}/results_mod/curve.json"))
    rho = [r["rho"] for r in rows]
    gur = [r["gurobi_cov"] for r in rows]
    mdl = [r["model_cov"] for r in rows]
    unseen = {1.25, 1.75, 4.0}

    fig, ax = plt.subplots(figsize=(9.6, 4.8), dpi=200)
    ax.plot(rho, gur, "-", color=BLUE, lw=2, zorder=3,
            label="Gurobi (reference)")
    ax.plot(rho, mdl, "-", color=ORANGE, lw=2, zorder=3,
            label="neural model (masked greedy)")
    for xs, ys, c in ((rho, gur, BLUE), (rho, mdl, ORANGE)):
        for x, y in zip(xs, ys):
            filled = x not in unseen
            ax.plot([x], [y], "o", ms=9, color=c, zorder=4,
                    markerfacecolor=(c if filled else SURF),
                    markeredgecolor=c, markeredgewidth=2)
    for x in sorted(unseen):
        ax.axvspan(x - 0.045, x + 0.045, color="#f3f2ee", zorder=0)
    leg = ax.legend(loc="lower right", frameon=False, fontsize=11,
                    handlelength=1.6, borderaxespad=1.2)
    for t in leg.get_texts():
        t.set_color(INK)
    ax.set_xlabel("budget slack ratio  $\\rho$      "
                  "(hollow markers + shading = $\\rho$ NEVER seen in training)")
    ax.set_ylabel("fleet coverage  (space–time cells)")
    ax.set_title("The model tracks the dial — including at budgets it never saw",
                 color=INK, fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.text(1.02, 690, "$\\rho=1$: budget forces the min-time route\n"
                       "→ model is EXACTLY optimal, 60/60",
            fontsize=10, color=INK2, va="top")
    ax.set_ylim(0, 830)
    style(ax)
    fig.tight_layout()
    fig.savefig(f"{R}/figS2_response_curve.png", bbox_inches="tight",
                facecolor=SURF)
    print("figS2 ok")


# ------------------------------------------------------------ figS3
def fig_s3():
    agg = json.load(open(f"{HERE}/results_mod/agg_3seed.json"))
    order = ["L1_same", "L2_odzero", "L3_vextrap", "L4a_rhoint", "L4b_rhoext"]
    labels = ["L1  same-distribution", "L2  OD zero-shot",
              "L3  fleet extrapolation\n      V ∈ {5,8}",
              "L4a  UNSEEN budget\n       (interpolation)",
              "L4b  UNSEEN budget\n       (extrapolation)"]
    vals = [100 * agg[k]["rel_gap_mean"] for k in order]
    errs = [100 * agg[k]["rel_gap_std"] for k in order]
    feas = [agg[k]["feasible"] for k in order]
    n = [agg[k]["n"] for k in order]

    fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=200)
    ypos = range(len(order))
    cols = [BLUE, BLUE, BLUE, ORANGE, ORANGE]
    ax.barh(list(ypos), vals, xerr=errs, height=0.62, color=cols, zorder=3,
            error_kw=dict(ecolor=INK2, lw=1.2, capsize=4))
    for i, (v, f, nn) in enumerate(zip(vals, feas, n)):
        ax.text(v + 1.0, i, f"{v:.1f}%      feasible {f}/{nn}", va="center",
                fontsize=10.5, color=INK2)
    ax.set_yticks(list(ypos))
    ax.set_yticklabels(labels, fontsize=10.5, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 42)
    ax.set_xlabel("mean objective gap vs Gurobi, relative to |objective|  "
                  "(mean ± std over 3 seeds; lower is better)")
    ax.set_title("Five-layer exam — 2 300 unseen cases, "
                 "100 % feasible everywhere",
                 color=INK, fontsize=13, fontweight="bold", loc="left", pad=12)
    ax.grid(True, axis="x", color=GRID, lw=1.0, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    fig.tight_layout()
    fig.savefig(f"{R}/figS3_layers.png", bbox_inches="tight", facecolor=SURF)
    print("figS3 ok")


if __name__ == "__main__":
    fig_s1()
    fig_s2()
    fig_s3()
