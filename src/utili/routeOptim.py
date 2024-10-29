"""
Date: Aug 13, 2024
Author: Yilin Wang
Note: this file includes all the functions related to the pyomo optimization
List:
"""
import copy

import pandas as pd
import numpy as np
from pyomo.environ import *
import json
import gurobipy
import time


class RouteOptim:
    def __init__(self, CTM_resultPath, CTM_FDParam):
        # CTM_number_initial = pd.read_csv(CTM_resultPath['number'])
        self.CTM_numberMatrix_ori = pd.read_csv(CTM_resultPath['number']).iloc[:, 1:].to_numpy()
        self.CTM_numberOutMatrix_ori = pd.read_csv(CTM_resultPath['outnumber']).iloc[:, 1:].to_numpy()
        self.CTM_signalMatrix_ori = pd.read_csv(CTM_resultPath['sigflag']).iloc[:, 1:].to_numpy()
        self.CTM_connection = np.loadtxt(CTM_resultPath['connectionMatrix'])

        with open(CTM_resultPath['cellIdx'], 'r') as file:
            self.CTM_cellIdx = [line.strip() for line in file]

        # with open(CTM_resultPath['cellIdx'], 'r') as file:
        #     self.CTM_cellIdx = [line.strip() for line in file]

        # in future development, this two inputs will be replaced by direct dataframe

        # temp downgrade dimensions from the input [veh, time]
        self.max_time = 10
        self.CTM_numberMatrix = self.CTM_numberMatrix_ori[:, 0:self.max_time]
        self.CTM_numberOutMatrix = self.CTM_numberOutMatrix_ori[:, 0:self.max_time]
        self.CTM_signalMatrix = self.CTM_signalMatrix_ori[:, 0:self.max_time]

        self.ctm_fd = CTM_FDParam
        # self.CTM_cellCost = pd.read_csv(CTM_resultPath['number'])

        # self.FD

    @staticmethod
    def get_costCTM(number_matrix, outnumber, FD_param, signal_matrix):
        """
        :param number: a matrix of ctm vehicle number  [cell * time]
        :return: a matrix of cell cost over time [cell * time]
        """
        K = number_matrix / FD_param['length']  # density matrix
        Q = copy.deepcopy(K)
        # flow matrix
        for i in range(number_matrix.shape[0]):
            for j in range(number_matrix.shape[1]):
                Q[i, j] = FD_param['v_f'] * K[i, j] if K[i, j] <= FD_param['q_max'] / FD_param['v_f'] else -FD_param[
                    'w'] * (K[i, j] - FD_param['k_jam'])
        V = np.ones(K.shape) * FD_param['v_f']
        for i in range(K.shape[0]):
            for j in range(K.shape[1]):
                V[i, j] = Q[i, j] / K[i, j] if K[i, j] != 0 else V[i, j]
        C = number_matrix - outnumber  # travel delay, also denoted as travel cost for each cell over time
        V = V * signal_matrix
        return K, Q, V, C

    def build_model(self, veh_num=100):
        """
        :param veh_num: total number of vehicle currently
        :return:
        """
        self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
                                                          self.CTM_signalMatrix)
        self.model = ConcreteModel()
        # Z, T = K.shape
        self.model.Z = Set(initialize=[i for i in range(self.K.shape[0])], doc='set of cell index')
        self.model.T = Set(initialize=[i for i in range(self.K.shape[1])], doc='set of time index')
        self.model.TT = Set(initialize=[i for i in range(self.K.shape[1] - 1)], doc='set of (time-1) index')
        self.model.A = Set(initialize=[i for i in range(veh_num)], doc='set of vehicle index')
        self.model.alpha1 = Param(default=0.5)
        self.model.alpha2 = Param(default=0.5)
        self.model.l = Param(default=0.08)
        self.model.deltaT = Param(default=5 / 3600)
        self.model.M = Param(default=999999)

        self.model.x = Var(self.model.A, self.model.Z, self.model.T, within=Binary, bounds=[0,None])

        def add_cell_time_parameter(m):  # the input is a numpy array, with a dimension of [cell_idx, time_idx]
            return {(i, t): m[i, t] for i in range(m.shape[0]) for t in range(m.shape[1])}

        # cost parameter
        self.model.c = Param(self.model.Z, self.model.T, default=0, initialize=add_cell_time_parameter(self.C))
        # speed parameter
        self.model.v = Param(self.model.Z, self.model.T, default=0, initialize=add_cell_time_parameter(self.V))

        # signal flag parameter
        self.model.eta = Param(self.model.Z, self.model.T, default=0,
                               initialize=add_cell_time_parameter(self.CTM_signalMatrix))

        # matrix connection
        self.model.Pi = Param(self.model.Z, self.model.Z, default=0,
                              initialize=add_cell_time_parameter(self.CTM_connection))

        def sum_x_over_a_rule(model, i, t):
            return sum(model.x[a, i, t] for a in model.A)

        # Create an expression or parameter to store the sum over 'a'
        self.model.sum_x_over_a = Expression(self.model.Z, self.model.T, rule=sum_x_over_a_rule)

        ##################### start the constraint ###########################
        # 1.one vehicle rul
        def one_veh_rule(model, a, t):
            return sum(model.x[a, i, t] for i in model.Z) == 1

        self.model.oneVehConst = Constraint(self.model.A, self.model.T, rule=one_veh_rule)

        # 2.cell signal constraint
        # def cell_signal_rule(model, a):
        #     for i in model.Z:
        #         for t in model.T:
        #             return (1 - model.sig[i, t]) * (model.x[a, i, t+1] - model.x[a, i, t]) >= 0
        # self.model.cellSigConst = Constraint(self.model.A, rule=cell_signal_rule)

        # 2. cell travel distance constrain
        def travel_distance_rule(model, a, i, t):
            # model.trange1 = Set(initialize=[i for i in range(t+1)], doc='a dynamic t range over time1')

            return sum(model.x[a, i, m] * model.v[i, m] * model.deltaT for m in range(t + 1)) <= model.eta[
                i, t] * model.l + model.M * (1 - model.eta[i, t])

        self.model.travelDistanceConst = Constraint(self.model.A, self.model.Z, self.model.T, rule=travel_distance_rule)

        # 3. cell signal constringts
        def cell_signal_rule(model, a):
            for i in model.Z:

                for t in model.T:
                    return (1 - model.eta[i, t]) * (model.x[a, i, t + 1] - model.x[a, i, t]) >= 0

        self.model.cellSigConst = Constraint(self.model.A, rule=cell_signal_rule)

        # 4.flow conservation law
        '''20241005 try a new linearlized big M constraint'''
        self.model.K1 = Var(self.model.A, self.model.Z, self.model.T, within=Binary, bounds=[0, None])
        self.model.K2 = Var(self.model.A, self.model.Z, self.model.T, within=Binary, bounds=[0, None])

        self.model.delta1 = Param(self.model.A, self.model.Z, self.model.T, default=0.5, within=PositiveReals)
        self.model.delta2 = Param(self.model.A, self.model.Z, self.model.T, default=0.5, within=PositiveReals)
        M = 9999999
        #start sub expression for flow conservation law
        def flow_conservationM_rule_delta1(model, a, i, t):
            return model.delta1[a, i, t] == sum(model.x[a, i, m] * model.v[i, m] * model.deltaT * model.eta[i, m] for m in range(t + 1))/model.l
        self.model.flowConservConstDelta1 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservationM_rule_delta1)
        def flow_conservationM_rule_delta2(model, a, i, t):
            return model.delta2[a, i, t] == sum(model.Pi[k, i] * model.eta[i, t] * sum(model.x[a, k, m] * model.v[i, m] * model.deltaT * model.eta[k, m] for m in range(t + 1)) for k in model.Z) / model.l
        self.model.flowConservConstDelta2 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservationM_rule_delta2)
        def flow_conservationM_ruleK11(model, a, i, t):
            return model.K1[a, i, t]<=(model.delta1[a, i, t]-1+M)/M
        self.model.flowConservConstBigMK11 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservationM_ruleK11)
        def flow_conservationM_ruleK12(model, a, i, t):
            return model.K1[a, i, t]>=(model.delta1[a, i, t]-1)/M
        self.model.flowConservConstBigMK12 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservationM_ruleK12)
        def flow_conservationM_ruleK21(model, a, i, t):
            return model.K2[a, i, t]<=(model.delta2[a, i, t]-1+M)/M
        self.model.flowConservConstBigMK21 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservationM_ruleK21)
        def flow_conservationM_ruleK22(model, a, i, t):
            return model.K2[a, i, t]>=(model.delta2[a, i, t]-1)/M
        self.model.flowConservConstBigMK22 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservationM_ruleK22)

        def flow_conservation_rule(model, a, i, t):
            return model.x[a, i, t + 1] == (1 - model.K1[a, i, t])*model.x[a, i, t] + model.K2[a, i, t] * sum(model.Pi[k, i] * model.x[a, k, t] for k in model.Z)
        self.model.flow_conservationConstFinal = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservation_rule)
        #
        """this is the old conservation law with nonlinear format"""
        ##############################################################################################################################
        # def actF(x, k=100, H=1):
        #     return (1+tanh(k*(x-1)))*H*(x-1)
        #
        # def flow_conservation_rule(model, a, i, t):
        #     # model.trange2 = Set(initialize=[i for i in range(t+1)], doc='a dynamic t range over time2')
        #     fcp1 = (1 - actF(999 + sum(
        #         model.x[a, i, m] * model.v[i, m] * model.deltaT * model.eta[i, m] for m in range(t + 1)) / model.l)) * \
        #            model.x[a, i, t]  # part 1
        #     fcp2 = actF(sum(model.Pi[k, i] * model.eta[i, t] * sum(
        #         model.x[a, k, m] * model.v[i, m] * model.deltaT * model.eta[k, m] for m in range(t + 1)) for k in
        #                     model.Z) / model.l) * sum(model.Pi[k, i] * model.x[a, k, t] for k in model.Z)
        #     return model.x[a, i, t + 1] == fcp1 + fcp2
        #
        # self.model.flow_conservationConst = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservation_rule)
        #############################################################################################################################

        # def flow_conservation_rule1(model, a, i, t):
        #     model.trange = Set(initialize=[i for i in range(t)], doc='a dynamic t range over time')
        #     return model.x[a, i, t+1] == model.x[a, i, t] + model.x[a, i, t]*(1-2*model.x[a, i, t])*activateFunction(sum(sum(-model.Pi[i, k] * model.x[a, k, tt]*model.v[i,tt]*model.deltaT for k in model.Z) for tt in model.trange)/model.l)
        # self.flow_convervationConst = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservation_rule1)
        #
        # def flow_conservation_rule2(model, a, i, t):
        #     model.trange = Set(initialize=[i for i in range(t)], doc='aa dynamic t range over time')
        #     return sum(model.Pi[i, k] * model.x[a, k. t+1] for k in model.Z) == activateFunction(sum(model.x[a, i, tt]*model.v[i,tt]*model.deltaT for tt in model.trange)/model.l)
        # self.flow_convervationConst2 = Constraint(self.model.A, self.model.Z, self.model.TT, rule=flow_conservation_rule2)

        # 5.OD constraint
        # need another input from the network on current vehicle cell index
        # for testing purpose, hardcoding the o-d origins,
        # test case1: veh 1: from E101 to E107
        # test case2: veh 2: from E101 to E108
        veh_od = {0: {'from': self.CTM_cellIdx.index('A1.E101.C0'), 'to': self.CTM_cellIdx.index('A0.E6.C7')},
                  1: {'from': self.CTM_cellIdx.index('A1.E101.C0'), 'to': self.CTM_cellIdx.index('A0.E2.C7')}}

        # veh_od = {0: {'from': self.CTM_cellIdx.index('A1.E101.C0'), 'to': self.CTM_cellIdx.index('A1.-E107.C0')},
        #           1: {'from': self.CTM_cellIdx.index('A1.E101.C0'), 'to': self.CTM_cellIdx.index('A1.-E108.C0')}}

        # vi_id = 0
        # fixed cell list
        fixlist = ['A1.E119.C0', 'A1.E119.C4', 'A1.E119.C5', 'A1.E119.C6', 'A1.E119.C7',
                   'A1.E118.C0', 'A1.E118.C4', 'A1.E118.C5', 'A1.E118.C6', 'A1.E118.C7',
                   'A1.E117.C0', 'A1.E117.C4', 'A1.E117.C5', 'A1.E117.C6', 'A1.E117.C7',
                   'A1.E116.C0', 'A1.E116.C4', 'A1.E116.C5', 'A1.E116.C6', 'A1.E116.C7',
                   'A1.E115.C0', 'A1.E115.C4', 'A1.E115.C5', 'A1.E115.C6', 'A1.E115.C7',
                   'A1.E114.C0', 'A1.E114.C4', 'A1.E114.C5', 'A1.E114.C6', 'A1.E114.C7',
                   'A1.E113.C0', 'A1.E113.C4', 'A1.E113.C5', 'A1.E113.C6', 'A1.E113.C7',
                   'A1.E112.C0', 'A1.E112.C4', 'A1.E112.C5', 'A1.E112.C6', 'A1.E112.C7',
                   'A1.E111.C0', 'A1.E111.C4', 'A1.E111.C5', 'A1.E111.C6', 'A1.E111.C7',
                   'A1.E110.C0', 'A1.E110.C4', 'A1.E110.C5', 'A1.E110.C6', 'A1.E110.C7',
                   'A1.E109.C0', 'A1.E109.C4', 'A1.E109.C5', 'A1.E109.C6', 'A1.E109.C7',
                   'A1.E108.C0', 'A1.E108.C4', 'A1.E108.C5', 'A1.E108.C6', 'A1.E108.C7',
                   'A1.E106.C0', 'A1.E106.C4', 'A1.E106.C5', 'A1.E106.C6', 'A1.E106.C7',
                   'A1.E105.C0', 'A1.E105.C4', 'A1.E105.C5', 'A1.E105.C6', 'A1.E105.C7',
                   'A1.E104.C0', 'A1.E104.C4', 'A1.E104.C5', 'A1.E104.C6', 'A1.E104.C7',
                   'A1.E103.C0', 'A1.E103.C4', 'A1.E103.C5', 'A1.E103.C6', 'A1.E103.C7',
                   'A0.E9.C1', 'A0.E9.C2', 'A0.E9.C3', 'A0.E9.C4', 'A0.E9.C5', 'A0.E9.C6', 'A0.E9.C7',
                   'A0.-E9.C1', 'A0.-E9.C2', 'A0.-E9.C3', 'A0.-E9.C4', 'A0.-E9.C5', 'A0.-E9.C6','A0.-E9.C7',
                   'A0.E10.C1', 'A0.E10.C2', 'A0.E10.C3', 'A0.E10.C4', 'A0.E10.C5', 'A0.E10.C6', 'A0.E10.C7',
                   'A0.-E10.C1', 'A0.-E10.C2', 'A0.-E10.C3', 'A0.-E10.C4', 'A0.-E10.C5', 'A0.-E10.C6','A0.-E10.C7',

                   ]
        for fxcellidx in fixlist:
            for t in range(self.max_time):
                self.model.x[0, self.CTM_cellIdx.index(fxcellidx), t].fixed = True
                self.model.x[0, self.CTM_cellIdx.index(fxcellidx), t].fixed = 0
                self.model.x[1, self.CTM_cellIdx.index(fxcellidx), t].fixed = True
                self.model.x[1, self.CTM_cellIdx.index(fxcellidx), t].fixed = 0

        for k, v in veh_od.items():
            self.model.x[k, v['from'], 0].fixed = True
            self.model.x[k, v['from'], 0].value = 1

            self.model.x[k, v['to'], self.max_time - 1].fixed = True
            self.model.x[k, v['to'], self.max_time - 1].value = 1

            # vi_id += 1

        # self.model.x[1, 0, 0].fixed = True
        # self.model.x[1, 0, 0].value = 0

        # def OD_constraint_rule(model):
        #     return model.x[1, 10, 0] == 1  #[a, i, t]
        # self.odConst = Constraint(rule=OD_constraint_rule)

        def objective_rule(model):
            # x_sum_a = sum(model.x[a, :, :] for a in model.A)
            # print(x_sum_a
            part1 = model.alpha1 * sum(
                model.c[i, t] * model.sum_x_over_a[i, t] for t in model.T for i in model.Z)  # travel cost
            part2 = model.alpha2 * sum(model.x[a, i, t] for t in model.T for i in model.Z for a in model.A) / (
                    self.C.shape[0] * self.C.shape[1] * veh_num)  # coverage cost
            part3 = 0
            return part1 - part2

        self.model.obj = Objective(rule=objective_rule, sense=minimize)

        # instance = self.model.create_instance(data)
        # self.model.pprint()
        return self.V

    def solve_model(self, solverString='glpk'):
        solver = SolverFactory(solverString)
        print('i will start')
        # self.model.cons1.pprint()
        solver.solve(self.model, tee=True).write()
        # self.model.x.display()

        # Extract the variable values into a numpy array
        print('start to convert output')
        x_np = np.zeros((len(self.model.A), len(self.model.Z), len(self.model.T)))

        for a_idx, a in enumerate(self.model.A):
            for i_idx, i in enumerate(self.model.Z):
                for t_idx, t in enumerate(self.model.T):
                    x_np[a_idx, i_idx, t_idx] = self.model.x[a, i, t].value

        return x_np


def checkX(x):
    print('x shape is:{}'.format(x.shape))
    x_tmp = np.sum(x, axis=1)
    print('x_tmp shape is:{}'.format(x_tmp.shape))
    for i in range(x_tmp.shape[0]):
        for j in range(x_tmp.shape[1]):
            if x_tmp[i, j] != 1:
                print('x_tmp[{},{}] is not good with value {}'.format(i, j, x_tmp[i, j]))


def getRouteFromX(x, cell_idx):
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

    Ropt = RouteOptim(CTM_Path, FD_param)
    V = Ropt.build_model(veh_num=2)
    x = Ropt.solve_model(solverString='gurobi_direct')
    # checkX(x)

    with open(CTM_Path['cellIdx'], 'r') as file:
        CTM_cellIdx = [line.strip() for line in file]

    rout_list = getRouteFromX(x, CTM_cellIdx)

    print(x[1, :, :])
