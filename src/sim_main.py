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

    path = "sumo_cfg/toy_net/toy_test.sumocfg"
    s = Simulation(max_time=3600, link_num=60, resolution=0.1, config=path, time_interval=10)
    s.sim()

    for i in range(36000):
        # print('yes')
        traci.simulationStep()
