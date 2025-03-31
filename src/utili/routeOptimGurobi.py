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

    def build_model_smallexample(self, veh_num=100):
        # self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
        #                                                   self.CTM_signalMatrix)

        # 12 links, 2 veh, 30 step
        self.C = np.ones((12, 100))
        self.CTM_connection = np.array([[0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                                        [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                                        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
                                        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                                        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])

        # Example Data
        max_t = 50 # max time step
        I = [i for i in range(self.CTM_connection.shape[0])]  # Links (nodes)
        A = [0, 1]  # Vehicles
        T = range(50)  # Time horizon

        # start and end node
        veh_od = {0: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')},
                  1: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')}}

        M = 999999

        # for k, v in veh_od.items():
        #     # a = v['from']
        #     x[k, v['from'], 0].lb = 1
        #     x[k, v['from'], 0].ub = 1

        # start = 0  # Start node
        # end = 3  # End node

        # Parameters as dictionaries
        c = {(i, t): self.C[i, t] + i + t +2 for i in I for t in T}
        self.c = c
        # v = {(i, t): self.V[i, t] for i in I for t in T}
        # eta = {(i, t): self.CTM_signalMatrix[i, t] for i in I for t in T}
        Pi = {(i, j): self.CTM_connection[i, j] for i in I for j in I}
        d = {(i, j, t): int((self.C[i, t] + i + t +2) * self.CTM_connection[i, j]) for i in I for j in I if i != j for t in T}  # Example: Travel cost increases with time

        # Model Initialization
        model = Model("TDVRP")

        # Decision Variables
        x = model.addVars(A, I, T, vtype=GRB.BINARY, name="x")  # Vehicle on link at time t
        z = model.addVars(I, I, A, T, vtype=GRB.BINARY, name="z")  # Vehicle moves between links
        tau = model.addVars(A, I, vtype=GRB.INTEGER, name="tau")
        the = model.addVars(I, I, A, vtype=GRB.INTEGER, name="theta")  # theta variable
        eta = model.addVars(A, I, T, vtype=GRB.BINARY, name="eta") # binary variable for arrive time constraint




        model.setObjective(
            quicksum(d[i, j, t] * x[a, i, t] for i in I for j in I for t in T for a in A if (i, j, t) in d),
            GRB.MINIMIZE
        )

        # Constraints

    # # 1. Flow conservation
    #     # NOTE:20241216 we found the current flow conservation law is infeasible
    #     for a in A:
    #         for j in I:
    #             for t in T:
    #                 for i in I:
    #                     if (i, j, t) in d:
    #                         if t > 0 and t + d[i, j, t] <= max_t - 1:
    #                             # print("i, j, a, t, pi, d", i, j, a, t, Pi[(i, j)],d[(i, j, t)])
    #                             model.addConstr(quicksum(z[i, j, a, t] for i in I) == x[a, j, t + d[i, j, t]], name='flow conservation')
    # 1.1 FLow conservation (linearlized)
        # axillary variable z
        for i in I:
            for a in A:
                for t in T:
                    if (i != 5 and i != 11):
                        model.addConstr(x[a, i, t] == quicksum(z[i, j, a, t] for j in I), name='axillary variable z')
        # aa = Pi[(0, 1)]
        model.addConstrs((z[i, j, a, t] <= Pi[i, j] * x[a, i, t] for a in A for j in I for i in I for t in T), name='network tepology')  # network tepology constraint

        # linearlized flow conservation
        # for a in A:
        #     model.addConstrs(the[i, j, a] <= M * z[i, j, a, t] for i in I for j in I for t in T)  # bounding travel (This is

        # arrive time flow conservation law
        for t in T:
            model.addConstrs((
                tau[a, j] >= tau[a, i] + the[i, j, a] - M * (1 - z[i, j, a, t]) for a in A for i in I for j in I), name='arrive time constraint')

    # # 2. add-on x-z condition
        for a in A:
            for i in I:
                for j in I:
                    model.addConstr(quicksum(x[a, j, t] for t in T) <= quicksum(x[a, i, t] for t in T), name='x-z conditon1')
                    model.addConstrs((quicksum(x[a, j, t] for t in T) >= quicksum(x[a, i, t] for t in T) - (1 - z[i, j, a, m]) for m in T), name='x-z conditon2')



        # line travel time rules
        model.addConstrs(the[i, j, a] == (1 - Pi[i, j]) * 10000 + Pi[i, j] * quicksum(c[i, t] * x[a, i, t] for t in T) for a in A for j in I for i in I if (i!=5 and i!=11))

    # 3. Time-dependent link constraints
        for a in A:
            for t in T:
                model.addConstr(quicksum(x[a, i, t] for i in I) <= 1)


    # *4.


    # # 4. linearlized bound condition between x and tao
    #     for i in I:
    #         for a in A:
    #             model.addConstr(quicksum(eta[a, i, t] for t in T) == 1, name=f"OneHot_(a, i){a}_{i}")
    #
    #     # 2. Link tau to delta
    #     for i in I:
    #         for a in A:
    #             model.addConstr(quicksum(t * eta[a, i, t] for t in T) == tau[a, i], name=f"TauLink_{a}_{i}")
    #
    #     # 3. Bind x to delta
    #     for i in I:
    #         for a in A:
    #             for t in T:
    #                 model.addConstr(x[a, i, t] == eta[a, i, t], name=f"BindX_{a}_{i}_{t}")
        # for a in A:
        #     for t in T:
        #         model.addConstr(quicksum(q[i] * x[i, a, t] for i in I) <= Q[a])

        # 5. Start and end points

        model.addConstr(x[0, 0, 0] == 1)
        model.addConstr(x[1, 6, 0] == 1)
        model.addConstr(quicksum(x[0, 11, t] for t in T) == 1)
        model.addConstr(quicksum(x[1, 5, t] for t in T) == 1)


        # # 6. Binary coupling between x and z
        # for i in I:
        #     for j in I:
        #         for a in A:
        #             for t in T:
        #                 if (i, j, t) in d:
        #                     model.addConstr(z[i, j, a, t] <= x[a, i, t])

        self.model = model
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
        self.model.optimize()
        if self.model.status == GRB.INFEASIBLE:
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

            solution_array = np.zeros((2, 12, 50), dtype=int)

            # Populate the array with solution values
            for a in range(solution_array.shape[0]):
                for i in range(solution_array.shape[1]):
                    for t in range(solution_array.shape[2]):
                        var_x = self.model.getVarByName(f"x[{a},{i},{t}]")
                        if int(round(var_x.x)) == 1:
                            print('#########x({},{},{})={}'.format(a, i, t, var_x.x))
                        for j in range(solution_array.shape[1]):
                            var_z = self.model.getVarByName(f"z[{i},{j},{a},{t}]")
                            if int(round(var_z.x)) == 1:
                                var_tao = self.model.getVarByName(f"tau[{a},{i}]")
                                var_theta = self.model.getVarByName(f"theta[{i},{j},{a}]")
                                print("$$$$$$$$$ z({},{},{},{}) = 1 $$$$$$$$ tao({}, {}) = {} $$$$ theta({},{},{})={} $$$ c({},{})={} $$ x({},{},{})={}".format(i, j, a, t, a, i, var_tao.x, i, j, a, var_theta.x, i, t, self.c[(i,t)], a, i, t, var_x.x))

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
