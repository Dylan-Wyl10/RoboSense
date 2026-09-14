# /usr/bin/env python
"""
Author: Yilin Wang
Date: 06/01/2023
"""

import numpy as np
import random


def od_generator(filepath, time, size, linkflow):
    node_dict = {1: 'A',
                 2: 'B',
                 3: 'C',
                 4: 'D',
                 5: 'E',
                 6: 'F'
                 }  # this node restore index of the network node from number to letter
    # write od pair
    flow = round(linkflow * time/3600)
    with open(filepath, "w") as od:
        print('$O;D2', file=od)
        print('0.00 {}'.format(str(round((time / 3600), 2))), file=od)
        print('1.00', file=od)
        for nx in range(size):
            for ny in range(size):
                if nx == 0 or ny == 0 or nx == size - 1 or ny == size - 1:
                    if nx == ny or nx+ny == size:
                        veh_num = 2 * flow
                    else:
                        veh_num = flow
                    print(nx, ny, '\t')
                    print('{}{}_in {}{}_out {}'.format(node_dict[nx + 1], node_dict[ny + 1],
                                                node_dict[size-nx], node_dict[size-ny],
                                                str(veh_num)), file=od)
        # print()
