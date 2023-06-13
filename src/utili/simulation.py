"""
Date: June 13, 2023
Author: Yilin Wang
Note: this script contains the source code for the class for simualtion. including the necessary methods to muliplate simulate and the defined space for variables .
Structures:
- Simulation
"""
from tools import *


class Simulation:
    def __init__(self, max_time, link_num, resolution):
        self.MAXSTEP = max_time / resolution
        self.link_flows = gen_LF_table(link_num)

    def run(self):
        for step in range(self.MAXTIME)

