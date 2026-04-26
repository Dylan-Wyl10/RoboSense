# Here is the rewritten script using Gurobi syntax, following the structure of the original Pyomo script


import copy
import pandas as pd
import numpy as np
from gurobipy import Model, GRB, quicksum
from collections import deque
import json
from functools import lru_cache
import time
from src.utili.config_debug_tmp import CaseStudyConfig


class RouteOptimGurobi:
    def __init__(self, CTM_FDParam, veh_od, max_time, current_time, CTM_resultPath=None, CTM_input=None, Load_mode='file'):
        # Initialize data matrices from file paths
        self.Load_mode = Load_mode
        if Load_mode == 'file':
            self.CTM_numberMatrix_ori = pd.read_csv(CTM_resultPath['number']).iloc[:, 1:].to_numpy()
            self.CTM_signalMatrix_ori = pd.read_csv(CTM_resultPath['sigflag']).iloc[:, 1:].to_numpy()
            self.CTM_connection_ori = np.loadtxt(CTM_resultPath['connectionMatrix'])
            with open(CTM_resultPath['cellIdx'], 'r') as file:
                self.CTM_cellIdx_ori = [line.strip() for line in file]
        elif Load_mode == 'direct':
            self.CTM_numberMatrix_ori = CTM_input['number'].to_numpy()
            self.CTM_signalMatrix_ori = CTM_input['sigflag'].to_numpy()
            self.CTM_connection_ori = CTM_input['cell connection']
            self.CTM_cellIdx_ori = CTM_input['cell idx']

        elif Load_mode == "toynet":
            self.CTM_numberMatrix_ori = None
            self.CTM_signalMatrix_ori = None
            self.CTM_connection_ori = None
            self.CTM_cellIdx_ori = None

        self.veh_od = veh_od
        self.sumo_time = current_time

        self.max_time = max_time
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

        ####### downgrade CTM network
        # downgrageIdx = [self.CTM_cellIdx_ori.index(ci) for ci in self.CTM_cellIdx_downgrade]
        # self.CTM_numberMatrix = self.CTM_numberMatrix_ori[downgrageIdx, 100:100 + self.max_time]
        # self.CTM_signalMatrix = self.CTM_signalMatrix_ori[downgrageIdx, 100:100 + self.max_time]
        # self.CTM_connection = self.CTM_connection_ori[np.ix_(downgrageIdx, downgrageIdx)]
        # self.cellidx = self.CTM_cellIdx_downgrade

        self.CTM_numberMatrix = self.CTM_numberMatrix_ori
        self.CTM_signalMatrix = self.CTM_signalMatrix_ori
        self.CTM_connection = self.CTM_connection_ori
        self.cellidx = self.CTM_cellIdx_ori

        self.ctm_fd = CTM_FDParam

    def get_costCTM(self, number_matrix, FD_param, signal_matrix):
        K = number_matrix / FD_param['length']  # density matrix
        Q = copy.deepcopy(K)
        # set a binary variable to distiguish the shape of the FD
        kc_l, kc_r = FD_param['q_max'] / FD_param['v_f'], FD_param['k_jam']-FD_param['q_max']/FD_param['w']
        istrangle = True if abs(kc_l-kc_r) <= 1e-5 else False
        # flow matrix
        if istrangle:
            for i in range(number_matrix.shape[0]):
                for j in range(number_matrix.shape[1]):
                    Q[i, j] = FD_param['v_f'] * K[i, j] if K[i, j] <= FD_param['q_max'] / FD_param['v_f'] else -FD_param[
                        'w'] * (K[i, j] - FD_param['k_jam'])
        else:  # if the FD is not trangle
            for i in range(number_matrix.shape[0]):
                for j in range(number_matrix.shape[1]):
                    if K[i, j] <= kc_l:
                        Q[i, j] = FD_param['v_f'] * K[i, j]
                    elif kc_l < K[i, j] <= kc_r:
                        Q[i, j] = FD_param['q_max']
                    elif kc_r < K[i, j] <= FD_param['k_jam']:
                        Q[i, j] = -FD_param['w'] * (K[i, j] - FD_param['k_jam'])

        V = np.ones(K.shape) * FD_param['v_f']
        C = np.ones(K.shape)
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
    def get_small_net_param(veh=2, time_step=45):

        # 2x2 network
        # con = {1: [2, 9], 2: [11], 3: [4, 10], 4: [12], 5: [6], 6: [14],
        #        7: [3, 8], 8: [5, 15], 9: [4, 10], 10: [6], 11: [12], 12: [14],
        #        13: [7, 1], 14: [], 15: []}

        # 3x3 network, single direction
        con = {1: [2, 16], 2: [3, 19], 3: [22], 4: [5, 17], 5: [6, 20], 6: [23],
               7: [8, 18], 8: [9, 21], 9: [24], 10: [11], 11: [12], 12: [26],
               13: [4, 14], 14: [7, 15], 15: [10], 16: [5, 17], 17: [18, 8], 18: [11],
               19: [6, 20], 20: [9, 21], 21: [12], 22: [23], 23: [24], 24: [26],
               25: [1, 13], 26: []}

        link = len(con)
        # link, veh, time_step = 15, 2, 45
        C = np.ones((link, time_step))
        for i in range(C.shape[0]):
            for t in range(C.shape[1]):
                C[i, t] = (i + t + 1) % 5 + 1

        connection = np.zeros((len(con.keys()), len(con.keys())))
        for k, v in con.items():
            for vv in v:
                connection[k - 1, vv - 1] = 1

        # veh_od = {0: {'from': 1, 'to': 26, 'time': 0},
        #           1: {'from': 1, 'to': 26, 'time': 1},
        #           2: {'from': 1, 'to': 26, 'time': 2},
        #           3: {'from': 1, 'to': 26, 'time': 3}}

        return connection, time_step, C

    def set_optm_input(self, veh_od, time_step):
        self.veh_od = veh_od

    @staticmethod
    def find_paths(Pi, start, end, max_length=None, mode="length", top_k=None, max_route=None):
        """
        Find paths from start to end with either max_length constraint or top-k shortest paths.

        Args:
            Pi (np.ndarray): Adjacency matrix, Pi[i, j] = 1 means edge from i to j exists.
            start (int): Index of start node.
            end (int): Index of end node.
            max_length (int or None): Maximum path length (only for mode='length').
            mode (str): 'length' to filter by max_length, or 'topk' to return k shortest paths.
            top_k (int or None): Number of paths to return in topk mode.
            max_route (int or None): Max number of routes to return in length mode.

        Returns:
            List[List[int]]: List of complete paths from start to end.
        """
        assert mode in ["length", "topk"], "mode must be 'length' or 'topk'"

        result_paths = []

        if mode == "length":
            def dfs(node, path, visited, depth):
                if max_length is not None and depth > max_length:
                    return
                if max_route is not None and len(result_paths) >= max_route:
                    return
                path.append(node)
                if node == end:
                    result_paths.append(path.copy())
                else:
                    for neighbor in np.where(Pi[node] == 1)[0]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            dfs(neighbor, path, visited, depth + 1)
                            visited.remove(neighbor)
                path.pop()

            dfs(start, [], set([start]), 1)

        elif mode == "topk":
            queue = deque()
            queue.append(([start], set([start])))

            while queue and len(result_paths) < top_k:
                current_path, visited = queue.popleft()
                last_node = current_path[-1]

                if last_node == end:
                    result_paths.append(current_path)
                    continue

                for neighbor in np.where(Pi[last_node] == 1)[0]:
                    if neighbor not in visited:
                        new_path = current_path + [neighbor]
                        new_visited = visited.copy()
                        new_visited.add(neighbor)
                        queue.append((new_path, new_visited))

        return result_paths

    @staticmethod
    def extract_arcs_within_time(paths, C, t0):
        """
        args:
            paths (List[List[int]]): All possible node paths.
            C (np.ndarray): Travel time matrix, C[i, t] indicates travel time at node i at time t.
            t0 (int or float): Starting time for traversal.
        """
        arc_set = set()
        arcs_with_time = []

        for p in paths:
            current_time = t0
            for i in range(len(p) - 1):
                from_node = p[i]
                to_node = p[i + 1]

                t_idx = int(min(current_time, C.shape[1] - 1))  # clip current_time within C validation range
                arc = (p[i], p[i + 1])
                travel_time = C[from_node, t_idx]

                earliest = current_time
                latest = current_time + travel_time
                # Create a hashable representation for deduplication
                arc_key = (from_node, to_node, round(earliest, 6), round(latest, 6))  # Round for stability

                if arc_key not in arc_set:
                    arc_set.add(arc_key)
                    arcs_with_time.append([from_node, to_node, int(earliest), int(latest)])
                current_time += travel_time
        return arcs_with_time

    def build_model(self, param, veh_num=2, small_net=True, parseZ=True):
        print('start build model')
        # self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
        #                                                   self.CTM_signalMatrix)

        # Case_config = CaseStudyConfig()
        if small_net:
            self.CTM_connection, time_step, self.C = self.get_small_net_param()
        else:
            self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix,
                                                              self.ctm_fd,
                                                              self.CTM_signalMatrix)
            time_step = self.K.shape[1]

            # small network for case study
            # self.veh_od = Case_config.small_net_od
            # self.veh_od = Case_config.full_net_2200_od   # full network in 2200s in simulation

            # self.veh_od = CTM.generateODforOPTIm  # a preset api for CTM od

        # Parameters
        alpha1, alpha2, M, = param[0], param[1], param[2]

        # Sets
        I = [i for i in range(self.CTM_connection.shape[0])]  # Links (nodes)
        A = [i for i in range(veh_num)]  # Vehicles
        T = [i for i in range(time_step)]  # Time horizon

        self.para_set = (A, I, T)

        # load static parameters
        c = {(i, t): self.C[i, t] for i in I for t in T}
        Pi = {(i, j): self.CTM_connection[i, j] for i in I for j in I}

        self.c = c  # for visulization pupers
        ######################################################

        # Model Initialization
        model = Model("TDVRP-CTM")

        # Decision Variables
        # x = model.addVars(A, I, T, vtype=GRB.BINARY, name="x")  # Vehicle on link at time t
        # y = model.addVars(I, T, vtype=GRB.BINARY, name="y",)  # occupation variable y


        if parseZ:
            z_keys = []
            x_keys = set()
            w_keys = set()
            y_keys = set()

            t0 = time.time()
            route4all = []
            for a in A:
                # a filter indexed by a to indicate the feasible path for z
                t1 = time.time()
                max_route = min(2 ** (len(self.veh_od[a]["current_route"])), 512)
                routes = self.find_paths(self.CTM_connection, self.veh_od[a]["from"], self.veh_od[a]["to"],
                                         max_length=5*self.veh_od[a]["route_length"], mode='length', top_k=100, max_route=max_route)
                print(f'veh {a} find {len(routes)} feasible route in {max_route} to cell {self.veh_od[a]["to"]} with budget {self.veh_od[a]["budget"]} '
                      f'and route length {self.veh_od[a]["route_length"]} need {time.time() - t1} seconds')
                print(f'veh {a} edge pos: {self.veh_od[a]["edge_pos"]}, remin_edge: {self.veh_od[a]["remine_edge"]}, '
                      f'budget:{self.veh_od[a]["budget"]}, current route:{self.veh_od[a]["current_route"]}')
                print(f'veh {a} edge: {self.veh_od[a]['current_edge']}')
                if len(routes) == 0:
                    from_now = self.cellidx[self.veh_od[a]["from"]]
                    if from_now.endswith('.C6'):
                        from_new = from_now[:-3] + '.C7'
                    elif from_now.endswith('.C7'):
                        from_new = from_now[:-3] + '.C6'
                    else:
                        from_new = from_now
                    self.veh_od[a]["from"] = self.cellidx.index(from_new)
                    # provide a backup option for vehicle on no changing zone.
                    with open("log.txt", "a") as f:
                        f.write(f'veh {self.veh_od[a]["name"]} is in cell {from_now} at {self.sumo_time} to cell{self.cellidx[self.veh_od[a]["to"]]}, '
                                f'will be in new start cell {from_new}. the route length is {self.veh_od[a]["route_length"]} \n')
                    # print(f'veh {a} is in new cell{self.cellidx[self.veh_od[a]['from']]} now')
                    routes = self.find_paths(self.CTM_connection, self.cellidx.index(from_new), self.veh_od[a]["to"],
                                             max_length=self.veh_od[a]["route_length"], mode='topk', top_k=100, max_route=max_route)
                    print(
                        f'veh {a} find {len(routes)} new feasible route from cell {from_new} in {max_route} with budget {self.veh_od[a]["budget"]}'
                        f' and remine route {self.veh_od[a]["route_length"]},  need {time.time() - t1} seconds')

                t1 = time.time()
                r_cell = []
                for r in routes:
                    r_cell.append([self.CTM_cellIdx_ori[rr] for rr in r])
                route4all.append(r_cell)
                arcs = self.extract_arcs_within_time(routes, self.C, self.veh_od[a]["time"])
                print(f'veh {a} extract {len(arcs)} arcs need {time.time() - t1} seconds')
                t1 = time.time()
                for arc in arcs:
                    i, j, t, s = arc[0], arc[1], arc[2], arc[3]
                    if s < len(T):
                        z_keys.append((a, i, j, t, s))
                        x_keys.add((a, i, t))
                        for tt in range(t, s):
                            w_keys.add((a, i, tt))
                print(f'veh {a} extract x, w, z in {time.time() - t1} seconds')
                # print('yes')
            print(f'z_keys has been created within {time.time() - t0} seconds')



            self.z_keys = z_keys
            self.x_keys = list(x_keys)
            self.w_keys = list(w_keys)

            # set y based on w
            self.idx_count_y = []
            # self.rec_6 = {}
            for wkey in self.w_keys:
                yi, yt = wkey[1], wkey[2]
                if (yi, yt) not in self.idx_count_y:
                    self.idx_count_y.append((yi, yt))
                    y_keys.add((yi, yt))
            self.y_keys = list(y_keys)

            z = model.addVars(z_keys, vtype=GRB.BINARY, name="z")  # Vehicle moves between links
            x = model.addVars(self.x_keys, vtype=GRB.BINARY, name="x")
            y = model.addVars(self.y_keys, vtype=GRB.BINARY, name="y")
            omg = model.addVars(self.w_keys, vtype=GRB.BINARY, name="omega")
        else:
            "Note: this part is not implemented in constraint"
            x = model.addVars(A, I, T, vtype=GRB.BINARY, name="x")  # Vehicle on link at time t
            omg = model.addVars(A, I, T, vtype=GRB.BINARY, name="omega")  # variable omege
            y = model.addVars(I, T, vtype=GRB.BINARY, name="y") # variable y
            z = model.addVars(A, I, I, T, T, vtype=GRB.BINARY, name="z")  # Vehicle moves between link

        # tau = model.addVars(A, I, vtype=GRB.INTEGER, name="tau")
        # the = model.addVars(I, I, A, vtype=GRB.INTEGER, name="theta")  # theta variable
        # eta = model.addVars(A, I, T, vtype=GRB.BINARY, name="eta")  # binary variable for arrive time constraint

        # for xvar in model.getVars():
        #     a = xvar.VarName
        #     print(a)

        print(f"build_model: veh_num={veh_num}")
        model.setObjective(
            alpha1 * quicksum(
                (c[key[1], key[2]] * x[key] for key in self.x_keys if (key[1], key[2]) in c)) / veh_num - alpha2 * quicksum(
                y[ykey] for ykey in self.y_keys) / (self.CTM_connection.shape[0] * time_step), GRB.MINIMIZE)
            # quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A),


        ################################################ Constraints ###################################################
        print("condition 0 is finished")
        t1 = time.time()
        # 1. FLow conservation (linearlized)
        # axillary variable z
        if parseZ:
            # for a in A:
            #     model.addConstrs((x[a, i, t] == quicksum(z[key] for key in z_keys if key[0] == a and key[1] == i and key[3] == t)
            #                       for i in I for t in T if i != self.veh_od[a]['to']), name='axillary variable z')

            for xkey in self.x_keys:
                a, i, t = xkey[0], xkey[1], xkey[2]
                if i != self.veh_od[a]['to']:
                    model.addConstr(
                        x[xkey] == quicksum(z[key] for key in z_keys if key[0] == a and key[1] == i and key[3] == t)
                        , name='axillary_variable z')
            # for a in A:
            #     for i in I:
            #         for t in T:
            #             if i != self.veh_od[a]['to']:
            #                 model.addConstr(x[a, i, t] == quicksum(
            #                     z[key] for key in z_keys if key[0] == a and key[1] == i and key[3] == t)
            #                                 , name='axillary variable z')
        else:
            for a in A:
                for i in I:
                    for t in T:
                        # if (i != veh_odtmp[a]['to'] and i != 11):
                        if i != self.veh_od[a]['to']:
                            model.addConstr(x[a, i, t] == quicksum(z[a, i, j, t, s] for j in I for s in T),
                                            name='axillary_variable z')

        print(f"constraint 1 is completed at time {time.time() - t1}")
        t1 = time.time()
        # 2. Network Tepology constraint
        for key in z_keys:
            a, i, j, t, s = key
            model.addConstr(z[key] <= x[a, i, t],
                            name=f'z_leq_x_a{a}_i{i}_j{j}_t{t}_s{s}')  # network tepology constraint
        print(f"constraint 2 is completed at time {time.time() - t1}")
        t1 = time.time()

        # 3* network flow conservation law, od constraint
        if parseZ:
            idx_count_3 = []  #flow conservation index recordings
            for zkey in z_keys:
                a, j, s = zkey[0], zkey[2], zkey[4]
                if (a, j, s) not in idx_count_3:
                    idx_count_3.append((a, j, s))
                    incoming = quicksum(z[key] for key in z_keys if key[0] == a and key[2] == j and key[4] == s)
                    outgoing = quicksum(z[key] for key in z_keys if key[0] == a and key[1] == j and key[3] == s)
                    if (j != self.veh_od[a]['from'] and j != self.veh_od[a]['to']):
                    # if j != self.veh_od[a]['from']:
                        model.addConstr(incoming - outgoing == 0, name=f'netflow_conservation[{a},{j},{s}]')
                    elif j == self.veh_od[a]['to']:
                        model.addConstr(quicksum(z[key] for key in z_keys if key[0] == a and key[2] == j) == 1, name=f'netflow_conservation_end{j}')

        # 3**  od constraing
        for a in self.veh_od.keys():
            model.addConstr(x[(a, self.veh_od[a]['from'], 0)] == 1, name='od_law')

        print(f"constraint 3 is completed at time {time.time() - t1}")
        t1 = time.time()

        # 4. Time-dependent link constraints
        # for a in A:
        #     for t in T:
        model.addConstrs(
            (quicksum(x[xkey] for xkey in self.x_keys if xkey[0] == a and xkey[2] == t) <= 1 for a in A for t in T),
            name="time dependent link constraints")
        print(f"constraint 4 is completed at time {time.time() - t1}")
        t1 = time.time()

        # 5. Time-travel bound for vehicle
        # model.addConstrs(quicksum(x[a, i, t] for t in T) <= 1 for a in A for i in I)
        model.addConstrs(
            (quicksum(x[xkey] for xkey in self.x_keys if xkey[0] == a and xkey[1] == i) <= 1 for a in A for i in I),
            name="time dependent link constraints")
        print(f"constraint 5 is completed at time {time.time() - t1}")
        t1 = time.time()

        # 6. omega-y condition (phase 2)
        # model.addConstrs((y[i, t] <= quicksum(omg[okey] for okey in self.w_keys if okey[1] == i and okey[2] == t)
        #                   for i in I for t in T), name="omega-y condition1")
        # model.addConstrs((M * y[i, t] >= quicksum(omg[okey] for okey in self.w_keys if okey[1] == i and okey[2] == t)
        #                   for i in I for t in T), name="omega-y condition2")
        # print(f'constraint 6 is completed at time {time.time() - t1}')
        # t1 = time.time()

        # self.idx_count_6 = []
        self.rec_6 = {}
        for ykey in self.y_keys:
            i, t = ykey[0], ykey[1]
            self.rec_6[(i, t)] = [okey for okey in self.w_keys if okey[1] == i and okey[2] == t]
            model.addConstr(y[ykey] <= quicksum(omg[okey] for okey in self.w_keys if okey[1] == i and okey[2] == t)
                            , name="omega-y condition1")
            model.addConstr(
                M * y[ykey] >= quicksum(omg[okey] for okey in self.w_keys if okey[1] == i and okey[2] == t)
                , name="omega-y condition2")

            # if (i, t) not in self.idx_count_6:
            #     self.idx_count_6.append((i, t))
            #     self.rec_6[(i, t)] = [okey for okey in self.w_keys if okey[1] == i and okey[2] == t]
            #     model.addConstr(y[i, t] <= quicksum(omg[okey] for okey in self.w_keys if okey[1] == i and okey[2] == t)
            #                      , name="omega-y condition1")
            #     model.addConstr(
            #         M * y[i, t] >= quicksum(omg[okey] for okey in self.w_keys if okey[1] == i and okey[2] == t)
            #          , name="omega-y condition2")
        print(f'constraint 6 is completed at time {time.time() - t1}')
        t1 = time.time()

        # 7. omega-x condition (phase 2)
        # print('at here')
        self.time_step = int(len(T))

        model.addConstrs(
            (omg[okey] <= quicksum(x[xkey] for xkey in self.x_keys if xkey[0] == okey[0] and xkey[1] == okey[1]) for
             okey in self.w_keys), name="omega-x condition eq11")
        # model.addConstrs(omg[okey] <= quicksum(x[key] for x in key if (key[0] = okey[0] and key[1]=okey[1])) for okey in self.w_keys)
        # =======================================================================================================
        # for a in A:
        #     for i in I:
        #         for t in T:
        #             t_mid = int(t + c[i, t])
        #             t_end = self.time_step
        #             model.addConstr(quicksum(omg[a, i, k] for k in range(0, t)) <= M * (1 - x[a, i, t]),
        #                             name="omega-x condition-eq16")
        #
        #             # model.addConstr(quicksum(omg[okey] for k in range(0, t)) <= M * (1 - x[a, i, t]),
        #             #                 name="omega-x condition-eq16")
        #             if t_mid <= self.time_step - 1:  # here the time index --> max time step minors 1
        #                 model.addConstr(quicksum(omg[a, i, k] for k in range(t, t_mid)) >= x[a, i, t] * c[i, t],
        #                                 name="omega-x condition-eq17")
        #                 model.addConstr(quicksum(omg[a, i, k] for k in range(t, t_mid)) <= x[a, i, t] * c[i, t] + M * (
        #                         1 - x[a, i, t]), name="omega=x condition-eq18")
        #                 model.addConstr(quicksum(omg[a, i, k] for k in range(t_mid, t_end)) <= M * (1 - x[a, i, t]),
        #                                 name="omega-x condition-eq19")
        # =========================================================================================================
        for xkey in self.x_keys:
            a, i, t = xkey[0], xkey[1], xkey[2]
            t_m, t_e = int(t + c[i, t]), self.time_step
            model.addConstr(quicksum(
                omg[wkey] for wkey in self.w_keys if (wkey[0] == a and wkey[1] == i and 0 <= wkey[2] <= t - 1)) <= M * (
                                        1 - x[xkey]), name="omega-x condition-eq16")
            if t_m <= self.time_step - 1:
                model.addConstr(quicksum(
                    omg[wkey] for wkey in self.w_keys if (wkey[0] == a and wkey[1] == i and t <= wkey[2] <= t_m - 1)) >= x[xkey] * c[i, t],
                                                                name="omega-x condition-eq17")
                model.addConstr(quicksum(
                    omg[wkey] for wkey in self.w_keys if (wkey[0] == a and wkey[1] == i and t <= wkey[2] <= t_m - 1)) <=
                                x[xkey] * c[i, t] + M * (1 - x[xkey]), name="omega=x condition-eq18")
                model.addConstr(quicksum(
                    omg[wkey] for wkey in self.w_keys if (wkey[0] == a and wkey[1] == i and t_m <= wkey[2] <= t_e - 1))<=
                                M * (1 - x[a, i, t]), name="omega-x condition-eq19")

        # model.setParam("IntFeasTol", 1e-9)
        self.model = model
        print(f'model build complete! at time {time.time() - t1}')
        return model


    # this function is permanently abundoned, saving here for notes.
    def build_model_smallexample(self, param, veh_od, alpha=0.5):  # this is temperoarily set as small
        # self.K, self.Q, self.V, self.C = self.get_costCTM(self.CTM_numberMatrix, self.CTM_numberOutMatrix, self.ctm_fd,
        #                                                   self.CTM_signalMatrix)

        # 20250401: update link, veh, max time step without hardcoding.
        alpha1, alpha2, M, = param[0], param[1], param[2]
        self.veh = len(veh_od)

        self.CTM_connection, self.time_step, self.C = self.get_small_net_param()

        self.link = self.CTM_connection.shape[0]


        # Example Data
        # max_t =   # max time step
        I = [i for i in range(self.CTM_connection.shape[0])]  # Links (nodes)
        A = [i for i in range(self.veh)]  # Vehicles
        T = [i for i in range(self.time_step)]  # Time horizon

        self.para_set = (A, I, T)

        # Parameters as dictionaries
        c = {(i, t): self.C[i, t]for i in I for t in T}
        self.c = c

        Pi = {(i, j): self.CTM_connection[i, j] for i in I for j in I}

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
            alpha1 * quicksum(quicksum(c[i, t] * x[a, i, t] for i in I for t in T if (i, t) in c) for a in A) -
            alpha2 * quicksum(y[i, t] for i in I for t in T) / (self.link * self.time_step),
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
                                # print('preset z[{},{},{},{},{}] with cost c[{},{}]={}, Pi = {}'.format(a, i, j, t, s, i,
                                #                                                                        t, c[i, t],
                                #                                                                        Pi[i, j]))

        print("condition 0 is completed")
        # 1. FLow conservation (linearlized)
        # axillary variable z
        for a in A:
            for i in I:
                for t in T:
                    # if (i != veh_odtmp[a]['to'] and i != 11):
                    if i != veh_od[a]['to']:
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
            model.addConstr(x[a, veh_od[a]['from'], veh_od[a]['time']] == 1)
            model.addConstr(quicksum(x[a, veh_od[a]['to'], t] for t in T) == 1)
            for j in I:
                for s in T:
                    # if (j == 0 or j == 6):
                    #     model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(z[a, j, k, s, r] for k in I for r in T) == -1, name='3*netflow_conservation1')
                    # if j == veh_odtmp[a]['to']:
                    #     model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(z[a, j, k, s, r] for k in I for r in T) == 1, name='3*netflow_conservation2')
                    if (j != veh_od[a]['from'] and j != veh_od[a]['to']):
                        #     print('j is {}'.format(j))
                        # else:
                        model.addConstr(quicksum(z[a, i, j, t, s] for i in I for t in T) - quicksum(
                            z[a, j, k, s, r] for k in I for r in T) == 0, name='3*netflow_conservation3')

        # 4. Time-dependent link constraints
        for a in A:
            for t in T:
                model.addConstr(quicksum(x[a, i, t] for i in I) <= 1)

        # 5. Time-travel bound for vehicle
        model.addConstrs(quicksum(x[a, i, t] for t in T) <= 1 for a in A for i in I)

        # 6. omega-y condition (phase 2)
        model.addConstrs(y[i, t] <= quicksum(omg[a, i, t] for a in A) for i in I for t in T)
        model.addConstrs(M * y[i, t] >= quicksum(omg[a, i, t] for a in A) for i in I for t in T)

        # 7. omega-x condition (phase 2)
        print('at here')

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

        # model.addConstrs()

        self.model = model
        print('model build complete!')
        return model

    # this function is to tmp test for the small ctm network
    def solve_model(self, CtmDowngrade=False):
        self.model.reset(0)
        self.model.setParam('MIPGap', 0.0005)  # set mini gap

        print('begin to optimize')
        self.model.optimize()
        if self.model.status == GRB.INFEASIBLE:
            print('release an infeasible model')
            self.model.computeIIS()
            self.model.write("infeasibile.ilp")


        # Check if a feasible solution was found
        if self.model.status == GRB.OPTIMAL:
            # self.model.write("model.lp")
            # self.model.write("model.sol")
            print(f"Optimal objective value: {self.model.objVal}")

            A, I, T = self.para_set

            # Retrieve dimensions
            num_vehicles = len(A)
            num_cells = len(I)
            num_timesteps = len(T)

            # # Initialize an empty array for the solution
            solution_x = np.zeros((num_vehicles, num_cells, num_timesteps), dtype=int)
            solution_y = np.zeros((num_cells, num_timesteps), dtype=int)
            solution_omg = np.zeros((num_vehicles, num_cells, num_timesteps), dtype=int)

            # solution_array = np.zeros((self.veh, self.link, self.time_step), dtype=int)

            # Populate the array with solution values
            if CtmDowngrade:
                cell_idx = self.CTM_cellIdx_downgrade
            else:
                cell_idx = self.CTM_cellIdx_ori

            # save x variable
            if self.Load_mode == "toynet":
                for a in range(solution_x.shape[0]):
                    for t in range(solution_x.shape[2]):
                        for i in range(solution_x.shape[1]):
                            var_x = self.model.getVarByName(f"x[{a},{i},{t}]")
                            if int(round(var_x.x)) == 1:
                                print('#########x({},{},{})={}, at link {} at time {}, cost is {} '.format(a, i, t, var_x.x,
                                                                                                       i+1, t,
                                                                                                       self.c[(i, t)]))
                            solution_x[a, i, t] = int(round(var_x.x))
            else:
                for xkey in self.x_keys:
                    a, i, t = xkey[0], xkey[1], xkey[2]
                    var_x = self.model.getVarByName(f"x[{a},{i},{t}]")
                    if int(round(var_x.x)) == 1:
                        # a, i, t = xkey[0], xkey[1], xkey[2]
                        # print('#########x({},{},{})={}, at cell {} at time {}, cost is {} '.format(a, i, t, var_x.x,
                        #                                                                              cell_idx[i], t,
                        #                                                                              self.c[(i, t)]))
                        solution_x[a, i, t] = int(round(var_x.x))

                # save y variable
                for ykey in self.y_keys:
                    i, t = ykey[0], ykey[1]
                    var_y = self.model.getVarByName(f"y[{i},{t}]")
                    solution_y[i, t] = int(var_y.x)

                # save omg variable
                # for a in range(solution_omg.shape[0]):
                #     for i in range(solution_omg.shape[1]):
                #         for t in range(solution_omg.shape[2]):
                #             var_omg = self.model.getVarByName(f"omega[{a},{i},{t}]")
                #             solution_omg[a, i, t] = int(var_omg.x)

                for wkey in self.w_keys:
                    a, i, t  = wkey[0], wkey[1], wkey[2]
                    var_omg = self.model.getVarByName(f"omega[{a},{i},{t}]")
                    solution_omg[a, i, t] = int(var_omg.x)

            return solution_x, solution_y, solution_omg, self.model.objVal
        else:
            print("No optimal solution found.")
            return None, None, None, None

    def getRouteFromX(self, x):
        # cell_idx = self.cellidx
        # input x: [veh, link, time]
        veh_rt = {}
        for a in range(x.shape[0]):
            rt = []
            for t in range(x.shape[2]):
                for i in range(x.shape[1]):
                    if (x[a, i, t] == 1 and i != self.veh_od[a]['to']):
                        rt.append(self.cellidx[i])
            veh_rt[a] = rt
        return veh_rt

    # def getRouteSumo(self, x, cav_info):
    #     if x is not None:
    #         # veh_rt = {}
    #         for a in range(x.shape[0]):
    #             rt = {}
    #             for t in range(x.shape[2]):
    #                 for i in range(x.shape[1]):
    #                     if (x[a, i, t] == 1 and i != self.veh_od[a]['to']):
    #                         edge = self.cellidx[i].split('.')
    #                         rt[edge[1]] = None
    #                         # rt.add(edge[1])
    #             cav_info[a]['update_route'] = list(rt.keys())
    #         return cav_info
    #     else:
    #         print('no x is generated for edge')
    #         return  # should return a flag for


