"""
Date: Jun 02, 2023
Author: Yilin (Dylan) Wang
Note: this script is to generate the od flow for toynet
"""

import argparse
import numpy as np
import json
from routegenerator import od_generator

def main(args):
    time = args.timeframe  # length of the total simualtion
    path = args.savepath  # output path for route od file
    od_generator(path, args.seed)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('--timeframe',
                           default=0,
                           type=int,
                           help='simulation length (default:0)')

    argparser.add_argument('--savepath',
                           default='tmp_save_route.rou.xml',
                           type=str,
                           help='save path for the route file')

    argparser.add_argument('--seed',
                           default=42,
                           type=int,
                           help='random seed')

    args = argparser.parse_args()
    main(args)
