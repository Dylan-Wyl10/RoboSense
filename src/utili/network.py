"""
Date: June 18, 2023
Author: Yilin Wang
Note: this script includes the scripts about network infrastructure
List:
"""

import traci
import numpy as np


class Graph:
    def __init__(self, x_size, y_size):
        self.link_num = (x_size - 1) * y_size + (y_size - 1) * x_size
        self.node_list = self.getNodes(x_size, y_size)

    @staticmethod
    def getNodes(x_size, y_size):
        tmp = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        node_list = []
        for x in range(x_size):
            for y in range(y_size):
                node_list.append(tmp[x]+tmp[y])
        return node_list

