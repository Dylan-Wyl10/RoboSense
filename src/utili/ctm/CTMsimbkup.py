"""
Date: Nov 1, 2023,
Author: Yilin Wang
Note: this script is about the CTM model in SUMO network
Features:
 - construct the network from network xml file directly linked with SUMO
 - uniformly
"""
from src.utili.ctm.ctmcomponent import Cell, Corridor
import pandas as pd
import re
import threading

class CTMSim(threading.Thread):
    lock = threading.Lock()

    def __init__(self, tick_length, tick_to_update_demand, event):
        super().__init__()
        self.current_step = 0
        self.total_steps = 0
        self.tick = tick_length
        self.tick_to_update_demand = tick_to_update_demand
        self.pause_event = threading.Event()
        self.mainthread_event = event
        # self.condition = condition
        self.condition = threading.Condition(self.lock)

    # Initialize the simulation
    def init_sim(self):
        print("Initializing CTMSim...")
        """
        inital simulation.
        1. read SUMO net file, restore network structure
        2. 
        """
        print("Initialize Complete!")

    def run(self):
        self.init_sim()
        linkdf = pd.read_csv('link.csv', dtype={'link_id': object, 'to_node_id': object, 'from_node_id': object})
        corridor_dict = {}
        time_to_update_demand = 50  # update deamnd per 50 time ticks, if time_tick = 6, 50 time ticks means 300 seconds, that is, 5 minutes.
        for corridor in self.link:
            cells = self.link[corridor]
            corr_demand = self.demand.where(self.demand['corridor_id'] == corridor).dropna(subset=['corridor_id'])
            corr_link = linkdf.where(linkdf['corridor_id'] == corridor).dropna(subset=['corridor_id'])
            corr_supply = self.supply.where(self.supply['corridor_id'] == corridor).dropna(subset=['corridor_id'])
            start_string = self.supply.iloc[0]['time_period']
            end_string = self.supply.iloc[-1]['time_period']
            start_hour = int(re.split(r'_', start_string)[0]) / 100
            start_min = int(re.split(r'_', start_string)[0]) % 100
            end_hour = int(re.split(r'_', end_string)[0]) / 100
            end_min = int(re.split(r'_', end_string)[0]) % 100
            total_time = int(end_hour) + end_min / 60 - int(start_hour) - start_min / 60  # hour
            total_tick = int(total_time * 3600 / self.tick)
            supply_period = (int(re.split(r'_', start_string)[1]) % 100 - int(
                re.split(r'_', start_string)[0]) % 100) * 60 / self.tick
            if supply_period == 0:
                supply_period = 60 * 60 / self.tick

            dfindex = []
            main_roads = []
            ramps = []
            self.total_steps = total_tick

            for elem in cells:
                dfindex.append(elem.getCompleteAddress())

                if elem.ramp_flag == 0:
                    main_roads.append(elem)
                else:
                    ramps.append(elem)

            ramp_df = corr_link.where(corr_link['ramp_flag'] == 1).dropna(subset=['corridor_id'])
            if len(ramp_df):
                ramp_demand_df = corr_demand.where(corr_demand['ramp_flag'] == 1).dropna(subset=['corridor_id'])
            else:
                ramp_demand_df = pd.DataFrame()

            df = pd.DataFrame(index=dfindex)
            flowdf = pd.DataFrame(index=dfindex)

            corridor_dict[corridor] = Corridor(corridor, cells, corr_demand, corr_link, corr_supply,
                                               total_tick, supply_period, main_roads, ramps, df,
                                               flowdf, ramp_df, ramp_demand_df, dfindex)

        # with self.condition:
        #     self.condition.notify()
        #     while self.current_step < self.total_steps:
        #         self.condition.wait()  # Wait for the signal to proceed
        #         if self.current_step < self.total_steps:
        #             self.simulation_main(corridor_dict)
        #             self.current_step += 1
        #         else:
        #             break

        self.mainthread_event.set()
        while self.current_step < self.total_steps:
            self.pause_event.wait()  # Wait for the signal to proceed
            if self.current_step < self.total_steps:
                self.simulation_main(corridor_dict, linkdf)
                self.current_step += 1
            else:
                break

    def simulationStep(self):
        self.pause_event.set()

    def resume_simulation(self):
        with self.condition:
            self.condition.notify()  # Notify the waiting thread to proceed

    def stop_sim(self):
        with self.condition:
            self.current_step = self.total_steps  # Skip remaining steps
            self.condition.notify()  # Notify the waiting thread to exit

    def simulation_main(self, corridor_list, linkdf):
        t = self.current_step
        for corr_key in corridor_list:
            density = []
            flow = []
            corridor = corridor_list[corr_key]
            if not t:
                for elem in corridor.cells:
                    if elem.ramp_flag == 1:
                        continue
                    link_order = linkdf.where(linkdf['link_id'] == elem.linkid).dropna(subset=['corridor_id']).iloc[0][
                        'corridor_link_order']
                    elem.k = corridor.supply.where(corridor.supply['corridor_id'] == corridor.name).dropna(
                        subset=['corridor_id']).where(corridor.supply['corridor_link_order'] == link_order).dropna(
                        subset=['corridor_id']).iloc[0]['density']

            if not t % self.tick_to_update_demand and len(corridor.demand):
                if int(t / self.tick_to_update_demand) >= len(corridor.demand):
                    Cell.getFirstCell(corridor.cells[0].linkid).arr_rate = corridor.demand.iloc[-1]['demand']
                else:
                    Cell.getFirstCell(corridor.cells[0].linkid).arr_rate = \
                    corridor.demand.iloc[int(t / self.tick_to_update_demand)]['demand']

            corridor.ramp_df = corridor.Link.where(corridor.Link['ramp_flag'] == 1).dropna(subset=['corridor_id'])
            if len(corridor.ramp_df):
                corridor.ramp_demand_df = corridor.demand.where(corridor.demand['ramp_flag'] == 1).dropna(
                    subset=['corridor_id'])
                if len(corridor.ramp_demand_df) == 0:
                    Cell.getFirstCell(corridor.ramp_df.iloc[0]['link_id']).arr_rate = 600
                else:
                    if not t % self.tick_to_update_demand and len(corridor.demand):
                        if int(t / self.tick_to_update_demand) >= len(corridor.demand):
                            Cell.getFirstCell(corridor.ramp_df.iloc[0]['link_id']).arr_rate = \
                            corridor.ramp_demand_df.iloc[-1]['demand']
                        else:
                            Cell.getFirstCell(corridor.ramp_df.iloc[0]['link_id']).arr_rate = \
                            corridor.ramp_demand_df.iloc[int(t / self.tick_to_update_demand)]['demand']

            for elem in corridor.ramps:
                elem.updateDensity()

            for elem in corridor.main_roads:
                if not t % corridor.supply_period:
                    if elem.ramp_flag == 0:
                        link_order = \
                        linkdf.where(linkdf['link_id'] == elem.linkid).dropna(subset=['corridor_id']).iloc[0][
                            'corridor_link_order']
                        new_qmax = corridor.supply.where(corridor.supply['corridor_link_order'] == link_order).dropna(
                            subset=['corridor_id']).iloc[int(t / corridor.supply_period)]['volume']
                        # the volume changes only affects the last cell of the link.
                        Cell.getLastCell(elem.linkid).qmax = new_qmax

                elem.updateDensity()
            for elem in corridor.cells:
                density.append(elem.k)
                flow.append(elem.outflow)
                elem.updated = False

            corridor.df = pd.concat(
                [corridor.df, pd.DataFrame(data=density, index=corridor.dfindex, columns=["t%i" % t])], axis=1)
            corridor.flowdf = pd.concat(
                [corridor.flowdf, pd.DataFrame(data=flow, index=corridor.dfindex, columns=["t%i" % t])], axis=1)

        self.mainthread_event.set()
