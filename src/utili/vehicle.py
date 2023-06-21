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
    """
    this class is a method class, that means there are no data stored in this class
    """

    def __init__(self, v_id):
        self.my_route = None
        self.v_id = v_id
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

    def getNewRoute(self, Graph, time_interval, k):
        '''
        # k is the input variables for k-shortest path
        find the new route and update through traci
        input: Graph -- network class that contains the network information and methods
        '''
        #  06/16/2023 this function needs to be updated later with enumerating all routes.
        self.getMyEdge()
        self.route_with_edge = traci.vehicle.getRoute(self.v_id)   # my route with a list of edge.
        desti_node = Graph.getNextNode(self.route_with_edge[-1])
        if len(self.route_with_edge) > 1:
            next_node = Graph.getNextNode(self.v_current_edge)  # next closest node.
            k_shortest_path = Graph.findKShortPath(k, next_node. desti_node)  # the output here has to be a list of k-shortest path, the length is k
            # best_path = Graph.getBestPath(k_shortest_path)
        else:
            k_shortest_path = [self.v_current_edge]

        # return k_shortest_path to simulation.updateRoute for future process
        return k_shortest_path

    def setNewRoute(self, my_route):
        '''
        Note: traci.route.add only accept list as route, need to convert the
        result into list so it can be utilized by other traci functions
        '''
        traci.vehicle.setRoute(self.v_id, self.my_route)
