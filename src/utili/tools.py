"""
Date: June 13, 2023
Author: Yilin Wang
Note: script file for useful links.
List:
1. gen_LF_table(): generate a blank table to restore the travel information for each link.
2. update_LF_table(): update link-flow table
"""

import numpy as np


def gen_LF_table(link_num):
    table = {}
    for idx in range(link_num):
        table['E' + str(idx + 1)] = []
        table['-E' + str(idx + 1)] = []
    return table
