"""
Date: June 18, 2023,
Author: Yilin Wang
Note: this script includes the scripts about network infrastructure
List:
"""

import traci
import numpy as np
import sumolib
import networkx as nx
import re


class Intersection:
    def __init__(self, inter_id, net):
        self.net = net
        self.id = inter_id
        self.link_idx = {'in': self.net.getNode(self.id).getIncoming(),
                         'out': self.net.getNode(self.id).getOutgoing()}
        self.link_flow = {}
        self.link_phaseIdx_table = {}
        self.phase_split_time = [20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2]
        # self.position = traci.junction.getPosition(self.id)

    def setLinkPhaseIndex(self):
        inbounds = [e.getID() for e in self.link_idx['in']]  # inbound edges
        for e_in in inbounds:
            self.link_phaseIdx_table[e_in] = []
        self.tls_id = self.net.getEdge(inbounds[0]).getTLS().getID()
        all_links = traci.trafficlight.getControlledLinks(self.tls_id)
        for i in range(len(all_links)):
            edge_idx = self.net.getLane(all_links[i][0][0]).getEdge().getID()
            self.link_phaseIdx_table[edge_idx].append(i)

    def getEdgeByUpperNode(self, upper_node):
        """
        return edge index by given upper node index
        :param upper_node:
        :return:
        """
        for edg in self.link_idx['in']:
            if edg.getFromNode().getID() == upper_node:
                tt = edg.getID
                return edg.getID()

    def getPosition(self):
        self.position = traci.junction.getPosition(self.id)

    # get necessary information about intersections
    def getLinkInfo(self, link_flow_table):
        '''
        1. get related edge index
        2. update current link flow
        :return:
        '''
        # self.position = traci.junction.getPosition(self.id)
        # 1.get related edge index
        # 2.update link flow
        for in_edge_idx in self.link_idx['in']:
            self.link_flow[in_edge_idx] = link_flow_table[in_edge_idx]
        # print('yes')

    def getEdgeTravelTime(self, v_id, edge_id, time, link_input, mode):
        """
        :param cav_id: current v_id (type = cav)
        :param edge_id:
        :param time: should be the absolute time that start the link
        :param link_input:
        :param mode:
        :return:
        """
        ff_speed = self.net.getEdge(edge_id).getSpeed()
        edge_length = self.net.getEdge(edge_id).getLength()
        self.setLinkPhaseIndex()
        self.SPaT = []
        time_onStopBar = time + edge_length / ff_speed
        current_time = traci.simulation.getTime()
        phase_current = traci.trafficlight.getRedYellowGreenState(self.tls_id)
        # self.phase_split_time = [20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2]
        cycle_length = sum(self.phase_split_time[:12])

        if phase_current[self.link_phaseIdx_table[edge_id][0]] == 'G':
            green_time = traci.trafficlight.getNextSwitch(self.tls_id) - current_time  # current phase remain time
            self.SPaT = [phase_current[self.link_phaseIdx_table[edge_id][0]], green_time]
            est_arriveTime = (
                                   cycle_length - green_time + time_onStopBar - current_time) % cycle_length  # future time local coordinate in cycle
        else:
            # SPaT = [phase_current[self.link_phaseIdx_table[edge_id][0]], traci.trafficlight.getNextSwitch(self.tls_id)]
            # self.phase_split_time = [20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2, 20, 3, 2]
            edge_phaseSeq = self.link_phaseIdx_table[edge_id][0] // 5  # 5 = number of connection in each phase
            phase_id = traci.trafficlight.getPhase(self.tls_id)  # current phase id
            if phase_id < 3 * edge_phaseSeq:
                red_time = traci.trafficlight.getNextSwitch(self.tls_id) - current_time + sum(
                    self.phase_split_time[phase_id + 1:edge_phaseSeq * 3])
            elif phase_id > 3 * edge_phaseSeq:
                # tmp = self.phase_split_time[phase_id+1: 12 +edge_phaseSeq*3]
                red_time = traci.trafficlight.getNextSwitch(self.tls_id) - current_time + sum(
                    self.phase_split_time[phase_id + 1: 12 + edge_phaseSeq * 3])
            self.SPaT = [phase_current[self.link_phaseIdx_table[edge_id][0]], red_time]  # SPaT here is current status
            est_arriveTime = (80 - red_time + time_onStopBar - current_time) % cycle_length  # predicted arrive time in cycle
        if mode == "history":
            q_0 = 3600 / 3600
            q_1 = link_input / 3600
            x_pr = 80 * q_0 / (q_0 - q_1)  # time that clear the queue
            # y_pr = q_1 * x_pr
            if est_arriveTime > x_pr:  # no queue
                return time_onStopBar, time_onStopBar
            elif est_arriveTime <= x_pr:
                y_1 = q_1 * est_arriveTime
                x_0 = y_1 / q_0 + 80
                return time_onStopBar, time_onStopBar + x_0
        elif mode == "detect":
            dis_tmp = {}
            for v in link_input:
                dis_tmp[v] = self.net.getEdge(edge_id).getLength() - traci.vehicle.getLanePosition(v)
            dis_tmp = dict(sorted(dis_tmp.items(), key=lambda x: x[1], reverse=False))
            queue_seq = list(dis_tmp.keys()).index(v_id)  # sequence in queue for given v_id
            link_tt = dis_tmp[v_id]/ff_speed  # link travel time
            if self.SPaT[0] == 'G':
                est_arriveTime = (cycle_length - self.SPaT[1] + (link_tt + time) - current_time) % cycle_length
            elif self.SPaT[0] == 'r':
                est_arriveTime = (80 - self.SPaT[1] + (link_tt + time) - current_time) % cycle_length
            x_pr = max(80 + 2 * (queue_seq+1), 100)
            if est_arriveTime > x_pr:
                return link_tt + time, link_tt + time
            elif est_arriveTime <= x_pr:
                return link_tt + time, link_tt + time + 2 * (queue_seq+1)  # 0628 YW: hardcoding time headway=2s


