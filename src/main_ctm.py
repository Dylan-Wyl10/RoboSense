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

# Make both the project root and src/ importable (PyCharm-style), matching
# src/data_analysis/*_rerun.py. utili/network.py imports `src.utili.ctm...`
# absolutely, so the project root must be on sys.path or running this file
# directly from src/ fails with ModuleNotFoundError: No module named 'src'.
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_FOR_IMPORTS = os.path.dirname(SRC_DIR)
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PROJECT_ROOT_FOR_IMPORTS)

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

    # if cfg.is_vislz:
    #     pipe.ctmPlot(ctm_value="../result/ctmResult/logs/ctm_test1/test4200s_5percent/occupation_4200s_400flow_5percent_bench.npy",
    #              cell_list=cellidx,
    #              cell_coordinates='../sumo_cfg/5x5net/CTMcfg/Cells.csv',
    #              title_str="11111",
    #              plot=cfg.plot_mode,  # [video, figure]
    #              )


    if cfg.is_sim:
        sim = Simulation(start_time=600, max_time=cfg.sumo_maxtime, link_num=40, resolution=0.1,
                     net_file=cfg.net_file, time_interval=5, sizeX=5, sizeY=5,
                     link_dirct_file=cfg.link_node_dirct_file,
                     demand_file=cfg.demand_file,
                     turn_rate=cfg.turn_rate)

        sim.simCTM(config=cfg.sumo_cfg, param=cfg.param, ctm_fd=cfg.ctm_fd, ctm_interval=cfg.ctm_interval,
                   ctm_time_opt=cfg.ctm_time_opt, ctm_time_norm=cfg.ctm_time_normal, ctm_demand_mode=cfg.is_real_demand,
                   optim_interval=cfg.opt_interval, saving_path=cfg.saving_path, GUImode=cfg.sumo_gui, route=cfg.is_route,
                   bench_mode=cfg.is_bench, coverage_objective=cfg.coverage_objective)

        # score = pipe.evalCTM(file_gt='../src/ctm_gt.npy',
        #                      file_rec='../src/ctm_rec.npy',
        #                      cell_json='../result/ctmResult/CTMcell_index.json',
        #                      eval_start=cfg.eval_start, eval_duration=cfg.eval_dur, method='mape')
    if cfg.ctm_cali:
        sim = Simulation(start_time=600, max_time=cfg.sumo_maxtime, link_num=40, resolution=0.1,
                         net_file=cfg.net_file, time_interval=5, sizeX=5, sizeY=5,
                         link_dirct_file=cfg.link_node_dirct_file,
                         demand_file=cfg.demand_file,
                         turn_rate=cfg.turn_rate)
        sim.calibrateCTM(ctm_fd=cfg.ctm_fd, ctm_interval=cfg.ctm_interval,
                         cell_json="../result/ctmResult/CTMcell_index.json",
                         sumo_config=cfg.sumo_cfg,
                         saving_path=cfg.saving_path, ctm_demand_mode=cfg.is_real_demand)
