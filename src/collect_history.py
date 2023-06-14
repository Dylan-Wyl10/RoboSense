"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the script that used to collect historical travel information for link travel modeling. The script will apply the following steps:
        1. Run the simulation.
        2. Count the link flow
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

from simulation import Simulation

if __name__ == '__main__':
    # argparser = argparse.ArgumentParser(description=__doc__)
    max_step = 36000  # define the maximum steps for the simulation
    path = "sumo_cfg/toy_net/toy_test.sumocfg"
    s = Simulation(max_time=30000, link_num=60, resolution=0.1, config=path)
    # s.sim()
    s.get_LF_table()
    # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    # start simulation

