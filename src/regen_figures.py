"""
Regenerate paper figures from the canonical post-fix experiment data.

Covers:
- Figure 16: Sensing Power (4 panels)
- Figure 17: Segment popularity distributions ($p_i$) per panel
- Figure 18: Route diversity (`route_diversity.png`)
- Figure 19: Travel-distance histogram grid (4 configs x 6 alphas)
- Figure 20: Travel-time histogram grid (4 configs x 6 alphas)

All figures use the eval window (`cfg.eval_start`, `cfg.eval_dur`) so that
aggregated CAV statistics are consistent with Table 3.

Author: Research Agent
"""

import sys
import os
import json
from collections import defaultdict

if 'SUMO_HOME' not in os.environ:
    os.environ['SUMO_HOME'] = '/usr/share/sumo'
    tools_path = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools_path)

import numpy as np
import pickle
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt

# Add project root and src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, script_dir)

from utili.tools import (
    Pipline, remove_branch, popularity_from_visit_matrix,
    Cnv_curve, getSensorPower, plot_Cnv_curves, plot_p_distribution
)
from config import Config

# ============================================================
# Configuration
# ============================================================

RESULT_BASE = '../result/ctmResult/logs/ctm_test1/1215test'
FIGURE_OUTPUT = '../result/plot_ctm/sensorpowerEval'
LATEX_FIG_DIR = '../partb_latex_latest/figure'

SP_CASES = ['10_cover', '100_cover', '1000_cover', '3000_cover', '10000_cover', '100000_cover']

# Cases used for Figs 18-20 (full alpha sweep)
ALPHA_CASES_FULL = [
    '10_cover', '100_cover', '500_cover', '1000_cover', '1500_cover',
    '2000_cover', '2500_cover', '3000_cover', '5000_cover',
    '10000_cover', '100000_cover',
]

# Configs that appear in Figs 18-20
EXP_CONFIGS = [
    # (label, dir, color, marker, linestyle, fname_prefix, title_pct)
    ('10% MPR',        '350_5400s_10percent_new_normVeh',       'green',  'o', '-',  '10p',       r'10\%'),
    ('5% MPR',         '350_5400s_5percent_new_normVeh',        'red',    's', '-',  '5p',        r'5\%'),
    ('2% MPR',         '350_5400s_2percent_new_normVeh',        'blue',   '^', '-',  '2p',        r'2\%'),
    ('10% no budget',  '350_5400s_10percent_nobgt_new_normVeh', 'purple', 'D', '--', '10p_nobgt', r'10\%\ No\ Budget'),
]

# Histogram-grid alpha columns (Fig 19/20)
HIST_CASES = [
    ('100_cover',    '100',    'a100'),
    ('1000_cover',   '1000',   'a1000'),
    ('3000_cover',   '3000',   'a3000'),
    ('5000_cover',   '5000',   'a5000'),
    ('10000_cover',  '10000',  'a10000'),
    ('100000_cover', '10^{5}', 'a1e5'),
]

# Histogram bin/range conventions
DIST_RANGE = (1500, 10500)
DIST_BINS = 9
DIST_XMAX = 7000      # visible upper limit on travel-distance panels
TIME_RANGE = (200, 2200)
TIME_BINS = 12

# Label mapping: convert case names to α₂ format
LABEL_MAP = {
    '10_cover':     r'$\alpha_2 = 10$',
    '100_cover':    r'$\alpha_2 = 100$',
    '1000_cover':   r'$\alpha_2 = 1000$',
    '3000_cover':   r'$\alpha_2 = 3000$',
    '10000_cover':  r'$\alpha_2 = 10000$',
    '100000_cover': r'$\alpha_2 = 10^5$',
}

# The 4 panels for Figure 16
PANELS = [
    {
        'case_str': '350_5400s_2percent_new_normVeh',
        'save_tag': 'pr2',
        'panel_label': 'Penetration Rate = 2%',
    },
    {
        'case_str': '350_5400s_5percent_new_normVeh',
        'save_tag': 'pr5',
        'panel_label': 'Penetration Rate = 5%',
    },
    {
        'case_str': '350_5400s_10percent_new_normVeh',
        'save_tag': 'pr10',
        'panel_label': 'Penetration Rate = 10%',
    },
    {
        # No-budget placeholder: use 10% data
        'case_str': '350_5400s_10percent_new_normVeh',
        'save_tag': 'pr10_nobgt',
        'panel_label': 'Penetration Rate = 10% (No Budget)',
    },
]

cfg = Config()


