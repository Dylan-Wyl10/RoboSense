"""
Date: June 13, 2023
Author: Yilin Wang
Note: this script contains the source code for the class for simualtion. including the necessary methods to muliplate simulate and the defined space for variables .
Structures:
- Simulation
"""
from utili.tools import *
import traci
import re
import json


class Simulation:
    def __init__(self, max_time, link_num, resolution, config):
        self.time = None
        self.MAXSTEP = int(max_time / resolution)
        self.resolution = resolution
        self.link_flows_table = gen_LF_table(link_num)  # link flow table for all edges
        self.link_flows = {}
        self.config = config  # 06/14/2023: temporaryly set sumo config path

    def sim(self):
        traci.start(["sumo-gui", "-c", self.config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        for step in range(self.MAXSTEP):
            self.update_route()
            self.update_tsc()
            self.update_veh()
            step += 1
            self.time = step * self.resolution
            traci.simulationStep()
            if self.time >= 600:
                print("Simulation has ended due to max out")
                traci.close()

    def get_LF_table(self):
        traci.start(["sumo-gui", "-c", self.config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        # for step in range(self.MAXSTEP):
        while traci.simulation.getMinExpectedNumber() > 0:
            self.update_lf_table()
            # print(self.link_flows_table['E1'])
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            if traci.simulation.getMinExpectedNumber() <= 10:
                print("Simulation has ended due to no enough vehicle")
                self.filter_lf_table()
                traci.close()

    def update_lf_table(self):
        for k, v in self.link_flows_table.items():
            eg_id = traci.edge.getLastStepVehicleIDs(k)
            self.link_flows_table[k] = list(set(v) | set(eg_id))

    def filter_lf_table(self):
        """
        Note: this is the function is enumerate the lf table and remove cav information
        :param self.link_flow_table
        :return:
        """
        self.link_flows = {}
        for k, v in self.link_flows_table.items():
            for id in v:
                tmp = re.findall(r'[0-9]+|[a-z]+', id)
                if re.findall(r'[0-9]+|[a-z]+', id)[0] == 'cav':
                    v.remove(id)
            self.link_flows[k] = (3600 * len(v))/self.time
            """od_i, n = re.findall(r'[0-9]+|[a-z]+', id)  # od_idx, v_idx"""
            # v.append(ttmp)

    def update_route(self):
        return

    def update_tsc(self):
        return

    def update_veh(self):
        return

    def save_lf(self, path):  # save link flow table to file
        with open(path, "w") as outfile:
            json.dump(self.link_flows, outfile)

    def load_lf(self, path):
        with open(path, "r") as infile:
            self.link_flows = json.load(infile)