if __name__ == '__main__':
    CTM_Path = {'number': '../../result/ctmResult/CTMnumber_3600_1800dis.csv',
                'sigflag': '../../result/ctmResult/CTMsigflag_3600_1800dis.csv',
                'connectionMatrix': '../../result/ctmResult/CTMconnection.txt',
                'cellIdx': '../../result/ctmResult/CTMcell_index.json'
                }

    # print(SolverFactory("gurobi_direct").available())
    FD_param = {
        'v_f': 57.6,  # km/hr
        'k_jam': 133,  # veh/km
        'q_max': 1890,  # veh/hour
        'w': 19.85,
        'length': 0.08,  # km
        'delta_t': 5 / 3600,  # hr
    }
    param = (1, 1e6, 999999)

    time1 = time.time()
    # this is a case study for the subnet of CTM network
    caseConfig = CaseStudyConfig()
    cav_od = caseConfig.toy_net_od

    Ropt = RouteOptimGurobi(FD_param, veh_od=cav_od, max_time=150, current_time=0, CTM_resultPath=CTM_Path, Load_mode='toynet')
    Ropt.build_model_smallexample(param=param, veh_od=cav_od)
    # Ropt.build_model(param=param, veh_num=len(cav_od), small_net=True)
    x, y, omg, objective_value = Ropt.solve_model(CtmDowngrade=False)
    print('time cost is {}'.format(time.time() - time1))

    with open(CTM_Path['cellIdx'], 'r') as file:
        CTM_cellIdx = [line.strip() for line in file]

    rout_list = Ropt.getRouteFromX(x)

    np.save('../../result/middle_result0520/x_tmp.npy', x)
    np.save('../../result/middle_result0520/y_tmp.npy', y)
    np.save('../../result/middle_result0520/omg_tmp.npy', omg)

    print(x[1, :, :])