def generate_sensing_power_figure(panel_config):
    """Generate one sensing power panel (Figure 16 subplot)."""
    sp_case_str = panel_config['case_str']
    save_tag = panel_config['save_tag']
    sp_base = f'{RESULT_BASE}/{sp_case_str}'

    # Filter to existing cases
    all_cases = [
        c for c in SP_CASES
        if os.path.isdir(os.path.join(sp_base, c))
        and os.path.exists(os.path.join(sp_base, c, 'occupation.npy'))
        and os.path.exists(os.path.join(sp_base, c, 'num_cav.pkl'))
    ]

    occ_path  = [os.path.join(sp_base, c, 'occupation.npy') for c in all_cases]
    ncav_path = [os.path.join(sp_base, c, 'num_cav.pkl')    for c in all_cases]

    # Use cleaned labels
    labels = [LABEL_MAP.get(c, c) for c in all_cases]

    # Compute B per case
    B = []
    for case in all_cases:
        trip_path = os.path.join(sp_base, case, 'sumolog_tmp', 'tripinfo0.xml')
        _, summ = Pipline.evalTripInfo(trip_info=trip_path,
                                       eval_start=cfg.eval_start,
                                       eval_end=cfg.eval_start + cfg.eval_dur)
        cav_summ = summ.get('cav', {})
        if cav_summ and cav_summ.get('vehicle_count', 0) > 0:
            b_val = 100 * cav_summ['avg_routeLength'] / cav_summ['avg_duration']
        else:
            b_val = 0.0
        B.append(b_val)
        print(f"  [{case}] B={b_val:.4f}")

    pipe = Pipline()
    occ_ls, cav_num_ls = pipe.getOcc(matrix_ls=occ_path,
                                      eval_start=cfg.eval_start,
                                      eval_duration=cfg.eval_dur)

    curves = [
        {
            "Ns": occ_ls[i].shape[0],
            "B": B[i]/80,
            "visit_mat": occ_ls[i],
            "Nv_vals": range(0, 250),
            "label": labels[i],
            "ncav_list": ncav_path[i],
            "cav_num": cav_num_ls[i],
        }
        for i in range(len(occ_ls))
    ]

    # Clean title - no case string
    clean_title = r"Sensing Power($C_{nv}$) vs Number of CAV ($N_v$)"

    # Save to the figure output directory with a clean filename
    save_name = f"1215test_{sp_case_str}_sensingpower.png"
    if save_tag == 'pr10_nobgt':
        save_name = f"1215test_350_5400s_10percent_nobgt_new_normVeh_sensingpower.png"

    save_path = os.path.join(FIGURE_OUTPUT, save_name)

    results, pnp_ls = plot_Cnv_curves(
        curves,
        save_path=save_path,
        mode="count",
        check_ns_equals_segments=True,
        title=clean_title,
        show=False,
    )

    print(f"  Saved sensing power figure: {save_path}")
    return results, pnp_ls, all_cases, save_tag


def generate_p_distribution_figures(pnp_ls, all_cases, save_tag):
    """Generate p_i distribution figures (Figure 17 subplots) for one penetration rate."""

    # First pass: find the max x value across all cases for unified xlim
    max_p = 0
    for pnp in range(len(pnp_ls)):
        p = np.asarray(pnp_ls[pnp]).squeeze()
        p_sum = np.sum(p)
        if not np.isclose(p_sum, 1.0):
            p = p / p_sum
        max_p = max(max_p, np.max(p))

    # Add 10% padding
    xlim_upper = max_p * 1.1

    # Create output subdir
    pdistr_dir = os.path.join(FIGURE_OUTPUT, f"{save_tag}_Pdistr")
    os.makedirs(pdistr_dir, exist_ok=True)

    for pnp in range(len(pnp_ls)):
        case_name = all_cases[pnp]
        alpha_label = LABEL_MAP.get(case_name, case_name)

        # Clean title: just the distribution name
        clean_title = f"Segment Popularity Distribution ({alpha_label})"

        save_path = os.path.join(pdistr_dir, f"p_distr_{case_name}.png")

        # Call plot_p_distribution with cleaned title
        # We need to handle xlim ourselves since the original function doesn't support it
        p = np.asarray(pnp_ls[pnp]).squeeze()
        p_sum = np.sum(p)
        if not np.isclose(p_sum, 1.0):
            p = p / p_sum

        num_bins = 30
        counts, bin_edges = np.histogram(p, bins=num_bins)
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        bin_width = bin_edges[1] - bin_edges[0]

        plt.figure(figsize=(8, 4))
        plt.bar(bin_centers, counts, width=bin_width, align="center")
        plt.xlabel("p value")
        plt.ylabel("Frequency")
        plt.title(clean_title)
        plt.ylim(0, 450)
        plt.xlim(0, xlim_upper)
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"  Saved p_distr: {save_path}")


