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
<<<<<<< HEAD
    file_dir['trip_bench'] = "../result/sumolog_pr{}/tripinfor_benchmark.xml".format(pr)

    for a in alpha_set:
        file_dir['trip_{}'.format(a)] = "../result/sumolog_pr{}/tripinfo{}.xml".format(pr, a)

    
    #     save_info = {'cover_table': "../result/PR{} TestingNew/pr{}_cover_{}_step{}.npy".format(pr, pr, a, step),
    #                  'cover_table_benchmark': "../result/PR{} Testing/cover_table_benchmark.npy".format(pr)}
    #
    #     path = "sumo_cfg/toy_net/toy_test_{}.sumocfg".format(a)
    #     lf_table_path = "../result/link_flow/pr{}_link_flow_3600.json".format(pr)
    #     s = Simulation(max_time=3600, link_num=60, resolution=0.1,
    #                    net_file='sumo_cfg/toy_net/toy_net1.net.xml',
    #                    time_interval=step)
    #     s.load_lf(lf_table_path)
    #     s.sim(save_info, path, parameters=(1, p), deroute_num=2, k=256)
    #     traci.close()
    # # s.sim_benchmark(save_info)
=======
    file_dir['benchmark'] = "../result/PR{} TestingNew/sumolog_tmp/tripinfo_benchmark.xml".format(pr)

    for alp in alpha_set:
        file_dir[str(alp)] = "../result/PR{} TestingNew/sumolog_tmp/tripinfo{}.xml".format(pr, alp)

    print(file_dir)
    for _, v in file_dir.items():
        analysisTrip(v)
>>>>>>> a7cbfc6ddda823e3b6335d0322846c15358dd4ca
