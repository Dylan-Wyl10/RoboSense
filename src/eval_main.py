"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the main script that simulates the CAV rerouting with TSC
Note!!!!: this is the test temporoal script for debugging (yilin, 20231129)
"""
# Status check for Sumo environment
import sys
import os
import argparse
from simulation import Simulation
import argparse

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    os.environ['SUMO_HOME'] = '/usr/share/sumo'
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    print('SUMO_HOME fixed')
    # sys.exit("please declare environment variable 'SUMO_HOME'")

import traci
from config import Config
# from utili import Pipline
from utili.tools import *

if __name__ == '__main__':
    cfg = Config()
    pipe = Pipline()
    od_process = ODProcessor()

    with open('../result/ctmResult/CTMcell_index.json', 'r') as file:
        cellidx = [line.strip() for line in file]

    if cfg.is_vislz:
        pipe.ctmPlot(
            ctm_value=["../result/ctmResult/logs/ctm_test1/350_5400s_2percent/0cover/occupation.npy",
                       "../result/ctmResult/logs/ctm_test1/350_5400s_2percent/100000cover/occupation.npy"],
            cell_list=cellidx,
            cell_coordinates='../sumo_cfg/5x5net/CTMcfg/Cells.csv',
            title_str="Cell Occupation Distribution",
            plot=cfg.plot_mode,  # [video, figure. historgram]
            eval_start=cfg.eval_start, eval_duration=cfg.eval_dur,
        )

    if cfg.is_eval:
        test = '1215test'
        pr = '350_5400s_2percent_new_normVeh'
        EVAL_CASES = [
            '0_cover',
            # '1_cover',
            # '3_cover',
            # '5_cover',
            # '10_cover',
            # '30_cover',
            # '50_cover',
            # '100_cover',
            # '300_cover',
            # '500_cover',
            # '700_cover',
            # '1000_cover',
            # '1250_cover',
            # '1500_cover',
            # '1750_cover',
            # '2000_cover',
            # '2250_cover',
            '2500_cover',
            # '2750_cover',
            # '3000_cover',
            # '4000_cover',
            '5000_cover',
            # '6000_cover',
            # '7000_cover',
            # '8000_cover',
            # '9000_cover',
            '10000_cover',
            # '30000_cover',
            # '50000_cover',
            # '70000_cover',
            '100000_cover',
            # '300000_cover',
            # '500000_cover',
            # '700000_cover',
            # '1000000_cover',
            # '3000000_cover',
            # '5000000_cover',
            # '7000000_cover',
            # '10000000_cover'
        ]
        LOG_BASE = f"../result/ctmResult/logs/ctm_test1/{test}/{pr}"

        # --- Trip info evaluation (all cases) ---
        veh_results, summaries = [], []
        for case in EVAL_CASES:
            veh_r, summ = pipe.evalTripInfo(
                trip_info=f"{LOG_BASE}/{case}/sumolog_tmp/tripinfo0.xml",
                eval_start=cfg.eval_start, eval_end=cfg.eval_start + cfg.eval_dur)
            veh_results.append(veh_r)
            summaries.append(summ)
            print(f"  [{case}] trip summary: {summ}")

        labels = [c.replace('_cover', '') for c in EVAL_CASES]

        plot_cav_duration_histogram(
            data_list=veh_results,
            labels=labels,
            attribute="routeLength",
            bins=30,
            title="Histogram of CAV Travel Distance",
            save_path=f"../result/plot_ctm/timeDistribution/{test}_{pr}_distance.png",
        )
        plot_cav_duration_histogram(
            data_list=veh_results,
            labels=labels,
            attribute="duration",
            bins=30,
            title="Histogram of CAV Travel Time",
            save_path=f"../result/plot_ctm/timeDistribution/{test}_{pr}_travelTime.png",
        )

        # --- CTM evaluation (all cases) ---
        for case in EVAL_CASES:
            score, gt, rec = pipe.evalCTM(
                file_gt=f'{LOG_BASE}/{case}/ctm_gt.npy',
                file_rec=f'{LOG_BASE}/{case}/ctm_rec.npy',
                cell_json='../result/ctmResult/CTMcell_index.json',
                eval_start=cfg.eval_start, eval_duration=cfg.eval_dur, method='mae', vis=False)
            print(f"  [{case}] CTM score: {score}")

        # --- Occupancy evaluation (each case vs first case as reference) ---
        ref_occ = f"{LOG_BASE}/{EVAL_CASES[0]}/occupation.npy"
        for case in EVAL_CASES[1:]:
            occ_result = pipe.evalOcc(
                bench_occ=ref_occ,
                ctm_occ=f"{LOG_BASE}/{case}/occupation.npy",
                eval_start=cfg.eval_start, eval_duration=cfg.eval_dur)
            print(f"  [{EVAL_CASES[0]} vs {case}] occ: {occ_result}")

    if cfg.is_sensorPower:
        # --- Directory to scan (change this to switch experiment) ---
        sp_case_str = '1215test/350_5400s_2percent_new_normVeh'
        sp_base = f'../result/ctmResult/logs/ctm_test1/{sp_case_str}'

        # --- Define cases to include (same style as EVAL_CASES) ---
        SP_CASES = [
            # 'bench',
            # '0_cover',
            # '1_cover',
            '10_cover',
            '100_cover',
            # '500_cover',
            '1000_cover',
            # '1500_cover',
            # '2000_cover',
            # '2500_cover',
            '3000_cover',
            # '5000_cover',
            '10000_cover',
            '100000_cover'
        ]

        # Filter to only cases that exist and have the required files
        all_cases = [
            c for c in SP_CASES
            if os.path.isdir(os.path.join(sp_base, c))
            and os.path.exists(os.path.join(sp_base, c, 'occupation.npy'))
            and os.path.exists(os.path.join(sp_base, c, 'num_cav.pkl'))
        ]

        occ_path  = [os.path.join(sp_base, c, 'occupation.npy') for c in all_cases]
        ncav_path = [os.path.join(sp_base, c, 'num_cav.pkl')    for c in all_cases]
        label     = all_cases

        # --- Compute B per case from tripinfo: B = 100 * avg_routeLength / avg_duration (CAV only) ---
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

        occ_ls, cav_num_ls = pipe.getOcc(matrix_ls=occ_path, eval_start=cfg.eval_start, eval_duration=cfg.eval_dur)
        curves = [{"Ns": occ_ls[i].shape[0], "B": B[i]/80, "visit_mat": occ_ls[i], "Nv_vals": range(0, 250),
                   "label": label[i], "ncav_list": ncav_path[i], "cav_num": cav_num_ls[i]} for i in range(len(occ_ls))]

        save_tag = sp_case_str.replace('/', '_')
        results, pnp_ls = plot_Cnv_curves(curves, save_path=f"../result/plot_ctm/sensorpowerEval/{save_tag}_sensingpower.png", mode="count", check_ns_equals_segments=True,
                                          title=f"Sensing Power($C_{{nv}}$) vs Number of CAV ($N_v$)\n{sp_case_str}")

        for pnp in range(len(pnp_ls)):
            plot_p_distribution(pnp_ls[pnp], title=f"Distribution of Cell [{all_cases[pnp]}]\n{sp_case_str}",
                            save_dir=f"../result/plot_ctm/sensorpowerEval/p_distr_{all_cases[pnp]}.png",
                            y_lim=(0, 450))
        print('111')
        # ################################################################################################################

    if cfg.is_odeval:   # evaluate route through od pair
        od_process.load_data(input_json_path='../result/ctmResult/logs/ctm_test1/350_5400s_5percent/10000cover/od_route.json')
        od_process.build_od_groups(sort_by='alpha')

        topo = od_process.load_topology_config(input_json_path='../sumo_cfg/5x5net/netgrid_topology.json')
        od_process.set_topology(topo)

        # add a function to plot all od pairs

        ods = od_process.available_od_keys()
        od_1 = ods[12]
        od_process.plot_network_edge_usage(od_key=od_1, case_string='1e6 5%', mode='width')

        # aaa = od_process.build_od_groups()
        # od_process.plot_od_histogram(sort="count")
        print('yese')

    if cfg.ctm_cell_vis:  # this is to visulize the ctm result for links
        # cell_idx = json.load(open('../result/ctmResult/logs'))
        with open('../result/plot_ctm/CTMcell_index.json', 'r') as file:
            cell_idx = [line.strip() for line in file]

        ctm_pred = np.load('../result/ctmResult/logs/ctm_test1/350_5400s_5percent/1000000cover/ctm_rec.npy')[:, 360:]
        ctm_gt = np.load('../result/ctmResult/logs/ctm_test1/350_5400s_5percent/1000000cover/ctm_gt.npy')[:, 360:]

        linkCTMvislz(cell_idx, ctm_pred, ctm_gt)

    if cfg.get_optm_time:

        case = '1215test'
        paths = {
                "2_percent": {"0cover": {"cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/0cover/num_cav.pkl",
                                         "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/0cover/time_optim.pkl"},
                              "1e4cover": {"cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/1e4cover/num_cav.pkl",
                                           "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/1e4cover/time_optim.pkl"},
                              "1e5cover": {"cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/1e5cover/num_cav.pkl",
                                           "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/1e5cover/time_optim.pkl"},
                              "1e6cover": {"cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/1e6cover/num_cav.pkl",
                                           "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_2percent/1e6cover/time_optim.pkl"}
                              },
                "5_percent": {
                "0cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/0cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/0cover/time_optim.pkl"},
                "1e4cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/1e4cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/1e4cover/time_optim.pkl"},
                "1e5cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/1e5cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/1e5cover/time_optim.pkl"},
                "1e6cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/1e6cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_5percent/1e6cover/time_optim.pkl"}
                },
            "10_percent": {
                "0cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/0cover/num_cav.pkl",
                     "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/0cover/time_optim.pkl"},
                "1e4cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e4cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e4cover/time_optim.pkl"},
                "1e5cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e5cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e5cover/time_optim.pkl"},
                "1e6cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e6cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e6cover/time_optim.pkl"},
                "1e7cover": {
                    "cav": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e7cover/num_cav.pkl",
                    "time": f"../result/ctmResult/logs/ctm_test1/{case}/350_5400s_10percent/1e7cover/time_optim.pkl"}
            },
}

        plot_cav_time_boxplots(paths, save_dir="../result/plot_ctm/solving_time/boxplot.png", show=True)

        print('yes')
        # linkCTMvislz()


