"""
Date: June 13, 2023
Author: Yilin Wang
Note: this script contains the source code for the class for simualtion. including the necessary methods to muliplate simulate and the defined space for variables .
Structures:
- Simulation
"""

import copy
import numpy as np

from utili.tools import *
from utili.vehicle import *
from utili.network import Network
import traci
import re
import json


class Simulation:
    def __init__(self, max_time, link_num, resolution, config, lfHisPath, net_file, time_interval):
        self.step = 0
        self.time = 0
        self.time_interval = time_interval
        self.MAXSTEP = int(max_time / resolution)
        self.resolution = resolution
        self.link_flows_table = gen_LF_table(link_num)  # link flow table for all edges
        self.link_flows_num = {}
        self.link_flows_observation = {}
        self.config = config  # 06/14/2023: temporaryly set sumo config path
        self.time_interval = 10  # 06/18/2023: plan cav route in every 10s
        self.Network = Network(6, 6, net_file)
        self.cav_list = []
        self.load_lf(lfHisPath)  # 06/18/2023: load link-flow table from given path
        self.cover_timeSpace = np.zeros((120, 20000))  # hardcoding binary space for cover rate

    def sim(self):
        traci.start(["sumo-gui", "-c", self.config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        self.step = 0
        self.Network.netInit(6, 6)
        # self.link_flows_table = self.link_flows_hisNum  # get history link-flow table
        while True:
            # the following steps only apply in a GIVEN TIME Interval
            # step1: get cav information from the network, update cav list
            if self.step % 10 == 0:
                self.getCAVinfo()
                # update observation
                self.updateObsv()

            # step2: enumerate all cav from list, choose proper route and update vehicle information
            if self.step % (self.time_interval * 10) == 0:  # plan for the start of every time interval

                # -steps:
                # -2A: enumerate all cav. for each cav.
                #       -2AA: get k-shortest path considering distance
                #       -2AB: calculate travel time and cover rate for each candidate route
                #       -2AC: choose the best route and apply accordingly
                #       -2AD: update CAV routing table
                self.updateRoute()

                # # step2: check observation and update link-flow table (value only); then the output also calculate
                # # link-cost with observed data or historical data
                # self.updateNetwork()

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
            edge_id = traci.vehicle.getRoadID(v_id)
            if re.findall(r'[0-9]+|[a-z]+', v_id)[0] == "cav" and int(re.findall(r'[0-9]+|[a-z]+', edge_id)[0]) <= 60:
                self.cav_list.append(v_id)
                # print(v_id, self.step, traci.vehicle.getRoadID(v_id))

    def updateObsv(self):
        """
        06/22/2023 update: use this function to check observation and cover time-space table
        step2: check observation and update link-flow table (value only); then the output also calculate
        link-cost with observed data or historical data
        self.link_flows_table = current link-flow information
        :return:
        """
        # for k, v in self.link_flows_table.items():
        #     self.link_flows_observation[k] = 0  # get history link-flow table
        for cav_id in self.cav_list:
            cav_edge = traci.vehicle.getRoadID(cav_id)
            link_idx = re.findall(r'[0-9]+|[a-z]+', cav_edge)
            if int(link_idx[0]) <= 60:
                # self.link_flows_observation[cav_edge] = 1
                time_idx = round(self.time)
                if cav_edge[0] == '-':
                    self.cover_timeSpace[int(link_idx[0]) + 59, time_idx] = 1
                else:
                    self.cover_timeSpace[int(link_idx[0]) -1 , time_idx] = 1

        # 06/20/2023_Notes: self.link_flow_table is realtime updated table, this still have
        # problem for this case.
        # self.Graph.updateIntersection(self.link_flows_table)

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
        self.link_flows_num = {}
        for k, v in self.link_flows_table.items():
            for id in v:
                if re.findall(r'[0-9]+|[a-z]+', id)[0] == 'cav':
                    v.remove(id)
            self.link_flows_num[k] = (3600 * len(v)) / self.time
            """od_i, n = re.findall(r'[0-9]+|[a-z]+', id)  # od_idx, v_idx"""
            # v.append(ttmp)

    def updateRoute(self, k=32, parameters=(1, 1000)):
        """
        step2: enumerate all cav from list, choose proper route and update vehicle information
                # -steps:
                # -2A: enumerate all cav. for each cav.
                #       -2AA: get k-shortest path considering distance
                #       -2AB: calculate travel time and cover rate for each candidate route
                #       -2AC: choose the best route and apply accordingly
                #       -2AD: update CAV routing table
        :return:
        """
        for cav_id in self.cav_list:
            # 1.get k shortest path considering distance
            cav_edgeID = traci.vehicle.getRoadID(cav_id)
            my_nextNode = self.Network.getNextNode(cav_edgeID)
            my_desNode = self.Network.getLastNode(traci.vehicle.getRoute(cav_id)[-1])
            # if my_desNode == 'AD_1' or my_desNode == 'AD_1':
            #     print(cav_id, cav_edgeID)
            #     print("@@@@@@@@@@@")
            print(cav_id, my_nextNode, my_desNode)
            k_shortest_path = self.Network.findKShortPath(k, my_nextNode, my_desNode)

            # 2. calculate travel time and cover rate for each candidate route
            # 3. get delta_cover for each candidate path
            arrive_time_table = []  # store the node arrive time for each path selection
            delta_cover_table = []  # store the change of cover rate for each candidate path
            for sp in k_shortest_path:
                route = [cav_edgeID]
                for node_idx in range(len(sp) - 1):
                    node2edge = self.Network.node_list[sp[node_idx + 1]].getEdgeByUpperNode(sp[node_idx])
                    route.append(node2edge)
                route.append(traci.vehicle.getRoute(cav_id)[-1])
                """
                06/21/2023: 
                - until now, <tmp> & <sp> has been DUIQI !!!
                - next step is to calculate arrival time for each node in sp with route[:-1]
                - another input is an if table about if the edge is observed currently
                """
                node_time = self.Network.getNodeArrTime(route[:-1], sp, self.time, cav_id,
                                                        self.link_flows_hisNum)  # arrive time on each node for given path route
                arrive_time_table.append(node_time[-1])

                # this is the end of arrive time calculation, next is the change of cover rate
                cover_ts_pre = copy.deepcopy(self.cover_timeSpace)  # get a tmp matrix to calculate cover
                for idx in range(len(route[:-1])):
                    node_timeTmp = copy.deepcopy(node_time)
                    node_timeTmp.insert(0, self.time)
                    edge_idx_num = int(re.findall(r'[0-9]+|[a-z]+', route[:-1][idx])[0])
                    if edge_idx_num <= 60:
                        # # determine the start and end time point for each occupation
                        # start_idx = node_timeTmp[1]
                        # end_idx = int(node_timeTmp[2])
                        if route[:-1][idx][0] == '-':
                            link_pos = edge_idx_num + 60  # determine the link idx in cover time-space table
                        else:
                            link_pos = edge_idx_num
                        for k in range(round(node_timeTmp[idx]), round(node_timeTmp[idx + 1])):
                            cover_ts_pre[link_pos - 1, k] = 1
                # calculate cover rate from NEXT NODE to the END
                duration = round(node_time[-1]) - round(node_time[0])
                cover_delta = (np.sum(cover_ts_pre) - np.sum(self.cover_timeSpace)) / duration
                delta_cover_table.append(cover_delta)

            # 4. calculate objective and get best route, update the routing prediction table
            path_obj_table = copy.deepcopy(delta_cover_table)
            for i in range(len(arrive_time_table)):
                path_obj_table[i] = - parameters[0] * arrive_time_table[i] + parameters[1] * delta_cover_table[i]
            best_route_node = k_shortest_path[path_obj_table.index(max(path_obj_table))]
            best_route = [cav_edgeID]
            for node_idx in range(len(best_route_node) - 1):
                node2edge = self.Network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(best_route_node[node_idx])
                best_route.append(node2edge)
            best_route.append(traci.vehicle.getRoute(cav_id)[-1])
            traci.vehicle.setRoute(cav_id, best_route)
            # print('lplpl')
        # traci.vehicle.setRoute(cav_id, route)
        # tmp = self.Network.getNextNode('E1')
        return

    def save_lf(self, path):  # save link flow table to file, this is designed for history collection
        with open(path, "w") as outfile:
            json.dump(self.link_flows_num, outfile)
            print('nn')

    def load_lf(self, path):  # this load link flow history
        with open(path, "r") as infile:
            self.link_flows_hisNum = json.load(infile)
