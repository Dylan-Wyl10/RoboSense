"""
Date: Aug 13, 2024
Author: Yilin Wang
Note: this file includes all the functions related to the pyomo optimization
List:
"""

import pandas as pd
import numpy as np
from pyomo.environ import *

class RouteOptim:
    def __init__(self, CTM_resultPath):
        self.CTM_number = pd.read_csv(CTM_resultPath['number'])
        self.CTM_cellCost = pd.read_csv(CTM_resultPath['number'])
        # self.FD

    def build_model(self):
        self.model = AbstractModel()
        self.model.T = Set()
        self.model.I = Set()
        self.model.A = Set()
        self.model.alpha1 = Param()
        self.model.alpha2 = Param()

        # tt = self.cost_df_to_np(self.CTM_cellCost)
        # ttt = tt.keys()
        # self.model.x = Var(self.model.A, self.model.T, self.model.I, within=NonNegativeIntegers, bounds=(0, 1), initialize=0)
        self.model.x = Var(self.model.A, self.model.T, self.model.I, within=Binary, initialize=0)

        self.model.c = Param(self.model.I, self.model.T, default=0, initialize=self.cost_df_to_np(self.CTM_cellCost))

        self.model.obj = Objective(rule=self.objective_rule, sense=minimize)

        # print(self.CTM_cellCost)
        I_set = len(list(self.CTM_cellCost.index))  # Extracts 'i1', 'i2', 'i3'
        T_set = len(list(self.CTM_cellCost.columns))

        data = {
            None: {
                'T': [t for t in range(T_set)],  # Set of time periods
                'I': [i for i in range(I_set)],  # Set of indices/cells
                'A': [a for a in range(30)],  # Example total number of vehicles
                'alpha1': {None: 0.5},
                'alpha2': {None: 0.5},
            }
        }

        instance = self.model.create_instance(data)
        self.model.pprint()
        solver = SolverFactory('glpk')
        solver.solve(instance)
        instance.display()


    @staticmethod
    def cost_df_to_np(df):
        a = df.to_numpy()[:, 1:]
        return {(i, t): a[i, t] for i in range(a.shape[0]) for t in range(a.shape[1])}

    @staticmethod
    def objective_rule(model):
        part1 = model.alpha1 * sum(model.c[i, t] * sum(model.x[a, t, i] for a in model.A) for t in model.T for i in model.I )

        part2 = model.alpha2 * sum(model.x[a, t, i] for t in model.T for i in model.I for a in model.A) / model.T * model.A * model.I

        return part1 - part2

    # def getCost(self):





if __name__ == '__main__':
    CTM_Path = {'number': '../../result/ctmResult/CTMnumber_3600_1800dis.csv'}

    Ropt = RouteOptim(CTM_Path)
    Ropt.build_model()
