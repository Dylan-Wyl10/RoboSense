"""
Date: June 18, 2023
Author: Yilin Wang
Note: this script includes the scripts about network infrastructure
List:
"""

import traci
import numpy as np
import sumolib


class Intersection():
    def __init__(self, inter_id):
        self.id = inter_id

    # get necessary information about intersections
    def getLinkInfo(self):
        '''
        1. get related edge index
        2. get historical link flow
        :return:
        '''
        self.position = traci.junction.getPosition(self.id)

        print('yes')
    # def getLinkDelay(self, edge_id, time_interval, start_time, end_time):


class Graph:
    def __init__(self, x_size, y_size, net_file):
        self.link_num = (x_size - 1) * y_size + (y_size - 1) * x_size
        self.node_list = self.getNodeList(x_size, y_size)  # restore the list of id on intersection
        self.net_config = net_file

    @staticmethod
    def getNodeList(x_size, y_size):
        tmp = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        node_list = {}
        for x in range(x_size):
            for y in range(y_size):
                node_id = tmp[x] + tmp[y]
                node_list[node_id] = Intersection(node_id)
        print('yes')
        return node_list

    def updateIntersection(self):
        for n_id, inter in self.node_list.items():
            inter.getLinkInfo()

    def getNextNode(self, edge_id):
        """
        return the end node index with the inputs of edge id
        :input: edge index
        :return: node index
        """
        # parse the net
        net = sumolib.net.readNet(self.net_config)
        # retrieve the successor node ID of an edge
        nextNodeID = net.getEdge(edge_id).getToNode().getID()
        return nextNodeID

    def findKShortPath(self, k, start_node, desti_node):
        '''
        k-shortest path algorithm considering the travel cost, if there are multiple
        options, return all possible path.
        :param k:
        :param start_node:
        :param desti_node:
        :return:
        '''

    def getBestPath(self, k_shortest_path, time_interval):
        '''
        get best path from k-shortest path candidate considering other component.
        This function can be replaced with optimization formulation in the future.
        :param k_shortest_path:
        :param time_interval:
        :return:
        '''
