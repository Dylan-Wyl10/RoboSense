"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the script that used to collect historical travel information for link travel modeling. The script will apply the following steps:
        1. Run the simulation.
        2. Count the link flow
"""
# Status check for Sumo environment
from simulation import Simulation
import sys
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
    max_step = 36000  # define the maximum steps for the simulation
    path = "sumo_cfg/toy_net/toy_test_benchmark.sumocfg"
    lf_table_savepath = "../result/link_flow/pr1_link_flow_3600.json"
    # s = Simulation(max_time=3600, link_num=60, resolution=0.1, config=path, time_interval=10, lfHisPath=lf_table_path)
    # s.sim()
    s = Simulation(max_time=3600, link_num=60, resolution=0.1,
                   net_file='sumo_cfg/toy_net/toy_net1.net.xml',
                   time_interval=20)
    s.get_LF_table(config=path)
    print('yesyes')
    s.save_lf(lf_table_savepath)


    # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    # start simulation