class Network:
    def __init__(self, x_size, y_size, net_file):
        self.link_num = (x_size - 1) * y_size + (y_size - 1) * x_size
        # self.net_config = net_file
        self.net = sumolib.net.readNet(net_file)
        self.G = nx.Graph()  # initial a graph component
        self.node_list = self.getNodeList(x_size, y_size, self.net)  # restore the list of id on intersection

    def netInit(self, x_size, y_size):
        for n in self.node_list.values():
            n.getPosition()
        self.makeGraph(x_size, y_size)

    @staticmethod
    #  this function is used to get distances from two node objects
    def getEdgeDis(node1, node2):
        # n1 = node1.position
        return np.sqrt((node1.position[0] - node2.position[0]) ** 2 + (node1.position[1] - node2.position[1]) ** 2)

    def makeGraph(self, x_size, y_size):
        tmp_node = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        for x in range(x_size):
            for y in range(y_size):
                if x + 1 < x_size and y + 1 < y_size:
                    current = tmp_node[x] + tmp_node[y]
                    current_right = tmp_node[x] + tmp_node[y + 1]
                    current_down = tmp_node[x + 1] + tmp_node[y]
                    dis1 = self.getEdgeDis(self.node_list[current], self.node_list[current_right])
                    dis2 = self.getEdgeDis(self.node_list[current], self.node_list[current_down])
                    self.G.add_weighted_edges_from([(current, current_right, dis1),
                                                    (current, current_down, dis2)])
                elif y + 1 == y_size and x + 1 < x_size:
                    current = tmp_node[x] + tmp_node[y]
                    current_down = tmp_node[x + 1] + tmp_node[y]
                    dis2 = self.getEdgeDis(self.node_list[current], self.node_list[current_down])
                    self.G.add_weighted_edges_from([(current, current_down, dis2)])
                elif x + 1 == x_size and y + 1 < y_size:
                    current = tmp_node[x] + tmp_node[y]
                    current_right = tmp_node[x] + tmp_node[y + 1]
                    dis1 = self.getEdgeDis(self.node_list[current], self.node_list[current_right])
                    self.G.add_weighted_edges_from([(current, current_right, dis1)])
                elif x == y == x_size - 1:
                    break

    @staticmethod
    def getNodeList(x_size, y_size, net):
        tmp = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        node_list = {}
        for x in range(x_size):
            for y in range(y_size):
                node_id = tmp[x] + tmp[y]
                node_list[node_id] = Intersection(node_id, net)
        return node_list

    def updateIntersection(self, link_flows_table):
        for n_id, inter in self.node_list.items():
            inter.getLinkInfo(link_flows_table)  # update link flow for each intersection

    def getNextNode(self, edge_id):
        """
        return the end node index with the inputs of edge id
        :input: edge index
        :return: node index
        """
        # retrieve the successor node ID of an edge
        nextNodeID = self.net.getEdge(edge_id).getToNode().getID()
        return nextNodeID

    def getFromNode(self, edge_id):
        """
        return the start node index with the inputs of edge id
        :param edge_id:
        :return: node index
        """
        lastNodeID = self.net.getEdge(edge_id).getFromNode().getID()
        return lastNodeID

    def getShortDistance(self, start_node, dest_node):
        """
        return the length of shortest path given start and destination
        """
        return nx.shortest_path_length(self.G, start_node, dest_node, weight=None, method='dijkstra')

    def findKShortPath(self, k, start_node, desti_node, flexibility):
        '''
        k-shortest path algorithm considering the travel cost, if there are multiple
        options, return all possible path.
        :param k: max number of candidate path
        :param start_node:
        :param desti_node:
        :param flexibility: parameters for derouting option (0926update: a ratio of the number of shortest path)
                            (1103update: flexibility calculated by vehicle status/ like a budget)
        :return:
        '''

        # start_node = 'DE'
        # desti_node = 'DE'
        # sp_num = len(list(nx.all_shortest_paths(self.G, start_node, desti_node)))  # number of shortest path
        # max_path_num = min(int(sp_num * flexibility), k)  # number of candidate path = min(max bound, deroute number)

        max_path_num = k
        sp_length = nx.shortest_path_length(self.G, start_node, desti_node, weight=None, method='dijkstra')
        tmp = int(sp_length + flexibility)
        paths = list(nx.all_simple_paths(self.G, start_node, desti_node, cutoff=tmp))
        paths.sort(key=len)
        return paths[:max_path_num]

    def getNodeArrTime(self, route_OnEdge, route_OnNode, current_time, cav_id, lf_history):
        """
        :param route_OnEdge: route that indicate edges
        :param route_OnNode: route that indicate nodes
        :param current_time: current simulation time
        :param cav_id: a binary observed table(edge-dict) for link-flow [0: history, 1:observation]
        :param lf_history: historical link-flow table(edge-dict)
        :return:
        """
        route_NodeTime = []  # this will record the time that leave each node
        time = current_time  # for current edge, edge_start time = current time
        for idx in range(len(route_OnNode)):
            edge = route_OnEdge[idx]
            node = route_OnNode[idx]
            # edge is the in bound link for each node
            # tmp = int(re.findall(r'[0-9]+|[a-z]+', edge)[0])
            """
            edge_time: absolute time that on stop bar
            edge_leave_time: time that leaves the edge --> time that arrive this node
             """
            if idx == 0:  # defaultly, the first edge in edge list is the current edge
                link_input = traci.lane.getLastStepVehicleIDs(traci.vehicle.getLaneID(cav_id))  # this is the veh_id list on link
                edge_time, edge_leave_time = self.node_list[node].getEdgeTravelTime(cav_id, edge, time, link_input,
                                                                                    mode="detect")
            else:
                link_input = lf_history[edge]
                edge_time, edge_leave_time = self.node_list[node].getEdgeTravelTime(cav_id, edge, time, link_input,
                                                                                    mode='history')
            time = edge_leave_time
            route_NodeTime.append(edge_leave_time)

            # if int(re.findall(r'[0-9]+|[a-z]+', edge)[0]) > 60:
            #     link_input = traci.edge.getLastStepVehicleIDs(edge)  # this is an id list on link
            #     edge_time, edge_leave_time = self.node_list[node].getEdgeTravelTime(edge, time, link_input,
            #                                                                         mode="detect")
            #     if lf_observ[edge] == 1:
            #         link_input = traci.edge.getLastStepVehicleIDs(edge)  # this is an id list on link
            #         edge_time, edge_leave_time = self.node_list[node].getEdgeTravelTime(edge, time, link_input,
            #                                                                             mode="detect")
            #     elif lf_observ[edge] == 0:  # use historical data to estimate
            #         link_input = lf_history[edge]
            #         edge_time, edge_leave_time = self.node_list[node].getEdgeTravelTime(edge, time, link_input,
            #                                                                             mode='history')
            # route_NodeTime.append(edge_time)
            # the node must be end node for edge

        # self.node_list
        return route_NodeTime

    # def getBestPath(self, k_shortest_path, time_interval):
    #     '''
    #     get best path from k-shortest path candidate considering other component.
    #     This function can be replaced with optimization formulation in the future.
    #     :param k_shortest_path:
    #     :param time_interval:
    #     :return:
    #     '''
