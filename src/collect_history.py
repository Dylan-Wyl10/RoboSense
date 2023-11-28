"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the script that used to collect historical travel information for link travel modeling. The script will apply the following steps:
        1. Run the simulation.
        2. Count the link flow
"""
# Status check for Sumo environment
import traci

import argparse
from simulation import Simulation
import sys
import os
import os

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    os.environ['SUMO_HOME'] = '/usr/share/sumo'
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
    print('SUMO_HOME fixed')
    # sys.exit("please declare environment variable 'SUMO_HOME'")



if __name__ == '__main__':
    # argparser = argparse.ArgumentParser(description=__doc__)
    current_directory = os.getcwd()
    print(f"Current Working Directory: {current_directory}")

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

    max_step = 10 * args.maxtime  # define the maximum steps for the simulation
    path = args.net_dirc + ("/simcfg/benchmark.sumocfg")
    pr = 5
    lf_table_savepath = "../result/{}/link_flow/pr{}_link_flow_3600.json".format(args.netname, pr)
    save_info = {'cover_table_benchmark': "../result/{}/PR5 TestingNew/pr5_cover_benchmark.npy".format(args.netname)}

    s = Simulation(start_time=600, max_time=args.maxtime, link_num=40, resolution=0.1,
                   net_file='../sumo_cfg/5x5net/5x5net.net.xml',
                   time_interval=20, sizeX=5, sizeY=5)
    s.get_LF_table(config=path)
    s.save_lf(lf_table_savepath)
    print('lf table has been saved')
    traci.close()
    s.sim_benchmark(save_info, config=path)


    # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    # start simulation

