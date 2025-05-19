# Here is the rewritten script using Gurobi syntax, following the structure of the original Pyomo script


import copy
import pandas as pd
import numpy as np
from gurobipy import Model, GRB, quicksum
import json
import time


class RouteOptimGurobi:
    def __init__(self, CTM_resultPath, CTM_FDParam):
        # Initialize data matrices from file paths
        self.CTM_numberMatrix_ori = pd.read_csv(CTM_resultPath['number']).iloc[:, 1:].to_numpy()
        self.CTM_numberOutMatrix_ori = pd.read_csv(CTM_resultPath['outnumber']).iloc[:, 1:].to_numpy()
        self.CTM_signalMatrix_ori = pd.read_csv(CTM_resultPath['sigflag']).iloc[:, 1:].to_numpy()
        self.CTM_connection_ori = np.loadtxt(CTM_resultPath['connectionMatrix'])

        with open(CTM_resultPath['cellIdx'], 'r') as file:
            self.CTM_cellIdx_ori = [line.strip() for line in file]

        self.max_time = 120
        self.CTM_cellIdx_downgrade = ['A1.E101.C0', 'A1.E101.C4', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7',
                                      'A1.E102.C0', 'A1.E102.C4', 'A1.E102.C5', 'A1.E102.C6', 'A1.E102.C7',
                                      'A1.E103.C0', 'A1.E103.C4', 'A1.E103.C5', 'A1.E103.C6', 'A1.E103.C7',
                                      'A1.E120.C0', 'A1.E120.C4', 'A1.E120.C5', 'A1.E120.C6', 'A1.E120.C7',
                                      'A1.-E101.C0', 'A1.-E101.C4', 'A1.-E101.C3', 'A1.-E101.C2', 'A1.-E101.C1',
                                      'A1.-E102.C0', 'A1.-E102.C4', 'A1.-E102.C3', 'A1.-E102.C2', 'A1.-E102.C1',
                                      'A1.-E103.C0', 'A1.-E103.C4', 'A1.-E103.C3', 'A1.-E103.C2', 'A1.-E103.C1',
                                      'A1.-E120.C0', 'A1.-E120.C4', 'A1.-E120.C3', 'A1.-E120.C2', 'A1.-E120.C1',
                                      'A0.E1.C1', 'A0.E1.C2', 'A0.E1.C3', 'A0.E1.C4', 'A0.E1.C5', 'A0.E1.C6',
                                      'A0.E1.C7',
                                      'A0.-E1.C1', 'A0.-E1.C2', 'A0.-E1.C3', 'A0.-E1.C4', 'A0.-E1.C5', 'A0.-E1.C6',
                                      'A0.-E1.C7',
                                      'A0.E2.C1', 'A0.E2.C2', 'A0.E2.C3', 'A0.E2.C4', 'A0.E2.C5',
                                      'A0.-E2.C1', 'A0.-E2.C2', 'A0.-E2.C3', 'A0.-E2.C4', 'A0.-E2.C5',
                                      'A0.E5.C1', 'A0.E5.C2', 'A0.E5.C3', 'A0.E5.C4', 'A0.E5.C5', 'A0.E5.C6',
                                      'A0.E5.C7',
                                      'A0.-E5.C1', 'A0.-E5.C2', 'A0.-E5.C3', 'A0.-E5.C4', 'A0.-E5.C5', 'A0.-E5.C6',
                                      'A0.-E5.C7',
                                      'A0.E6.C1', 'A0.E6.C2', 'A0.E6.C3', 'A0.E6.C4', 'A0.E6.C5',
                                      'A0.-E6.C1', 'A0.-E6.C2', 'A0.-E6.C3', 'A0.-E6.C4', 'A0.-E6.C5',
                                      'A0.E21.C1', 'A0.E21.C2', 'A0.E21.C3', 'A0.E21.C4', 'A0.E21.C5', 'A0.E21.C6',
                                      'A0.E21.C7',
                                      'A0.-E21.C1', 'A0.-E21.C2', 'A0.-E21.C3', 'A0.-E21.C4', 'A0.-E21.C5',
                                      'A0.-E21.C6', 'A0.-E21.C7',
                                      'A0.E22.C1', 'A0.E22.C2', 'A0.E22.C3', 'A0.E22.C4', 'A0.E22.C5',
                                      'A0.-E22.C1', 'A0.-E22.C2', 'A0.-E22.C3', 'A0.-E22.C4', 'A0.-E22.C5',
                                      'A0.E25.C1', 'A0.E25.C2', 'A0.E25.C3', 'A0.E25.C4', 'A0.E25.C5', 'A0.E25.C6',
                                      'A0.E25.C7',
                                      'A0.-E25.C1', 'A0.-E25.C2', 'A0.-E25.C3', 'A0.-E25.C4', 'A0.-E25.C5',
                                      'A0.-E25.C6', 'A0.-E25.C7',
                                      'A0.E26.C1', 'A0.E26.C2', 'A0.E26.C3', 'A0.E26.C4', 'A0.E26.C5',
                                      'A0.-E26.C1', 'A0.-E26.C2', 'A0.-E26.C3', 'A0.-E26.C4', 'A0.-E26.C5',
                                      ]
        downgrageIdx = [self.CTM_cellIdx_ori.index(ci) for ci in self.CTM_cellIdx_downgrade]

        self.CTM_numberMatrix = self.CTM_numberMatrix_ori[downgrageIdx, 100:100 + self.max_time]
        self.CTM_numberOutMatrix = self.CTM_numberOutMatrix_ori[downgrageIdx, 100:100 + self.max_time]
        self.CTM_signalMatrix = self.CTM_signalMatrix_ori[downgrageIdx, 100:100 + self.max_time]
        self.CTM_connection = self.CTM_connection_ori[np.ix_(downgrageIdx, downgrageIdx)]
        self.ctm_fd = CTM_FDParam

    def get_costCTM(self, number_matrix, outnumber, FD_param, signal_matrix):
        K = number_matrix / FD_param['length']  # density matrix
        Q = copy.deepcopy(K)
        # flow matrix
        for i in range(number_matrix.shape[0]):
            for j in range(number_matrix.shape[1]):
                Q[i, j] = FD_param['v_f'] * K[i, j] if K[i, j] <= FD_param['q_max'] / FD_param['v_f'] else -FD_param[
                    'w'] * (K[i, j] - FD_param['k_jam'])
        V = np.ones(K.shape) * FD_param['v_f']
        C = np.zeros(K.shape)
        V = V * signal_matrix
        for i in range(K.shape[0]):
            for j in range(K.shape[1]):
                V[i, j] = Q[i, j] / K[i, j] if K[i, j] != 0 else V[i, j]
                # start to calculate the time cost (number of time steps)
                step_need = 0
                distance_remained = FD_param['length']
                for jj in range(j, K.shape[1]):
                    distance_remained -= V[i, jj] * FD_param['delta_t']
                    step_need += 1
                    if distance_remained <= 0:
                        C[i, j] = step_need
                        break

        # C = number_matrix - outnumber  # travel delay, also denoted as travel cost for each cell over time
        # V = V * signal_matrix
        return K, Q, V, C
    
    @staticmethod
    def get_small_net_param():
        link, veh, time_step = 15, 2, 45
        C = np.ones((link, time_step))
        for i in range(C.shape[0]):
            for t in range(C.shape[1]):
                C[i, t] = (C[i, t] + i + t + 2) % 4 + 1 
        # c = {(i, t): (C[i, t] + i + t + 2) % 4 + 1 for i in range(C.shape[0]) for t in range(C.shape[1])}
        # self.c = c
        
        # 2x2 network
        con = {1: [2, 9], 2: [11], 3: [4, 10], 4: [12], 5: [6], 6: [14],
               7: [3, 8], 8: [5, 15], 9: [4, 10], 10: [6], 11: [12], 12: [14],
               13: [7, 1], 14: [], 15: []}

        connection = np.zeros((len(con.keys()), len(con.keys())))
        for k, v in con.items():
            for vv in v:
                connection[k - 1, vv - 1] = 1

        veh_od = {0: {'from': 12, 'to': 13, 'time': 0},
                  1: {'from': 12, 'to': 13, 'time': 0}}
        
        return veh_od, connection, time_step, C
        

    def build_model(self, veh_num=2, small_net=True, parseZ=True):
        print('start build model')
        # self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
        #                                                   self.CTM_signalMatrix)
        
        if small_net:
            self.veh_od, self.CTM_connection, time_step, self.C = self.get_small_net_param()
        else:
            self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix,
                                                              self.ctm_fd,
                                                              self.CTM_signalMatrix)
            time_step = self.K.shape[1]
            self.veh_od = {0: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                          'to': self.CTM_cellIdx_downgrade.index('A1.-E120.C0'),
                          'time': 0},
                          1: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                          'to': self.CTM_cellIdx_downgrade.index('A1.-E120.C0'),
                          'time': 0}}
            # self.veh_od = CTM.generateODforOPTIm  # a preset api for CTM od

        # Parameters
        alpha1, alpha2, l, deltaT, M, eps = 0.5, 100000, 0.08, 5 / 3600, 999999, 10e-5

        # Sets
        I = [i for i in range(self.CTM_connection.shape[0])]  # Links (nodes)
        A = [i for i in range(veh_num)]  # Vehicles
        T = [i for i in range(time_step)]  # Time horizon

        self.para_set = (A, I, T)

        # load static parameters
        c = {(i, t): self.C[i, t] for i in I for t in T}
        Pi = {(i, j): self.CTM_connection[i, j] for i in I for j in I}
        # d = {(i, j, t): int(((self.C[i, t] + i + t + 2) % 4 + 1) * self.CTM_connection[i, j]) for i in I for j in I if
        #      i != j for
        #      t in T}  # Example: Travel cost increases with time
        self.c = c  # for visulization pupers
        ######################################################

        # Model Initialization
        model = Model("TDVRP-CTM")

        # Decision Variables
        x = model.addVars(A, I, T, vtype=GRB.BINARY, name="x")  # Vehicle on link at time t
        y = model.addVars(I, T, vtype=GRB.BINARY, name="y")  # occupation variable y  
        if parseZ:
            z_keys = []

            for a in A:
                for i in I:
                    for j in I:
                        if Pi.get((i, j), 0) != 1:
                            continue
                        for t in T:
                            s = int(t + c.get((i, t), 0))
                            if s < len(T):
                                z_keys.append((a, i, j, t, s))
            self.z_keys = z_keys
            z = model.addVars(z_keys, vtype=GRB.BINARY, name="z")  # Vehicle moves between links
        else:
            z = model.addVars(A, I, I, T, T, vtype=GRB.BINARY, name="z")  # Vehicle moves between link    
        omg = model.addVars(A, I, T, vtype=GRB.BINARY, name="omega")  # variable omege

        # tau = model.addVars(A, I, vtype=GRB.INTEGER, name="tau")
        # the = model.addVars(I, I, A, vtype=GRB.INTEGER, name="theta")  # theta variable
        # eta = model.addVars(A, I, T, vtype=GRB.BINARY, name="eta")  # binary variable for arrive time constraint

        model.setObjective(
            alpha1 * quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A) - alpha2 * quicksum(y[i, t] for i in I for t in T) / (self.CTM_connection.shape[0] * time_step),
            # quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A),
            GRB.MINIMIZE)

        ################################################ Constraints ###################################################
        print("condition 0 is finished")
        # 1. FLow conservation (linearlized)
        # axillary variable z
        if parseZ:
            for a in A:
                for i in I:
                    for t in T:
                        # if (i != veh_odtmp[a]['to'] and i != 11):
                        if i != self.veh_od[a]['to']:
                            model.addConstr(x[a, i, t] == quicksum(z[key] for key in z_keys if key[0] == a and key[1] == i and key[3] == t)
                            , name='axillary variable z')
        else:
            for a in A:
                for i in I:
                    for t in T:
                        # if (i != veh_odtmp[a]['to'] and i != 11):
                        if i != self.veh_od[a]['to']:
                            model.addConstr(x[a, i, t] == quicksum(z[a, i, j, t, s] for j in I for s in T),
                                            name='axillary variable z')


        print("constraint 1 is completed")
        # 2. Network Tepology constraint
        for key in z_keys:
            a, i, j, t, s = key
            model.addConstr(z[key] <= x[a, i, t], name=f'z_leq_x_a{a}_i{i}_j{j}_t{t}_s{s}')  # network tepology constraint
        print("constraint 2 is completed")

        # 3* network flow conservation law, od constraint
        for a in A:
            model.addConstr(x[a, self.veh_od[a]['from'], self.veh_od[a]['time']] == 1)
            model.addConstr(quicksum(x[a, self.veh_od[a]['to'], t] for t in T) == 1)
            for j in I:
                for s in T:
                    incoming = quicksum(z[key] for key in z_keys if key[0] == a and key[2] == j and key[4] == s)
                    outgoing = quicksum(z[key] for key in z_keys if key[0] == a and key[1] == j and key[3] == s)
                    if (j != self.veh_od[a]['from'] and j != self.veh_od[a]['to']):
                        model.addConstr(incoming - outgoing == 0, name='3*netflow_conservation3')
                    # elif j == veh_od[a]['to']:
                    #     model.addConstr(incoming - outgoing == 1, name='2*netflow_conservation2')

                        # model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(
                        #     z[a, j, k, s, r] for k in I for r in T) == 0, name='3*netflow_conservation3')
        print("constraint 3 is completed")

        # 4. Time-dependent link constraints
        for a in A:
            for t in T:
                model.addConstr(quicksum(x[a, i, t] for i in I) <= 1)
        print("constraint 4 is completed")

        # 5. Time-travel bound for vehicle
        model.addConstrs(quicksum(x[a, i, t] for t in T) <= 1 for a in A for i in I)
        print("constraint 5 is completed")


        # 6. omega-y condition (phase 2)
        model.addConstrs(y[i, t] <= quicksum(omg[a, i, t] for a in A) for i in I for t in T)
        model.addConstrs(M * y[i, t] >= quicksum(omg[a, i, t] for a in A) for i in I for t in T)
        print('constraint 6 is completed')

        # 7. omega-x condition (phase 2)
        # print('at here')
        self.time_step = int(len(T))
        model.addConstrs(omg[a, i, t] <= quicksum(x[a, i, t] for t in T) for a in A for i in I for t in T)
        for a in A:
            for i in I:
                for t in T:
                    t_mid = int(t + c[i, t])
                    t_end = self.time_step - 1
                    model.addConstr(quicksum(omg[a, i, k] for k in range(0, t - 1)) <= M * (1 - x[a, i, t]))
                    if t_end <= self.time_step - 2:  # here the time index --> max time step minors 1
                        model.addConstr(quicksum(omg[a, i, k] for k in range(t, t_mid)) >= x[a, i, t] * c[i, t])
                        model.addConstr(quicksum(omg[a, i, k] for k in range(t, t_mid)) <= x[a, i, t] * c[i, t] + M * (
                                    1 - x[a, i, t]))
                        model.addConstr(quicksum(omg[a, i, k] for k in range(t_mid, t_end)) <= M * (1 - x[a, i, t]))

        self.model = model
        print('model build complete!')
        return model

    def build_model_smallexample(self, veh_num=100, alpha=0.5):  # this is temperoarily set as small
        # self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
        #                                                   self.CTM_signalMatrix)

        # 20250401: update link, veh, time step without hardcoding.
        self.link, self.veh, self.time_step = 15, 2, 45

        self.C = np.ones((self.link, self.time_step))
        # self.CTM_connection = np.array([[0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
        #                                 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        #                                 [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
        #                                 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        #                                 [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        #                                 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        #                                 [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        #                                 [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        #                                 [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
        #                                 [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        #                                 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        #                                 [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
        con = {1: [2, 9], 2: [11], 3: [4, 10], 4: [12], 5: [6], 6: [14],
               7: [3, 8], 8: [5, 15], 9: [4, 10], 10: [6], 11: [12], 12: [14],
               13: [7, 1], 14: [], 15: []}

        # bi-directory 3x3
        # con = {1: [2, 9], 2: [11], 3: [4, 10, 21], 4: [12, 23], 5: [6, 22], 6: [24, 26],
        #        7: [3, 8], 8: [5], 9: [4, 10, 15], 10: [6, 17], 11: [12, 16], 12: [18, 26],
        #        13: [19], 14: [9, 13], 15: [8, 19], 16: [10, 15, 21], 17: [20], 18: [17, 22],
        #        19: [1], 20: [15, 19], 21: [2, 13], 22: [4, 15, 21], 23: [14], 24: [16, 23],
        #        25: [1, 7], 26: []}


        ####################################################################################################
        # a 3x3 grid network with multiple entry and exit, the index is real index but no -1
        # con = {1: [2, 16], 2: [3, 19], 3: [22], 4: [5, 17], 5: [6, 20], 6: [23],
        #        7: [8, 18], 8: [9, 21], 9: [24], 10: [11], 11: [12], 12: [24],
        #        13: [4, 14], 14: [7, 15], 15: [10], 16: [5, 17], 17: [18, 8], 18: [11],
        #        19: [6, 20], 20: [9, 21], 21: [12], 22: [23], 23: [24], 24: [26],
        #        25: [1, 13], 26: []}
        self.CTM_connection = np.zeros((len(con.keys()), len(con.keys())))
        for k, v in con.items():
            for vv in v:
                self.CTM_connection[k - 1, vv - 1] = 1
        #####################################################################################################

        # Example Data
        # max_t =   # max time step
        I = [i for i in range(self.CTM_connection.shape[0])]  # Links (nodes)
        A = [i for i in range(self.veh)]  # Vehicles
        T = [i for i in range(self.time_step)]  # Time horizon

        self.para_set = (A, I, T)

        # start and end node
        veh_od = {0: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')},
                  1: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')}}
        #  notes 20250401:
        # -1. the to node must be a complete last link without downstream link?, use index here
        veh_odtmp = {0: {'from': 12, 'to': 13, 'time': 0},
                     1: {'from': 12, 'to': 13, 'time': 0}}
                     # 2: {'from': 24, 'to': 25, 'time': 2},
                     # 3: {'from': 24, 'to': 25, 'time': 3}}
        # veh_odtmp = {0: {'from': 12, 'to': 14}}

        M = 999999

        # for k, v in veh_od.items():
        #     # a = v['from']
        #     x[k, v['from'], 0].lb = 1
        #     x[k, v['from'], 0].ub = 1

        # start = 0  # Start node
        # end = 3  # End node

        # Parameters as dictionaries
        c = {(i, t): (self.C[i, t] + i + t + 2)%4 + 1 for i in I for t in T}
        self.c = c

        Pi = {(i, j): self.CTM_connection[i, j] for i in I for j in I}
        d = {(i, j, t): int(((self.C[i, t] + i + t + 2)%4 + 1) * self.CTM_connection[i, j]) for i in I for j in I if i != j for
             t in T}  # Example: Travel cost increases with time

        # Model Initialization
        model = Model("TDVRP")

        # Decision Variables
        x = model.addVars(A, I, T, vtype=GRB.BINARY, name="x")  # Vehicle on link at time t
        y = model.addVars(I, T, vtype=GRB.BINARY, name="y")  # occupation variable y
        z = model.addVars(A, I, I, T, T, vtype=GRB.BINARY, name="z")  # Vehicle moves between links
        omg = model.addVars(A, I, T, vtype=GRB.BINARY, name="omega")  # variable omege

        # tau = model.addVars(A, I, vtype=GRB.INTEGER, name="tau")
        # the = model.addVars(I, I, A, vtype=GRB.INTEGER, name="theta")  # theta variable
        # eta = model.addVars(A, I, T, vtype=GRB.BINARY, name="eta")  # binary variable for arrive time constraint

        model.setObjective(
            alpha * quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A) - (1-alpha)
                                        * quicksum(y[i, t] for i in I for t in T)/(self.link * self.time_step),
            # quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A),
            GRB.MINIMIZE
        )


        ################################################ Constraints ###################################################
        # 0. preset Z condition
        for a in A:
            for i in I:
                for j in I:
                    for t in T:
                        for s in T:
                            if not (s == t + c[i, t] and Pi[i, j] == 1):
                                model.addConstr(z[a, i, j, t, s] == 0, name='PresetZCondition_0')
                            # else:
                                # model.addConstr(z[a, i, j, t, s] <= 1, name='PresetZCondition_1')
                                print('preset z[{},{},{},{},{}] with cost c[{},{}]={}, Pi = {}'.format(a, i, j, t, s, i,
                                                                                                       t, c[i, t],
                                                                                                       Pi[i, j]))

        print("condition 0 is completed")
        # 1. FLow conservation (linearlized)
        # axillary variable z
        for a in A:
            for i in I:
                for t in T:
                    # if (i != veh_odtmp[a]['to'] and i != 11):
                    if i != veh_odtmp[a]['to']:
                        model.addConstr(x[a, i, t] == quicksum(z[a, i, j, t, s] for j in I for s in T),
                                        name='axillary variable z')
        # 2. Network Tepology constraint
        model.addConstrs(
            (z[a, i, j, t, s] <= Pi[i, j] * x[a, i, t] for a in A for j in I for i in I for t in T for s in T),
            name='network tepology')  # network tepology constraint

        # # arrive time law
        # for t in T:
        #     model.addConstrs((
        #         tau[a, j] >= tau[a, i] + the[i, j, a] - M * (1 - z[a, i, j, t, s]) for a in A for i in I for j in I for s in T), name='arrive time constraint')
        #
        # # line travel time rules
        # model.addConstrs(
        #     the[i, j, a] == (1 - Pi[i, j]) * 10000 + Pi[i, j] * quicksum(c[i, t] * x[a, i, t] for t in T) for a in A for
        #     j in I for i in I if (i != veh_odtmp[a]['to']))

        # 3* network flow conservation law, od constraint
        for a in A:
            model.addConstr(x[a, veh_odtmp[a]['from'], veh_odtmp[a]['time']] == 1)
            model.addConstr(quicksum(x[a, veh_odtmp[a]['to'], t] for t in T) == 1)
            for j in I:
                for s in T:
                    # if (j == 0 or j == 6):
                    #     model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(z[a, j, k, s, r] for k in I for r in T) == -1, name='3*netflow_conservation1')
                    # if j == veh_odtmp[a]['to']:
                    #     model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(z[a, j, k, s, r] for k in I for r in T) == 1, name='3*netflow_conservation2')
                    if (j != veh_odtmp[a]['from'] and j != veh_odtmp[a]['to']):
                        #     print('j is {}'.format(j))
                        # else:
                        model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(
                            z[a, j, k, s, r] for k in I for r in T) == 0, name='3*netflow_conservation3')

        # 4. Time-dependent link constraints
        for a in A:
            for t in T:
                model.addConstr(quicksum(x[a, i, t] for i in I) <= 1)

        # 5. Time-travel bound for vehicle
        model.addConstrs(quicksum(x[a, i, t] for t in T) <=1 for a in A for i in I)


        # 6. omega-y condition (phase 2)
        model.addConstrs(y[i, t] <= quicksum(omg[a, i, t] for a in A) for i in I for t in T)
        model.addConstrs(M*y[i, t] >= quicksum(omg[a, i, t] for a in A) for i in I for t in T)

        # 7. omega-x condition (phase 2)
        print('at here')

        model.addConstrs(omg[a, i, t] <= quicksum(x[a, i, t] for t in T) for a in A for i in I for t in T)
        for a in A:
            for i in I:
                for t in T:
                    t_mid = int(t+c[i, t])
                    t_end = self.time_step -1
                    model.addConstr(quicksum(omg[a, i, k] for k in range(0, t - 1)) <= M*(1 - x[a, i, t]))
                    if t_end <= self.time_step - 2:  # here the time index --> max time step minors 1
                        model.addConstr(quicksum(omg[a, i, k] for k in range(t, t_mid)) >= x[a, i, t] * c[i, t])
                        model.addConstr(quicksum(omg[a, i, k] for k in range(t, t_mid)) <= x[a, i, t] * c[i, t] + M*(1-x[a, i, t]))
                        model.addConstr(quicksum(omg[a, i, k] for k in range(t_mid, t_end)) <= M * (1 - x[a, i, t]))



        # model.addConstrs()


        self.model = model
        print('model build complete!')
        return model

    """ old solve model code, wait to be cleared """
    # def solve_model(self):
    #     """Solve the Gurobi model and return the objective value and solution details."""
    #     # Build the model if it hasn't been built yet
    #     # if not hasattr(self, 'model'):
    #     #     self.build_model()
    #
    #     self.model.reset(0)
    #     # debug part
    #     # self.model.computeIIS()
    #     # self.model.write("../../result/milpLog/infeasibile.ilp")
    #
    #     # Optimize the model
    #     # self.model.feasRelaxS(0, True, False, True)
    #     print('begin to optimize')
    #     self.model.optimize()
    #     if self.model.status == GRB.INFEASIBLE:
    #         print('release an infeasible model')
    #         self.model.computeIIS()
    #         self.model.write("../../result/milpLog/infeasibile.ilp")
    #     #     print("lalalala")
    #     #     self.model.feasRelaxS(0, True, False, True)
    #     #     self.model.optimize()
    #     # self.model.optimize()
    #
    #     # Check if a feasible solution was found
    #     if self.model.status == GRB.OPTIMAL:
    #         print(f"Optimal objective value: {self.model.objVal}")
    #
    #         # A, Z, T, TT = self.param
    #
    #         # # Retrieve dimensions
    #         # num_vehicles = len(A)
    #         # num_cells = len(Z)
    #         # num_timesteps = len(T)
    #
    #         # # Initialize an empty array for the solution
    #         # solution_array = np.zeros((num_vehicles, num_cells, num_timesteps), dtype=int)
    #
    #         solution_array = np.zeros((self.veh, self.link, self.time_step), dtype=int)
    #
    #         # Populate the array with solution values
    #         for a in range(solution_array.shape[0]):
    #             for i in range(solution_array.shape[1]):
    #                 for t in range(solution_array.shape[2]):
    #                     var_x = self.model.getVarByName(f"x[{a},{i},{t}]")
    #                     # if int(round(var_x.x)) == 1:
    #                     #     print('#########x({},{},{})={}'.format(a, i, t, var_x.x))
    #                     for j in range(solution_array.shape[1]):
    #                         for s in range(solution_array.shape[2]):
    #                             var_z = self.model.getVarByName(f"z[{a},{i},{j},{t},{s}]")
    #                             # var_z = self.model.getVarByName(f"z[{i},{j},{a},{t}]")
    #                             if int(round(var_z.x)) == 1:
    #                                 var_tao = self.model.getVarByName(f"tau[{a},{i}]")
    #                                 var_theta = self.model.getVarByName(f"theta[{i},{j},{a}]")
    #                                 print(
    #                                     "$$$$$$$$$ z({},{},{},{},{}) = 1 $$$$$$$ c({},{})={} $$ x({},{},{})={}".format(
    #                                         a, i+1, j+1, t, s, i+1, t, self.c[(i, t)], a, i+1, t, var_x.x))
    #
    #                     solution_array[a, i, t] = int(round(var_x.x))
    #
    #         return solution_array, self.model.objVal
    #     else:
    #         print("No optimal solution found.")
    #         return None, None


    # this function is to tmp test for the small ctm network
    def solve_model(self):
        self.model.reset(0)
        # debug part
        # self.model.computeIIS()
        # self.model.write("../../result/milpLog/infeasibile.ilp")

        # Optimize the model
        # self.model.feasRelaxS(0, True, False, True)
        print('begin to optimize')
        self.model.optimize()
        if self.model.status == GRB.INFEASIBLE:
            print('release an infeasible model')
            self.model.computeIIS()
            self.model.write("../../result/milpLog/infeasibile.ilp")
        #     print("lalalala")
        #     self.model.feasRelaxS(0, True, False, True)
        #     self.model.optimize()
        # self.model.optimize()

        # Check if a feasible solution was found
        if self.model.status == GRB.OPTIMAL:
            print(f"Optimal objective value: {self.model.objVal}")

            A, I, T = self.para_set

            # Retrieve dimensions
            num_vehicles = len(A)
            num_cells = len(I)
            num_timesteps = len(T)

            # # Initialize an empty array for the solution
            solution_array = np.zeros((num_vehicles, num_cells, num_timesteps), dtype=int)

            # solution_array = np.zeros((self.veh, self.link, self.time_step), dtype=int)

            # Populate the array with solution values
            for a in range(solution_array.shape[0]):
                for t in range(solution_array.shape[2]):
                    for i in range(solution_array.shape[1]):
                        var_x = self.model.getVarByName(f"x[{a},{i},{t}]")
                        if int(round(var_x.x)) == 1:
                            print('#########x({},{},{})={}, at cell {} at time {}, cost is {} '.format(a, i, t, var_x.x, self.CTM_cellIdx_downgrade[i], t, self.c[(i, t)]))

                        solution_array[a, i, t] = int(round(var_x.x))

            return solution_array, self.model.objVal
        else:
            print("No optimal solution found.")
            return None, None

    def getRouteFromX(self, x):
        cell_idx = self.CTM_cellIdx_downgrade
        # input x: [veh, link, time]
        veh_rt = {}
        for a in range(x.shape[0]):
            rt = []
            for t in range(x.shape[2]):
                for i in range(x.shape[1]):
                    if (x[a, i, t] == 1 and i!= self.veh_od[a]['to']):
                        rt.append(cell_idx[i])
            veh_rt[a] = rt
        return veh_rt


