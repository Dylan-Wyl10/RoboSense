"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the main script that simulates the CAV rerouting with TSC
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

if __name__ == '__main__':
    # argparser = argparse.ArgumentParser(description=__doc__)
    # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    # p_set = [100, 300, 500, 1000, 2000]
    p_set = [0, 100, 1000, 2000]
    pr = 2
    step = 20

    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('--net_dirc',
                           default='../sumo_cfg/5x5net',
                           type=str,
                           help='working dirctory for current simulation(sumo config)')
    argparser.add_argument('--maxtime',
                           default=4200,
                           type=int,
                           help='max simulation length(unit:s)')

    argparser.add_argument('--netname',
                           default='5x5net',
                           type=str,
                           help='network name used for configuration')

    args = argparser.parse_args()


    for p in p_set:
        save_info = {'cover_table': "../result/{}/PR{} TestingNew/pr{}_cover_{}_step{}.npy".format(args.netname, pr, pr, p, step),
                     'cover_table_benchmark': "../result/PR{} Testing/cover_table_benchmark.npy".format(pr)}

        path = "../sumo_cfg/{}/case{}.sumocfg".format(args.netname, p)
        lf_table_path = "../result/{}/link_flow/pr{}_link_flow_3600.json".format(args.netname, pr)
        s = Simulation(start_time=600, max_time=args.maxtime, link_num=40, resolution=0.1,
                       net_file='../sumo_cfg/5x5net/5x5net.net.xml',
                       time_interval=20, sizeX=5, sizeY=5)
        s.load_lf(lf_table_path)
        s.sim(save_info, path, parameters=(1, p), deroute_num=2, k=256)
        traci.close()
    # s.sim_benchmark(save_info)
