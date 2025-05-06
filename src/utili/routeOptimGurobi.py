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

        self.max_time = 35
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

    def build_model(self, veh_num=100):
        self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
                                                          self.CTM_signalMatrix)

        # Initialize Gurobi model
        model = Model("RouteOptimization")

        # Parameters
        alpha1, alpha2, l, deltaT, M, eps = 0.5, 0.5, 0.08, 5 / 3600, 999999, 10e-5

        # Sets
        Z = range(self.K.shape[0])
        T = range(self.K.shape[1])
        TT = range(self.K.shape[1] - 1)
        A = range(veh_num)

        self.param = (A, Z, T, TT)

        # Variables
        x = model.addVars(A, Z, T, vtype=GRB.BINARY, name="x")
        z = model.addVars(A, Z, Z, T, vtype=GRB.BINARY, name="z")
        y = model.addVars(Z, T, vtype=GRB.BINARY, name="y")
        tao = model.addVars(A, Z, vtype=GRB.INTEGER, name="arrive time tao")
        the = model.addVars(A, Z, T, vtype=GRB.INTEGER,
                            name="travel time on cell i for veh a at time t")  # theta variable

        # Parameters as dictionaries
        c = {(i, t): self.C[i, t] for i in Z for t in T}
        # v = {(i, t): self.V[i, t] for i in Z for t in T}
        # eta = {(i, t): self.CTM_signalMatrix[i, t] for i in Z for t in T}
        Pi = {(i, j): self.CTM_connection[i, j] for i in Z for j in Z}

        # Objective function: minimize travel cost
        # model.setObjective(
        #     alpha1 * quicksum(c[i, t] * x[a, i, t] for a in A for i in Z for t in T) +
        #     alpha2 * quicksum(y[i, t] for i in Z for t in T) / (
        #             self.C.shape[0] * self.C.shape[1]),
        #     GRB.MINIMIZE
        # )
        model.setObjective(
            alpha1 * quicksum(c[i, t] * x[a, i, t] for a in A for i in Z for t in T),
            GRB.MINIMIZE
        )

        """=========================================2024Dec new formulation============================================================"""

        # Part 1:Flow conservation law
        model.addConstrs(
            x[a, i, t] == quicksum(z[a, i, j, t] for j in Z) for a in A for i in Z for t in T)  # axillary variable z

        model.addConstrs(z[a, i, j, t] <= Pi[i, j] * x[a, i, t] for a in A for j in Z for i in Z for t in
                         T)  # network tepology constraint

        # linearlized flow conservation
        for a in A:
            model.addConstrs(the[a, i, t] <= M * z[a, i, j, t] for i in Z for j in Z for t in T)  # bounding travel
        for t in T:
            model.addConstrs(
                tao[a, j] >= tao[a, i] + the[a, i, t] - M * (1 - z[a, i, j, t]) for a in A for i in Z for j in Z)
        model.addConstrs(the[a, i, t] == c[i, t] * x[a, i, t] for a in A for i in Z for t in T)

        # coverage constraints

        # delta = model.addVars(Z, T, vtype=GRB.BINARY, name ="binary variable for linearlized detection constraint")
        # model.addConstrs(quicksum(x[a, i, t] for a in A) - 1 <= delta[i, t] for i in Z for t in T)
        # model.addConstrs(y[i, t] >= 1-(1-delta[i, t])*M for i in Z for t in T)
        # model.addConstrs(y[i, t] <= 1+(1+delta[i, t])*M for i in Z for t in T)
        # model.addConstrs(y[i, t] >= quicksum(x[a, i, t] for a in A)-delta[i, t]*M for i in Z for t in T)
        # model.addConstrs(y[i, t] <= quicksum(x[a, i, t] for a in A)+delta[i, t]*M for i in Z for t in T)

        # one vehicle at a time constraints
        model.addConstrs(quicksum(x[a, i, t] for t in T) <= 1 for a in A for i in Z)

        """============================================================================================================================"""
        # # 1. One vehicle constraint
        # model.addConstrs((quicksum(x[a, i, t] for i in Z) == 1 for a in A for t in T), "OneVehicle rules")
        #
        # # 2. Speed constraint example (Placeholder)
        # for t in T:
        #     model.addConstrs(
        #         quicksum(x[a, i, m] * v[i, m] * deltaT for m in range(t)) <= eta[i, t] * l + M * (1 - eta[i, t]) for a
        #         in A for i in Z)
        #
        # # 3. Cell siganl COnstraint
        # model.addConstrs((1 - eta[i, t]) * (x[a, i, t + 1] - x[a, i, t]) >= 0 for a in A for i in Z for t in TT)
        #
        # # 4. Flow conservation laws, since gurobi does not support bool value, so activation function is not working.,
        #
        # # delta1 = np.zeros((len(A), len(Z), len(T)), dtype=float)
        # # delta1 = model.addVars(A, Z, T, vtype=GRB.CONTINUOUS)
        # # delta2 = np.zeros((len(A), len(Z), len(T)), dtype=float)
        # # delta2 = model.addVars(A, Z, T, vtype=GRB.CONTINUOUS)
        # K1 = model.addVars(A, Z, T, lb=0, ub=1, vtype=GRB.INTEGER, name="k1")
        # K2 = model.addVars(A, Z, T, lb=0, ub=1, vtype=GRB.INTEGER, name="k2")
        # # for a in A:
        # #     for i in Z:
        # #         for t in TT:
        # #
        # #             d1 = quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1))/l
        # #             d2 = quicksum(Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in Z)
        # #             d1_v, d2_v = d1.X, d2.X
        # #             if d1_v > 1:
        # #                 k1 = 1
        # #             else:
        # #                 k1 = 0
        # #             if d2_v > 1:
        # #                 k2 = 1
        # #             else:
        # #                 k2 = 0
        # #             model.addConstrs(x[a, i, t + 1] == (1-k1)*x[a, i, t]+k2*quicksum(Pi[k, i]*x[a, k, t] for k in Z) for a in A for i in Z for t in TT )
        #
        # # 4.1
        # # model.addConstrs(quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1))/l == delta1[a, i, t] for a in A for i in Z for t in TT)
        # # 4.2
        # # model.addConstrs(quicksum(Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in Z) == delta2[a, i, t] for a in A for i in Z for t in TT)
        #
        #
        # # # 4.3 K11
        # # model.addConstrs(
        # #     K1[a, i, t] - ((quicksum(
        # #         x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1)) / l - 1 + M) / M) <= 0
        # #     for a in A for i in Z for t in T)
        # # # 4.3 K12
        # # model.addConstrs(
        # #     K1[a, i, t] - ((quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1)) / l - 1) / M) >= eps
        # #     for a in A for i in Z for t in T)
        # # # 4.3 K11
        # # model.addConstrs(K2[a, i, t] - ((quicksum(
        # #     Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in
        # #     Z) - 1 + M) / M) <= 0 for a in A for i in Z for t in T)
        # # # 4.3 K11
        # # model.addConstrs(K2[a, i, t] - ((quicksum(
        # #     Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in
        # #     Z) - 1) / M) >= eps for a in A for i in Z for t in T)
        # #
        # # model.addConstrs(
        # #     x[a, t, t + 1] == (1 - K1[a, i, t]) * x[a, i, t] + K2[a, i, t] * quicksum(Pi[k, i] * x[a, k, t] for k in Z)
        # #
        #
        # model.addConstrs(
        #     x[a, t, t + 1] == (1 - 1) * x[a, i, t] + 0 * quicksum(Pi[k, i] * x[a, k, t] for k in Z)
        #     for a in A for i in Z for t in TT)
        #
        #
        #
        #
        # # model.addConstrs((x[a, i, t+1]==(1-actF(quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1))/l))+ \
        # #                  actF(quicksum(Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in Z) / l) * quicksum(Pi[k, i] * x[a, k, t] for k in Z)
        # #                           for a in A for i in Z for t in TT),"FlowConservation")
        # # model.addConstrs((quicksum(Pi[i, j] * x[a, i, t] for j in Z) >= 0 for a in A for i in Z for t in TT),
        # #                  "FlowConstraint")

        veh_od = {0: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')},
                  1: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')}}

        for k, v in veh_od.items():
            # a = v['from']
            x[k, v['from'], 0].lb = 1
            x[k, v['from'], 0].ub = 1

            # x[k, v['to'], self.max_time - 1].lb = 1
            # x[k, v['to'], self.max_time - 1].ub = 1

        self.model = model
        return model

    def build_model2(self, veh_num=100):
        self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
                                                          self.CTM_signalMatrix)

        # Parameters
        alpha1, alpha2, l, deltaT, M, eps = 0.5, 0.5, 0.08, 5 / 3600, 999999, 10e-5

        # Sets
        # Z = range(self.K.shape[0])
        # T = range(self.K.shape[1])
        # TT = range(self.K.shape[1] - 1)
        # A = range(veh_num)

        # Example Data
        I = [i for i in range(self.K.shape[0])]  # Links (nodes)
        A = [0, 1]  # Vehicles
        T = range(self.K.shape[1])  # Time horizon
        # d = {(i, j): 1 for i in I for j in I if i != j}  # Travel times/costs
        q = {i: 1 for i in I}  # Demand at each link
        Q = {a: 2 for a in A}  # Vehicle capacities

        # start and end node
        veh_od = {0: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')},
                  1: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')}}

        # for k, v in veh_od.items():
        #     # a = v['from']
        #     x[k, v['from'], 0].lb = 1
        #     x[k, v['from'], 0].ub = 1

        start = 0  # Start node
        end = 3  # End node

        # Parameters as dictionaries
        c = {(i, t): self.C[i, t] for i in I for t in T}
        v = {(i, t): self.V[i, t] for i in I for t in T}
        eta = {(i, t): self.CTM_signalMatrix[i, t] for i in I for t in T}
        Pi = {(i, j): self.CTM_connection[i, j] for i in I for j in I}
        d = {(i, j, t): t + 1 for i in I for j in I if i != j for t in T}  # Example: Travel cost increases with time

        # Model Initialization
        model = Model("TDVRP")

        # Decision Variables
        x = model.addVars(I, A, T, vtype=GRB.BINARY, name="x")  # Vehicle on link at time t
        z = model.addVars(I, I, A, T, vtype=GRB.BINARY, name="z")  # Vehicle moves between links

        model.setObjective(
            quicksum(d[i, j, t] * z[i, j, a, t] for i in I for j in I for a in A for t in T if (i, j, t) in d),
            GRB.MINIMIZE
        )

        # Constraints

        # 1. Flow conservation
        for a in A:
            for i in I:
                for t in T:
                    if t > 0:
                        model.addConstr(
                            quicksum(z[j, i, a, t - d[j, i, t]] for j in I if (j, i, t) in d and t - d[j, i, t] >= 0)
                            == x[i, a, t]
                        )
        # 2. Time-dependent link constraints
        for a in A:
            for t in T:
                model.addConstr(quicksum(x[i, a, t] for i in I) <= 1)

        # 3. Link usage constraints
        for i in I:
            for t in T:
                model.addConstr(quicksum(x[i, a, t] for a in A) <= 1)

        # 4. Capacity constraints
        for a in A:
            for t in T:
                model.addConstr(quicksum(q[i] * x[i, a, t] for i in I) <= Q[a])

        # 5. Start and end points

        # for k, v in veh_od.items():
        # # a = v['from']
        # x[k, v['from'], 0].lb = 1
        # x[k, v['from'], 0].ub = 1

        for a in A:
            model.addConstr(quicksum(x[start, a, t] for t in T) == 1)
            model.addConstr(quicksum(x[end, a, t] for t in T) == 1)

        # 6. Binary coupling between x and z
        for i in I:
            for j in I:
                for a in A:
                    for t in T:
                        if (i, j, t) in d:
                            model.addConstr(z[i, j, a, t] <= x[i, a, t])

        self.model = model
        return model

    def build_model_smallexample(self, veh_num=100, alpha=0.5):
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

        tau = model.addVars(A, I, vtype=GRB.INTEGER, name="tau")
        the = model.addVars(I, I, A, vtype=GRB.INTEGER, name="theta")  # theta variable
        eta = model.addVars(A, I, T, vtype=GRB.BINARY, name="eta")  # binary variable for arrive time constraint

        model.setObjective(
            # alpha * quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A) - (1-alpha)
            #                             * quicksum(y[i, t] for i in I for t in T)/(self.link * self.time_step),
            quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A),
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
                                # print('preset z[{},{},{},{},{}] with cost c[{},{}]={}, Pi = {}'.format(a, i, j, t, s, i,
                                #                                                                        t, c[i, t],
                                #                                                                        Pi[i, j]))

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

    def solve_model(self):
        """Solve the Gurobi model and return the objective value and solution details."""
        # Build the model if it hasn't been built yet
        # if not hasattr(self, 'model'):
        #     self.build_model()

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

            # A, Z, T, TT = self.param

            # # Retrieve dimensions
            # num_vehicles = len(A)
            # num_cells = len(Z)
            # num_timesteps = len(T)

            # # Initialize an empty array for the solution
            # solution_array = np.zeros((num_vehicles, num_cells, num_timesteps), dtype=int)

            solution_array = np.zeros((self.veh, self.link, self.time_step), dtype=int)

            # Populate the array with solution values
            for a in range(solution_array.shape[0]):
                for i in range(solution_array.shape[1]):
                    for t in range(solution_array.shape[2]):
                        var_x = self.model.getVarByName(f"x[{a},{i},{t}]")
                        # if int(round(var_x.x)) == 1:
                        #     print('#########x({},{},{})={}'.format(a, i, t, var_x.x))
                        for j in range(solution_array.shape[1]):
                            for s in range(solution_array.shape[2]):
                                var_z = self.model.getVarByName(f"z[{a},{i},{j},{t},{s}]")
                                # var_z = self.model.getVarByName(f"z[{i},{j},{a},{t}]")
                                if int(round(var_z.x)) == 1:
                                    var_tao = self.model.getVarByName(f"tau[{a},{i}]")
                                    var_theta = self.model.getVarByName(f"theta[{i},{j},{a}]")
                                    print(
                                        "$$$$$$$$$ z({},{},{},{}, {}) = 1 $$$$$$$$ tao({}, {}) = {} $$$$ theta({},{},{})={} $$$ c({},{})={} $$ x({},{},{})={}".format(
                                            a, i+1, j+1, t, s, a, i+1, var_tao.x, i+1, j+1, a, var_theta.x, i+1, t, self.c[(i, t)], a,
                                            i+1, t, var_x.x))

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
                    if x[a, i, t] == 1:
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
    Ropt.build_model_smallexample(veh_num=2)
    x, objective_value = Ropt.solve_model()
    print('time cost is {}'.format(time.time() - time1))

    with open(CTM_Path['cellIdx'], 'r') as file:
        CTM_cellIdx = [line.strip() for line in file]

    rout_list = Ropt.getRouteFromX(x)

    print(x[1, :, :])
