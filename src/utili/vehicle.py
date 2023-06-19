"""
Date: June 16, 2023
Author: Yilin Wang
Note: this script includes the necessary vehicle control module
List:
"""

import sys
import os
import re

import traci


class Vehicle:

    def __init__(self, v_id, k):
        self.v_id = v_id
        self.k = k  # k is the input variables for k-shortest path
        self.v_type = re.findall(r'[0-9]+|[a-z]+', self.v_id)[0]
        self._sequential_id = re.findall(r'[0-9]+|[a-z]+', self.v_id)[1]
        self.v_ori_edge = None
        self.v_des_edge = None
        self.v_route_idx = None
        self.v_current_edge = None
        # self.Route_in_edges_list = None
        self.v_current_loc = None  # vehicle current edge id

    def getMyLocation(self):
        self.v_current_loc = traci.vehicle.getPosition(self.v_id)

    def getMyEdge(self):
        self.v_current_edge = traci.vehicle.getRoadID(self.v_id)

    def getNewRoute(self, Graph, time_interval):
        '''
        find the new route and update through traci
        input: Graph -- network class that contains the network information and methods
        '''
        #  06/16/2023 this function needs to be updated later with enumerating all routes.
        self.getMyEdge()
        self.route_with_edge = traci.vehicle.getRoute(self.v_id)   # my route with a list of edge.
        desti_node = Graph.getNodeByEdge(self.route_with_edge[-1])
        if len(self.route_with_edge) > 1:
            next_node = Graph.getNodeByEdge(self.v_current_edge)
            self.k_shortest_path = Graph.findKShortPath(self.k)  # the output here has to be a list of k-shortest path, the length is k
        else:
            self.k_shortest_path = [self.v_current_edge]# c_r_list = []  # create a list to record the cover rate
        # for sp in self.k_shortest_path:
        #     cover_rate = Graph.getCoverRate(sp, time_interval, cav_route)  # get the expected cover rate
        # traci.vehicle.setRoute(self.v_id, self.route_with_edge)
        '''
        Note: the type of find_route_value.edges is tuple, and traci.route.add only accept list as route, so self.Route_in_edges_list need to convert the
        result into list so it can be utilized by other traci functions
        '''
        return self.k_shortest_path
