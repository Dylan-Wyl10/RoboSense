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
from itertools import groupby



class Simulation:
    def __init__(self, start_time, max_time, link_num, resolution, net_file, time_interval, sizeX, sizeY):
        self.step = 0
        self.time = 0
        self.start_time = start_time
        self.time_interval = time_interval
        self.max_time = max_time
        self.MAXSTEP = int(max_time / resolution)
        self.resolution = resolution
        self.link_num = link_num
        self.link_flows_table = gen_LF_table(link_num)  # link flow table for all edges
        self.link_flows_num = {}
        self.link_flows_observation = {}
        # self.config = config  # 06/14/2023: temporaryly set sumo config path
        self.Network = Network(5, 5, net_file)
        self.cav_list = []
        self.cover_LinkTimeVeh = np.zeros((2*link_num, 7000, 500))  # index = [link, time, veh], value is hardcoded as 0 (binary)
        self.sizeX, self.sizeY = sizeX, sizeY
        # # build a time-space table for vehicle index
        # self.cover_idTable = []
        # for i in range(self.cover_LinkTimeVeh.shape[0]):
        #     t = []
        #     for j in range(self.cover_LinkTimeVeh.shape[1]):
        #         t.append([])
        #     self.cover_idTable.append(t)
        # self.cover_idTable = np.array(self.cover_idTable)
        self.cav_route = {}

    def sim(self, save_path, config, parameters, flex=0, k=32):
        traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.flex = flex  # default flexibility of the vehicle
        self.time = 0  # simulation time index
        self.step = 0
        self.Network.netInit(self.sizeX, self.sizeY)

        # initial the cav list
        self.cav_dic = {}
        # self.link_flows_table = self.link_flows_hisNum  # get history link-flow table
        while True:

            # the following steps only apply in a GIVEN TIME Interval
            if self.step % (self.time_interval * 10) == 0:
            # step1: update cav dictionary information, add new and remove completed cav
                self.updateCAVinfo()

            # step2: enumerate all cav from list, choose proper route and update vehicle information
            # if self.step % (self.time_interval * 10) == 0:  # plan for the start of every time interval
                self.getCAVctrlList()
                print('step is:', self.step, parameters[1])
                # -steps:
                # -2A: enumerate all cav. for each cav.
                #       -2AA: get k-shortest path considering distance
                #       -2AB: calculate travel time and cover rate for each candidate route
                #       -2AC: choose the best route and apply accordingly
                #       -2AD: update CAV routing table
                # $$$$$$$$$$$$$$$$$$$$$$$$$$
                # 1103 update: update the path selection logic:
                # current flexibility = original sp length + flexibility - number of edges traveled - current sp length
                # self.getVecFlex()
                self.updateRoute(k, parameters)

                """
                # stepXXXX: (this will be added on next): adjust signal time plan. 
                self.update_tsc()
                self.update_veh()
                """
            # step3: update observation information every 1 second
            if self.step % 10 == 0:
                # self.getCAVctrlList()
                # update observation
                self.updateObsv()
                self.checkCoverTable()
            # step4: push simulation and update information
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()

            # stop and save the results
            # if self.step > self.MAXSTEP and traci.simulation.getMinExpectedNumber() <= 10:
            if self.step > self.MAXSTEP or (traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):

                path = save_path['cover_table{}'.format(parameters[1])]
                np.save(path, self.cover_LinkTimeVeh[:, self.start_time:self.max_time, :])
                print("Simulation has ended due to no enough vehicle")
                break

    def sim_benchmark(self, save_path, config="../sumo_cfg/5x5net/benchmark.sumocfg"):
        traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        self.step = 0
        self.Network.netInit(self.sizeX, self.sizeY)
        # self.link_flows_table = self.link_flows_hisNum  # get history link-flow table
        while True:

            # collect CAV infor evry 1 second == 10s
            if self.step % 10 == 0:
                # self.getCAVctrlList()
                # update observation
                self.updateObsv()
                self.checkCoverTable()

            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            # stop and save the results
            if self.step > self.MAXSTEP or (traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                path = save_path['cover_table_benchmark']
                np.save(path, self.cover_LinkTimeVeh)
                print("Simulation has ended due to no enough vehicle")
                break

    # 06/18/2023 get historical link flow table through simulation
    def get_LF_table(self, config):
        traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        # for step in range(self.MAXSTEP):
        while True:
            if self.time > self.start_time:
                self.update_lf_table()
            # print(self.link_flows_table['E1'])
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            if self.step > self.MAXSTEP or (traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                # if self.step > self.MAXSTEP:
                print("Simulation has ended due to no enough vehicle")
                self.filter_lf_table()
                break

    # get list that will plan in this step
    def getCAVctrlList(self):
        self.cav_list = []
        for v_id in traci.vehicle.getIDList():
            if re.findall(r'[0-9]+|[a-z]+', v_id)[0] == "cav" and traci.vehicle.getLanePosition(v_id) < 350:# type and no changing zone constrain
                edge_id = traci.vehicle.getRoadID(v_id)
                if edge_id[0] == 'E' or int(re.findall(r'[0-9]+|[a-z]+', edge_id)[0]) <= self.link_num:
                    # print(edge_id)
                    self.cav_list.append(v_id)  # return the cav list that needs to be controlled


    # def getVecFlex(self):
    #     """
    #     calculate cav flexibility through cav information dictionary.
    #     1103 update: current flexibility = original sp length + flexibility - number of edges traveled - current sp length
    #
    #     """
    #
    #     for cav_id in self.cav_list:
    #         # tmp_route = ('E5', 'E26', 'E10', 'E31', 'E15', 'E36', 'E20', '-E112')
    #         # traci.vehicle.setRoute(cav_id, tmp_route)
    #         orig_node = self.Network.getNextNode(traci.vehicle.getRoute(cav_id)[0])
    #         des_node = self.Network.getFromNode(traci.vehicle.getRoute(cav_id)[-1])
    #
    #
    #         tmp = traci.vehicle.getRoute(cav_id)
    #         print(tmp)


    def updateObsv(self):
        """
        06/22/2023 update: use this function to check observation and cover time-space table
        step2: check observation and update link-flow table (value only); then the output also calculate
        link-cost with observed data or historical data
        self.link_flows_table = current link-flow information
        :return:
        """
        time_idx = round(self.time)
        for edge in traci.edge.getIDList():
            edge_idx = int(re.findall(r'[0-9]+|[a-z]+', edge)[0]) - 1
            # vv_id = traci.edge.getLastStepVehicleIDs(edge)
            # if time_idx == 40:
            #     print('llll')
            if edge_idx < self.link_num:
                v_id = traci.edge.getLastStepVehicleIDs(edge)  # vehicle id list
                for v in v_id:
                    v_tem = re.findall(r'[0-9]+|[a-z]+', v)  # [type, num]
                    if v_tem[0] == 'cav':
                        cav_idx = int(v_tem[1]) # cav index = cav numbber - 1
                        for eID in range(self.cover_LinkTimeVeh.shape[0]):
                            self.cover_LinkTimeVeh[eID, time_idx, cav_idx] = 0 # clear current edge occupation before update
                        if edge[0] == '-':
                            self.cover_LinkTimeVeh[edge_idx + self.link_num, time_idx, cav_idx] = 1
                        else:
                            self.cover_LinkTimeVeh[edge_idx, time_idx, cav_idx] = 1

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
            self.link_flows_num[k] = (3600 * len(v)) / (self.time - self.start_time)
            """od_i, n = re.findall(r'[0-9]+|[a-z]+', id)  # od_idx, v_idx"""
            # v.append(ttmp)

    def updateCAVinfo(self):
        for v_id in traci.vehicle.getIDList():
            if traci.vehicle.getTypeID(v_id) == 'cav':
                vidx = int(re.findall(r'[0-9]+|[a-z]+', v_id)[1])
                if v_id not in self.cav_dic:
                    # default add vehicle
                    sp_length = self.Network.getShortDistance(self.Network.getNextNode(traci.vehicle.getRoute(v_id)[0]), self.Network.getFromNode(traci.vehicle.getRoute(v_id)[-1]))
                    self.cav_dic[v_id] = {'original': self.Network.getNextNode(traci.vehicle.getRoute(v_id)[0]),
                                          'destination': self.Network.getFromNode(traci.vehicle.getRoute(v_id)[-1]),
                                          'currentFlex': self.flex,  # initial flexibility, must be even number
                                          'spLength': sp_length,
                                          'currentRoute': []}
                else:
                    # calculate and update current flexibility
                    veh_cover = self.cover_LinkTimeVeh[:, :, vidx]
                    links, time = veh_cover.shape
                    tmp = []
                    for t in range(time):
                        for l in range(links):
                            if veh_cover[l, t] == 1:
                                tmp.append(l + 1)  # sumo link index starts from 1 while matrix starts form zero
                                # combined_paths[vehicle][scenario_index].append(link)
                    route_tmp = [key for key, group in groupby(tmp)]
                    self.cav_dic[v_id]['currentRoute'] = route_tmp
                    edge_current = traci.vehicle.getRoadID(v_id)
                    # edgelink_idx = int(re.findall(r'[0-9]+|[a-z]+', '-E22')[0])
                    if edge_current[0] != '-':
                        nextNode_tmp = self.Network.getNextNode(edge_current)
                        sp_current = self.Network.getShortDistance(nextNode_tmp, self.cav_dic[v_id]['destination'])

                        # 1103 update: current flexibility = original sp length + flexibility - number of edges traveled - current sp length
                        tmp_flex = self.cav_dic[v_id]['spLength'] + self.cav_dic[v_id]['currentFlex'] - len(route_tmp) - sp_current
                        self.cav_dic[v_id]['currentFlex'] = max(tmp_flex, 0)
                        print(f'vehicle {v_id} has flex {self.cav_dic[v_id]["currentFlex"]}')


    def updateRoute(self, k, parameters):
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
            # print(f'current veh idx is {cav_id} in a list of {self.cav_list}')
            # 1.get k shortest path considering distance
            veh_idx = int(re.findall(r'[0-9]+|[a-z]+', cav_id)[1])  # [num = actual number -1]
            cav_edgeID = traci.vehicle.getRoadID(cav_id)
            my_nextNode = self.Network.getNextNode(cav_edgeID)
            my_desNode = self.Network.getFromNode(traci.vehicle.getRoute(cav_id)[-1])

            k_shortest_path = self.Network.findKShortPath(k, my_nextNode, self.cav_dic[cav_id]['destination'], self.cav_dic[cav_id]['currentFlex'])

            # 0710: get vehicle departure time
            # tmp = traci.vehicle.getDeparture(cav_id)
            dep_time = traci.vehicle.getDeparture(cav_id) # get departure time

            # 2. calculate travel time and cover rate for each candidate route
            # 3. get delta_cover for each candidate path
            arrive_time_table = []  # store the node arrive time for each path selection
            delta_cover_table = []  # store the change of cover rate for each candidate path
            path_obj_table = []  # store the object value for each candidate path

            # objective value for last candidate path, since the objective is to get max, the default number is -1000000.
            last_bestRoute_obj = -10000


            # print(f'check cover table at start of {cav_id} at time {self.time}')
            # self.checkCoverTable()

            # enumerate all candidate path
            for sp in k_shortest_path:
                # remove future route
                for l in range(self.cover_LinkTimeVeh.shape[0]):
                    for t in range(int(self.time), self.cover_LinkTimeVeh.shape[1]):
                        self.cover_LinkTimeVeh[l, t, veh_idx] = 0
                # print(f'begin to check if cover table is cleared for vehicle {cav_id} at time {self.time} on path {sp}')
                self.checkCoverTable()
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

                # 0630update: 4. We need to remove the current veh from current time to the future.

                # this is the end of arrive time calculation, next is the change of cover rate
                # cover_ts_pre = copy.deepcopy(self.cover_LinkTimeVeh)  # get a tmp matrix to calculate cover
                # cover_ts_pre = np.copy(self.cover_LinkTimeVeh)

                node_timeTmp = copy.deepcopy(node_time)
                node_timeTmp.insert(0, self.time)

                route_startTime = round(node_timeTmp[0])
                route_endTime = round(node_timeTmp[-1])
                duration = route_endTime - route_startTime
                # predicted cover rate for given route,  this is temp data point
                cover_ts_pre = np.copy(self.cover_LinkTimeVeh[:, route_startTime: route_endTime, :])

                for idx in range(len(route[:-1])):
                    edge_idx_num = int(re.findall(r'[0-9]+|[a-z]+', route[:-1][idx])[0])
                    if edge_idx_num < self.link_num + 1:
                        # # determine the start and end time point for each occupation
                        # start_idx = node_timeTmp[1]
                        # end_idx = int(node_timeTmp[2])
                        if route[:-1][idx][0] == '-':
                            link_pos = edge_idx_num + self.link_num  # determine the link idx in cover time-space table
                        else:
                            link_pos = edge_idx_num
                        for k in range(round(node_timeTmp[idx]) - int(node_timeTmp[0]), round(node_timeTmp[idx + 1]) - int(node_timeTmp[0])):
                            # print(k)
                            cover_ts_pre[link_pos - 1, k-1, veh_idx] = 1

                # get the time-space cover table
                cover_pre = np.where(np.sum(cover_ts_pre, axis=2) > 0, 1, 0)
                cover_now = np.where(np.sum(self.cover_LinkTimeVeh[:, route_startTime: route_endTime, :], axis=2) > 0, 1, 0)

                cover_delta = (np.sum(cover_pre) - np.sum(cover_now)) / duration
                delta_cover_table.append(cover_delta)

                # 4. calculate objective and get best route, update the routing based on best objective
                #  0710 YW: update objective considering total travel time instead of current steps.
                current_route_obj = - parameters[0] * (node_time[-1] - dep_time) + parameters[1] * cover_delta
                path_obj_table.append(current_route_obj)
                if current_route_obj > last_bestRoute_obj:
                    self.cover_LinkTimeVeh[:, route_startTime: route_endTime, :] = cover_ts_pre
                    best_route_node = sp  # get best route idx and path(node)
                    best_route = [cav_edgeID]

                    # convert node path to edge path
                    for node_idx in range(len(best_route_node) - 1):
                        node2edge = self.Network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                            best_route_node[node_idx])
                        best_route.append(node2edge)
                    best_route.append(traci.vehicle.getRoute(cav_id)[-1])
                    traci.vehicle.setRoute(cav_id, best_route)
                    last_bestRoute_obj = current_route_obj
                del cover_ts_pre, cover_pre
            # print('yes')
        # return

    def save_lf(self, path):  # save link flow table to file, this is designed for history collection
        with open(path, "w") as outfile:
            json.dump(self.link_flows_num, outfile)
            print('nn')

    def load_lf(self, path):  # this load link flow history
        with open(path, "r") as infile:
            self.link_flows_hisNum = json.load(infile)


    ###20231011: some debug tools
    def checkCoverTable(self):
        # cover table  = [edge, time, veh]
        v_idx = traci.vehicle.getIDList()
        for v in v_idx:
            v_tem = re.findall(r'[0-9]+|[a-z]+', v)  # [type, num]
            if v_tem[0] == 'cav':
                cav_idx = int(v_tem[1]) - 1
                tableLinkTime = self.cover_LinkTimeVeh[:, :, cav_idx]
                for t in range(tableLinkTime.shape[1]):
                    # print(np.sum(tableLinkTime[:, t]))
                    if np.sum(tableLinkTime[:, t]) > 1:
                        print(f"Vehicle {cav_idx+1} is more than one pos at time {t}, current time is {self.time}:")




