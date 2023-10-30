"""
Date: Jun 02, 2023
Author: Yilin (Dylan) Wang
Note: this script is to generate the od flow for toynet
"""

import argparse
import numpy as np
import json
from odgenerator import od_generator


def main(args):
    time = args.timeframe  # length of the total simualtion
    path = args.savepath  # output path for route od file
    od_generator(path, args.timeframe, args.size, args.linkflow)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument('--timeframe',
                           default=0,
                           type=int,
                           help='simulation length (default:0)')

    argparser.add_argument('--savepath',
                           default='od_file.od',
                           type=str,
                           help='save path for the route file')

    argparser.add_argument('--size',
                           default=6,
                           type=int,
                           help='size for the network, must accomandate with taz file')

    argparser.add_argument('--linkflow',
                           default=100,
                           type=int,
                           help='hour rate for link flow rate')

    args = argparser.parse_args()
    main(args)
