"""
Date: Sept 28, 2023,
Author: Yilin Wang
Note:
    - this script is used for analysis on traffic log to figure out the details on the operation on CAVs via different parameters.
List:
"""


import numpy as np
import xml.dom.minidom



if __name__ == '__main__':

    alpha_set = [0, 100, 300, 500, 1000, 2000]
    pr = 5
    step = 20
    file_dir = {}

    for p in p_set:
        save_info = {'cover_table': "../result/PR{} TestingNew/pr{}_cover_{}_step{}.npy".format(pr, pr, p, step),
                     'cover_table_benchmark': "../result/PR{} Testing/cover_table_benchmark.npy".format(pr)}

        path = "sumo_cfg/toy_net/toy_test_{}.sumocfg".format(p)
        lf_table_path = "../result/link_flow/pr{}_link_flow_3600.json".format(pr)
        s = Simulation(max_time=3600, link_num=60, resolution=0.1,
                       net_file='sumo_cfg/toy_net/toy_net1.net.xml',
                       time_interval=step)
        s.load_lf(lf_table_path)
        s.sim(save_info, path, parameters=(1, p), deroute_num=2, k=256)
        traci.close()
    # s.sim_benchmark(save_info)
