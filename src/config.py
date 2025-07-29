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
        self.sumo_maxtime = 5400
        self.sumo_gui = False

        # CTM settings
        self.ctm_time_opt = 1500  # max time for ctm calculation for optimial
        self.ctm_time_normal = 10
        self.ctm_interval = 5
        # self.ctm_fd={
        #             'v_f': 57.6,  # km/hr
        #             'k_jam': 133,  # veh/km
        #             'q_max': 1744,  # veh/hour
        #             'w': 17.94,
        #             'length': 0.08,  # km
        #             'delta_t': 5 / 3600,  # hr
        #             }

        self.ctm_fd={
                    'v_f': 57.6,  # km/hr
                    'k_jam': 133,  # veh/km
                    'q_max': 1800,  # veh/hour
                    'w': 22.84,
                    'length': 0.08,  # km
                    'delta_t': 5 / 3600,  # hr
                    }


        # Optim settings config
        self.param = (1, 10000000, 999999)  # alpha-1, alpha-2, M
        self.opt_interval = 100  # unite in second  999999if no optimal
        self.is_route = True

        # saving info
        self.saving_dir = '../result/ctmResult/logs'
        self.occupation_matrix = '../result/ctmResult/logs'
        self.saving_path = {'occupation': '../result/tmpnet/CTMTEST/occupation.npy',}

        # pipeline mode
        self.is_bench = False  #[True, False]
        self.is_vislz = False  # [True, False]
        self.plot_mode = 'figure'  # [figure, video]
        self.is_sim = True  # [True, False]
        self.is_eval = True  # [True, False]
        self.eval_start = 0 # evaluation start time
        self.eval_dur = 5400
