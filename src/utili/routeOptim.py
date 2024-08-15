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
        self.CTM_number = CTM_resultPath['number']
        self.CTM_cellCost = CTM_resultPath['number']

    def build_model(self):
        self.model = AbstractModel()
        self.model.T = Set()
        self.model.I = Set()
        self.model.A = Param(within=NonNegativeIntegers)

        self.model.alpha1 = Param()
        self.model.alpha2 = Param()

        self.model.x = Var(self.model.A, self.model.T, self.model.I, within=Binary)
        self.model.c = Param(self.model.t, self.model.I, initialize=self.cost_dict_from_df(self.CTM_cellCost))

        self.model.obj = Objective(rule=self.objective_rule, sense=minimize)

        instance = self.model.create_instance()

    @staticmethod
    def cost_dict_from_df(df):
        return {(t, i): df.at[t, i] for t in df.index for i in df.columns}

    @staticmethod
    def objective_rule(model):
        part1 = sum(model.alpha1 * model.c[t, i] * model.x[a, t, i] for t in model.T for i in model.I for a in model.A)

        part2 = model.alpha2 * sum(model.x[a, t, i] for t in model.T for i in model.I for a in model.A) / model.T * model.A * model.I

        return part1 - part2




if __name__ == '__main__':
    CTM_Path = {'number': 'result/ctmResult/CTMnumber_3600_1800dis.csv'}

    Ropt = RouteOptim(CTM_Path)
    Ropt.build_model()
    Ropt.build_model()
