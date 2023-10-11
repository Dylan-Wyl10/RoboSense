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

    p_set = [0, 100, 300, 500, 1000, 2000]
    # p_set = [100, 1000, 2000]
    pr = 5
    step = 20

    for p in p_set:
        save_info = {'cover_table': "../result/PR{} TestingNew/pr{}_cover_{}_step{}.npy".format(pr, pr, p, step),
                     'cover_table_benchmark': "../result/PR{} Testing/cover_table_benchmark.npy".format(pr)}

        path = "sumo_cfg/toy_net/toy_test_{}.sumocfg".format(p)
        lf_table_path = "../result/link_flow/pr{}_link_flow_3600.json".format(pr)
        s = Simulation(max_time=3600, link_num=60, resolution=0.1,
                       net_file='sumo_cfg/toy_net/toy_net1.net.xml',
                       time_interval=step)
        s.load_lf(lf_table_path)
        s.sim(save_info, path, parameters=(1, p), deroute_num=2, k=256)
        traci.close()
    # s.sim_benchmark(save_info)
