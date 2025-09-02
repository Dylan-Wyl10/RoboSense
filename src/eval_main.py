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
            ctm_value=["../result/ctmResult/logs/ctm_test1/350_5400s_5percent/10000cover/occupation.npy",
                       "../result/ctmResult/logs/ctm_test1/350_5400s_5percent/100000cover/occupation.npy"],
            cell_list=cellidx,
            cell_coordinates='../sumo_cfg/5x5net/CTMcfg/Cells.csv',
            title_str="Cell Occupation Distribution",
            plot=cfg.plot_mode,  # [video, figure. historgram]
            eval_start=cfg.eval_start, eval_duration=cfg.eval_dur,
        )

    if cfg.is_eval:
        occ_result = pipe.evalOcc(
            bench_occ="../result/ctmResult/logs/ctm_test1/350_5400s_10percent/0cover/occupation.npy",
            ctm_occ="../result/ctmResult/logs/ctm_test1/350_5400s_10percent/1000000cover/occupation.npy",
            eval_start=cfg.eval_start, eval_duration=cfg.eval_dur)
        #
        veh_result_1, summary_1 = pipe.evalTripInfo(
            trip_info="../result/ctmResult/logs/ctm_test1/350_5400s_10percent/0cover/sumolog_tmp/tripinfo0.xml",
            eval_start=cfg.eval_start, eval_end=cfg.eval_dur)

        veh_result_2, summary_2 = pipe.evalTripInfo(
            trip_info="../result/ctmResult/logs/ctm_test1/350_5400s_10percent/1000000cover/sumolog_tmp/tripinfo0.xml",
            eval_start=cfg.eval_start, eval_end=cfg.eval_dur)

        plot_cav_duration_histogram(
            data_list=[veh_result_1, veh_result_2],
            labels=[r"$\alpha_1:\alpha_2=1:0$", r"$\alpha_1:\alpha_2=1:10^{6}$"],
            attribute="routeLength",  # "duration", routeLength
            bins=30,
            title="Historgram of CAV Travel Distance",  # Travel Duration Distribution (CAV)", "Travel Route Length Distribution (CAV)"
        )
        # plot_cav_duration_histogram(veh_result_2)
        plot_cav_duration_histogram(
            data_list=[veh_result_1, veh_result_2],
            labels=[r"$\alpha_1:\alpha_2=1:0$", r"$\alpha_1:\alpha_2=1:10^{6}$"],
            attribute="duration",  # "duration", routeLength
            bins=30,
            title="Historgram of CAV Travel Time",
            # Travel Duration Distribution (CAV)", "Travel Route Length Distribution (CAV)"
        )

        score = pipe.evalCTM(file_gt='../result/ctmResult/logs/ctm_test1/350_5400s_2percent/10000cover/ctm_gt.npy',
                             file_rec='../result/ctmResult/logs/ctm_test1/350_5400s_2percent/10000cover/ctm_rec.npy',
                             cell_json='../result/ctmResult/CTMcell_index.json',
                             eval_start=cfg.eval_start, eval_duration=cfg.eval_dur, method='mape', vis=False)

        print(score)
    if cfg.is_odeval:
        od_process.load_data(input_json_path='../result/ctmResult/logs/ctm_test1/350_5400s_2percent/1000000cover/od_route.json')
        od_process.build_od_groups(sort_by='alpha')

        topo = od_process.load_topology_config(input_json_path='../sumo_cfg/5x5net/netgrid_topology.json')
        od_process.set_topology(topo)

        # add a function to plot all od pairs

        ods = od_process.available_od_keys()
        od_1 = ods[0]
        od_process.plot_network_edge_usage(od_key=od_1, case_string='1e6 2%', mode='color')

        # aaa = od_process.build_od_groups()
        # od_process.plot_od_histogram(sort="count")
        print('yese')

