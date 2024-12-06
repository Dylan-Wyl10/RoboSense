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
                    distance_remained -= V[i, jj] * FD_param ['delta_t']
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
        tao = model.addVars(A, Z, vtype=GRB.BINARY, name="arrive time tao")
        the = model.addVars(Z, Z, T, vtype=GRB.BINARY, name="travel time from i to j at time t")# theta variable

        # Parameters as dictionaries
        c = {(i, t): self.C[i, t] for i in Z for t in T}
        v = {(i, t): self.V[i, t] for i in Z for t in T}
        eta = {(i, t): self.CTM_signalMatrix[i, t] for i in Z for t in T}
        Pi = {(i, j): self.CTM_connection[i, j] for i in Z for j in Z}

        # Objective function: minimize travel cost
        model.setObjective(
            alpha1 * quicksum(c[i, t] * x[a, i, t] for a in A for i in Z for t in T) +
            alpha2 * quicksum(y[i, t] for i in Z for t in T) / (
                    self.C.shape[0] * self.C.shape[1]),
            GRB.MINIMIZE
        )
    
        # 1. One vehicle constraint
        model.addConstrs((quicksum(x[a, i, t] for i in Z) == 1 for a in A for t in T), "OneVehicle rules")

        # 2. Speed constraint example (Placeholder)
        for t in T:
            model.addConstrs(
                quicksum(x[a, i, m] * v[i, m] * deltaT for m in range(t)) <= eta[i, t] * l + M * (1 - eta[i, t]) for a
                in A for i in Z)

        # 3. Cell siganl COnstraint
        model.addConstrs((1 - eta[i, t]) * (x[a, i, t + 1] - x[a, i, t]) >= 0 for a in A for i in Z for t in TT)

        # 4. Flow conservation laws, since gurobi does not support bool value, so activation function is not working.,

        # delta1 = np.zeros((len(A), len(Z), len(T)), dtype=float)
        # delta1 = model.addVars(A, Z, T, vtype=GRB.CONTINUOUS)
        # delta2 = np.zeros((len(A), len(Z), len(T)), dtype=float)
        # delta2 = model.addVars(A, Z, T, vtype=GRB.CONTINUOUS)
        K1 = model.addVars(A, Z, T, lb=0, ub=1, vtype=GRB.INTEGER, name="k1")
        K2 = model.addVars(A, Z, T, lb=0, ub=1, vtype=GRB.INTEGER, name="k2")
        # for a in A:
        #     for i in Z:
        #         for t in TT:
        #
        #             d1 = quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1))/l
        #             d2 = quicksum(Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in Z)
        #             d1_v, d2_v = d1.X, d2.X
        #             if d1_v > 1:
        #                 k1 = 1
        #             else:
        #                 k1 = 0
        #             if d2_v > 1:
        #                 k2 = 1
        #             else:
        #                 k2 = 0
        #             model.addConstrs(x[a, i, t + 1] == (1-k1)*x[a, i, t]+k2*quicksum(Pi[k, i]*x[a, k, t] for k in Z) for a in A for i in Z for t in TT )

        # 4.1
        # model.addConstrs(quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1))/l == delta1[a, i, t] for a in A for i in Z for t in TT)
        # 4.2
        # model.addConstrs(quicksum(Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in Z) == delta2[a, i, t] for a in A for i in Z for t in TT)


        # # 4.3 K11
        # model.addConstrs(
        #     K1[a, i, t] - ((quicksum(
        #         x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1)) / l - 1 + M) / M) <= 0
        #     for a in A for i in Z for t in T)
        # # 4.3 K12
        # model.addConstrs(
        #     K1[a, i, t] - ((quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1)) / l - 1) / M) >= eps
        #     for a in A for i in Z for t in T)
        # # 4.3 K11
        # model.addConstrs(K2[a, i, t] - ((quicksum(
        #     Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in
        #     Z) - 1 + M) / M) <= 0 for a in A for i in Z for t in T)
        # # 4.3 K11
        # model.addConstrs(K2[a, i, t] - ((quicksum(
        #     Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in
        #     Z) - 1) / M) >= eps for a in A for i in Z for t in T)
        #
        # model.addConstrs(
        #     x[a, t, t + 1] == (1 - K1[a, i, t]) * x[a, i, t] + K2[a, i, t] * quicksum(Pi[k, i] * x[a, k, t] for k in Z)
        #

        model.addConstrs(
            x[a, t, t + 1] == (1 - 1) * x[a, i, t] + 0 * quicksum(Pi[k, i] * x[a, k, t] for k in Z)
            for a in A for i in Z for t in TT)




        # model.addConstrs((x[a, i, t+1]==(1-actF(quicksum(x[a, i, m] * v[i, m] * deltaT * eta[i, m] for m in range(t + 1))/l))+ \
        #                  actF(quicksum(Pi[k, i] * eta[i, t] * quicksum(x[a, k, m] * v[i, m] * deltaT * eta[k, m] for m in range(t + 1)) for k in Z) / l) * quicksum(Pi[k, i] * x[a, k, t] for k in Z)
        #                           for a in A for i in Z for t in TT),"FlowConservation")
        # model.addConstrs((quicksum(Pi[i, j] * x[a, i, t] for j in Z) >= 0 for a in A for i in Z for t in TT),
        #                  "FlowConstraint")


        veh_od = {0: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')},
                  1: {'from': self.CTM_cellIdx_downgrade.index('A1.E101.C0'),
                      'to': self.CTM_cellIdx_downgrade.index('A0.E6.C4')}}

        for k, v in veh_od.items():
            # a = v['from']
            x[k, v['from'], 0].lb = 1
            x[k, v['from'], 0].ub = 1

            x[k, v['to'], self.max_time - 1].lb = 1
            x[k, v['to'], self.max_time - 1].ub = 1

        self.model = model
        return model

    def solve_model(self):
        """Solve the Gurobi model and return the objective value and solution details."""
        # Build the model if it hasn't been built yet
        if not hasattr(self, 'model'):
            self.build_model()

        # Optimize the model
        if self.model.status == GRB.INFEASIBLE:
            self.model.feasRelaxS(1, False, False, True)
            self.model.optimize()
        # self.model.optimize()

        # Check if a feasible solution was found
        if self.model.status == GRB.OPTIMAL:
            print(f"Optimal objective value: {self.model.objVal}")

            A, Z, T, TT = self.param

            # Retrieve dimensions
            num_vehicles = len(A)
            num_cells = len(Z)
            num_timesteps = len(T)

            # Initialize an empty array for the solution
            solution_array = np.zeros((num_vehicles, num_cells, num_timesteps), dtype=int)

            # Populate the array with solution values
            for a in range(num_vehicles):
                for i in range(num_cells):
                    for t in range(num_timesteps):
                        var = self.model.getVarByName(f"x[{a},{i},{t}]")
                        solution_array[a, i, t] = int(round(var.x)) if var.x > 0.5 else 0

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
    Ropt.build_model(veh_num=2)
    x, objective_value = Ropt.solve_model()
    print('time cost is {}'.format(time.time() - time1))

    with open(CTM_Path['cellIdx'], 'r') as file:
        CTM_cellIdx = [line.strip() for line in file]

    rout_list = Ropt.getRouteFromX(x)

    print(x[1, :, :])
