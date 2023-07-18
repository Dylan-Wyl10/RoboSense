"""
Date: May 26, 2023
Author: Yilin Wang
Note: this script is the script that used to collect historical travel information for link travel modeling. The script will apply the following steps:
        1. Run the simulation.
        2. Count the link flow
"""
# Status check for Sumo environment
import traci

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
    lf_table_savepath = "../result/link_flow/link_flow_3600.json"
    save_info = {'cover_table': "../result/PR2 Testing/cover_2000_step20.npy",
                 'cover_table_benchmark': "../result/PR2 Testing/cover_table_benchmark1.npy"}

    s = Simulation(max_time=3600, link_num=60, resolution=0.1,
                   net_file='sumo_cfg/toy_net/toy_net1.net.xml',
                   time_interval=20)
    s.get_LF_table(config=path)
    s.save_lf(lf_table_savepath)
    print('lf table has been saved')
    traci.close()
    s.sim_benchmark(save_info)


    # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])

    # start simulation

