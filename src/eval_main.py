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
from utili import Pipline

if __name__ == '__main__':
    cfg = Config()
    pipe = Pipline()

    with open('../result/ctmResult/CTMcell_index.json', 'r') as file:
        cellidx = [line.strip() for line in file]

    if cfg.is_vislz:
        pipe.ctmPlot(
            ctm_value="../result/ctmResult/logs/ctm_test1/test4200s_5percent/occupation_4200s_400flow_5percent_bench.npy",
            cell_list=cellidx,
            cell_coordinates='../sumo_cfg/5x5net/CTMcfg/Cells.csv',
            plot=cfg.plot_mode,  # [video, figure]
        )

    if cfg.is_eval:
        occ_result = pipe.evalOcc(
            bench_occ="../result/ctmResult/logs/ctm_test1/350_5400s_2percent/bench/occupation.npy",
            ctm_occ="../result/ctmResult/logs/ctm_test1/350_5400s_2percent/10000cover/occupation.npy",
            eval_start=cfg.eval_start, eval_duration=cfg.eval_dur)
        #
        veh_result, summary = pipe.evalTripInfo(
            trip_info="../result/ctmResult/logs/ctm_test1/350_5400s_2percent/10000cover/sumolog_tmp/tripinfo0.xml")



        # pipe.plotTripInfo(veh_resutl)

        # calculate entropy
        # rr = pipe.evaluate_distribution_balance(occ_path="../result/ctmResult/logs/ctm_test1/350_5400s_2percent/cover/occupation.npy",
        #                                         eval_start=cfg.eval_start, eval_duration=cfg.eval_dur)

        # score = pipe.evalCTM(file_gt='../result/ctmResult/logs/ctm_test1/350_4200s_5percent/cover/ctm_gt.npy',
        #                      file_rec='../result/ctmResult/logs/ctm_test1/350_4200s_5percent/cover/ctm_rec.npy',
        #                      cell_json='../result/ctmResult/CTMcell_index.json',
        #                      eval_start=cfg.eval_start, eval_duration=cfg.eval_dur, method='mape')

        score = pipe.evalCTM(file_gt='../result/ctmResult/logs/ctm_test1/350_5400s_2percent/10000cover/ctm_gt.npy',
                             file_rec='../result/ctmResult/logs/ctm_test1/350_5400s_2percent/10000cover/ctm_rec.npy',
                             cell_json='../result/ctmResult/CTMcell_index.json',
                             eval_start=cfg.eval_start, eval_duration=cfg.eval_dur, method='mape', vis=False)

        print(score)
