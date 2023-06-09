"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the main script that simulates the CAV rerouting with TSC
"""
# Status check for Sumo environment
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

import traci

if __name__ == '__main__':
    traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/dualogs/049/iteration_049.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    for i in range(36000):
        # print('yes')
        traci.simulationStep()
