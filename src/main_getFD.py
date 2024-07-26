"""
Date: July 23, 2024
Author: Yilin Wang
Note: Use this script to get the fundemental diagram from the SUMO environment.
"""
import pandas as pd
# Status check for Sumo environment
import traci

import argparse
from simulation import Simulation
import sys
import os
import os

def get_FD(sim_args, GUImode=False):
    start_time, max_time, resolution, time_interval, sumo_config, net_file = sim_args
    if GUImode:
        traci.start(["sumo-gui", "-c", sumo_config, "--lateral-resolution=0.1",
                     "--step-length={}".format(resolution)])
    else:
        traci.start(["sumo", "-c", sumo_config, "--lateral-resolution=0.1",
                     "--step-length={}".format(resolution)])

    step = 0

    links = traci.edge.getIDList()

    density = {}
    speed_mean = {}
    flow = {}

    for edge in links:
        density[edge] = []
        speed_mean[edge] = []
        flow[edge] = []

    while True:
        if (step % (time_interval * 10) == 0 and step > start_time/resolution):
            print('yes')
            for edge_id in links:
                # density
                density[edge_id].append(traci.edge.getLastStepVehicleNumber(edge_id))
                # mean speed
                speed_mean[edge_id].append(traci.edge.getLastStepMeanSpeed(edge_id))
                # flow rate
                flow[edge_id].append(len(traci.edge.getLastStepVehicleIDs(edge_id)))
        step += 1
        traci.simulationStep()

        # stop and save the results
        if step > (max_time/resolution) or (
                traci.simulation.getMinExpectedNumber() <= 10 and step > start_time):
            # path = save_path['cover_table_benchmark']
            densitydf = pd.DataFrame(density).T
            speeddf = pd.DataFrame(speed_mean).T
            flowdf = densitydf*speeddf/0.08 # veh/hour

            # save the result
            densitydf.to_csv('../result/ctmResult/Linknumber_sim.csv')
            speeddf.to_csv('../result/ctmResult/Linkspeed_sim.csv')
            flowdf.to_csv('../result/ctmResult/Flow_sim.csv')
            print("Sim has ended due to no enough vehicle")
            break




if __name__ == '__main__':
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        os.environ['SUMO_HOME'] = '/usr/share/sumo'
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
        print('SUMO_HOME fixed')

    # add configurations
    args = [600, 2400, 0.1, 1,
            '../sumo_cfg/5x5net/simcfg/benchmark.sumocfg',
            '../sumo_cfg/5x5net/5x5net.net.xml']
    # start time, max time, resolution, time interval, net configuration

    get_FD(args, GUImode=False)


#
#     max_step = 10 * args.maxtime  # define the maximum steps for the simulation
#     path = args.net_dirc + ("/simcfg/benchmark.sumocfg")
#     pr = 5
#     lf_table_savepath = "../result/{}/link_flow/pr{}_link_flow_3600.json".format(args.netname, pr)
#     save_info = {'cover_table_benchmark': "../result/{}/PR5 TestingNew/pr5_cover_benchmark.npy".format(args.netname)}
#
#     s = Simulation(start_time=600, max_time=args.maxtime, link_num=40, resolution=0.1,
#                    net_file='../sumo_cfg/5x5net/5x5net.net.xml',
#                    time_interval=20, sizeX=5, sizeY=5)
#     # s.get_LF_table(config=path)
#     # s.save_lf(lf_table_savepath)
#     print('lf table has been saved')
#     # traci.close()
#     s.sim_getBench(save_info, config=path)
#
#
#     # traci.start(["sumo-gui", "-c", "sumo_cfg/toy_net/toy_test.sumocfg", "--lateral-resolution=0.1", "--step-length=0.1"])
#
#     # start simulation
#
