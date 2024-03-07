"""
Date: June 13, 2023
Author: Yilin Wang
Note: this script contains the source code for the class for simualtion. including the necessary methods to muliplate simulate and the defined space for variables .
Structures:
- CTMSim
"""

import copy

from utili.tools import *
from utili.network import Network
import traci
import json
from src.utili.ctm.ctmcomponent import *


class Simulation:
    def __init__(self, start_time, max_time, link_num, resolution, net_file, time_interval, sizeX, sizeY, link_dirct_file, demand_file, turn_rate):
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
        self.network = Network(5, 5, net_file, link_dirct_file, demand_file, turn_rate)
        self.cav_list = []
        self.cover_LinkTimeVeh = np.zeros((2 * link_num, 7000, 1000))  # index = [link, time, veh], value is hardcoded as 0 (binary)
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

    def sim(self, save_path, config, flextable, parameters, flex=0, k=32, GUImode=False):
        if GUImode:
            traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                         "--step-length={}".format(str(self.resolution))])
        else:
            traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.flex = flex  # default flexibility of the vehicle
        self.time = 0  # simulation time index
        self.step = 0
        self.network.netInit(self.sizeX, self.sizeY)

        # initial the cav list
        self.cav_dic = {}
        # self.link_flows_table = self.link_flows_hisNum  # get history link-flow table

        # # initial CTM
        # self.CTM = CTM(self.network, tick_interval=5)  # 20111128 defaultly set tick as 5s.
        # self.CTM.init()

        while True:

            # the following steps only apply in a GIVEN TIME Interval
            if self.step % (self.time_interval * 10) == 0:
                # step1: update cav dictionary information, the following inforamtion will be updated:
                # - 1.1 select and update the flexibility for current cav in the list.
                # - 1.2 determine the next intended link based on no changing zone constrains.
                print("###########################")
                print('step is:', self.step, parameters[1])

                self.updateCAVinfo()

                # step2: enumerate all cav from list, choose proper route and update vehicle information
                # if self.step % (self.time_interval * 10) == 0:  # plan for the start of every time interval
                self.getCAVList()
                # print('step is:', self.step, parameters[1])

                # step2: enumerate all cav. for each cav.
                #       -2.1: get k-shortest path considering distance
                #       -2.2: calculate travel time and cover rate for each candidate route
                #       -2.3: choose the best route and apply accordingly
                #       -2.4: update CAV routing table

                self.updateRoute(k, parameters)

                # """temp set route for debug 20231130"""
                # cavtestroute = ["E108", "E38", "E39", "-E16", "-E35", "-E11", "E31", "-E14", "-E27", "-E9", "E23", "-E118"]
                # traci.vehicle.setRoute('cav1', cavtestroute)


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
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                path = save_path['cover_table{}'.format(parameters[1])]
                np.save(path, self.cover_LinkTimeVeh[:, self.start_time:self.max_time, :])
                with open(flextable, 'w') as flxfile:
                    json.dump(self.cav_dic, flxfile)
                print("Sim has ended due to no enough vehicle")
                break

    def simCTM(self, save_path, config, flextable, parameters, flex, k=32, GUImode=False):
        if GUImode:
            traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                         "--step-length={}".format(str(self.resolution))])
        else:
            traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.flex = flex  # default flexibility of the vehicle
        self.time = 0  # simulation time index
        self.step = 0
        self.network.netInit(self.sizeX, self.sizeY)

        # initial the cav list
        self.cav_dic = {}

        # initial CTM
        self.CTM = CTM(self.network, tick_interval=5)  # 20111128 defaultly set tick as 5s.
        self.CTM.init()

        while True:

            # in a given time interval of CTM model, an observation will be updated each step, then the CTM needs to be
            # implemented for a given range.
            if self.step % (self.time_interval * 10) == 0:
                # step1: update cav dictionary information, the following inforamtion will be updated:
                # - 1.1 select and update the flexibility for current cav in the list.
                # - 1.2 determine the next intended link based on no changing zone constrains.
                print("###########################")
                print('step is:', self.step, parameters[1])

                self.updateCAVinfo()

                # step2: update current observation and CTM model till the longest trip
                # step2.1: get a list of cav that in the network
                self.getCAVList()

                # step3: enumerate all cav from list, choose proper route and update vehicle information


                # step3.1: enumerate all cav. for each cav.
                #       -1: get k-shortest path considering distance
                #       -2: calculate travel time and cover rate for each candidate route based on CTM
                #       -3: choose the best route and apply accordingly
                

                self.updateRoute(k, parameters)

                # """temp set route for debug 20231130"""
                # cavtestroute = ["E108", "E38", "E39", "-E16", "-E35", "-E11", "E31", "-E14", "-E27", "-E9", "E23", "-E118"]
                # traci.vehicle.setRoute('cav1', cavtestroute)


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
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                path = save_path['cover_table{}'.format(parameters[1])]
                np.save(path, self.cover_LinkTimeVeh[:, self.start_time:self.max_time, :])
                with open(flextable, 'w') as flxfile:
                    json.dump(self.cav_dic, flxfile)
                print("Sim has ended due to no enough vehicle")
                break


    def sim_benchmark(self, save_path, config="../sumo_cfg/5x5net/benchmark.sumocfg"):
        traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        self.step = 0
        self.network.netInit(self.sizeX, self.sizeY)
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
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                path = save_path['cover_table_benchmark']
                np.save(path, self.cover_LinkTimeVeh[:, self.start_time:self.max_time, :])
                print("CTMSim has ended due to no enough vehicle")
                break

    # 06/18/2023 get historical link flow table through simulation
    def get_LF_table(self, config):
        traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
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
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                # if self.step > self.MAXSTEP:
                print("CTMSim has ended due to no enough vehicle")
                self.filter_lf_table()
                break

    # get list that will plan in this step
    def getCAVList(self):
        self.cav_list = []
        for v_id in traci.vehicle.getIDList():
            if re.findall(r'[0-9]+|[a-z]+', v_id)[0] == "cav":
                edge_id = traci.vehicle.getRoadID(v_id)
                if not (edge_id[0] == '-' and int(re.findall(r'[0-9]+|[a-z]+', edge_id)[0]) > self.link_num):
                    # print(edge_id)
                    self.cav_list.append(v_id)  # return the cav list that needs to be controlled

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
                        cav_idx = int(v_tem[1])  # cav index = cav numbber - 1
                        for eID in range(self.cover_LinkTimeVeh.shape[0]):
                            self.cover_LinkTimeVeh[
                                eID, time_idx, cav_idx] = 0  # clear current edge occupation before update
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
                edge_current = traci.vehicle.getRoadID(v_id)  # check if the vehicle in the network
                nextNode = self.network.getNextNode((edge_current))
                # step1: calculate and update flexibility
                if v_id not in self.cav_dic:
                    # default add vehicle initial state
                    sp_length = self.network.getShortDistance(self.network.getNextNode(traci.vehicle.getRoute(v_id)[0]),
                                                              self.network.getFromNode(
                                                                  traci.vehicle.getRoute(v_id)[-1]))
                    self.cav_dic[v_id] = {'original': self.network.getNextNode(traci.vehicle.getRoute(v_id)[0]),
                                          'destination': self.network.getFromNode(traci.vehicle.getRoute(v_id)[-1]),
                                          'Flex': [self.flex],  # initial flexibility, must be even number
                                          'currentFlex': self.flex,
                                          'deltaCover': 1,
                                          'spLength': sp_length,
                                          'currentRoute': [None],
                                          'isControl': True,  # this is the flag that determines if cav need to be controlled.
                                          'nextEdges': None}
                elif self.cav_dic[v_id]['isControl']: # if not first time, update flexibility
                    if int(re.findall(r'[0-9]+|[a-z]+', edge_current)[0]) <= self.link_num:

                        last_edge = self.cav_dic[v_id]['currentRoute'][-1]
                        if edge_current != last_edge:
                            self.cav_dic[v_id]['currentRoute'].append(edge_current)
                        # if not (edge_current[0] == '-' and int(
                        #         re.findall(r'[0-9]+|[a-z]+', edge_current)[0]) > self.link_num):
                        # nextNode_tmp = self.network.getNextNode(edge_current)
                        sp_current = self.network.getShortDistance(nextNode, self.cav_dic[v_id]['destination'])
                        # 1103 update: current flexibility = original sp length + initial flexibility - number of edges traveled - current sp length
                        tmp_flex = self.cav_dic[v_id]['spLength'] + self.cav_dic[v_id]['Flex'][0] - len(
                            self.cav_dic[v_id]['currentRoute']) + 1 - sp_current
                        self.cav_dic[v_id]['Flex'].append(max(tmp_flex, 0))
                        self.cav_dic[v_id]['currentFlex'] = max(tmp_flex, 0)
                        # if tmp_flex == 0:
                        #     print('we have something')
                print(f'vehicle {v_id} has flex {self.cav_dic[v_id]["currentFlex"]} with {self.cav_dic[v_id]["isControl"]}')
                # step2: determine the intended next edge if in no changing zone
                if not (edge_current[0] == '-' and int(
                        re.findall(r'[0-9]+|[a-z]+', edge_current)[0]) > self.link_num):
                    # edge_idxnum = int(re.findall(r'[0-9]+|[a-z]+', edge_current)[0])
                    lane_current = traci.vehicle.getLaneID(v_id)  # lane id for the current vehicle
                    lane_tmp = self.network.sumonet.getLane(lane_current)  # lane object for current vehicle
                    # edges_outid = [e.getID() for e in self.network.node_list[nextNode].link_idx['out']]
                    # aa = self.network.sumonet.getEdge(edge_current).getLength() - traci.vehicle.getLanePosition(v_id)
                    if self.network.sumonet.getEdge(edge_current).getLength() - traci.vehicle.getLanePosition(v_id) <= 160:
                        self.cav_dic[v_id]['nextEdges'] = [cnt.getTo().getID() for cnt in lane_tmp.getOutgoing()] #  if vehicle in no changing zone
                    else:
                        # print(f'next Node is {nextNode}, veh{v_id} in nochanging zone')
                        self.cav_dic[v_id]['nextEdges'] = [e.getID() for e in self.network.node_list[nextNode].link_idx['out']]  # if not in no-changing zone
                #

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
            print(f'start from veh {cav_id}')
            # 1204 update: check control flag first
            if self.cav_dic[cav_id]['isControl']:
                # print(f'current veh idx is {cav_id} in a list of {self.cav_list}')
                # 1.get k shortest path considering distance
                veh_idx = int(re.findall(r'[0-9]+|[a-z]+', cav_id)[1])
                cav_edgeID = traci.vehicle.getRoadID(cav_id)
                my_nextNode = self.network.getNextNode(cav_edgeID)
                sp_length = (self.cav_dic[cav_id]['spLength']*400)/14

                k_shortest_path = self.network.findKShortPath(k, my_nextNode, self.cav_dic[cav_id]['destination'],
                                                              self.cav_dic[cav_id]['currentFlex'])


                # filter k_shortest_path with the following rules: (20231203)
                # 1. remove the routes that not realistic based on the no changing zone regulation
                # 2. z

                # 0710: get vehicle departure time
                # tmp = traci.vehicle.getDeparture(cav_id)
                dep_time = traci.vehicle.getDeparture(cav_id)  # get departure time

                # 2. calculate travel time and cover rate for each candidate route
                # 3. get delta_cover for each candidate path
                arrive_time_table = []  # store the node arrive time for each path selection
                delta_cover_table = []  # store the change of cover rate for each candidate path
                path_obj_table = []  # store the object value for each candidate path

                # objective value for last candidate path, since the objective is to get max, the default number is -1000000.
                last_bestRoute_obj = -1000000

                # print(f'check cover table at start of {cav_id} at time {self.time}')
                # self.checkCoverTable()
                # print(f'vehicle {cav_id} has sp {k_shortest_path} ')

                # remove future route for selected vehicle
                for l in range(self.cover_LinkTimeVeh.shape[0]):
                    for t in range(int(self.time), self.cover_LinkTimeVeh.shape[1]):
                        self.cover_LinkTimeVeh[l, t, veh_idx] = 0
                # print(f'begin to check if cover table is cleared for vehicle {cav_id} at time {self.time} on path {sp}')
                self.checkCoverTable()
                cover_LTV_tmp = copy.deepcopy(self.cover_LinkTimeVeh)

                # enumerate all candidate path, select the possible paths that fits the no-changing zone restriction
                route_candidate = []
                for sp in k_shortest_path:
                    # print(f'current route{sp} is for vehcile {cav_id}')
                    route = [cav_edgeID]
                    for node_idx in range(len(sp) - 1):
                        node2edge = self.network.node_list[sp[node_idx + 1]].getEdgeByUpperNode(sp[node_idx])
                        route.append(node2edge)
                    route.append(traci.vehicle.getRoute(cav_id)[-1])
                    """
                    06/21/2023: 
                    - until now, <tmp> & <sp> has been DUIQI !!!
                    - next step is to calculate arrival time for each node in sp with route[:-1]
                    - another input is an if table about if the edge is observed currently
                    """
                    if route[1] in self.cav_dic[cav_id]['nextEdges']:
                        route_candidate.append([sp, route])  # pairing node path and edge path

                del k_shortest_path

                for (sp, route) in route_candidate:
                    node_time = self.network.getNodeArrTime(route[:-1], sp, self.time, cav_id,
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
                    # cover_ts_pre = np.copy(self.cover_LinkTimeVeh[:, route_startTime: route_endTime, :])
                    cover_ts_pre = copy.deepcopy(cover_LTV_tmp[:, route_startTime: route_endTime, :])

                    for idx in range(len(route[:-1])):
                        edge_idx_num = int(re.findall(r'[0-9]+|[a-z]+', route[:-1][idx])[0])
                        if edge_idx_num < self.link_num:
                            # # determine the start and end time point for each occupation
                            # start_idx = node_timeTmp[1]
                            # end_idx = int(node_timeTmp[2])
                            if route[:-1][idx][0] == '-':
                                link_pos = edge_idx_num + self.link_num  # determine the link idx in cover time-space table
                            else:
                                link_pos = edge_idx_num
                            for k in range(round(node_timeTmp[idx]) - int(node_timeTmp[0]),
                                           round(node_timeTmp[idx + 1]) - int(node_timeTmp[0])):
                                # print(k)
                                cover_ts_pre[link_pos - 1, k - 1, veh_idx] = 1

                    # get the time-space cover table
                    cover_pre = np.where(np.sum(cover_ts_pre, axis=2) > 0, 1, 0)
                    cover_now = np.where(
                        np.sum(cover_LTV_tmp[:, route_startTime: route_endTime, :], axis=2) > 0,
                        1, 0)

                    cover_delta = (np.sum(cover_pre) - np.sum(cover_now)) / duration
                    delta_cover_table.append(cover_delta)

                    # 4. calculate objective and get best route, update the routing based on best objective
                    #  0710 YW: update objective considering total travel time instead of current steps.
                    current_route_obj = - (parameters[0]/sp_length) * (node_time[-1] - dep_time) + parameters[1] * cover_delta
                    path_obj_table.append(current_route_obj)
                    if current_route_obj >= 1.10 * last_bestRoute_obj:  # bubble up and get best
                        best_cover = cover_ts_pre
                        best_rou_end = route_endTime
                        best_route_node = sp  # get best route idx and path(node)
                        last_bestRoute_obj = current_route_obj
                        best_travel_time = (node_time[-1] - dep_time)

                        # best_route = [cav_edgeID]
                        # # convert node path to edge path
                        # for node_idx in range(len(best_route_node) - 1):
                        #     node2edge = self.network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                        #         best_route_node[node_idx])
                        #     best_route.append(node2edge)

                        self.cav_dic[cav_id]['deltaCover'] = cover_delta
                        # print(f'vehicle {cav_id} delta cover is {cover_delta}')

                        # stop planning threshold
                        if (abs(self.cav_dic[cav_id]['deltaCover'] - 1) < 0.01 or self.cav_dic[cav_id]['currentFlex'] == 0):
                            self.cav_dic[cav_id]['isControl'] = False

                            best_route = [cav_edgeID]
                            # convert node path to edge path
                            for node_idx in range(len(best_route_node) - 1):
                                node2edge = self.network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                                    best_route_node[node_idx])
                                best_route.append(node2edge)
                            self.cover_LinkTimeVeh[:, route_startTime: best_rou_end, :] = best_cover
                            best_route.append(traci.vehicle.getRoute(cav_id)[-1])
                            traci.vehicle.setRoute(cav_id, best_route)
                            print(f'vehicle {cav_id} is set to False with route {best_route}, flex is {self.cav_dic[cav_id]["Flex"]} and cover is {self.cav_dic[cav_id]["deltaCover"]}')
                            break
                        # self.cav_dic[cav_id]['isControl'] = False if (abs(self.cav_dic[cav_id]['deltaCover'] - 1) < 0.05 or self.cav_dic[cav_id]['Flex'] == 0) else True
                        isctrl = self.cav_dic[cav_id]['isControl']
                        # pr
                        # hicle {cav_id} current node is {best_route_node} best obj is {last_bestRoute_obj} with time {best_travel_time} and cover {cover_delta}, control is {isctrl}')
                        del cover_ts_pre, cover_pre
                    if sp == route_candidate[-1][0]:  # in the last, update route and
                        isctrl = self.cav_dic[cav_id]['isControl']
                        best_route = [cav_edgeID]
                        # convert node path to edge path
                        for node_idx in range(len(best_route_node) - 1):
                            node2edge = self.network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                                best_route_node[node_idx])
                            best_route.append(node2edge)
                        self.cover_LinkTimeVeh[:, route_startTime: best_rou_end, :] = best_cover
                        best_route.append(traci.vehicle.getRoute(cav_id)[-1])
                        traci.vehicle.setRoute(cav_id, best_route)
                        print(
                            f'vehicle {cav_id} current route is {best_route} with best obj {last_bestRoute_obj} with time {best_travel_time}, control is {isctrl}')

                        del cover_LTV_tmp

                # print('yes')
            else:
                print(f'vehicle {cav_id} will not be controlled due to its best route')
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
                        print(f"Vehicle {cav_idx + 1} is more than one pos at time {t}, current time is {self.time}:")
