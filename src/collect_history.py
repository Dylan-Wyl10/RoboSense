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
    path = "sumo_cfg/toy_net/toy_test.sumocfg"
    lf_table_path = "../result/link_flow_3600.json"
    s = Simulation(max_time=3600, link_num=60, resolution=0.1, config=path, time_interval=10, lfHisPath=lf_table_path)
    # s.sim()
    s.get_LF_table()
    print('yesyes')
    s.save_lf(lf_table_path)


    # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    # start simulation

