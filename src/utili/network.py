"""
Date: June 18, 2023
Author: Yilin Wang
Note: this script includes the scripts about network infrastructure
List:
"""

import traci
import numpy as np
import sumolib
import networkx as nx


class Intersection:
    def __init__(self, inter_id, net):
        self.net = net
        self.id = inter_id
        self.link_idx = {'in': self.net.getNode(self.id).getIncoming(),
                         'out': self.net.getNode(self.id).getOutgoing()}
        self.link_flow = {}
        # self.position = traci.junction.getPosition(self.id)

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

    # def getTravelTime

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

        print('yes')
    # def getLinkDelay(self, edge_id, time_interval, start_time, end_time):


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

    def getLastNode(self, edge_id):
        """
        return the start node index with the inputs of edge id
        :param edge_id:
        :return: node index
        """
        lastNodeID = self.net.getEdge(edge_id).getFromNode().getID()
        return lastNodeID

    def findKShortPath(self, k, start_node, desti_node):
        '''
        k-shortest path algorithm considering the travel cost, if there are multiple
        options, return all possible path.
        :param k:
        :param start_node:
        :param desti_node:
        :return:
        '''
        paths = list(nx.all_shortest_paths(self.G, start_node, desti_node))
        # paths = list(nx.all_shortest_paths(self.G, 'AA', 'FF'))
        # paths = list(nx.bidirectional_shortest_path(self.G, 'AA', 'FF'))
        return paths[:k]

    def getBestPath(self, k_shortest_path, time_interval):
        '''
        get best path from k-shortest path candidate considering other component.
        This function can be replaced with optimization formulation in the future.
        :param k_shortest_path:
        :param time_interval:
        :return:
        '''