if __name__ == '__main__':
    CTM_Path = {'number': '../../result/ctmResult/CTMnumber_3600_1800dis.csv',
                'outnumber': '../../result/ctmResult/CTMnumber_out_3600_1800dis.csv',
                'sigflag': '../../result/ctmResult/CTMsigflag_3600_1800dis.csv',
                'connectionMatrix': '../../result/ctmResult/CTMconnection.txt',
                'cellIdx': '../../result/ctmResult/CTMcell_index.json'
                }

    # print(SolverFactory("gurobi_direct").available())
    FD_param = {
        'v_f': 57.6,  # km/hr
        'k_jam': 133,  # veh/km
        'q_max': 1744,  # veh/hour
        'w': 17.94,
        'length': 0.08,  # km
        'delta_t': 5 / 3600,  # hr
    }

    time1 = time.time()
    Ropt = RouteOptimGurobi(CTM_Path, FD_param)
    # Ropt.build_model_smallexample(veh_num=2)
    Ropt.build_model(veh_num=2, small_net=False)
    x, objective_value = Ropt.solve_model()
    print('time cost is {}'.format(time.time() - time1))

    with open(CTM_Path['cellIdx'], 'r') as file:
        CTM_cellIdx = [line.strip() for line in file]

    rout_list = Ropt.getRouteFromX(x)

    print(x[1, :, :])
