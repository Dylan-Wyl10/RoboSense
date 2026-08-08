"""
Date: June 13, 2023
Author: Yilin Wang
Note: this script contains the source code for the class for simualtion. including the necessary methods to muliplate simulate and the defined space for variables .
Structures:
- CTMSim
"""

import copy
import pickle
import time
import matplotlib.pyplot as plt

# from utili import CTM_visulization
from utili.network import Network
from utili.routeOptimGurobi import RouteOptimGurobi
import traci
import json
from src.utili.ctm.ctmcomponent import *
# from utili.routeOptim import RouteOptim
import os
from utili.tools import evalCTM, linkCTMvislz, checkCTM
from config import Config


class Simulation:
    def __init__(self, start_time, max_time, link_num, resolution, net_file, time_interval, sizeX, sizeY,
                 link_dirct_file, demand_file, turn_rate):
        self.step = 0
        self.time = 0
        self.start_time = start_time
        self.time_interval = time_interval
        self.max_time = max_time
        self.MAXSTEP = int(max_time / resolution)
        self.resolution = resolution
        self.sizeX, self.sizeY = sizeX, sizeY
        self.link_num = link_num

        # self.config = config  # 06/14/2023: temporaryly set sumo config path
        self.network = Network(self.sizeX, self.sizeY, net_file, link_dirct_file, demand_file, turn_rate)
        self.cav_list = []

        self.cav_route = {}

    def sim(self, save_path, config, flextable, parameters, link_num, sizeX, sizeY, flex=0, k=32, GUImode=False):
        if GUImode:
            traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                         "--step-length={}".format(str(self.resolution))])
        else:
            traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                         "--step-length={}".format(str(self.resolution))])
        self.link_num = link_num
        self.link_flows_table = gen_LF_table(link_num)
        self.link_flows_num = {}
        self.link_flows_observation = {}
        self.cover_LinkTimeVeh = np.zeros(
            (2 * link_num, 7000, 1000))  # index = [link, time, veh], value is hardcoded as 0 (binary)
        self.sizeX, self.sizeY = sizeX, sizeY

        self.flex = flex  # default flexibility of the vehicle
        self.time = 0  # simulation time index
        self.step = 0
        self.network.netInit(self.sizeX, self.sizeY)

        # initial the cav list
        self.cav_dic = {}
        # self.link_flows_table = self.link_flows_hisNum  # get history link-flow table

        # # initial CTM
        # self.CTM = CTM(self.network, tick_interval=5)  # 20111128 defaultly set tick as 5s.
        # self.CTM.init()

        while True:

            # the following steps only apply in a GIVEN TIME Interval
            if self.step % (self.time_interval * 10) == 0:
                # step1: update cav dictionary information, the following inforamtion will be updated:
                # - 1.1 select and update the flexibility for current cav in the list.
                # - 1.2 determine the next intended link based on no changing zone constrains.
                print("###########################")
                print('step is:', self.step, parameters[1])

                self.updateCAVinfo_StopandForward()

                # step2: enumerate all cav from list, choose proper route and update vehicle information
                # if self.step % (self.time_interval * 10) == 0:  # plan for the start of every time interval
                self.getCAVList()
                # print('step is:', self.step, parameters[1])

                # step2: enumerate all cav. for each cav.
                #       -2.1: get k-shortest path considering distance
                #       -2.2: calculate travel time and cover rate for each candidate route
                #       -2.3: choose the best route and apply accordingly
                #       -2.4: update CAV routing table

                self.updateRoute(k, parameters)

                # """temp set route for debug 20231130"""
                # cavtestroute = ["E108", "E38", "E39", "-E16", "-E35", "-E11", "E31", "-E14", "-E27", "-E9", "E23", "-E118"]
                # traci.vehicle.setRoute('cav1', cavtestroute)

                """
                # stepXXXX: (this will be added on next): adjust signal time plan. 
                self.update_tsc()
                self.update_veh()
                """
            # step3: update observation information every 1 second
            if self.step % 10 == 0:
                # self.getCAVctrlList()
                # update observation
                self.updateObsv()
                self.checkCoverTable()
            # step4: push simulation and update information
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()

            # stop and save the results
            # if self.step > self.MAXSTEP and traci.simulation.getMinExpectedNumber() <= 10:
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                path = save_path['cover_table{}'.format(parameters[1])]
                np.save(path, self.cover_LinkTimeVeh[:, self.start_time:self.max_time, :])
                with open(flextable, 'w') as flxfile:
                    json.dump(self.cav_dic, flxfile)
                print("Sim has ended due to no enough vehicle")
                break

    def simCTM(self, config, param, ctm_fd, ctm_interval, ctm_time_opt, ctm_time_norm, ctm_demand_mode, optim_interval, saving_path,
               GUImode=False, route=False, bench_mode=False):
        if GUImode:
            traci.start(["sumo-gui", "-c", config, "--lateral-resolution=0.1",
                         "--step-length={}".format(str(self.resolution))])
        else:
            traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                         "--step-length={}".format(str(self.resolution))])

        if route:
            self.ctm_interval = ctm_interval
        else:
            self.ctm_interval = 999999
        self.time = 0  # simulation time index
        self.step = 0
        self.network.netInit(self.sizeX, self.sizeY)

        # optimization parameter
        self.param = param

        # saving path
        self.saving_path = saving_path

        # initial the cav infor dic
        self.cav_dic = {}
        self.cav_tripInfo = {}

        # initial CTM
        self.CTM = CTM(ctm_fd, self.network, demand_mode=ctm_demand_mode, tick_interval=5, demand_gt=self.saving_path['ctm_demand_gt'])  # 20111128 defaultly set tick as 5s.
        self.cell_idx = self.CTM.init(max_flow=2400)
        if ctm_demand_mode == "dynamic":
            self.demand_cell_list = []
            for key in self.cell_idx:
                if key.split(".")[-1] == "C40":
                    self.demand_cell_list.append(key)

        self.cell_occupation = np.zeros(shape=(len(self.cell_idx), self.MAXSTEP // (5 * 10) + 1), dtype=int)
        self.ctm_groundtruth = np.zeros(shape=(len(self.cell_idx), self.MAXSTEP // (5 * 10) + 1), dtype=int)
        self.ctm_recordings = np.zeros(shape=(len(self.cell_idx), self.MAXSTEP // (5 * 10) + 1), dtype=float)
        # Per-CAV ordered cell-entry events for traversal-count segment popularity.
        # cav_cell_events[cav_id] = [(cell_id_str, ctm_step), ...]; only logged on cell transitions.
        self.cav_cell_events = {}
        self.cav_last_cell = {}

        self.optim_time, self.num_of_cav = [], []

        while True:

            # determin whether to calculate route
            if (self.step % (optim_interval * 10) == 0 and self.step != 0):
                is_optim = True
            else:
                is_optim = False

            if bench_mode:
                is_optim = False
            # is_optim = False

            if is_optim:
                CTM_maxtime = ctm_time_opt  # 200 steps
            else:
                CTM_maxtime = ctm_time_norm

            """
            CTM update for every 5 second in simulation, details are:
            
            """
            # CTM observation for each step, d an observation will be updated each step, then the CTM needs to be
            # if 1==2:
            if self.step % (self.ctm_interval * 10) == 0:
                # step 0: print current step number and get ground truth from CTM observation
                print("###########################")
                print('step is:', self.step)
                self.getCTMgroundTruth()
                time0 = time.time()

                # step 1: self get the current CAV information
                # step 1.1: update active cav list
                self.getCAVList()
                if (self.step % (optim_interval * 10) == 0 and self.step != 0):
                    self.num_of_cav.append(len(self.cav_list))
                    print(f'$$$$$$$$$$$$$number of cav is {len(self.cav_list)}')

                # step 1.2 update CAV o-d info for optimization, update CTM observation
                if len(self.cav_list) != 0:
                    print('cav')
                    update_table = self.getCTMObservation()  # enumerate cav list
                    for cid, v_num in update_table.items():
                        self.CTM.cells_dic[cid].n = v_num  # update number of vehicle
                    # update cav route-od info:
                    self.getCAVTrip()


                else:  # if there are no cav at time, dont update anything
                    self.cav_info = {}
                # step 1.3 update inbound ctm information based on ctm demand mode
                # if ctm_demand_mode == "dynamic":
                #     for cid in self.demand_cell_list:
                #         self.CTM.cells_dic[cid].n = self.ctm_groundtruth[self.cell_idx.index(cid), (self.step // (5 * 10))]

                # step 1.3: get CTM result for recording to evaluate the observation error
                self.getCTMrecord()

                # step 2.1: push CTM to next run, if no optimization if excuted, only caclulate one step further
                # Cells_saved_next means the snap shot for the next step , it is saved to reload
                self.snapshot_4_next, number_out, number_in, number, sigflag = self.CTM.runCTM(
                    traci.simulation.getTime(), CTM_maxtime)


                # step 2.2: reload CTM status for next step calculation
                for cid, cell in self.CTM.cells_dic.items():
                    cell.load_state(self.snapshot_4_next[cid])

                # self.evaluationCTM()


                # step 2.3: save and load result for optimal
                # hard coded parameter, need to be put into the config file in the future
                case_name = 'ctm_test1'
                log_dir = '../result/ctmResult/logs/' + case_name
                os.makedirs(log_dir, exist_ok=True)
                # ctm_fd = {
                #     'v_f': 57.6,  # km/hr
                #     'k_jam': 133,  # veh/km
                #     'q_max': 1744,  # veh/hour
                #     'w': 17.94,
                #     'length': 0.08,  # km
                #     'delta_t': 5 / 3600,  # hr
                # }
                input = {
                    'number': number,
                    'sigflag': sigflag,
                    'cell connection': self.CTM.connection_matrix,
                    'cell idx': self.cell_idx
                }

                if is_optim:
                    time_t1 = time.time()
                    self.getCAVOD()

                    if len(self.cav_info) == 0:
                        x = None
                    else:
                        print(f'number of cav being optimized is {len(self.cav_info)}')
                        self.Route_Optimizer = RouteOptimGurobi(CTM_FDParam=ctm_fd, veh_od=self.cav_info,
                                                                max_time=CTM_maxtime, current_time=self.step//10, CTM_input=input, Load_mode='direct')
                        self.Route_Optimizer.build_model(self.param, veh_num=len(self.cav_info), small_net=False)
                        x, y, omg, objective_value = self.Route_Optimizer.solve_model(CtmDowngrade=False)
                    # c_tmp = self.cav_list[0]
                    # route1 = traci.vehicle.getRoute(c_tmp)
                    # x = None
                    if x is not None:
                        self.getRoutefromX(x)

                        # if len(self.cav_info) > 0:
                        #     self.excuteCAVRoute()
                    else:
                        self.cav_info = {}
                        with open('log.txt', 'a') as f:
                            f.write(f'$$$$$$$$$$no solution at step {self.step}find\n')

                    # if len(self.cav_info) > 0:
                    #     self.excuteCAVRoute()

                    # omm = np.sum(omg, axis=0)
                    # yy = (omm > 0).astype(int)



                    optimTime = time.time()-time_t1
                    print(f'time for optimization is {optimTime}')
                    self.optim_time.append(optimTime)


                    # update cav route
                    # self.updateRoute()

                    # save results
                    # normdense.to_csv(log_dir + '/CTMdensityNorm.csv')
                    # number.to_csv('../result/ctmResult/CTMnumber_3600_1800dis.csv')
                    # density.to_csv('../result/ctmResult/CTMdensity_3600_1800dis.csv')
                    # number_out.to_csv('../result/ctmResult/CTMnumber_out_3600_1800dis.csv')
                    # sigflag.to_csv('../result/ctmResult/CTMsigflag_3600_1800dis.csv')
                    # np.savetxt('../result/ctmResult/CTMconnection.txt', self.CTM.connection_matrix)
                    # with open('../result/ctmResult/CTMcell_index.json', 'w') as file:
                    #     for item in cell_idx:
                    #         file.write(f"{item}\n")
                    # with open('../result/ctmResult/CTMcell_index.json', 'wb') as file:
                    #     json.dump(cell_idx, file)

                    # CTM visulization
                    # CTM_visulization('../result/ctmResult/CTMdensityNorm.csv', '../sumo_cfg/5x5net/CTMcfg/Cells.csv')
                    # print('okey')

                if len(self.cav_info) > 0:
                    self.excuteCAVRoute()
                # step4: push simulation and update information
                print(f'time for entire step is {time.time() - time0}')

            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()

            # stop and save the results
            # if self.step > self.MAXSTEP and traci.simulation.getMinExpectedNumber() <= 10:
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                # path = saving_path['occupation']
                # np.save(path, self.cell_occupation)
                self.saveEvaluation()
                print("Sim has ended due to no enough vehicle")
                break

    def calibrateCTM(self, ctm_fd, ctm_interval, cell_json, sumo_config, saving_path, ctm_demand_mode):
        """
        this function is used for optimal ctm result calibration, the bench parameter is set below
        self.ctm_fd = {
            'v_f': 57.6,  # km/hr
            'k_jam': 133,  # veh/km
            'q_max': 1800,  # veh/hour
            'w': 22.84,
            'length': 0.08,  # km
            'delta_t': 5 / 3600,  # hr
        }
        assuming: v_f, k_jam, length, delta_t is fixed, q_max&w is moving with values
        """

        traci.start(["sumo", "-c", sumo_config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(0.1))])
        # q_maxls = [1600, 1650, 1700, 1750, 1800, 1850, 1900, 1950, 2000, 2050]
        q_maxls = [1875 + 5*i for i in range(10)]  # center 1900
        delta_kcls = [0 + 2*i for i in range(20)]  # center 10
        # q_maxls = 1700 + ls
        # wls = [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
        # wls = [25, 25.5, 26, 26.5, 27, 27.5, 28, 28.5, 29, 29.5, 30]

        ctm_gt = np.load(saving_path['ctm_demand_gt'])

        self.network.netInit(self.sizeX, self.sizeY)
        start_time = 1800  # time of starting evaluation
        data = {"best_mape": {"mape": 999999,
                              "mae": 999999,
                              "qm": 1800,
                              "w": 20,
                              "delt_kc": 0},
                "best_mae": {"mape": 999999,
                             "mae": 999999,
                             "qm": 1800,
                             "w": 20,
                             "delt_kc": 0},
                }
        case_idx = 0
        # best_comb = {"score": 999999,
        #              "qm": 1800,
        #              "w": 20}


        CTM_tmp = CTM(ctm_fd, self.network, demand_mode='dynamic', tick_interval=ctm_interval,
                      demand_gt=saving_path['ctm_demand_gt'])
        cell_idx = CTM_tmp.init(max_flow=1800)
        # with open('../result/plot_ctm/CTMcell_index.json', 'w') as file:
        #     for item in cell_idx:
        #         file.write(f"{item}\n")

        # ctm_gtev = ctm_gt[:, start_time // 5:]

        # the calibration cretiran should only consider 20 loading links
        link_load_cell = ['A1.E101.C40', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7',
                          'A1.E102.C40', 'A1.E102.C5', 'A1.E102.C6', 'A1.E102.C7',
                          'A1.E103.C40', 'A1.E103.C5', 'A1.E103.C6', 'A1.E103.C7',
                          'A1.E104.C40', 'A1.E104.C5', 'A1.E104.C6', 'A1.E104.C7',
                          'A1.E105.C40', 'A1.E105.C5', 'A1.E105.C6', 'A1.E105.C7',
                          'A1.E106.C40', 'A1.E106.C5', 'A1.E106.C6', 'A1.E106.C7',
                          'A1.E107.C40', 'A1.E107.C5', 'A1.E107.C6', 'A1.E107.C7',
                          'A1.E108.C40', 'A1.E108.C5', 'A1.E108.C6', 'A1.E108.C7',
                          'A1.E109.C40', 'A1.E109.C5', 'A1.E109.C6', 'A1.E109.C7',
                          'A1.E110.C40', 'A1.E110.C5', 'A1.E110.C6', 'A1.E110.C7',
                          'A1.E111.C40', 'A1.E111.C5', 'A1.E111.C6', 'A1.E111.C7',
                          'A1.E112.C40', 'A1.E112.C5', 'A1.E112.C6', 'A1.E112.C7',
                          'A1.E113.C40', 'A1.E113.C5', 'A1.E113.C6', 'A1.E113.C7',
                          'A1.E114.C40', 'A1.E114.C5', 'A1.E114.C6', 'A1.E114.C7',
                          'A1.E115.C40', 'A1.E115.C5', 'A1.E115.C6', 'A1.E115.C7',
                          'A1.E116.C40', 'A1.E116.C5', 'A1.E116.C6', 'A1.E116.C7',
                          'A1.E117.C40', 'A1.E117.C5', 'A1.E117.C6', 'A1.E117.C7',
                          'A1.E118.C40', 'A1.E118.C5', 'A1.E118.C6', 'A1.E118.C7',
                          'A1.E119.C40', 'A1.E119.C5', 'A1.E119.C6', 'A1.E119.C7',
                          'A1.E120.C40', 'A1.E120.C5', 'A1.E120.C6', 'A1.E120.C7']
                          # 'A0.E2.C6',
                          # 'A0.E3.C1', 'A0.E3.C2', 'A0.E3.C3', 'A0.E3.C4',
                          # 'A0.E3.C5', 'A0.E3.C6', 'A0.E3.C7']

        ctm_gtev = ctm_gt[[cell_idx.index(c) for c in link_load_cell], start_time//5:]


        for qm in q_maxls:
            for delta_kc in delta_kcls:
                # qm = 1895
                # qm = 1920

                if delta_kc < ctm_fd['k_jam'] - qm/ctm_fd['v_f']:  # bound the minimium w slop
                    w = qm/(ctm_fd['k_jam'] - qm/ctm_fd['v_f'] - delta_kc)
                    # w = 19.71890016981609
                    # w = 19.2
                    # reset all cells

                    # qm, w = 2050, 74.791
                    CTM_tmp.resetValue(qmax=qm, w=w)
                    time0 = time.time()

                    # assign a snapshot at the start_time, the start time idx = start_time//self.tick + 1
                    for cid in cell_idx:
                        CTM_tmp.cells_dic[cid].n = ctm_gt[cell_idx.index(cid), start_time//5]
                        c = cid.split(".")[-1]
                    # get CTM result
                    _, y_out, y_in, number, signal = CTM_tmp.runCTM(time_current=1800, time_range=3600)
                    number_np = number.to_numpy()
                    yout_np = y_out.to_numpy()
                    yin_np = y_in.to_numpy()

                    number_npev = number_np[[cell_idx.index(c) for c in link_load_cell]]
                    # yout_npev = yout_np[[cell_idx.index(c) for c in link_load_cell]]
                    # yin_npev = yin_np[[cell_idx.index(c) for c in link_load_cell]]
                    # sum1, sum2 = np.sum(ctm_gtev), np.sum(number_npev)

                    # checkCTM(number_npev, yin_npev, yout_npev)

                    # This is the plot for error analysis for ctm
                    # =================================================================================
                    # errors = np.mean(ctm_gtev - number_np, axis=1)
                    # cells = np.array([s.split('.')[0] for s in cell_idx])
                    #
                    # # === 按C编号排序（C1, C2, ..., C40） ===
                    # unique_cells = np.array(
                    #     sorted(np.unique(cells), key=lambda x: int(x[1:]) if x[1:].isdigit() else 1e9))
                    #
                    # # === 聚合每个cell的误差 ===
                    # grouped_errors = [errors[cells == cid] for cid in unique_cells]
                    #
                    # # === 绘制箱线图 ===
                    # plt.figure(figsize=(10, 5))
                    # plt.boxplot(grouped_errors, labels=unique_cells, patch_artist=True)
                    # plt.xlabel('Cell ID', fontsize=11)
                    # plt.ylabel('Error Value', fontsize=11)
                    # plt.title('Error Distribution by Cell ID', fontsize=13)
                    # plt.grid(True, linestyle='--', alpha=0.6)
                    #
                    # # 可选：为每个箱体设置颜色渐变
                    # colors = plt.cm.viridis(np.linspace(0, 1, len(unique_cells)))
                    # for patch, color in zip(plt.gca().artists, colors):
                    #     patch.set_facecolor(color)
                    #
                    # plt.tight_layout()
                    # plt.show()
                    # ======================================================================= end of tmp plot



                    # linkCTMvislz(cell_idx, number_np, ctm_gt[:, start_time // 5:], mode="link")
                    # score_mape, _, _ = evalCTM(ctm_gtev, number_np, cell_json, eval_start=0, eval_duration=3600, method="mape")
                    score_mae, _, _ = evalCTM(ctm_gtev, number_npev, link_load_cell, eval_start=0, eval_duration=3600, method="mae")
                    # print(f'combination of qmam={qm} and w={w} has mape {score_mape} and mae {score_mae}')
                    data[case_idx] = {"qm": qm, "w": w, "mae": score_mae, "qmkc": qm/ctm_fd["v_f"],
                                      "del_kc": delta_kc, "km_kc": qm/ctm_fd["v_f"] + delta_kc}
                    case_idx += 1

                    if score_mae < data['best_mae']['mae']:
                        data['best_mae']['mae'] = score_mae
                        data['best_mae']['qm'] = qm
                        data['best_mae']['w'] = w
                        data['best_mae']['del_kc'] = delta_kc
                        data['best_mae']["km_kc"] = qm / ctm_fd["v_f"] + delta_kc
                        print(f'#######best mae {score_mae} has been updated, qm={qm} and w={w}, dkc={delta_kc}')
                else:
                    print(f'WARNING: qm={qm} and kc={delta_kc} is not a valid combination')

        # plot the best result from calibration
        # CTM_tmp.resetValue(qmax=data['best_mape']['qm'], w=data['best_mape']['w'])
        # for cid in cell_idx:
        #     CTM_tmp.cells_dic[cid].n = ctm_gt[cell_idx.index(cid), start_time // 5]
        #     c = cid.split(".")[-1]
        # # get CTM result
        # _, _, _, number, _ = CTM_tmp.runCTM(time_current=1800, time_range=3600)
        # number_np = number.to_numpy()
        # # print(f'time cost: {time.time() - time0}s')
        # linkCTMvislz(cell_idx, number_np, ctm_gtev)

        CTM_tmp.resetValue(qmax=data['best_mae']['qm'], w=data['best_mae']['w'])
        for cid in cell_idx:
            CTM_tmp.cells_dic[cid].n = ctm_gt[cell_idx.index(cid), start_time // 5]  # update ground truth from the snapshot time
            c = cid.split(".")[-1]
        # get CTM result
        _, _, _, number, _ = CTM_tmp.runCTM(time_current=1800, time_range=3600)
        number_np = number.to_numpy()
        # print(f'time cost: {time.time() - time0}s')
        # linkCTMvislz(cell_idx, number_np, ctm_gt[:, start_time//5:], mode="link")


        with open("../result/ctmResult/CTMcali.json", 'w') as f:
            json.dump(data, f, indent=4)


    # def linkCTMvislz(cell_idx, ctm, ctm_gt):
    #     # link_cellls = ['A1.E101.C40', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7']
    #     # link_cellls = ['A0.E11.C1', 'A0.E11.C2', 'A0.E11.C3', 'A0.E11.C4', 'A0.E11.C5', 'A0.E11.C6', 'A0.E11.C7']   # internal link
    #
    #     # choose one intersection
    #     link_cellls = ['A0.E5.C3', 'A0.E5.C4', 'A0.E5.C5', 'A0.E5.C6', 'A0.E5.C7',
    #                    'A0.-E5.C1', 'A0.-E5.C2', 'A0.-E5.C3', 'A0.-E5.C4', 'A0.-E5.C5',
    #                    'A0.E6.C1', 'A0.E6.C2', 'A0.E6.C3', 'A0.E6.C4', 'A0.E6.C5',
    #                    'A0.-E6.C3', 'A0.-E6.C4', 'A0.-E6.C5', 'A0.-E6.C6', 'A0.-E6.C7',
    #                    'A0.E25.C3', 'A0.E25.C4', 'A0.E25.C5', 'A0.E25.C6', 'A0.E25.C7',
    #                    'A0.-E25.C1', 'A0.-E25.C2', 'A0.-E25.C3', 'A0.-E25.C4', 'A0.-E25.C5',
    #                    'A0.E26.C1', 'A0.E26.C2', 'A0.E26.C3', 'A0.E26.C4', 'A0.E26.C5',
    #                    'A0.-E26.C3', 'A0.-E26.C4', 'A0.-E26.C5', 'A0.-E26.C6', 'A0.-E26.C7']
    #
    #     cell_ids = [cell_idx.index(c) for c in link_cellls]
    #     link_gt = ctm_gt[cell_ids]
    #     link_ctm = ctm[cell_ids]
    #
    #     mae = plot_gt_ctm_and_mae(link_gt, link_ctm, cell_idx, cell_ids)
    #
    #     print('yese')

    def sim_getBench(self, save_path, config="../sumo_cfg/5x5net/ctmbench.sumocfg"):
        traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        self.step = 0
        self.network.netInit(self.sizeX, self.sizeY)
        # self.link_flows_table = self.link_flows_hisNum  # get history link-flow table
        while True:

            # collect CAV infor evry 1 second == 10s
            if self.step % 10 == 0:
                # self.getCAVctrlList()
                # update observation
                self.updateObsv()
                self.checkCoverTable()

            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            # stop and save the results
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                path = save_path['cover_table_benchmark']
                np.save(path, self.cover_LinkTimeVeh[:, self.start_time:self.max_time, :])
                print("CTMSim has ended due to no enough vehicle")
                break

    # 06/18/2023 get historical link flow table through simulation
    def get_LF_table(self, config):
        traci.start(["sumo", "-c", config, "--lateral-resolution=0.1",
                     "--step-length={}".format(str(self.resolution))])
        self.time = 0  # simulation time index
        # for step in range(self.MAXSTEP):
        while True:
            if self.time > self.start_time:
                self.update_lf_table()
            # print(self.link_flows_table['E1'])
            self.step += 1
            self.time = self.step * self.resolution
            traci.simulationStep()
            if self.step > self.MAXSTEP or (
                    traci.simulation.getMinExpectedNumber() <= 10 and self.step > self.start_time):
                # if self.step > self.MAXSTEP:
                print("CTMSim has ended due to no enough vehicle")
                self.filter_lf_table()
                break

    # get list that will plan in this step
    def getCAVList(self):
        self.cav_list = []
        for v_id in traci.vehicle.getIDList():
            if re.findall(r'[0-9]+|[a-z]+', v_id)[0] == "cav":
                edge_id = traci.vehicle.getRoadID(v_id)
                if not (edge_id[0] == '-' and int(re.findall(r'[0-9]+|[a-z]+', edge_id)[0]) > self.link_num):
                    # print(edge_id)
                    self.cav_list.append(v_id)  # return the cav list that needs to be controlled

    def getCAVOD(self):

        self.cav_info = {}
        max_route = 12 # set the max route length threshold, if bigger than this number, cav will not optim.
        cav_index = 0  # sequential key for cav_info (only increments when a vehicle is added)
        for v_idx in range(len(self.cav_list)):
            cav_id = self.cav_list[v_idx]
            # print(cav_id)
            curr_cell, _ = self.getCellidxFromVeh(cav_id)
            current_route = traci.vehicle.getRoute(cav_id)
            current_edge = traci.vehicle.getRoadID(cav_id)
            edge_pos = current_route.index(current_edge)  # get current position of edge in total route list
            des_cell = 'A1.' + traci.vehicle.getRoute(cav_id)[-1] + '.C0'
            if len(current_route) >= max_route:  # max length bound
                continue
            else:

                # add budget for each cav
                edge_num_rem = len(current_route) - edge_pos - 1  # remaining number of edge

                # budget=0 fix: use shortest-path distance to prevent snowball effect
                if Config().budget == 0:
                    current_next_node = self.network.getNextNode(current_edge).split('_')[0]
                    dest_node = self.network.getNextNode(current_route[-1]).split('_')[0]
                    sp_remaining = self.network.getShortDistance(current_next_node, dest_node)
                    if sp_remaining == 0:
                        continue  # vehicle is on last edge, no routing needed
                    budget = 0
                else:
                    """
                    budge logic 20250729
                    1. if remaining route  length is greater than 4, than give budget
                    2. if already travel route is greater than 10, no budget
                    """
                    if edge_num_rem >= 6:
                        budget = 0
                    elif edge_pos >= 12:
                        budget = 0
                    else:
                        budget = Config().budget  # no budget:0, or budget:2

                """
                0827 Add od-route trace function
                """
                # budget = 0
                self.cav_info[cav_index] = {
                    'name': cav_id,
                    'from': self.cell_idx.index(curr_cell),
                    'to': self.cell_idx.index(des_cell),
                    'time': 0,
                    'budget': budget, # this is relavite time for optimization. since no prediction assumption, time default to zero
                    # 'route_length': (len(traci.vehicle.getRoute(cav_id)) - edge_pos + budget) * 5,
                    'remine_edge': edge_num_rem,
                    'edge_pos': edge_pos,
                    'route_length': sp_remaining if Config().budget == 0 else min(edge_num_rem + budget, 18 - edge_pos-1),
                    # 'route_length': edge_num_rem + budget,
                    'current_route': current_route,
                    'current_edge': current_edge
                }
                cav_index += 1

    def getCAVTrip(self):
        """
        This function is used to get the trip info for cavs, save dirctory self.cav_tripInfo (type: dict)
        """
        for cav_id in traci.vehicle.getIDList():
            if re.findall(r'[0-9]+|[a-z]+', cav_id)[0] == "cav":
                if cav_id not in self.cav_tripInfo.keys():
                    route = traci.vehicle.getRoute(cav_id)
                    edge = traci.vehicle.getRoadID(cav_id)
                    # convert route list to node list
                    route_node = [self.network.getNextNode(r) for r in route]
                    # if current edge is the end of the route
                    if edge == route[-1]:
                        trip_info = {}
                        trip_info['v_id'] = cav_id
                        trip_info['origin'] = self.network.getNextNode(route[0])
                        trip_info['destination'] = self.network.getFromNode(route[-1])
                        trip_info['route'] = route
                        trip_info['route_node'] = route_node
                        self.cav_tripInfo[cav_id] = trip_info
                        print(f'cav {cav_id} ')


    def getRoutefromX(self, x):
        if x is not None:
            # veh_rt = {}
            for a in range(x.shape[0]):
                rt_edge_lane = {}
                rt_cell = []
                # rt = []
                for t in range(x.shape[2]):
                    for i in range(x.shape[1]):
                        if (x[a, i, t] == 1 and i != self.cav_info[a]['to']):
                            rt_cell.append(self.cell_idx[i])
                            # edge = self.cell_idx[i].split('.')[1]
                            # if edge != pre:
                            #     rt.append(edge)
                            #     pre = edge
                self.cav_info[a]['route_cell'] = rt_cell
                for r in rt_cell:
                    parts = r.split('.')
                    if len(parts) >= 3:
                        edge = parts[1]
                        cell = parts[2].upper()
                        # add edge to dic if not seen
                        if edge not in rt_edge_lane:
                            rt_edge_lane[edge] = -1
                        # update lane
                        if cell == "C6":
                            rt_edge_lane[edge] = 1
                        elif cell == "C7":
                            rt_edge_lane[edge] = 0
                self.cav_info[a]['route_with_lane'] = rt_edge_lane
                self.cav_info[a]['update_route'] = list(rt_edge_lane.keys())
                if len(self.cav_info[a]['update_route']) > 0:
                    traci.vehicle.setRoute(self.cav_info[a]['name'], self.cav_info[a]['update_route'])




    def excuteCAVRoute(self):
        for v_idx in range(len(self.cav_info)):
            try:
                cav_id = self.cav_info[v_idx]['name']
                edge = traci.vehicle.getRoadID(cav_id)  # current edge

                # print(
                #     f"{cav_id} heading to {self.cell_idx[self.cav_info[v_idx]['to']]} "
                #     f"will be on lane {self.cav_info[v_idx]['route_with_lane'][edge]} "
                #     f"with route {self.cav_info[v_idx]['route_cell']}"
                # )
                # print(f"{cav_id} route and lane {self.cav_info[v_idx]['route_with_lane']}")

                if self.cav_info[v_idx]['route_with_lane'][edge] >= 0:
                    traci.vehicle.changeLane(
                        vehID=cav_id,
                        laneIndex=self.cav_info[v_idx]['route_with_lane'][edge],
                        duration=10
                    )
            except Exception as e:
                print(f"Skipping v_idx={v_idx} due to error: {e}")
                continue


    def updateObsv(self):
        """
        06/22/2023 update: use this function to check observation and cover time-space table
        step2: check observation and update link-flow table (value only); then the output also calculate
        link-cost with observed data or historical data
        self.link_flows_table = current link-flow information
        :return:
        """
        time_idx = round(self.time)
        for edge in traci.edge.getIDList():
            edge_idx = int(re.findall(r'[0-9]+|[a-z]+', edge)[0]) - 1
            # vv_id = traci.edge.getLastStepVehicleIDs(edge)
            # if time_idx == 40:
            #     print('llll')
            if edge_idx < self.link_num:
                v_id = traci.edge.getLastStepVehicleIDs(edge)  # vehicle id list
                for v in v_id:
                    v_tem = re.findall(r'[0-9]+|[a-z]+', v)  # [type, num]
                    if v_tem[0] == 'cav':
                        cav_idx = int(v_tem[1])  # cav index = cav numbber - 1
                        for eID in range(self.cover_LinkTimeVeh.shape[0]):
                            self.cover_LinkTimeVeh[
                                eID, time_idx, cav_idx] = 0  # clear current edge occupation before update
                        if edge[0] == '-':
                            self.cover_LinkTimeVeh[edge_idx + self.link_num, time_idx, cav_idx] = 1
                        else:
                            self.cover_LinkTimeVeh[edge_idx, time_idx, cav_idx] = 1

    def update_lf_table(self):
        for k, v in self.link_flows_table.items():
            eg_id = traci.edge.getLastStepVehicleIDs(k)
            self.link_flows_table[k] = list(set(v) | set(eg_id))

    def filter_lf_table(self):
        """
        Note: this is the function is enumerate the lf table and remove cav information
        :param self.link_flow_table
        :return:
        """
        self.link_flows_num = {}
        for k, v in self.link_flows_table.items():
            for id in v:
                if re.findall(r'[0-9]+|[a-z]+', id)[0] == 'cav':
                    v.remove(id)
            self.link_flows_num[k] = (3600 * len(v)) / (self.time - self.start_time)
            """od_i, n = re.findall(r'[0-9]+|[a-z]+', id)  # od_idx, v_idx"""
            # v.append(ttmp)

    def updateCAVinfo_StopandForward(self):
        """
        This is the old TRB version to update the CAV info
        """
        for v_id in traci.vehicle.getIDList():
            if traci.vehicle.getTypeID(v_id) == 'cav':
                edge_current = traci.vehicle.getRoadID(v_id)  # check if the vehicle in the network
                nextNode = self.network.getNextNode((edge_current))
                # step1: calculate and update flexibility
                if v_id not in self.cav_dic:
                    # default add vehicle initial state
                    sp_length = self.network.getShortDistance(self.network.getNextNode(traci.vehicle.getRoute(v_id)[0]),
                                                              self.network.getFromNode(
                                                                  traci.vehicle.getRoute(v_id)[-1]))
                    self.cav_dic[v_id] = {'original': self.network.getNextNode(traci.vehicle.getRoute(v_id)[0]),
                                          'destination': self.network.getFromNode(traci.vehicle.getRoute(v_id)[-1]),
                                          'Flex': [self.flex],  # initial flexibility, must be even number
                                          'currentFlex': self.flex,
                                          'deltaCover': 1,
                                          'spLength': sp_length,
                                          'currentRoute': [None],
                                          'isControl': True,
                                          # this is the flag that determines if cav need to be controlled.
                                          'nextEdges': None}
                elif self.cav_dic[v_id]['isControl']:  # if not first time, update flexibility
                    if int(re.findall(r'[0-9]+|[a-z]+', edge_current)[0]) <= self.link_num:

                        last_edge = self.cav_dic[v_id]['currentRoute'][-1]
                        if edge_current != last_edge:
                            self.cav_dic[v_id]['currentRoute'].append(edge_current)
                        # if not (edge_current[0] == '-' and int(
                        #         re.findall(r'[0-9]+|[a-z]+', edge_current)[0]) > self.link_num):
                        # nextNode_tmp = self.network.getNextNode(edge_current)
                        sp_current = self.network.getShortDistance(nextNode, self.cav_dic[v_id]['destination'])
                        # 1103 update: current flexibility = original sp length + initial flexibility - number of edges traveled - current sp length
                        tmp_flex = self.cav_dic[v_id]['spLength'] + self.cav_dic[v_id]['Flex'][0] - len(
                            self.cav_dic[v_id]['currentRoute']) + 1 - sp_current
                        self.cav_dic[v_id]['Flex'].append(max(tmp_flex, 0))
                        self.cav_dic[v_id]['currentFlex'] = max(tmp_flex, 0)
                        # if tmp_flex == 0:
                        #     print('we have something')
                print(
                    f'vehicle {v_id} has flex {self.cav_dic[v_id]["currentFlex"]} with {self.cav_dic[v_id]["isControl"]}')
                # step2: determine the intended next edge if in no changing zone
                if not (edge_current[0] == '-' and int(
                        re.findall(r'[0-9]+|[a-z]+', edge_current)[0]) > self.link_num):
                    # edge_idxnum = int(re.findall(r'[0-9]+|[a-z]+', edge_current)[0])
                    lane_current = traci.vehicle.getLaneID(v_id)  # lane id for the current vehicle
                    lane_tmp = self.network.sumonet.getLane(lane_current)  # lane object for current vehicle
                    # edges_outid = [e.getID() for e in self.network.node_list[nextNode].link_idx['out']]
                    # aa = self.network.sumonet.getEdge(edge_current).getLength() - traci.vehicle.getLanePosition(v_id)
                    if self.network.sumonet.getEdge(edge_current).getLength() - traci.vehicle.getLanePosition(
                            v_id) <= 160:
                        self.cav_dic[v_id]['nextEdges'] = [cnt.getTo().getID() for cnt in
                                                           lane_tmp.getOutgoing()]  # if vehicle in no changing zone
                    else:
                        # print(f'next Node is {nextNode}, veh{v_id} in nochanging zone')
                        self.cav_dic[v_id]['nextEdges'] = [e.getID() for e in self.network.node_list[nextNode].link_idx[
                            'out']]  # if not in no-changing zone
                #

    def updateRoute(self, k, parameters):
        """
        step2: enumerate all cav from list, choose proper route and update vehicle information
                # -steps:
                # -2A: enumerate all cav. for each cav.
                #       -2AA: get k-shortest path considering distance
                #       -2AB: calculate travel time and cover rate for each candidate route
                #       -2AC: choose the best route and apply accordingly
                #       -2AD: update CAV routing table
        :return:
        """
        for cav_id in self.cav_list:
            print(f'start from veh {cav_id}')
            # 1204 update: check control flag first
            if self.cav_dic[cav_id]['isControl']:
                # print(f'current veh idx is {cav_id} in a list of {self.cav_list}')
                # 1.get k shortest path considering distance
                veh_idx = int(re.findall(r'[0-9]+|[a-z]+', cav_id)[1])
                cav_edgeID = traci.vehicle.getRoadID(cav_id)
                my_nextNode = self.network.getNextNode(cav_edgeID)
                sp_length = (self.cav_dic[cav_id]['spLength'] * 400) / 14

                k_shortest_path = self.network.findKShortPath(k, my_nextNode, self.cav_dic[cav_id]['destination'],
                                                              self.cav_dic[cav_id]['currentFlex'])

                # filter k_shortest_path with the following rules: (20231203)
                # 1. remove the routes that not realistic based on the no changing zone regulation
                # 2. z

                # 0710: get vehicle departure time
                # tmp = traci.vehicle.getDeparture(cav_id)
                dep_time = traci.vehicle.getDeparture(cav_id)  # get departure time

                # 2. calculate travel time and cover rate for each candidate route
                # 3. get delta_cover for each candidate path
                arrive_time_table = []  # store the node arrive time for each path selection
                delta_cover_table = []  # store the change of cover rate for each candidate path
                path_obj_table = []  # store the object value for each candidate path

                # objective value for last candidate path, since the objective is to get max, the default number is -1000000.
                last_bestRoute_obj = -1000000

                # print(f'check cover table at start of {cav_id} at time {self.time}')
                # self.checkCoverTable()
                # print(f'vehicle {cav_id} has sp {k_shortest_path} ')

                # remove future route for selected vehicle
                for l in range(self.cover_LinkTimeVeh.shape[0]):
                    for t in range(int(self.time), self.cover_LinkTimeVeh.shape[1]):
                        self.cover_LinkTimeVeh[l, t, veh_idx] = 0
                # print(f'begin to check if cover table is cleared for vehicle {cav_id} at time {self.time} on path {sp}')
                self.checkCoverTable()
                cover_LTV_tmp = copy.deepcopy(self.cover_LinkTimeVeh)

                # enumerate all candidate path, select the possible paths that fits the no-changing zone restriction
                route_candidate = []
                for sp in k_shortest_path:
                    # print(f'current route{sp} is for vehcile {cav_id}')
                    route = [cav_edgeID]
                    for node_idx in range(len(sp) - 1):
                        node2edge = self.network.node_list[sp[node_idx + 1]].getEdgeByUpperNode(sp[node_idx])
                        route.append(node2edge)
                    route.append(traci.vehicle.getRoute(cav_id)[-1])
                    """
                    06/21/2023: 
                    - until now, <tmp> & <sp> has been DUIQI !!!
                    - next step is to calculate arrival time for each node in sp with route[:-1]
                    - another input is an if table about if the edge is observed currently
                    """
                    if route[1] in self.cav_dic[cav_id]['nextEdges']:
                        route_candidate.append([sp, route])  # pairing node path and edge path

                del k_shortest_path

                for (sp, route) in route_candidate:
                    node_time = self.network.getNodeArrTime(route[:-1], sp, self.time, cav_id,
                                                            self.link_flows_hisNum)  # arrive time on each node for given path route
                    arrive_time_table.append(node_time[-1])

                    # 0630update: 4. We need to remove the current veh from current time to the future.

                    # this is the end of arrive time calculation, next is the change of cover rate
                    # cover_ts_pre = copy.deepcopy(self.cover_LinkTimeVeh)  # get a tmp matrix to calculate cover
                    # cover_ts_pre = np.copy(self.cover_LinkTimeVeh)

                    node_timeTmp = copy.deepcopy(node_time)
                    node_timeTmp.insert(0, self.time)

                    route_startTime = round(node_timeTmp[0])
                    route_endTime = round(node_timeTmp[-1])
                    duration = route_endTime - route_startTime
                    # predicted cover rate for given route,  this is temp data point
                    # cover_ts_pre = np.copy(self.cover_LinkTimeVeh[:, route_startTime: route_endTime, :])
                    cover_ts_pre = copy.deepcopy(cover_LTV_tmp[:, route_startTime: route_endTime, :])

                    for idx in range(len(route[:-1])):
                        edge_idx_num = int(re.findall(r'[0-9]+|[a-z]+', route[:-1][idx])[0])
                        if edge_idx_num < self.link_num:
                            # # determine the start and end time point for each occupation
                            # start_idx = node_timeTmp[1]
                            # end_idx = int(node_timeTmp[2])
                            if route[:-1][idx][0] == '-':
                                link_pos = edge_idx_num + self.link_num  # determine the link idx in cover time-space table
                            else:
                                link_pos = edge_idx_num
                            for k in range(round(node_timeTmp[idx]) - int(node_timeTmp[0]),
                                           round(node_timeTmp[idx + 1]) - int(node_timeTmp[0])):
                                # print(k)
                                cover_ts_pre[link_pos - 1, k - 1, veh_idx] = 1

                    # get the time-space cover table
                    cover_pre = np.where(np.sum(cover_ts_pre, axis=2) > 0, 1, 0)
                    cover_now = np.where(
                        np.sum(cover_LTV_tmp[:, route_startTime: route_endTime, :], axis=2) > 0,
                        1, 0)

                    cover_delta = (np.sum(cover_pre) - np.sum(cover_now)) / duration
                    delta_cover_table.append(cover_delta)

                    # 4. calculate objective and get best route, update the routing based on best objective
                    #  0710 YW: update objective considering total travel time instead of current steps.
                    current_route_obj = - (parameters[0] / sp_length) * (node_time[-1] - dep_time) + parameters[
                        1] * cover_delta
                    path_obj_table.append(current_route_obj)
                    if current_route_obj >= 1.10 * last_bestRoute_obj:  # bubble up and get best
                        best_cover = cover_ts_pre
                        best_rou_end = route_endTime
                        best_route_node = sp  # get best route idx and path(node)
                        last_bestRoute_obj = current_route_obj
                        best_travel_time = (node_time[-1] - dep_time)

                        # best_route = [cav_edgeID]
                        # # convert node path to edge path
                        # for node_idx in range(len(best_route_node) - 1):
                        #     node2edge = self.network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                        #         best_route_node[node_idx])
                        #     best_route.append(node2edge)

                        self.cav_dic[cav_id]['deltaCover'] = cover_delta
                        # print(f'vehicle {cav_id} delta cover is {cover_delta}')

                        # stop planning threshold
                        if (abs(self.cav_dic[cav_id]['deltaCover'] - 1) < 0.01 or self.cav_dic[cav_id][
                            'currentFlex'] == 0):
                            self.cav_dic[cav_id]['isControl'] = False

                            best_route = [cav_edgeID]
                            # convert node path to edge path
                            for node_idx in range(len(best_route_node) - 1):
                                node2edge = self.network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                                    best_route_node[node_idx])
                                best_route.append(node2edge)
                            self.cover_LinkTimeVeh[:, route_startTime: best_rou_end, :] = best_cover
                            best_route.append(traci.vehicle.getRoute(cav_id)[-1])
                            traci.vehicle.setRoute(cav_id, best_route)
                            print(
                                f'vehicle {cav_id} is set to False with route {best_route}, flex is {self.cav_dic[cav_id]["Flex"]} and cover is {self.cav_dic[cav_id]["deltaCover"]}')
                            break
                        # self.cav_dic[cav_id]['isControl'] = False if (abs(self.cav_dic[cav_id]['deltaCover'] - 1) < 0.05 or self.cav_dic[cav_id]['Flex'] == 0) else True
                        isctrl = self.cav_dic[cav_id]['isControl']
                        # pr
                        # hicle {cav_id} current node is {best_route_node} best obj is {last_bestRoute_obj} with time {best_travel_time} and cover {cover_delta}, control is {isctrl}')
                        del cover_ts_pre, cover_pre
                    if sp == route_candidate[-1][0]:  # in the last, update route and
                        isctrl = self.cav_dic[cav_id]['isControl']
                        best_route = [cav_edgeID]
                        # convert node path to edge path
                        for node_idx in range(len(best_route_node) - 1):
                            node2edge = self.network.node_list[best_route_node[node_idx + 1]].getEdgeByUpperNode(
                                best_route_node[node_idx])
                            best_route.append(node2edge)
                        self.cover_LinkTimeVeh[:, route_startTime: best_rou_end, :] = best_cover
                        best_route.append(traci.vehicle.getRoute(cav_id)[-1])
                        traci.vehicle.setRoute(cav_id, best_route)
                        print(
                            f'vehicle {cav_id} current route is {best_route} with best obj {last_bestRoute_obj} with time {best_travel_time}, control is {isctrl}')

                        del cover_LTV_tmp

                # print('yes')
            else:
                print(f'vehicle {cav_id} will not be controlled due to its best route')
        # return

    def save_lf(self, path):  # save link flow table to file, this is designed for history collection
        with open(path, "w") as outfile:
            json.dump(self.link_flows_num, outfile)
            print('nn')

    def load_lf(self, path):  # this load link flow history
        with open(path, "r") as infile:
            self.link_flows_hisNum = json.load(infile)

    ###20231011: some debug tools
    def checkCoverTable(self):
        # cover table  = [edge, time, veh]
        v_idx = traci.vehicle.getIDList()
        for v in v_idx:
            v_tem = re.findall(r'[0-9]+|[a-z]+', v)  # [type, num]
            if v_tem[0] == 'cav':
                cav_idx = int(v_tem[1]) - 1
                tableLinkTime = self.cover_LinkTimeVeh[:, :, cav_idx]
                for t in range(tableLinkTime.shape[1]):
                    # print(np.sum(tableLinkTime[:, t]))
                    if np.sum(tableLinkTime[:, t]) > 1:
                        print(f"Vehicle {cav_idx + 1} is more than one pos at time {t}, current time is {self.time}:")

    def getCellidxFromVeh(self, v_id):
        """
        return CTM cell index, cell coordination (upper & lower bound), based on the vehicle given
        """
        cell_coord = []  # [upper bound x, lower bound x, lanes]
        link_long_x = traci.vehicle.getLanePosition(v_id)
        # cav_linklongitude_coord = traci.vehicle.getLanePosition(v_id)
        edge_idx, lane_idx = re.search(r'([-\w]+)_(\d+)', traci.vehicle.getLaneID(v_id)).group(1), re.search(
            r'([-\w]+)_(\d+)', traci.vehicle.getLaneID(v_id)).group(2)
        length = self.network.sumonet.getEdge(edge_idx).getLength()
        # idx = divmod(cav_linklongitude_coord, 80)[0]
        idx = link_long_x // 80  # assume cell is 80 meter long
        c_id = None
        if length < 400 and edge_idx[0] != '-':  # hard-coding here as entry link
            if idx == 0:
                c_id = 'A1.{}.{}'.format(edge_idx, 'C40')
                cell_coord = [80, 0, [0, 1]]
            elif idx == 1:
                c_id = 'A1.{}.{}'.format(edge_idx, 'C5')
                cell_coord = [160, 80, [0, 1]]
            elif idx >= 2 and lane_idx == '0':
                c_id = 'A1.{}.{}'.format(edge_idx, 'C7')
                cell_coord = [240, 160, [0]]
            elif idx >= 2 and lane_idx == '1':
                c_id = 'A1.{}.{}'.format(edge_idx, 'C6')
                cell_coord = [240, 160, [1]]
        elif length < 400 and edge_idx[0] == '-':  # hard-coding here as exit link
            if idx == 0 and lane_idx == '0':
                c_id = 'A1.{}.{}'.format(edge_idx, 'C2')
                cell_coord = [80, 0, [0]]
            elif idx == 0 and lane_idx == '1':
                c_id = 'A1.{}.{}'.format(edge_idx, 'C1')
                cell_coord = [80, 0, [1]]
            elif idx == 1:
                c_id = 'A1.{}.{}'.format(edge_idx, 'C3')
                cell_coord = [160, 80, [0, 1]]
            elif idx >= 2:
                c_id = 'A1.{}.{}'.format(edge_idx, 'C4')
                cell_coord = [240, 160, [0, 1]]

        else:  # normal link
            if idx == 0 and lane_idx == '0':
                c_id = 'A0.{}.{}'.format(edge_idx, 'C2')
                cell_coord = [80, 0, [0]]
            elif idx == 0 and lane_idx == '1':
                c_id = 'A0.{}.{}'.format(edge_idx, 'C1')
                cell_coord = [80, 0, [1]]
            elif idx == 1:
                c_id = 'A0.{}.{}'.format(edge_idx, 'C3')
                cell_coord = [160, 80, [0, 1]]
            elif idx == 2:
                c_id = 'A0.{}.{}'.format(edge_idx, 'C4')
                cell_coord = [240, 160, [0, 1]]
            elif idx == 3:
                c_id = 'A0.{}.{}'.format(edge_idx, 'C5')
                cell_coord = [320, 240, [0, 1]]
            elif idx >= 4 and lane_idx == '0':
                c_id = 'A0.{}.{}'.format(edge_idx, 'C7')
                cell_coord = [400, 320, [0]]
            elif idx >= 4 and lane_idx == '1':
                c_id = 'A0.{}.{}'.format(edge_idx, 'C6')
                cell_coord = [400, 320, [1]]
        if c_id == None:
            with open('log.txt', 'a') as f:
                f.write(f'cav {v_id} cannot find its cell at step {self.step}, location edge at {edge_idx} lane {lane_idx}'
                        f'link long position {link_long_x}, idx {idx} \n')

        return c_id, cell_coord

    def getCTMObservation(self):
        """
        task 1: update CAV cell-time observation
        task 2: update cell coverage table
        task 3: determine cav no changing zone
        """
        update_table = {}

        for cav_id in self.cav_list:
            cell_id, info = self.getCellidxFromVeh(cav_id)
            edge_idx, lane_idx = re.search(r'([-\w]+)_(\d+)', traci.vehicle.getLaneID(cav_id)).group(1), re.search(
                r'([-\w]+)_(\d+)', traci.vehicle.getLaneID(cav_id)).group(2)
            update_table[cell_id] = self.getVehNumfromEdge(edge_idx, info[0], info[1], info[2])
            """20250601: update cell coverage table"""
            self.cell_occupation[self.cell_idx.index(cell_id), (self.step // (5 * 10))] += 1
            # Record CAV cell-entry only on transitions (RLE-collapse consecutive same-cell samples).
            if self.cav_last_cell.get(cav_id) != cell_id:
                self.cav_cell_events.setdefault(cav_id, []).append((cell_id, self.step // (5 * 10)))
                self.cav_last_cell[cav_id] = cell_id
            """20250620: update vehicle no changing zone"""
            """20250715: bug fixing: this could affect benchmark planning if not routing. is this still necessary???"""
            # if self.network.sumonet.getEdge(edge_idx).getLength() - traci.vehicle.getLanePosition(
            #         cav_id) <= 80:  # last cell length as 80 meters, this is a hardcoded constrain.
            #     traci.vehicle.setLaneChangeMode(cav_id, 512)
        return update_table

    def getCTMgroundTruth(self):
        veh_list = traci.vehicle.getIDList()
        for veh in veh_list:
            cell_id, info = self.getCellidxFromVeh(veh)
            if cell_id is None:
                print(f'veh {veh} is in')
                continue
            else:
                self.ctm_groundtruth[self.cell_idx.index(cell_id), (self.step // (5 * 10))] += 1
        return

    def getCTMrecord(self):
        for cid, cell in self.CTM.cells_dic.items():
            self.ctm_recordings[self.cell_idx.index(cid), self.step // (5 * 10)] = cell.get_state_num()

    def saveEvaluation(self):
        np.save(f'{self.saving_path['ctm']}/ctm_gt.npy', self.ctm_groundtruth)
        np.save(f'{self.saving_path['ctm']}/ctm_rec.npy', self.ctm_recordings)
        np.save(self.saving_path['occupation'], self.cell_occupation)
        with open(self.saving_path['time_optim'], 'wb') as file:
            pickle.dump(self.optim_time, file)
        with open(self.saving_path['num_cav'], 'wb') as file:
            pickle.dump(self.num_of_cav, file)
        # save trip info
        with open(self.saving_path['od_route'], "w") as j_file:
            json.dump(self.cav_tripInfo, j_file, indent=4)
        # Save per-CAV cell-entry events for segment popularity computation.
        with open(self.saving_path['cav_cell_events'], 'wb') as file:
            pickle.dump(self.cav_cell_events, file)


    @staticmethod
    def getVehNumfromEdge(edge_id, upper, lower, lanes):
        """
        this function returns the number of vehicles in a cell in given edge.
        :param edge_id: the idx for the edge
        :param upper: the upper boundary for the distance (start as 0)
        :param lower: the lower boundary for the distance (end as 0)
        :param lanes: lane indexes included in the cell
        """
        count = 0
        veh_ls = list(traci.edge.getLastStepVehicleIDs(edge_id))
        for v in veh_ls:
            lane_idx = re.search(r'([-\w]+)_(\d+)', traci.vehicle.getLaneID(v)).group(2)
            # aa = traci.vehicle.getDistance(v)
            if ((traci.vehicle.getLanePosition(v) <= upper and traci.vehicle.getLanePosition(v) >= lower) and (
                    int(lane_idx) in lanes)):
                count += 1

        return count