def _eval_window_cav(trip_info_path):
    """Return list of CAV trip records inside the eval window.

    Each record is the dict produced by Pipline.evalTripInfo (keys include
    `id`, `duration`, `routeLength`). Returns [] if the file is missing.
    """
    if not os.path.exists(trip_info_path):
        return []
    result, _ = Pipline.evalTripInfo(
        trip_info_path,
        eval_start=cfg.eval_start,
        eval_end=cfg.eval_start + cfg.eval_dur,
    )
    return result.get('cav', [])


def generate_route_diversity_figure():
    """Figure 18: total distinct routes summed over O-D pairs vs alpha_2,
    and average route length, both normalized to alpha_2=10. Eval-window
    filtered so vehicle counts agree with Table 3."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    for label, cfg_dir, color, marker, ls, _, _ in EXP_CONFIGS:
        alphas, totU, lengths = [], [], []
        for case in ALPHA_CASES_FULL:
            od_p = os.path.join(RESULT_BASE, cfg_dir, case, 'od_route.json')
            trip_p = os.path.join(RESULT_BASE, cfg_dir, case, 'sumolog_tmp', 'tripinfo0.xml')
            if not os.path.exists(od_p):
                continue
            keep_ids = {r['id'] for r in _eval_window_cav(trip_p)}
            if not keep_ids:
                continue
            with open(od_p) as f:
                data = json.load(f)
            od = defaultdict(list)
            for v_id, info in data.items():
                if v_id not in keep_ids:
                    continue
                od[(info['origin'], info['destination'])].append(tuple(info['route']))
            if not od:
                continue
            u_total = sum(len(set(rs)) for rs in od.values())
            all_lens = [len(r) for rs in od.values() for r in rs]
            alphas.append(int(case.replace('_cover', '')))
            totU.append(u_total)
            lengths.append(sum(all_lens) / len(all_lens))

        if not alphas:
            continue
        u_norm = [v / totU[0] for v in totU]
        l_norm = [v / lengths[0] for v in lengths]
        ax1.plot(alphas, u_norm, color=color, marker=marker, label=label,
                 linewidth=1.5, markersize=5, linestyle=ls)
        ax2.plot(alphas, l_norm, color=color, marker=marker, label=label,
                 linewidth=1.5, markersize=5, linestyle=ls)

    for ax, ylab, title in [
        (ax1,
         "Diversification Ratio\n$U(\\alpha_2)\\,/\\,U(\\alpha_2{=}10)$",
         "(a) Diversification ratio across penetration rates"),
        (ax2,
         "Relative Average Route Length\n$\\bar L(\\alpha_2)\\,/\\,\\bar L(\\alpha_2{=}10)$",
         "(b) Average route length across penetration rates"),
    ]:
        ax.set_xscale('log')
        ax.set_xlabel(r"Coverage weight $\alpha_2$")
        ax.set_ylabel(ylab)
        ax.set_title(title)
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1.0, color='gray', linewidth=0.8, linestyle=':', alpha=0.5)

    plt.tight_layout()
    out = os.path.join(LATEX_FIG_DIR, 'route_diversity.png')
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  saved {out}")


def _save_hist_panel(base_vals, cur_vals, title, legend_alpha, xlabel,
                     bin_range, n_bins, out_path, xlim=None, ylim=None):
    plt.figure(figsize=(4.5, 3.5), dpi=150)
    plt.hist(base_vals, bins=n_bins, range=bin_range,
             alpha=0.55, color='cornflowerblue', label=r"$\alpha_2 = 10$")
    plt.hist(cur_vals, bins=n_bins, range=bin_range,
             alpha=0.55, color='indianred', label=legend_alpha)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel('Count')
    if xlim is not None:
        plt.xlim(*xlim)
    if ylim is not None:
        plt.ylim(*ylim)
    plt.legend(loc='upper right', fontsize=9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()


def generate_histogram_grid(attr, fname_kind, xlabel, bin_range, n_bins, xlim=None):
    """Generate the 24-panel histogram grid for one attribute.

    `attr` selects which trip field to plot (`routeLength` for Fig 19,
    `duration` for Fig 20). Files are written to
    `LATEX_FIG_DIR/routing_strategy/{fname_kind}_{config}_{alpha}.png`.

    Within each row (one penetration-rate config), all panels share a common
    y-axis upper limit so that bar heights can be compared across alpha values.
    """
    out_dir = os.path.join(LATEX_FIG_DIR, 'routing_strategy')
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for _, cfg_dir, _, _, _, fname_prefix, title_pct in EXP_CONFIGS:
        base_recs = _eval_window_cav(os.path.join(
            RESULT_BASE, cfg_dir, '10_cover', 'sumolog_tmp', 'tripinfo0.xml'))
        if not base_recs:
            print(f"  SKIP {cfg_dir}: missing/empty baseline tripinfo")
            continue
        base_vals = [r[attr] for r in base_recs]
        base_counts, _ = np.histogram(base_vals, bins=n_bins, range=bin_range)

        row_panels = []
        row_max = int(base_counts.max()) if base_counts.size else 0
        for case, a_disp, fname_suffix in HIST_CASES:
            recs = _eval_window_cav(os.path.join(
                RESULT_BASE, cfg_dir, case, 'sumolog_tmp', 'tripinfo0.xml'))
            if not recs:
                continue
            cur_vals = [r[attr] for r in recs]
            cur_counts, _ = np.histogram(cur_vals, bins=n_bins, range=bin_range)
            row_max = max(row_max, int(cur_counts.max()) if cur_counts.size else 0)
            row_panels.append((case, a_disp, fname_suffix, cur_vals))

        if not row_panels:
            continue

        row_ylim = (0, row_max * 1.05) if row_max > 0 else None

        for case, a_disp, fname_suffix, cur_vals in row_panels:
            title = fr"$\bf{{{title_pct}}}$, $\alpha_2 = {a_disp}$"
            legend_alpha = fr"$\alpha_2 = {a_disp}$"
            out_path = os.path.join(
                out_dir, f"{fname_kind}_{fname_prefix}_{fname_suffix}.png")
            _save_hist_panel(base_vals, cur_vals, title, legend_alpha,
                             xlabel, bin_range, n_bins, out_path,
                             xlim=xlim, ylim=row_ylim)
            n += 1
    print(f"  saved {n} {fname_kind} panels")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(FIGURE_OUTPUT, exist_ok=True)

    for panel in PANELS:
        print(f"\n{'='*60}")
        print(f"Processing: {panel['panel_label']}")
        print(f"{'='*60}")

        results, pnp_ls, all_cases, save_tag = generate_sensing_power_figure(panel)
        generate_p_distribution_figures(pnp_ls, all_cases, save_tag)

    print(f"\n{'='*60}\nFigure 18: route diversity\n{'='*60}")
    generate_route_diversity_figure()

    print(f"\n{'='*60}\nFigure 19: travel-distance histogram grid\n{'='*60}")
    generate_histogram_grid(
        attr='routeLength', fname_kind='dist',
        xlabel='Travel Distance (m)',
        bin_range=DIST_RANGE, n_bins=DIST_BINS,
        xlim=(DIST_RANGE[0], DIST_XMAX),
    )

    print(f"\n{'='*60}\nFigure 20: travel-time histogram grid\n{'='*60}")
    generate_histogram_grid(
        attr='duration', fname_kind='time',
        xlabel='Travel Time (s)',
        bin_range=TIME_RANGE, n_bins=TIME_BINS,
        xlim=None,
    )

    # Copy sensing-power / p_distr figures to the LaTeX figure directory.
    latex_fig_dir = os.path.join(LATEX_FIG_DIR, 'sensorpower')
    if os.path.isdir(latex_fig_dir):
        import shutil
        for panel in PANELS:
            sp_case_str = panel['case_str']
            save_tag = panel['save_tag']

            # Copy sensing power figure
            if save_tag == 'pr10_nobgt':
                src = os.path.join(FIGURE_OUTPUT, "1215test_350_5400s_10percent_nobgt_new_normVeh_sensingpower.png")
            else:
                src = os.path.join(FIGURE_OUTPUT, f"1215test_{sp_case_str}_sensingpower.png")

            if os.path.exists(src):
                dst = os.path.join(latex_fig_dir, os.path.basename(src))
                shutil.copy2(src, dst)
                print(f"Copied {os.path.basename(src)} -> LaTeX figure dir")

            # Copy p_distr figures
            pdistr_src = os.path.join(FIGURE_OUTPUT, f"{save_tag}_Pdistr")
            # Map save_tag to the original directory names used in LaTeX
            tag_to_latex_dir = {
                'pr2': '2percent_Pdistr',
                'pr5': '5percent_Pdistr',
                'pr10': '10percent_Pdistr',
                'pr10_nobgt': '10percent_nbgt_Pdistr',
            }
            pdistr_dst = os.path.join(latex_fig_dir, tag_to_latex_dir.get(save_tag, f"{save_tag}_Pdistr"))
            if os.path.isdir(pdistr_src):
                os.makedirs(pdistr_dst, exist_ok=True)
                for f in os.listdir(pdistr_src):
                    shutil.copy2(os.path.join(pdistr_src, f), os.path.join(pdistr_dst, f))
                print(f"Copied p_distr figures -> {pdistr_dst}")

    print("\nDone! All figures regenerated.")


if __name__ == '__main__':
    main()
