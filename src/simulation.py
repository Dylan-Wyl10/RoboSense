"""
Date: June 13, 2023
Author: Yilin Wang
Note: this script contains the source code for the class for simualtion. including the necessary methods to muliplate simulate and the defined space for variables .
Structures:
- Simulation
"""
from utili.tools import *
from utili.vehicle import *
from utili.network import Graph
import traci
import re
import json


class Simulation:
    def __init__(self, max_time, link_num, resolution, config, lfHisPath, time_interval):
        self.step = 0
        self.time = 0
        self.time_interval = time_interval
        self.MAXSTEP = int(max_time / resolution)
        self.resolution = resolution
        self.link_flows_table = gen_LF_table(link_num)  # link flow table for all edges
        self.link_flows = {}
        self.config = config  # 06/14/2023: temporaryly set sumo config path
        self.time_interval = 10  # 06/18/2023: plan cav route in every 10s
        self.Graph = Graph(6, 6)
        self.cav_list = []
        self.load_lf(lfHisPath)  # 06/18/2023: load link-flow table from given path

    def sim(self):
        traci.start(["sumo-gui", "-c", self.config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        self.step = 0
        while True:
            # the following steps only apply in a GIVEN TIME Interval
            if self.time % self.time_interval == 0:  # plan for the start of every time interval
                # step1: get cav information from the network, update cav list
                self.getCAVinfo()

                # step2: check observation and update link-flow table (value only); then the output also caculate
                # link-cost with observed data or historical data
                self.updateNetwork()

                # step3: enumerate all cav from list, choose proper route and update vehicle information
                # -steps:
                # -3A: enumerate all cav that close enough to the intersection, get k-shortest path
                # -3B: calculate cover rate in next 2 time interval, the inputs are signal timing plan and given k-sp
                # -3C: choose the best route and apply accordingly
                self.update_route()

                """
                # stepXXXX: (this will be added on next): adjust signal time plan. 
                self.update_tsc()
                self.update_veh()
                """
            # step4: push simulation and update information
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            if self.step > self.MAXSTEP and traci.simulation.getMinExpectedNumber() <= 10:
                print("Simulation has ended due to no enough vehicle")
                break

    # 06/18/2023 get historical link flow table through simulation
    def get_LF_table(self):
        traci.start(["sumo-gui", "-c", self.config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        # for step in range(self.MAXSTEP):
        while True:
            self.update_lf_table()
            # print(self.link_flows_table['E1'])
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            if self.step > self.MAXSTEP and traci.simulation.getMinExpectedNumber() <= 10:
                # if self.step > self.MAXSTEP:
                print("Simulation has ended due to no enough vehicle")
                self.filter_lf_table()
                break

    def getCAVinfo(self):
        self.cav_list = []
        for v_id in traci.vehicle.getIDList():
            if re.findall(r'[0-9]+|[a-z]+', v_id)[0] == "cav":
                self.cav_list.append(v_id)

    def updateNetwork(self):
        """
        step2: check observation and update link-flow table (value only); then the output also calculate
        link-cost with observed data or historical data
        :return:
        """


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
            self.link_flows[k] = (3600 * len(v)) / self.time
            """od_i, n = re.findall(r'[0-9]+|[a-z]+', id)  # od_idx, v_idx"""
            # v.append(ttmp)

    def update_route(self):
        return

    def update_tsc(self):
        return

    def update_veh(self):
        return

    def save_lf(self, path):  # save link flow table to file, this is designed for history collection
        with open(path, "w") as outfile:
            json.dump(self.link_flows, outfile)
            print('nn')

    def load_lf(self, path):
        with open(path, "r") as infile:
            self.link_flows = json.load(infile)
