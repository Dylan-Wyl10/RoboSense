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
    # detects = traci.inductionloop.getIDList()

    density = {}
    speed_mean = {}
    flow = {}

    # for det in detects:
    #     density[det] = []
    #     speed_mean[det] = []
    #     flow[det] = []

    for e in links:
        density[e] = []
        speed_mean[e] = []
        flow[e] = []

    while True:
        if (step % (time_interval * 10) == 0 and step > start_time/resolution):
            print('yes')

            # for det in detects:
            #     v_ids = traci.inductionloop.getIntervalVehicleIDs(det)
            #     t_head = traci.inductionloop.getTimeSinceDetection(det)
            #     speed_tmp = []
            #     occ = traci.inductionloop.getIntervalOccupancy(det)
            #
            #     if t_head != 0:
            #         density[det].append(10*occ/5)
            #         flow[det].append(3600/t_head)
            #     else:
            #         density[det].append(0)
            #         flow[det].append(0)


            for edge_id in links:
                v_ids = traci.edge.getLastStepVehicleIDs(edge_id)
                d_edge = len(v_ids)
                # density
                density[edge_id].append(d_edge)
            #     # mean speed
            #     speed_mean[edge_id].append(speed_all/d_edge if d_edge > 0 else 0)

        step += 1
        traci.simulationStep()

        # stop and save the results
        if step > (max_time/resolution) or (
                traci.simulation.getMinExpectedNumber() <= 10 and step > start_time):
            # path = save_path['cover_table_benchmark']
            densitydf = pd.DataFrame(density).T
            # speeddf = pd.DataFrame(speed_mean).T
            # flowdf = pd.DataFrame(flow).T
            # flowdf = densitydf*speeddf/0.08 # veh/hour

            # save the result
            densitydf.to_csv('../result/ctmResult/Linknumber_sim.csv')
            # speeddf.to_csv('../result/ctmResult/Linkspeed_sim.csv')
            # flowdf.to_csv('../result/ctmResult/Flow_sim.csv')
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
    args = [50, 2050, 0.1, 1,
            '../sumo_cfg/5x5net/simcfg/ctmbench.sumocfg',
            '../sumo_cfg/5x5net/5x5net.net.xml']
    # start time, max time, resolution, time interval, net configuration

    get_FD(args, GUImode=False)

#
