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


class RouteOptim:
    def __init__(self, CTM_resultPath, CTM_FDParam):
        # CTM_number_initial = pd.read_csv(CTM_resultPath['number'])
        self.CTM_numberMatrix = pd.read_csv(CTM_resultPath['number']).iloc[:, 1:].to_numpy()
        self.CTM_numberOutMatrix = pd.read_csv(CTM_resultPath['outnumber']).iloc[:, 1:].to_numpy()
        # in future development, this two inputs will be replaced by direct dataframe

        self.ctm_fd = CTM_FDParam
        # self.CTM_cellCost = pd.read_csv(CTM_resultPath['number'])

        # self.FD

    @staticmethod
    def get_costCTM(number_matrix, outnumber, FD_param):
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
        V = copy.deepcopy(K)
        for i in range(K.shape[0]):
            for j in range(K.shape[1]):
                V[i, j] = 0 if K[i, j] == 0 else Q[i, j] / K[i, j]
        C = number_matrix - outnumber  # travel delay, also denoted as travel cost for each cell over time
        return K, Q, V, C

    def build_model(self, veh_num=100):
        """
        :param veh_num: total number of vehicle currently
        :return:
        """
        K, Q, V, C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd)
        self.model = ConcreteModel()
        # Z, T = K.shape
        self.model.Z = Set(initialize=[i for i in range(K.shape[0])], doc='set of cell index')
        self.model.T = Set(initialize=[i for i in range(K.shape[1])], doc='set of time index')
        self.model.A = Set(initialze=[i for i in range(veh_num)], doc='set of vehicle index')
        self.model.alpha1 = Param()
        self.model.alpha2 = Param()

        self.model.x = Var(self.model.A, self.model.T, self.model.Z, within=Binary, initialize=0)

        def get_cost_dic(c):
            # the input is a numpy array
            return {(i, t): c[i, t] for i in range(c.shape[0]) for t in range(c.shape[1])}

        self.model.c = Param(self.model.Z, self.model.T, default=0, initialize=get_cost_dic(C))

        def objective_rule(model):
            part1 = model.alpha1 * sum(
                model.c[i, t] * sum(model.x[a, t, i] for a in model.A) for t in model.T for i in model.Z)
            part2 = model.alpha2 * sum(model.x[a, t, i] for t in model.T for i in model.Z for a in model.A) / (
                        C.shape[0] * C.shape[1] * veh_num)

            return part1 - part2

        self.model.obj = Objective(rule=objective_rule, sense=minimize)

        # instance = self.model.create_instance(data)
        self.model.pprint()
        solver = SolverFactory('glpk')
        solver.solve(self.model)
        self.model.display()

        # solver.solve(instance)
        # instance.display()


if __name__ == '__main__':
    CTM_Path = {'number': '../../result/ctmResult/CTMnumber_3600_1800dis.csv',
                'outnumber': '../../result/ctmResult/CTMflow_3600_1800dis.csv'}
    FD_param = {
        'v_f': 57.6,  # km/hr
        'k_jam': 133,  # veh/km
        'q_max': 1744,  # veh/hour
        'w': 17.94,
        'length': 0.08,  # km
        'delta_t': 5 / 3600,  # hr
    }

    Ropt = RouteOptim(CTM_Path, FD_param)
    Ropt.build_model()
