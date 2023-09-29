"""
Date: Sept 28, 2023,
Author: Yilin Wang
Note:
    - this script is used for analysis on traffic log to figure out the details on the operation on CAVs via different parameters.
List:
"""

import numpy as np
import xml.dom.minidom

def analysisTrip(trip_file):
    print(trip_file)


if __name__ == '__main__':

    alpha_set = [0, 100, 300, 500, 1000, 2000]
    pr = 5
    step = 20
    file_dir = {}
    file_dir['benchmark'] = "../result/PR{} TestingNew/sumolog_tmp/tripinfo_benchmark.xml".format(pr)

    for alp in alpha_set:
        file_dir[str(alp)] = "../result/PR{} TestingNew/sumolog_tmp/tripinfo{}.xml".format(pr, alp)

    print(file_dir)
    for _, v in file_dir.items():
        analysisTrip(v)
