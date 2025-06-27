"""This file is for configuration for CTM-SUMO simulation"""

class Config:
    def __init__(self):
        # input files
        self.net_file = '../sumo_cfg/5x5net/5x5net.net.xml'  # path for sumo netfile
        self.link_node_dirct_file = "../sumo_cfg/5x5net/linkdirction_5x5.csv"  # this file discribe the link index and direction for each intersection
        self.demand_file = "../sumo_cfg/5x5net/CTMcfg/demand.csv"  # ctm demand
        self.turn_rate = "../sumo_cfg/5x5net/turnRatios.add.xml"

        # SUMO-sim related
        net_name = "5x5net"
        self.sumo_cfg = f"../sumo_cfg/{net_name}/simcfg/case0ctm.sumocfg"
        self.time_resolution = 0.1
        self.sumo_maxtime = 4200

        # CTM settings
        self.ctm_time_opt = 1000
        self.ctm_time_normal = 10
        self.ctm_interval = 5

        # Optim settings config
        self.param = (0.5, 1000000, 999999)  # alpha-1, alpha-2, M
        self.opt_interval = 20  # unite in second  999999if no optimal

        # saving info
        self.saving_dir = '../result/ctmResult/logs'
        self.occupation_matrix = '../result/ctmResult/logs'
        self.saving_path = {'occupation': '../result/ctmResult/logs/ctm_test1/occupation.npy',}

        # visuilizaion mode
        self.is_vislz = True
        self.plot_mode = 'video'  # [figure, video]
        self.is_sim = False
