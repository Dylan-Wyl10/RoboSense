import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


class CTM_model:
    def __init__(self, fp="Plymouth/CTM_Plymouth_0207update.csv", sim_len=2100):

        self.sim_len = sim_len  # total simulation length (s)
        self.step_tt = np.zeros([sim_len])  # travel time
        self.step_delay = np.zeros([sim_len])  # delay

        # Initialize Signal Controller
        P = 4  # number of signal phases + AR phase
        self.signal = np.zeros(
            [self.sim_len, P])  # signal[row time][column phase], value 1 represent the phase is chosen

        network = pd.read_csv(fp, header=0,
                                        names=["cell_idx", "type", "n_pre_cell", "pr1", "pr2", "pr3",
                                               "n_fol_cell", "fo1", "fo2", "fo3", "jam_den", "capacity",
                                               "turn_l", "turn_th", "turn_r", "phase", "demand", "intersection",
                                               "approach", "num_lane", "seg_idx"])
        network = network.astype(str)
        network.type = network.type.astype(int)
        network.jam_den = network.jam_den.astype(float)
        network.capacity = network.capacity.astype(float)
        network.n_pre_cell = network.n_pre_cell.astype(int)
        network.n_fol_cell = network.n_fol_cell.astype(int)
        network.phase = network.phase.astype(int)
        network.turn_l = network.turn_l.astype(float)
        network.turn_th = network.turn_th.astype(float)
        network.turn_r = network.turn_r.astype(float)
        network.demand = network.demand.astype(float)
        network.num_lane = network.num_lane.astype(int)
        network.seg_idx = network.seg_idx.astype(int)
        self.total_demand = sum(network.demand)
        self.cell_dict = network.set_index('cell_idx').T.to_dict()

        # Intialize n, y, z as np.array to store cell status at the each time step
        self.n_cell = len(self.cell_dict)  # total number of cells, including all types of cells
        self.n_i_t = np.zeros([self.sim_len, self.n_cell])  # number of vehicle at cell i at time t
        self.y_i_t = np.zeros([self.sim_len, self.n_cell])  # number of vehicle entering cell i at time [t,t+1)
        self.z_i_t = np.zeros([self.sim_len, self.n_cell])  # number of vehicle leaving cell i at time [t,t+1)
        self.turn_ratio_dict = {}
        self.diverging_outflow = {}

        #         ffs=15; %free flow speed m/s
        #         t_step=2; %2s time step in ctm
        #         c_length=ffs*t_step; %cell length
        #         N=4; %Jam Density (one lane)
        #         Q=1; %Capacity (one lane)
        #         %Assuming triangle FD, calculate backward shockwave speed:
        #         kj=1000/(c_length/N);
        #         km=(Q/t_step*3600)/(ffs*3.6);
        #         w=(Q/t_step*3600)/(kj-km)/3.6;  %backwards shockwave speed m/s
        #         alpha=w/ffs;
        #         P=4;  %totally 4 phases

        # initialize parameters, assuming triangle FD
        self.v_f = 17.88  # m/s
        self.delta_t = 1
        self.delta_x = self.v_f * self.delta_t
        for idx in self.cell_dict.keys():
            # here we calculate the parameter for each cell
            N = self.cell_dict[idx]['jam_den']
            # Q = cell_dict[idx]['capacity']
            n_lane = self.cell_dict[idx]['num_lane']
            q_max = 1800 / 3600 * self.delta_t  # maximum flow rate per lane, veh/hr/lane -> veh/s/lane
            Q = q_max * n_lane
            k_jam = 1000 / (self.delta_x / (N / n_lane))  # jam density, veh/km
            k_cri = (q_max * 3600) / (self.v_f * 3.6)  # k_cri = (Q/self.delta_t*3600)/(self.v_f*3.6)  # veh/km
            w = (q_max * 3600) / (k_jam - k_cri) / 3.6  # shockwave speed, m/s
            alpha = w / self.v_f
            self.cell_dict[idx].update({
                "N": N,
                "Q": Q,
                "q_max": q_max,
                "k_jam": k_jam,
                "k_cri": k_cri,
                "w": w,
                "alpha": alpha
            })
            # print("cell_dict: cell",idx,cell_dict[idx]["w"]) ###
            if self.cell_dict[idx]['type'] == 1:  # diverging cell
                self.turn_ratio_dict[idx] = {self.cell_dict[idx]['fo1']: self.cell_dict[idx]['turn_l'],
                                             self.cell_dict[idx]['fo2']: self.cell_dict[idx]['turn_th'],
                                             self.cell_dict[idx]['fo3']: self.cell_dict[idx]['turn_r']}
                self.diverging_outflow[idx] = {self.cell_dict[idx]['fo1']: 0,
                                               self.cell_dict[idx]['fo2']: 0,
                                               self.cell_dict[idx]['fo3']: 0}

    def run_CTM(self, curr_phase, curr_t, pred_horizon=10):
        '''
        INPUT:
        curr_phase = int, current signal phase, index from 0 to (#phases-1) for green phase; index as #phase (or -1) represents the AR
        curr_t = int, current time step
        pred_horizon = int, prediction horizon (number of time steps)

        OUTPUT:
        the predicted cell status for the pred_horizon length of time.
        the estimated total vehicle delay, travel time at each time step in the prediction horizon.
        '''

        if self.sim_len < pred_horizon + curr_t:
            print(
                "WARNING: Prediction length over the simulation length! Enforce the pred horizon to be the difference between current time and simulation length")
            pred_horizon = int(self.sim_len - curr_t)

        # get cell status at time t
        #         pred_n_i_t = np.zeros([pred_horizon,self.n_cell])
        #         pred_n_i_t[0,:] = self.n_i_t[curr_t,:]

        self.signal[curr_t:curr_t + pred_horizon, curr_phase] = 1  # current phase value be set as 1

        #####update cell status for pre-horizon of time based on cell types######

        for t in range(curr_t, curr_t + pred_horizon):

            ## update leaving flow
            for i in range(self.n_cell):
                if self.cell_dict[str(i + 1)]["type"] in [0, 2, 3, 5]:  # ordinary, intersection, merging, source cell
                    # cell i
                    Q_i = self.cell_dict[str(i + 1)]["Q"]
                    N_i = self.cell_dict[str(i + 1)]["N"]
                    alpha = self.cell_dict[str(i + 1)]["alpha"]
                    n_i = self.n_i_t[t, i]

                    # following cells of i. for these types, # of fol is 1.
                    for f_cell in range(self.cell_dict[str(i + 1)]["n_fol_cell"]):
                        fo_cell_idx = self.cell_dict[str(i + 1)]["fo" + str(f_cell + 1)]
                        Q_i_f = self.cell_dict[fo_cell_idx]["Q"]
                        N_i_f = self.cell_dict[fo_cell_idx]["N"]
                        n_i_f = self.n_i_t[t, int(fo_cell_idx) - 1]

                        # cal z_i_t: minimum of ni(t),Qi(t),Qi+1(t),a(Ni+1(t)-ni+1(t))
                        # print("cell",i,"time",t,"calculate z_i_t: min",[n_i, Q_i, Q_i_f, alpha*(N_i_f - n_i_f)]) ###
                        if self.cell_dict[str(i + 1)]["type"] == 5:
                            self.z_i_t[t, i] = min([n_i, Q_i, Q_i_f])
                        else:
                            if alpha * (N_i_f - n_i_f) < 0:
                                f_cell_f = 0
                            else:
                                f_cell_f = alpha * (N_i_f - n_i_f)
                            self.z_i_t[t, i] = min(
                                [n_i, Q_i, Q_i_f, f_cell_f])  # should we use z_i_t or directly update the self.z_i_t?
                        #                             if i == 10:
                        #                                 print("cell 11: [n_i, Q_i, Q_i_f, f_cell_f] at t",t, [n_i, Q_i, Q_i_f, f_cell_f]) ###
                        if (self.cell_dict[str(i + 1)]["type"] == 2) and (
                                self.cell_dict[str(i + 1)]["phase"] != 0):  # intersection cell
                            phase = self.cell_dict[str(i + 1)]["phase"] - 1  # ranging from 0 to #phase
                            self.z_i_t[t, i] = self.z_i_t[t, i] * self.signal[t, phase]


                elif self.cell_dict[str(i + 1)]["type"] == 1:  # diverging cell
                    # following cells of i
                    Q_i = self.cell_dict[str(i + 1)]["Q"]
                    N_i = self.cell_dict[str(i + 1)]["N"]
                    alpha = self.cell_dict[str(i + 1)]["alpha"]
                    #                     print("alpha",alpha,'cell',i+1)
                    n_i = self.n_i_t[t, i]
                    total_max_outflow = min([n_i, Q_i])
                    total_outflow = 0
                    #                     if i == 11:
                    #                             print("cell 12 at time",t,"total_max_out_flow = min[n_i,Q_i]", [n_i,Q_i]) ###

                    for f_cell in range(self.cell_dict[str(i + 1)]["n_fol_cell"]):
                        # TODO: ask Prof.Feng about the left_veh in the original code
                        fo_cell_idx = self.cell_dict[str(i + 1)]["fo" + str(f_cell + 1)]
                        Q_i_f = self.cell_dict[fo_cell_idx]["Q"]
                        N_i_f = self.cell_dict[fo_cell_idx]["N"]
                        n_i_f = self.n_i_t[t, int(fo_cell_idx) - 1]

                        #                         if f_cell == 0:
                        #                             turn_ratio = self.cell_dict[str(i+1)]["turn_l"]
                        #                         elif f_cell == 1:
                        #                             turn_ratio = self.cell_dict[str(i+1)]["turn_th"]
                        #                         elif f_cell == 2:
                        #                             turn_ratio = self.cell_dict[str(i+1)]["turn_r"]
                        # print("self.turn_ratio_dict[i][fo_cell_idx]",self.turn_ratio_dict,i,fo_cell_idx)
                        j_flow = total_max_outflow * self.turn_ratio_dict[str(i + 1)][fo_cell_idx]

                        # cal z_i_t: minimum of ni(t),Qi(t),Qi+1(t),a(Ni+1(t)-ni+1(t))
                        if alpha * (N_i_f - n_i_f) < 0:
                            f_cell_f = 0
                        else:
                            f_cell_f = alpha * (N_i_f - n_i_f)
                        outflow = min([j_flow, Q_i_f, f_cell_f])  # note this line is different from original code

                        #                         if i == 11:
                        #                             print("cell 12 at time",t,"to following cell",fo_cell_idx," min([j_flow,Q_i_f,f_cell_f])", [j_flow,Q_i_f,f_cell_f]) ###

                        # print("outflow for cell",i+1,"from fol_cell",f_cell+1," at time",t,[j_flow,Q_i_f,alpha*(N_i_f-n_i_f)]) ###
                        # TODO: consider about the spillback scenario, when one following cell is blocked
                        # TODO 0307: we would consider that even one of following cells is congested, the other cells
                        #    should be able to continue to hold traffic flows. -> then we need one array to store the outflow
                        #    of non-congested directions.
                        if outflow <= 0:
                            # total_outflow = 0
                            # break
                            self.diverging_outflow[str(i + 1)][fo_cell_idx] = 0
                        else:
                            self.diverging_outflow[str(i + 1)][fo_cell_idx] = outflow
                            total_outflow += outflow

                    self.z_i_t[t, i] = total_outflow

                elif self.cell_dict[str(i + 1)]["type"] == 4:  # sink cell
                    self.z_i_t[t, i] = self.n_i_t[t, i]
                else:
                    print("Error: wrong cell type for cell " + str(i + 1))

            ## update incoming flow
            for i in range(self.n_cell):
                if self.cell_dict[str(i + 1)]["type"] in [0, 1, 2, 4]:  # ordinary, intersection, diverging, sink cell

                    # previous cells
                    for p_cell in range(self.cell_dict[str(i + 1)]["n_pre_cell"]):
                        pr_cell_idx = self.cell_dict[str(i + 1)]["pr" + str(p_cell + 1)]

                        if self.cell_dict[pr_cell_idx]["type"] == 1:
                            # self.y_i_t[t,i] = self.z_i_t[t,int(pr_cell_idx)-1]*self.turn_ratio_dict[pr_cell_idx][str(i+1)]
                            self.y_i_t[t, i] = self.diverging_outflow[pr_cell_idx][str(i + 1)]
                        #                             if pr_cell_idx == '12':
                        #                                 print("time",t,"cell",i+1,"recieve flow from cell",pr_cell_idx,"get",self.y_i_t[t,i]) ###
                        else:
                            self.y_i_t[t, i] = self.z_i_t[t, int(pr_cell_idx) - 1]
                        #                         if i == 10:
                        #                             print("time",t,"cell 11 sending flow",self.y_i_t[t,i])
                        if self.y_i_t[t, i] < 0:
                            print("negative y!", self.y_i_t[t, i], "cell", i + 1, "time", t)  ###

                elif self.cell_dict[str(i + 1)]["type"] == 3:  # merging cell
                    Q_i = self.cell_dict[str(i + 1)]["Q"]
                    N_i = self.cell_dict[str(i + 1)]["N"]
                    alpha = self.cell_dict[str(i + 1)]["alpha"]
                    n_i = self.n_i_t[t, i]
                    total_inflow = 0

                    # previous cells
                    for p_cell in range(self.cell_dict[str(i + 1)]["n_pre_cell"]):
                        pr_cell_idx = self.cell_dict[str(i + 1)]["pr" + str(p_cell + 1)]
                        Q_i_p = self.cell_dict[pr_cell_idx]["Q"]
                        N_i_p = self.cell_dict[pr_cell_idx]["N"]
                        n_i_p = self.n_i_t[t, int(pr_cell_idx) - 1]
                        total_inflow += self.z_i_t[t, int(pr_cell_idx) - 1]

                    #                     if total_inflow > min([Q_i,alpha*(N_i-n_i)]):
                    #                         print("WARNING: cell",i+1,"at time",t,": inflow over the capacity")
                    #                         self.y_i_t[t,i] = min([Q_i,alpha*(N_i-n_i)]) ### TODO: should we update z_i_t then?
                    #                     else:
                    self.y_i_t[t, i] = total_inflow

                elif self.cell_dict[str(i + 1)]["type"] == 5:  # source cell
                    # in our case, we use demand. But why original code use 0?
                    self.y_i_t[t, i] = self.cell_dict[str(i + 1)]["demand"]
                else:
                    print("Error: wrong cell type for cell " + str(i + 1))

            ## update number of vehicle in each cell
            for i in range(self.n_cell):
                self.n_i_t[t + 1, i] = self.n_i_t[t, i] + self.y_i_t[t, i] - self.z_i_t[t, i]
                #                 if i in [11,13]: #[101,103]:
                #                     print("time",t,"cell",i+1,"self.n_i_t[t,i]",self.n_i_t[t,i]," + self.y_i_t[t,i] ",self.y_i_t[t,i] ,"- self.z_i_t[t,i]",self.z_i_t[t,i]) ###
                if self.n_i_t[t + 1, i] < 0:
                    print("negative n! cell", i, "time", t, "z", self.z_i_t[t, i], "y", self.y_i_t[t, i])

                # update travel time and delay
                self.step_tt[t] += self.n_i_t[t, i]  # vehicle inside the cell
                self.step_delay[t] += self.n_i_t[t, i] - self.z_i_t[t, i]  # vehicle that are still waiting

        total_delay = np.sum(self.step_delay[curr_t:curr_t + pred_horizon])
        pred_net_status = self.n_i_t[curr_t:curr_t + pred_horizon, :]

        return total_delay, pred_net_status

    def update_CTM(self, phase_obs_t, obs_t, data, pred_horizon=10):
        '''
        based on the observed cell status to update CTM prediction
        Logic:
            1. If get new detection result, update n_i_t at the observation time
            2. Using updated n_i_t to run CTM and predict new n_i_t within the prediction horizon

        INPUT:
            data: should be the data in signal_controller.py, structure follows: data:{lane_id:{veh_id:{"position":value,"xxx":xxx,...},...},...}
            phase_obs_t: current phase at the observation time
            obs_t: observation time
            pred_horizon: the length of time to generate CTM prediction
        '''
        # select cells that are observed
        # HOW CAN WE KNOW WHICH CELL IS OBSERVED? We can load CAV location?

        # convert the data to obs_n_i_t: from data structure to generate observation cell info -> replace the observed cell info in n_i_t

        # replace the observed cell info
        self.n_i_t[obs_t,
        :] = obs_n_i_t  # TODO: the obs_n_i_t here should be the combination of observation and CTM estimation for non-observation part

        # update self.n_i_t and re-run prediction
        total_delay, pred_net_status = self.run_CTM(phase_obs_t, obs_t, pred_horizon)

        return total_delay, pred_net_status

    def get_state_CTM(self, t):
        # based on n_i_t, y_i_t, and z_i_t get RL state information at time t
        # the number of segments is set to be 3

        veh_info_t = {app: {seg: [] for seg in range(4)} for app in range(1, 9)}
        veh_len = 5  # veh length, meter
        inc_app = [[1, 3], [5], [7]]
        out_app = [[2, 4], [6], [8]]

        num_veh_inc = np.zeros((len(inc_app), 3))
        num_veh_out = np.zeros((len(out_app), 3))
        avg_speed_inc = np.zeros((len(inc_app), 3))
        num_cell_seg = np.zeros((len(inc_app), 3))
        avg_delay_inc = np.zeros(len(inc_app))

        # re-arrange the n_i_t info based on approach and segment
        for i in range(self.n_cell):
            app_i = int(self.cell_dict[str(i + 1)]["approach"])
            seg_i = self.cell_dict[str(i + 1)]["seg_idx"]
            num_veh = self.n_i_t[t, i]
            # the outgoing flow (veh/s) equals to speed (m/s) as delta t is 1. -> actually, we consider number of lane in y
            # but speed info does not contain this info. therefore, we can not directly transfer y to speed by multiplying veh len.
            # we also need the number of lane info for each cell.
            speed_veh = self.z_i_t[t, i] * veh_len / self.cell_dict[str(i + 1)]["num_lane"]
            step_delay = self.n_i_t[t, i] - self.z_i_t[t, i]  # how to get the total delay?
            veh_info_t[app_i][seg_i].append(
                [num_veh, speed_veh])  # veh_info_t:{app_i:{seg_i:[[num_veh,speed_veh],[,]...]}

        # get number of vehicle in incoming lanes
        for phase_idx in range(len(inc_app)):
            for app_idx in inc_app[phase_idx]:
                for seg_idx in range(1, 4):
                    num_veh_inc[phase_idx][seg_idx - 1] += sum(
                        cell_info[0] for cell_info in veh_info_t[app_idx][seg_idx])

        norm_num_veh_in = np.linalg.norm(np.ravel(num_veh_inc))
        if norm_num_veh_in == 0:
            norm_num_veh_in = 1
        num_veh_inc_final = np.ravel(num_veh_inc) / norm_num_veh_in

        # get number of vbehicle in outgoing lanes
        for phase_idx in range(len(out_app)):
            for app_idx in out_app[phase_idx]:
                for seg_idx in range(1, 4):
                    num_veh_out[phase_idx][seg_idx - 1] += sum(
                        cell_info[0] for cell_info in veh_info_t[app_idx][seg_idx])
        norm_num_veh_out = np.linalg.norm(np.ravel(num_veh_out))
        if norm_num_veh_out == 0:
            norm_num_veh_out = 1
        num_veh_out_final = np.ravel(num_veh_out) / norm_num_veh_out

        # get avg speed (for incoming lanes): the cell-based avg speed is different from the veh-based avg speed.
        for phase_idx in range(len(out_app)):
            for app_idx in out_app[phase_idx]:
                for seg_idx in range(1, 4):
                    avg_speed_inc[phase_idx][seg_idx - 1] += sum(
                        cell_info[1] for cell_info in veh_info_t[app_idx][seg_idx])
                    num_cell_seg[phase_idx][seg_idx - 1] += 1
        avg_spd_CV = np.ravel(avg_speed_inc / num_cell_seg)
        norm_CV = np.linalg.norm(avg_spd_CV)
        if norm_CV == 0:
            norm_CV = 1
        avg_speed_inc_final = avg_spd_CV / norm_CV

        # get delay (how to transfer step delay to total delay for each vehicle?
        #    if we can't get such total delay, which is hard to fetch under augmented CV scenario as well,
        #    can the RL agent use step delay (i.e. the delay between two decison steps)?)

        return [avg_speed_inc_final, num_veh_inc_final, num_veh_out_final]

    def viz_CTM(self, start_t, end_t, legend_bar=0.1):
        '''
        viz the cell status, i.e. n_i_t, over time
        mainly for debugging, will not plot inside the CAVLight
        '''

        # 0: normal
        # 1: diverging
        # 2: intersection
        # 3: merging
        # 4: sink
        # 5: source
        color_set = {0: "gray", 1: "green", 2: "red", 3: "orange", 4: "blue", 5: "brown"}

        plt.figure(figsize=(10, 6))

        # TODO: color the line based on the cell type
        for i in range(self.n_cell):
            cell_type = self.cell_dict[str(i + 1)]["type"]
            if max(self.n_i_t[:, i]) > legend_bar:
                plt.plot(range(start_t, end_t), self.n_i_t[start_t:end_t, i], color=color_set[cell_type],
                         label="cell " + str(i + 1))
            else:
                plt.plot(range(start_t, end_t), self.n_i_t[start_t:end_t, i], color=color_set[cell_type])
        plt.xlabel("time (s)")
        plt.ylabel("density (vhe/mi)")
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title="Cells with density \n over " + str(legend_bar))
        plt.title("CTM Time-density diagram with " + str(self.n_cell) + " cells and " + str(
            int(self.delta_t)) + "s time interval")

    def viz_CTM_matrix(self, time):
        approach = {str(i): [] for i in range(1, 9)}
        for i in range(self.n_cell):
            app = self.cell_dict[str(i + 1)]["approach"]
            approach[app].append(i)

        fig, axs = plt.subplots(2, 4, sharex=True, figsize=(16, 8))

        # plt.setp(axs, xticks=range(time))

        for app_idx, cell_ls in approach.items():
            #             axs[int(app_idx)-1].set_yticks(cell_ls)
            #             axs[int(app_idx)-1].set_yticklabels(cell_ls)
            #             axs[int(app_idx)-1].set_ylabel(app_idx)
            #             im = axs[int(app_idx)-1].imshow(self.n_i_t[:time,cell_ls].T, cmap='hot')

            #             r_idx = (int(app_idx)-1)//4
            #             c_idx = (int(app_idx)-1)%4
            idx = [[0, 0], [1, 0],
                   [0, 1], [1, 1],
                   [0, 2], [1, 2],
                   [0, 3], [1, 3]]
            r_idx = idx[int(app_idx) - 1][0]
            c_idx = idx[int(app_idx) - 1][1]

            sns.heatmap(self.n_i_t[:time, cell_ls].T,
                        yticklabels=np.array(cell_ls) + 1,
                        cmap='crest',
                        ax=axs[r_idx, c_idx])
            axs[r_idx, c_idx].set_ylabel('approach ' + app_idx)

        #         cbar_ax = fig.add_axes([1.05, 0.15, 0.05, 0.7])
        #         fig.colorbar(im, cax=cbar_ax)

        # plt.colorbar(fraction=0.05)
        plt.tight_layout()
        plt.show()