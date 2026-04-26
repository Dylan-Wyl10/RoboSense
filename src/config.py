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
        self.ctm_time_opt = 1000  # max time for ctm calculation for optimial
        self.ctm_time_normal = 10
        self.ctm_interval = 5
        self.is_real_demand = 'dynamic'  # ['static', 'dynamic']  this string indicates whether ctm use read demand


        self.ctm_fd={
                    'v_f': 57.6,  # km/hr  default 57.6
                    'k_jam': 1000/7.5,  # veh/km
                    'q_max': 1920,  # veh/hour
                    'w': 19.59,
                    'length': 0.08,  # km
                    'delta_t': 5 / 3600,  # hr
                    }

        # CAV routing parameter
        # this part is to determine the cav routing policies, includes: budget, max travel threshold, etc
        self.max_route = 12  # if cav has traveled more than this number of edges, dont plan this cav
        self.budget = 0


        # Optim settings config
        self.param = (1, 2000, 999999)  # alpha-1, alpha-2, M
        self.opt_interval = 100  # unite in second  999999if no optimal
        self.is_route = True  # whether route control is applied

        # saving info
        self.test_str = 'ctm_test1'  # test case string
        self.case_str = '1215test/350_5400s_10percent_nobgt_new_normVeh'
        self.senario_str = '2000_cover'
        self.saving_dir = f'../result/ctmResult/logs/{self.test_str}/{self.case_str}/{self.senario_str}'
        # self.occupation_matrix = '../result/ctmResult/logs'

        ## path for ctm groundtruth matrix, this should be generated from the bench testing
        # self.ctm_gt_demand = f"../result/ctmResult/logs/ctm_test1/{self.case_str}/bench/ctm_gt.npy"
        self.saving_path = {'occupation': f'{self.saving_dir}/occupation.npy',
                            'od_route': f'{self.saving_dir}/od_route.json',
                            'ctm_demand_gt': f'../result/ctmResult/logs/{self.test_str}/{self.case_str}/bench/ctm_gt.npy',
                            'ctm': f'{self.saving_dir}',
                            'time_optim': f'{self.saving_dir}/time_optim.pkl',
                            'num_cav': f'{self.saving_dir}/num_cav.pkl'}

        # pipeline mode
        self.is_bench = False  # [True, False]
        self.is_vislz = False  # [True, False]
        self.plot_mode = 'historgram'  # [figure, video, historgram]
        self.is_sim = True  # [True, False]  # Flag for whether the simulation is started

        # evaluation parameters
        self.is_eval = True  # [True, False]
        self.is_odeval = False  # [True, False]
        self.ctm_cali = False  # [True, False]  # sim main, whether ctm is calibrated
        self.is_sensorPower = False  # [True, False]
        self.get_optm_time = False  # [True, False]

        self.ctm_cell_vis = False  # [True, False]  # flag at eval_main to start visulize the ctm cells
        self.eval_start = 1800  # evaluation start time
        self.eval_dur = 3600
