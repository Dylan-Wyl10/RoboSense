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

    save_info = {'cover_table': "../result/cover_1000_step20.npy",
                        'cover_table_benchmark': "../result/cover_table_benchmark.npy"}

    path = "sumo_cfg/toy_net/toy_test.sumocfg"
    lf_table_path = "../result/link_flow/link_flow_3600.json"
    s = Simulation(max_time=3600, link_num=60, resolution=0.1,
                            net_file='sumo_cfg/toy_net/toy_net1.net.xml',
                            time_interval=20, lfHisPath=lf_table_path)
    s.sim(save_info, path, parameters=(1, 1000), k=256)
    # s.sim_benchmark(save_info)

