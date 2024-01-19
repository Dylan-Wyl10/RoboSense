"""
Date: Nov 1, 2023,
Author: Yilin Wang
Note: this script restores the components that build up CTM model
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
import threading
import queue
import socket


class Cell(object):
    idcase = {}

    def __init__(self, cellid, linkid, zoneid, time_interval=6, k=0, qmax=1800, kjam=220, vf=60, w=12,
                 length=0.1, updated=False, arr_rate=0, dis_rate=2160, ramp_flag=0):
        self.kjam = kjam
        self.cellid = cellid  # local address
        self.linkid = linkid  # link layer address
        self.zoneid = zoneid  # zone layer address
        self.vf = vf  # Time interval = length / vf
        self.w = w
        self.cfrom = []
        self.cto = []
        self.type = 'norm'  # defaultly set cell type = norm
        # identify the type of the cell
        if len(self.cto) == 2 and len(self.cfrom) == 1:
            self.type = 'div'  # diverge
        elif len(self.cto) == 1 and len(self.cfrom) == 2:
            self.type = 'merg'  # merge
        self.k = k  # density at time interval t
        self.oldk = k  # density at time interval t-1
        self.qmax = qmax
        self.length = length
        self.updated = updated
        self.arr_rate = arr_rate  # arrival rate
        self.dis_rate = dis_rate  # departure rate
        self.time_sec = time_interval
        self.time_hour = time_interval / 3600
        self.inflow = 0
        self.outflow = 0
        self.pk = 0.75
        self.pck = 0.25
        self.ramp_flag = ramp_flag
        if Cell.idcase.get(self.getCompleteAddress()) == None:
            Cell.idcase.setdefault(self.getCompleteAddress(), self)
        else:
            raise Exception("This id has been used by other cell")

    def addConnection(self, sink):
        if len(sink.cfrom) == 2 or len(self.cto) == 2:
            raise Exception("Cannot add more connection to cell %s and cell %s" % (
                self.getCompleteAddress(), sink.getCompleteAddress()))

        if (len(self.cto) and len(sink.cfrom)) and (len(sink.cto) == 2 or len(self.cfrom) == 2):
            raise Exception("Invaild cell connection! A cell cannot connect to merge and diverge cell simultaneously")

        self.cto.append(sink)  # An instance of cell class is stored, in order to use cto and cfrom as pointer.
        sink.cfrom.append(self)

    def deleteConnection(self, sink):
        if sink not in self.cto:
            raise Exception(
                "Cell %s is not connected with cell %s" % (self.getCompleteAddress(), sink.getCompleteAddress()))

        self.cto.remove(sink)
        sink.cfrom.remove(self)

    def getCell(cid):
        return Cell.idcase[cid]

    def getFirstCell(linkid):
        newDict = {}
        for key in Cell.idcase:
            if Cell.idcase[key].linkid == linkid:
                newDict[key] = Cell.idcase[key]

        return newDict[min(newDict.keys())]

    def getAllCellsInSameLink(linkid):
        result_list = []
        for key in Cell.idcase:
            if Cell.idcase[key].linkid == linkid:
                result_list.append(Cell.idcase[key])

        return result_list

    def getLastCell(linkid):
        newDict = {}
        for key in Cell.idcase:
            if Cell.idcase[key].linkid == linkid:
                cell_num = int(re.split(r'\D', Cell.idcase[key].cellid)[1])
                newDict[cell_num] = Cell.idcase[key]

        return newDict[max(newDict.keys())]

    def deleteCell(cid):
        poped = Cell.idcase.pop(cid)
        for elem in poped.cto:
            poped.deleteConnection(elem)
        del poped

    def getCompleteAddress(self):
        return "%s.%s.%s" % (self.zoneid, self.linkid, self.cellid)

    def updateDensity(self):  # This method can only be used by normal cell instance.
        if not self.updated:
            self.oldk = self.k
        if self.type == 'merg':  # Merge at here, we need to update density among this cell and two other upstream cells.
            pk = self.pk  # probability from upstream normal cell
            pck = 1 - self.pk  # probability from upstream merge cell
            for elem in self.cfrom:
                rek = np.min([self.qmax, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                if elem.ramp_flag == 0:
                    sbk = np.min([elem.qmax, elem.vf * elem.oldk]) * elem.time_hour / elem.length
                    prov = elem

                else:
                    sck = np.min([elem.qmax, elem.vf * elem.oldk]) * elem.time_hour / elem.length
                    if not elem.updated:
                        elem.oldk = elem.k

                    merge = elem

            try:  # In order to cope with situation that provious cell is the first cell (cfrom is empty)
                # prov.inflow = np.min([prov.qmax, prov.vf * prov.cfrom[0].oldk, prov.w * (prov.kjam - prov.oldk)]) * prov.time_hour / prov.length
                prov.inflow = prov.cfrom[0].outflow
                prov.outflow = np.min(
                    [np.median([pk * rek, sbk, rek - sck]), prov.vf * prov.oldk * prov.time_hour / prov.length])

            except:
                prov.inflow = np.min(
                    [prov.qmax, prov.arr_rate, prov.w * (prov.kjam - prov.oldk)]) * prov.time_hour / prov.length
                prov.outflow = np.min(
                    [np.median([pk * rek, sbk, rek - sck]), prov.vf * prov.oldk * prov.time_hour / prov.length])

            if len(merge.cfrom):
                # merge.inflow = np.min([merge.qmax, merge.vf * merge.cfrom[0].oldk, merge.w * (merge.kjam - merge.oldk)]) * merge.time_hour / merge.length
                merge.inflow = merge.cfrom[0].outflow
                merge.outflow = np.min(
                    [np.median([pck * rek, sck, rek - sbk]), merge.vf * merge.oldk * merge.time_hour / merge.length])
            else:
                merge.inflow = np.min(
                    [merge.qmax, merge.arr_rate, merge.w * (merge.kjam - merge.oldk)]) * merge.time_hour / merge.length
                merge.outflow = np.min(
                    [np.median([pck * rek, sck, rek - sbk]), merge.vf * merge.oldk * merge.time_hour / merge.length])

            if len(self.cto):
                self.inflow = np.min([self.qmax * self.time_hour / self.length, sbk + sck,
                                      self.w * (self.kjam - self.oldk) * self.time_hour / self.length])
                self.outflow = np.min([self.cto[0].qmax, self.oldk * self.vf, self.cto[0].w * (
                        self.cto[0].kjam - self.cto[0].oldk)]) * self.time_hour / self.length
            else:
                self.inflow = np.min([self.qmax * self.time_hour / self.length, sbk + sck,
                                      self.w * (self.kjam - self.oldk) * self.time_hour / self.length])
                self.outflow = np.min([self.qmax, self.oldk * self.vf, self.dis_rate]) * self.time_hour / self.length

            prov.k = np.max([prov.oldk + np.max([0, prov.inflow]) - np.max([0, prov.outflow]), 0])
            merge.k = np.max([merge.oldk + np.max([0, merge.inflow]) - np.max([0, merge.outflow]), 0])
            self.k = np.max([self.oldk + np.max([0, self.inflow]) - np.max([0, self.outflow]), 0])

            prov.updated, self.updated, merge.updated = True, True, True

        elif self.type == 'div':  # Diverge at here
            ptnc = self.pk  # Propotion towards to next normal cell
            ptdc = 1 - self.pk  # Propotion towards to diverge cell
            for elem in self.cto:
                if elem.ramp_flag == 0:
                    elem.oldk = elem.k
                    next_c = elem

                else:
                    if not elem.updated:
                        elem.oldk = elem.k

                    diverge = elem

            rck = np.min([next_c.qmax, next_c.w * (
                    next_c.kjam - next_c.oldk)]) * next_c.time_hour / next_c.length  # Receive ability of next normal cell
            rek = np.min([diverge.qmax, diverge.w * (diverge.kjam - diverge.oldk)]) * diverge.time_hour / diverge.length
            sbk = np.min([self.qmax, self.vf * self.oldk]) * self.time_hour / self.length

            try:  # In order to cope with situation that next cell is the last cell (cto is empty)
                next_c.inflow = ptnc * np.min([sbk, rek / ptdc, rck / ptnc])
                next_c.outflow = np.min([next_c.cto[0].qmax, next_c.vf * next_c.oldk, next_c.cto[0].w * (
                        next_c.cto[0].kjam - next_c.cto[0].oldk)]) * next_c.time_hour / next_c.length
            except:
                next_c.inflow = ptnc * np.min([sbk, rek / ptdc, rck / ptnc])
                next_c.outflow = np.min(
                    [next_c.qmax, next_c.vf * next_c.oldk, next_c.dis_rate]) * next_c.time_hour / next_c.length

            if len(diverge.cto):
                diverge.inflow = ptdc * np.min([sbk, rek / ptdc, rck / ptnc])
                diverge.outflow = np.min([diverge.cto[0].qmax, diverge.oldk * diverge.vf, diverge.cto[0].w * (
                        diverge.cto[0].kjam - diverge.cto[0].oldk)]) * diverge.time_hour / diverge.length
            else:
                diverge.inflow = ptdc * np.min([sbk, rek / ptdc, rck / ptnc])
                diverge.outflow = np.min(
                    [diverge.qmax, diverge.oldk * diverge.vf, diverge.dis_rate]) * diverge.time_hour / diverge.length

            if len(self.cfrom):
                self.inflow = np.min([self.qmax, self.cfrom[0].oldk * self.vf,
                                      self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                self.outflow = np.min([sbk, rek / ptdc, rck / ptnc])
            else:
                self.inflow = np.min(
                    [self.qmax, self.arr_rate, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                self.outflow = np.min([sbk, rek / ptdc, rck / ptnc])

            next_c.k = np.max([next_c.oldk + np.max([0, next_c.inflow]) - np.max([0, next_c.outflow]), 0])
            diverge.k = np.max([diverge.oldk + np.max([0, diverge.inflow]) - np.max([0, diverge.outflow]), 0])
            self.k = np.max([self.oldk + np.max([0, self.inflow]) - np.max([0, self.outflow]), 0])
            next_c.updated, self.updated, diverge.updated = True, True, True

        elif self.type == 'norm':  # Normal cell
            if self.updated:
                return

            if len(self.cfrom) == 0:
                self.inflow = np.min(
                    [self.qmax, self.arr_rate, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                self.outflow = np.min([self.cto[0].qmax, self.oldk * self.vf, self.cto[0].w * (
                        self.cto[0].kjam - self.cto[0].oldk)]) * self.time_hour / self.length

            elif len(self.cto) == 0:
                self.inflow = self.cfrom[0].outflow
                # self.inflow = np.min([self.qmax, self.cfrom[0].oldk * self.vf, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                self.outflow = np.min([self.qmax, self.oldk * self.vf, self.dis_rate]) * self.time_hour / self.length

            else:
                self.inflow = self.cfrom[0].outflow
                # self.inflow = np.min([self.qmax, self.cfrom[0].oldk * self.vf, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                self.outflow = np.min([self.qmax, self.oldk * self.vf, self.cto[0].w * (
                        self.cto[0].kjam - self.cto[0].oldk)]) * self.time_hour / self.length

            self.k = np.max([self.oldk + np.max([0, self.inflow]) - np.max([0, self.outflow]), 0])
            self.updated = True


class Node(object):
    idcase = {}

    def __init__(self, nid, x, y):
        self.id = nid
        self.x = x
        self.y = y
        self.link_in = []
        self.link_out = []
        Node.idcase[nid] = self

    def getNodeFromID(nid):
        return Node.idcase[nid]


class Link(object):
    idcase = {}

    def __init__(self, lid, fnode, tnode, speed, num_of_lanes, length):
        self.id = str(lid)
        self.source = str(fnode)
        self.sink = str(tnode)
        self.length = length
        self.speed = speed
        self.num_of_lanes = num_of_lanes
        Link.idcase[str(lid)] = self

    def getLinkFromID(lid):
        return Link.idcase[lid]


class Corridor(object):
    idcase = {}

    def __init__(self, corr_name, cells, corr_demand, corr_link, corr_supply,
                 total_tick, supply_period, main_roads, ramps, df, flowdf,
                 ramp_df, ramp_demand_df, dfindex):
        self.name = corr_name
        self.cells = cells
        self.demand = corr_demand
        self.link = corr_link
        self.supply = corr_supply
        self.total_tick = total_tick
        self.supply_period = supply_period
        self.main_roads = main_roads
        self.ramps = ramps
        self.df = df
        self.flowdf = flowdf
        self.ramp_df = ramp_df
        self.ramp_demand_df = ramp_demand_df
        self.current_step = 0
        self.dfindex = dfindex
        Corridor.idcase[corr_name] = self

    def printResults(self):
        self.df.to_csv("Density_profile_{0}.csv".format(self.name))
        self.flowdf.to_csv("Flow_profile_{0}.csv".format(self.name))

    def update(self):
        pass



def getCrossProduct(va, vb):
    return va[0] * vb[1] - va[1] * vb[0]


def getEuclideanDis(x1, x2, y1, y2):
    return np.sqrt(np.power(x2 - x1, 2) + np.power(y2 - y1, 2))


def changeLinkJamDensity(linkid, kjam):
    cell_list = Cell.getAllCellsInSameLink()
    for cell in cell_list:
        cell.kjam = kjam


def changeSpecificCellJamDensity(cid, kjam):
    Cell.getCell(cid).kjam = kjam


def changeLinkQmax(linkid, qmax):
    cell_list = Cell.getAllCellsInSameLink()
    for cell in cell_list:
        cell.qmax = qmax


def changeSpecificCellQmax(cid, qmax):
    Cell.getCell(cid).qmax = qmax


def changeLinkDemand(linkid, demand):
    Cell.getFirstCell(linkid).arr_rate = demand


def quicklyCreateCells(number, linkid, vf=60, kjam=220):
    cells = []
    for i in range(number):
        cells.append(Cell('C' + str(i), linkid, 'A0', vf=vf, kjam=kjam, arr_rate=0, dis_rate=1800))

    for index in range(len(cells)):
        if index < len(cells) - 1:
            cells[index].addConnection(cells[index + 1])

    return cells


def notifyThreads(condition):
    with condition:
        condition.notify()


def timeDependentDemand(order, t, miu, gamma, t0, t2=0, t3=0):
    if order == 1:
        return gamma * t + t0 + miu
    elif order == 2:
        return gamma * (t - t0) * (t2 - t) + miu
    elif order == 3:
        tbar = t0 + (3 * (t3 - t0) ** 2 - 4 * (t2 - t0) * (t3 - t0)) / (4 * (t3 - t0) - 6 * (t2 - t0))
        return miu + gamma * (t - t0) * (t - t2) * (t - tbar)
    else:
        raise Exception("Invaild input parameter! Order of time dependtent demand formula must be 1, 2 or 3")

def initializeCTM():
    event = threading.Event()
    sim = CTMSim(6, 50, event)
    sim.start()
    event.wait()
    return sim


def simulation_run_step(sim):
    sim.simulationStep()
    sim.mainthread_event.clear()
    sim.mainthread_event.wait()


class CTM():
    def __init__(self, network, tick_interval):
        super().__init__()
        self.current_step = 0
        self.tick = tick_interval  # time interval for CTM calculation
        self.net = network  # current network input is based on SUMO, the input format is net.xml
        self.link_ls = []

    def init(self):
        print(f'Initializing CTM for network{self.net.net_config}...')
        self.link_ls = [i[0] + i[1] for i in np.array(self.net.G.edges)] # get link index for ctm model
        """next is create unified cells for each corridos. some assumptions holds:
        
        """


        print('testing')


#
#
# if __name__ == '__main__':
#     start = datetime.now()
#     sim = initializeCTM()
#     for t in range(sim.total_steps):
#         sim.simulationStep()
#     sim.join()
#
#     for key in Corridor.idcase:
#         Corridor.idcase[key].printResults()
#     end = datetime.now()
#     print("Elapsed Time:", end - start)

