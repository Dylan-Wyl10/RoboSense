"""
Date: Nov 1, 2023,
Author: Yilin Wang
Note: this script restores the components that build up CTM model
"""
import time

import pandas as pd
import numpy as np
import re
from datetime import datetime
import threading
import queue
import socket
import copy


class Cell(object):
    idcase = {}

    def __init__(self, cellid, linkid, zoneid, time_interval=6, k=0, qmax=1800, kjam=220, vf=16, w=3.2,
                 length=0.1, updated=False, arr_rate=0, dis_rate=2160):
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
        self.connection_counts = []
        self.pk = 0.5  # probability from first cells, default 0.5
        # self.psk = 0.5  # probability from side stream cells, default 0.5
        # self.ramp_flag = ramp_flag  # define if the current cell is main road. [0:main, 1:side]
        self.observe_flag = False  # observation flag, default false, when obsever at time , update density.
        self.sig_flag = 1 # signal flag, usually for diverge cell. default value=1 (green)
        if Cell.idcase.get(self.getCompleteAddress()) == None:
            Cell.idcase.setdefault(self.getCompleteAddress(), self)
        else:
            raise Exception("This id has been used by other cell")

    def addConnection(self, sink):  # self ahead, sink back
        if len(sink.cfrom) == 2 or len(self.cto) == 2:
            raise Exception("Cannot add more connection to cell %s and cell %s" % (
                self.getCompleteAddress(), sink.getCompleteAddress()))

        if (len(self.cto) and len(sink.cfrom)) and (len(sink.cto) == 2 or len(self.cfrom) == 2):
            raise Exception("Invaild cell connection! A cell cannot connect to merge and diverge cell simultaneously")

        self.cto.append(sink)  # An instance of cell class is stored, in order to use cto and cfrom as pointer.
        sink.cfrom.append(self)

    # this function is only used for merge and diverge function.
    # 20240306: we have some hardcoding
    # isTo is a flag to determine whether we should add the counts on: -1:to cell, 0:both, 1:from cell
    def addConnectionCounts(self, sink, count):
        if len(sink.cfrom) == 2 or len(self.cto) == 2:
            raise Exception("Cannot add more connection to cell %s and cell %s" % (
                self.getCompleteAddress(), sink.getCompleteAddress()))

        if (len(self.cto) and len(sink.cfrom)) and (len(sink.cto) == 2 or len(self.cfrom) == 2):
            raise Exception("Invaild cell connection! A cell cannot connect to merge and diverge cell simultaneously")

        self.cto.append(sink)  # An instance of cell class is stored, in order to use cto and cfrom as pointer.
        sink.cfrom.append(self)

        self.connection_counts.append(count)
        sink.connection_counts.append(count)

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

    def updateRatio(self):
        # defaultly, pk shows the first ratio.
        if self.connection_counts:
            self.pk = self.connection_counts[0] / sum(self.connection_counts)

    def updateDensity(self):  # This method can only be used by normal cell instance.
        if not self.updated:
            self.oldk = self.k
        # self.qmax = self.sig_flag * self.qmax
        if len(self.cfrom) == 2:  # Merge at here, we need to update density among this cell and two other upstream cells.
            pk = self.pk  # probability from upstream normal cell
            pck = 1 - self.pk  # probability from upstream merge cell

            rek = np.min([self.qmax, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
            prov = self.cfrom[0]  # first cell note as 1

            if len(prov.cto) == 2:  # if prov cell is diverge cell.
                sbk = np.min([prov.qmax, prov.vf * prov.oldk]) * prov.pk * prov.time_hour / prov.length
            else:
                sbk = np.min([prov.qmax, prov.vf * prov.oldk]) * prov.time_hour / prov.length


            if not prov.updated:
                prov.oldk = prov.k

            merge = self.cfrom[1]
            if len(merge.cto) == 2:
                sck = np.min([merge.qmax, merge.vf * merge.oldk]) * (1 - merge.pk) * merge.time_hour / merge.length
            else:
                sck = np.min([merge.qmax, merge.vf * merge.oldk]) * merge.time_hour / merge.length
            if not merge.updated:
                merge.oldk = merge.k


            #########################################################################################
            # try:  # In order to cope with situation that provious cell is the first cell (cfrom is empty)
            #     # prov.inflow = np.min([prov.qmax, prov.vf * prov.cfrom[0].oldk, prov.w * (prov.kjam - prov.oldk)]) * prov.time_hour / prov.length
            #     prov.inflow = prov.cfrom[0].outflow
            #     prov.outflow = np.min(
            #         [np.median([pk * rek, sbk, rek - sck]), prov.vf * prov.oldk * prov.time_second / prov.length])
            #
            # except:
            #     prov.inflow = np.min(
            #         [prov.qmax, prov.arr_rate, prov.w * (prov.kjam - prov.oldk)]) * prov.time_second / prov.length
            #     prov.outflow = np.min(
            #         [np.median([pk * rek, sbk, rek - sck]), prov.vf * prov.oldk * prov.time_second / prov.length])
            #
            # if len(merge.cfrom):
            #     # merge.inflow = np.min([merge.qmax, merge.vf * merge.cfrom[0].oldk, merge.w * (merge.kjam - merge.oldk)]) * merge.time_hour / merge.length
            #     merge.inflow = merge.cfrom[0].outflow
            #     merge.outflow = np.min(
            #         [np.median([pck * rek, sck, rek - sbk]), merge.vf * merge.oldk * merge.time_second / merge.length])
            # else:
            #     merge.inflow = np.min(
            #         [merge.qmax, merge.arr_rate, merge.w * (merge.kjam - merge.oldk)]) * merge.time_second / merge.length
            #     merge.outflow = np.min(
            #         [np.median([pck * rek, sck, rek - sbk]), merge.vf * merge.oldk * merge.time_second / merge.length])

            #########################################################################################

            if sbk + sck >= rek:
                yk = np.median([pk * rek, sbk, rek - sck])
                yck = np.median([pck * rek, sck, rek - sbk])

            else:
                yk, yck = sbk, sck
                # print("yk", yk, yck, pk)
                # print('id', self.getCompleteAddress())


            if not len(prov.cfrom): # start from first cell
                prov.inflow = np.min([prov.qmax, prov.arr_rate, prov.w * (prov.kjam - prov.oldk)]) * prov.time_hour / prov.length
            else:
                # print(sum(fc.outflow for fc in prov.cfrom))
                prov.inflow = sum(fc.outflow for fc in prov.cfrom)
            if len(prov.cto) == 2:
                if pk == 0:
                    prov.outflow = np.min([0, prov.vf * prov.oldk * prov.time_hour / prov.length])
                else:
                    prov.outflow = np.min([yk / pk, prov.vf * prov.oldk * prov.time_hour / prov.length])
            else:
                prov.outflow = np.min([yk, prov.vf * prov.oldk * prov.time_hour / prov.length])

            if not len(merge.cfrom): # start from first cell
                merge.inflow = np.min([merge.qmax, merge.arr_rate, merge.w * (merge.kjam - merge.oldk)]) * merge.time_hour / merge.length
            else:
                merge.inflow = sum(fc.outflow for fc in merge.cfrom)

            if len(merge.cto) == 2:
                if pck == 0:
                    merge.outflow = np.min([0, merge.vf * merge.oldk * merge.time_hour / merge.length])
                else:
                    merge.outflow = np.min([yck / pck, merge.vf * merge.oldk * merge.time_hour / merge.length])
            else:
                merge.outflow = np.min([yck, merge.vf * merge.oldk * merge.time_hour / merge.length])

            ##################################################################################

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

        elif len(self.cto) == 2:  # Diverge at here
            # self.pk = self.connection_counts[0] / sum(self.connection_counts)

            ptnc = self.pk  # Propotion towards to next normal cell
            ptdc = 1 - self.pk  # Propotion towards to diverge cell

            next_c = self.cto[0]
            next_c.oldk = next_c.k

            diverge = self.cto[1]
            if not diverge.updated:
                diverge.oldk = diverge.k


            # for elem in self.cto:
            #     if elem.ramp_flag == 0:
            #         elem.oldk = elem.k
            #         next_c = elem
            #
            #     else:
            #         if not elem.updated:
            #             elem.oldk = elem.k
            #         diverge = elem

            rck = np.min([next_c.qmax, next_c.w * (
                    next_c.kjam - next_c.oldk)]) * next_c.time_hour / next_c.length  # Receive ability of next normal cell
            rek = np.min([diverge.qmax, diverge.w * (diverge.kjam - diverge.oldk)]) * diverge.time_hour / diverge.length
            sbk = np.min([self.qmax, self.vf * self.oldk]) * self.time_hour / self.length

            try:  # In order to cope with situation that next cell is the last cell (cto is empty)
                # if ptnc == 0:
                #     print('yes')
                if ptdc == 0:
                    next_c.inflow = ptnc * np.min([sbk, rck])
                elif ptnc == 0:
                    next_c.inflow = 0
                else:
                    next_c.inflow = ptnc * np.min([sbk, rek / ptdc, rck / ptnc])
                next_c.outflow = np.min([next_c.cto[0].qmax, next_c.vf * next_c.oldk, next_c.cto[0].w * (
                        next_c.cto[0].kjam - next_c.cto[0].oldk)]) * next_c.time_hour / next_c.length
            except:
                if ptdc == 0:
                    next_c.inflow = ptnc*np.min([sbk, rck])
                elif ptnc == 0:
                    next_c.inflow = 0
                else:
                    next_c.inflow = ptnc * np.min([sbk, rek / ptdc, rck / ptnc])
                next_c.outflow = np.min(
                    [next_c.qmax, next_c.vf * next_c.oldk, next_c.dis_rate]) * next_c.time_hour / next_c.length

            if len(diverge.cto):
                if ptdc == 0:
                    diverge.inflow = 0
                elif ptnc == 0:
                    diverge.inflow = np.min([sbk, rek])
                else:
                    diverge.inflow = ptdc * np.min([sbk, rek / ptdc, rck / ptnc])
                diverge.outflow = np.min([diverge.cto[0].qmax, diverge.oldk * diverge.vf, diverge.cto[0].w * (
                        diverge.cto[0].kjam - diverge.cto[0].oldk)]) * diverge.time_hour / diverge.length
            else:
                if ptdc == 0:
                    diverge.inflow = 0
                elif ptnc == 0:
                    diverge.inflow = np.min([sbk, rek])
                else:
                    diverge.inflow = ptdc * np.min([sbk, rek / ptdc, rck / ptnc])
                # diverge.inflow = ptdc * np.min([sbk, rek / ptdc, rck / ptnc])
                diverge.outflow = np.min(
                    [diverge.qmax, diverge.oldk * diverge.vf, diverge.dis_rate]) * diverge.time_hour / diverge.length

            if len(self.cfrom):
                self.inflow = np.min([self.qmax, self.cfrom[0].oldk * self.vf,
                                      self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                # self.outflow = np.min([sbk, rek / ptdc, rck / ptnc])
            else:
                self.inflow = np.min(
                    [self.qmax, self.arr_rate, self.w * (self.kjam - self.oldk)]) * self.time_hour / self.length
                # self.outflow = np.min([sbk, rek / ptdc, rck / ptnc])
            if ptdc == 0:
                self.outflow = np.min([sbk, rck])*self.sig_flag
            elif ptnc == 0:
                self.outflow = np.min([sbk, rek])*self.sig_flag
            else:
                self.outflow = np.min([sbk, rek/ptdc, rck/ptnc])*self.sig_flag

            next_c.k = np.max([next_c.oldk + np.max([0, next_c.inflow]) - np.max([0, next_c.outflow]), 0])
            diverge.k = np.max([diverge.oldk + np.max([0, diverge.inflow]) - np.max([0, diverge.outflow]), 0])
            self.k = np.max([self.oldk + np.max([0, self.inflow]) - np.max([0, self.outflow]), 0])
            next_c.updated, self.updated, diverge.updated = True, True, True

        else:  # Normal cell
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

    def switchConnection(self):
        if len(self.cto) == 2 and len(self.cfrom) == 2:
            raise Exception("Invaild cell connection! A cell cannot connect to merge and diverge cell simultaneously")
        if len(self.cto) == 2:
            self.cto[0], self.cto[1] = self.cto[1], self.cto[0]
            self.connection_counts[0], self.connection_counts[1] = self.connection_counts[1], self.connection_counts[0]
        if len(self.cfrom) == 2:
            self.cfrom[0], self.cfrom[1] = self.cfrom[1], self.cfrom[0]
            self.connection_counts[0], self.connection_counts[1] = self.connection_counts[1], self.connection_counts[0]


#
# class Node(object):
#     idcase = {}
#
#     def __init__(self, nid, x, y):
#         self.id = nid
#         self.x = x
#         self.y = y
#         self.link_in = []
#         self.link_out = []
#         Node.idcase[nid] = self
#
#     def getNodeFromID(nid):
#         return Node.idcase[nid]

#
# class Link(object):
#     idcase = {}
#
#     def __init__(self, lid, fnode, tnode, speed, num_of_lanes, length):
#         self.id = str(lid)
#         self.source = str(fnode)
#         self.sink = str(tnode)
#         self.length = length
#         self.speed = speed
#         self.num_of_lanes = num_of_lanes
#         Link.idcase[str(lid)] = self
#
#     def getLinkFromID(lid):
#         return Link.idcase[lid]

#
# class Corridor(object):
#     idcase = {}
#
#     def __init__(self, corr_name, cells, corr_demand, corr_link, corr_supply,
#                  total_tick, supply_period, main_roads, ramps, df, flowdf,
#                  ramp_df, ramp_demand_df, dfindex):
#         self.name = corr_name
#         self.cells = cells
#         self.demand = corr_demand
#         self.link = corr_link
#         self.supply = corr_supply
#         self.total_tick = total_tick
#         self.supply_period = supply_period
#         self.main_roads = main_roads
#         self.ramps = ramps
#         self.df = df
#         self.flowdf = flowdf
#         self.ramp_df = ramp_df
#         self.ramp_demand_df = ramp_demand_df
#         self.current_step = 0
#         self.dfindex = dfindex
#         Corridor.idcase[corr_name] = self
#
#     def printResults(self):
#         self.df.to_csv("Density_profile_{0}.csv".format(self.name))
#         self.flowdf.to_csv("Flow_profile_{0}.csv".format(self.name))
#
#     def update(self):
#         pass


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


# creat cells for a given link
def linkCreateCells(linkid, link_type='normal'):
    """
    number: total number of cells in one link
    Note that for 202402version, the tepology for the cells in link is fixed
    """
    cells = []
    if link_type == 'normal':  # normal line 400m, 7 cells
        cells.append(Cell('C' + str(1), linkid, 'A0', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                          dis_rate=1100))
        cells.append(Cell('C' + str(2), linkid, 'A0', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                          dis_rate=1100))
        cells.append(Cell('C' + str(3), linkid, 'A0', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                          dis_rate=2200))
        cells.append(Cell('C' + str(4), linkid, 'A0', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                          dis_rate=2200))
        cells.append(Cell('C' + str(5), linkid, 'A0', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                          dis_rate=2200))
        cells.append(Cell('C' + str(6), linkid, 'A0', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                          dis_rate=1100))
        cells.append(Cell('C' + str(7), linkid, 'A0', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                          dis_rate=1100))

        # add connection
        cells[0].addConnection(cells[2])  # 1-3
        cells[1].addConnection(cells[2])  # 2-3
        cells[2].addConnection(cells[3])  # 3-4
        cells[3].addConnection(cells[4])  # 4-5
        cells[4].addConnection(cells[5])  # 5-6
        cells[4].addConnection(cells[6])  # 5-7

    elif link_type == 'entry':  # entry line 240m, 4 cells

        # sink cell, id C0
        cells.append(
            Cell('C' + str(0), linkid, 'A1', time_interval=5, vf=50, kjam=99999, qmax=2200, length=0.08, arr_rate=0,
                 dis_rate=2200))
        cells.append(Cell('C' + str(4), linkid, 'A1', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                          dis_rate=2200))
        cells.append(Cell('C' + str(5), linkid, 'A1', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                          dis_rate=2200))
        cells.append(Cell('C' + str(6), linkid, 'A1', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                          dis_rate=1100))
        cells.append(Cell('C' + str(7), linkid, 'A1', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                          dis_rate=1100))

        cells[0].addConnection(cells[1])  # dummy-4
        cells[1].addConnection(cells[2])  # 4-5
        cells[2].addConnection(cells[3])  # 5-6
        cells[2].addConnection(cells[4])  # 5-7

    elif link_type == 'exit':  # entry line 240m, 4 cells
        cells.append(
            Cell('C' + str(1), linkid, 'A1', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                 dis_rate=1100))
        cells.append(
            Cell('C' + str(2), linkid, 'A1', time_interval=5, vf=50, kjam=133, qmax=1100, length=0.08, arr_rate=0,
                 dis_rate=1100))
        cells.append(
            Cell('C' + str(3), linkid, 'A1', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                 dis_rate=2200))
        cells.append(
            Cell('C' + str(4), linkid, 'A1', time_interval=5, vf=50, kjam=266, qmax=2200, length=0.08, arr_rate=0,
                 dis_rate=2200))
        cells.append(
            Cell('C' + str(0), linkid, 'A1', time_interval=5, vf=50, kjam=266, qmax=99999, length=0.08, arr_rate=0,
                 dis_rate=99999))

        cells[0].addConnection(cells[2])  # 1-3
        cells[1].addConnection(cells[2])  # 2-3
        cells[2].addConnection(cells[3])  # 3-4
        cells[3].addConnection(cells[4])  # 4-dummy

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
        self.link_ls = {}

    def init(self):
        print(f'Initializing CTM for network{self.net.net_config}...')
        # self.link_ls = [i[0] + i[1] for i in np.array(self.net.G.edges)] # get link index for ctm model
        link_info = {'link_id': [],
                     'from_link_id': [],
                     'to_link_id': [],
                     'length': [],
                     }
        for e in self.net.sumonet.getEdges():  # enumerate all edges in the sumo net file
            # 1. get link id and length
            link_info['link_id'].append(e.getID())
            link_info['length'].append(e.getLength())
            # 2. get from link id
            from_node_id = e.getFromNode().getID()
            if from_node_id in self.net.node_list.keys():
                inter = self.net.node_list[from_node_id]  # get intersection class by given node ID
                tmp = []
                for e_f in inter.link_idx['in']:
                    if re.findall(r'[0-9]+|[a-z]+', e_f.getID()) != re.findall(r'[0-9]+|[a-z]+', e.getID()):
                        tmp.append(e_f.getID())
                link_info['from_link_id'].append(tmp)
            else:
                link_info['from_link_id'].append('0')  # when link is the start link
            # 3. get to link id
            to_node_id = e.getToNode().getID()
            if to_node_id in self.net.node_list.keys():
                inter = self.net.node_list[to_node_id]  # get intersection class by given node ID
                tmp = []
                for e_t in inter.link_idx['in']:
                    if re.findall(r'[0-9]+|[a-z]+', e_t.getID())[0] != re.findall(r'[0-9]+|[a-z]+', e.getID())[0]:
                        tmp.append(e_t.getID())
                link_info['to_link_id'].append(tmp)
            else:
                link_info['to_link_id'].append('0')  # when link is the start link

        linkdf = pd.DataFrame(link_info)
        """next is create unified cells for each corridos"""

        # linkdf1 = pd.read_csv('link.csv', dtype={'link_id': object, 'to_link_id': object, 'from_link_id': object})
        # demand = pd.read_csv('demand.csv', index_col=0)
        # supply = pd.read_csv('supply.csv', dtype={'to_node_id': object, 'from_node_id': object})

        # corridors = linkdf['corridor_id'].drop_duplicates()
        # link = {}  # 20240222 update: save for future development on link cell list
        for i in range(len(linkdf)):
            # if the links is the entry link, creat two big cell for each lane
            if linkdf.iloc[i]['from_link_id'] == '0' and linkdf.iloc[i]['to_link_id'] != '0':
                print('creating cells for entry link {}'.format(linkdf.iloc[i]['link_id']))
                linkCreateCells(linkdf.iloc[i]['link_id'], link_type='entry')
            # normal link, need connections from both side with 8 cells for one link
            elif linkdf.iloc[i]['from_link_id'] != '0' and linkdf.iloc[i]['to_link_id'] != '0':
                print('creating cells for normal link {}'.format(linkdf.iloc[i]['link_id']))
                linkCreateCells(linkdf.iloc[i]['link_id'], link_type='normal')
            elif linkdf.iloc[i]['from_link_id'] != '0' and linkdf.iloc[i]['to_link_id'] == '0':
                print('creating cells for exit link {}'.format(linkdf.iloc[i]['link_id']))
                linkCreateCells(linkdf.iloc[i]['link_id'], link_type='exit')
            # tmpp = linkdf.iloc[i]['link_id']
            print('cells has been created')
        # aa = Cell.idcase

        print('start to get turn ratio')

        # add conncetions and add turn ratio on each intersection
        for node_key in self.net.node_list.keys():
            node = self.net.node_list[node_key]
            link_in, link_out = node.link_idx.values()

            # get node tepology, by default it should be (up, right, down, left), the output is a serise
            link_tplgy = node.link_node.loc[node.link_node['node_id'] == node_key].values.tolist()[0][1:]

            turn_counts = {'from_node': [],
                           'left': [],
                           'thr': [],
                           'right': []}

            for l_idx in range(len(link_tplgy)):
                # get edge id in
                e_id = next((edge.getID() for edge in link_in if
                             int(re.findall(r'[0-9]+|[a-z]+', edge.getID())[0]) == link_tplgy[l_idx]), None)
                # get cell id in
                c6_id = '{}.{}.{}'.format('A1' if link_tplgy[l_idx] > 100 else 'A0', e_id, 'C6')
                c7_id = '{}.{}.{}'.format('A1' if link_tplgy[l_idx] > 100 else 'A0', e_id, 'C7')

                # get other connected edge id, external out

                # idx = l_idx + 1, left turn
                lidx_tmp = (l_idx + 1) % 4
                ex_id_left = next((edge.getID() for edge in link_out if
                                   int(re.findall(r'[0-9]+|[a-z]+', edge.getID())[0]) == link_tplgy[lidx_tmp]), None)
                c2_ex1_id = '{}.{}.{}'.format('A1' if link_tplgy[lidx_tmp] > 100 else 'A0', ex_id_left, 'C2')

                # idx = l_idx + 2, through
                lidx_tmp = (l_idx + 2) % 4
                ex_id_thr = next((edge.getID() for edge in link_out if
                                  int(re.findall(r'[0-9]+|[a-z]+', edge.getID())[0]) == link_tplgy[(l_idx + 2) % 4]),
                                 None)
                c1_ex2_id = '{}.{}.{}'.format('A1' if link_tplgy[lidx_tmp] > 100 else 'A0', ex_id_thr, 'C1')
                c2_ex2_id = '{}.{}.{}'.format('A1' if link_tplgy[lidx_tmp] > 100 else 'A0', ex_id_thr, 'C2')

                # idx = l_idx + 3, right turn
                lidx_tmp = (l_idx + 3) % 4
                ex_id_right = next((edge.getID() for edge in link_out if
                                    int(re.findall(r'[0-9]+|[a-z]+', edge.getID())[0]) == link_tplgy[(l_idx + 3) % 4]),
                                   None)
                c1_ex3_id = '{}.{}.{}'.format('A1' if link_tplgy[lidx_tmp] > 100 else 'A0', ex_id_right, 'C1')

                """
                Next, update turning ratio, for each link phase, there are three merging cells and three diverging cell
                the turning ratio is calculated by the number of vehicles in turning table
                """

                turn_count_tmpdf = self.net.turn_rate.where(self.net.turn_rate['from'] == e_id).dropna(subset=['from'])

                turn_counts['from_node'].append(e_id)
                turn_counts['left'].append(0)
                turn_counts['right'].append(0)
                turn_counts['thr'].append(0)

                for i in range(len(turn_count_tmpdf)):
                    if ex_id_left == turn_count_tmpdf.iloc[i]['to']:
                        turn_counts['left'][-1] = turn_count_tmpdf.iloc[i]['count']
                    elif ex_id_thr == turn_count_tmpdf.iloc[i]['to']:
                        turn_counts['thr'][-1] = turn_count_tmpdf.iloc[i]['count']
                    elif ex_id_right == turn_count_tmpdf.iloc[i]['to']:
                        turn_counts['right'][-1] = turn_count_tmpdf.iloc[i]['count']

                # add connections in the intersection, on both side
                # right lane through
                Cell.getCell(c6_id).addConnectionCounts(Cell.getCell(c1_ex2_id), 0.5 * turn_counts['thr'][-1])
                # right lane right
                Cell.getCell(c6_id).addConnectionCounts(Cell.getCell(c1_ex3_id), turn_counts['right'][-1])
                # left lane left
                Cell.getCell(c7_id).addConnectionCounts(Cell.getCell(c2_ex1_id), turn_counts['left'][-1])
                # left lane through
                Cell.getCell(c7_id).addConnectionCounts(Cell.getCell(c2_ex2_id), 0.5 * turn_counts['thr'][-1])

            # print('start to shift')
            del c1_ex2_id, c1_ex3_id, c2_ex1_id, c2_ex2_id, ex_id_thr, ex_id_right, ex_id_left

            turn_countsdf = pd.DataFrame(turn_counts)
            # then we need to:
            # 1. shift cell7 for link in, and cell1 for link out
            # 2. update the in link cells counts
            for l in link_in:
                # e_id = l.getID()
                c7_id = '{}.{}.{}'.format('A1' if int(re.findall(r'[0-9]+|[a-z]+', l.getID())[0]) > 100 else 'A0',
                                          l.getID(), 'C7')
                Cell.getCell(c7_id).switchConnection()

                c5_id = '{}.{}.{}'.format('A1' if int(re.findall(r'[0-9]+|[a-z]+', l.getID())[0]) > 100 else 'A0',
                                          l.getID(), 'C5')
                Cell.getCell(c5_id).connection_counts.append(sum(Cell.getCell(c5_id).cto[0].connection_counts))
                Cell.getCell(c5_id).connection_counts.append(sum(Cell.getCell(c5_id).cto[1].connection_counts))
                del c7_id, c5_id

            for l in link_out:
                # e_id = l.getID()
                c1_id = '{}.{}.{}'.format('A1' if int(re.findall(r'[0-9]+|[a-z]+', l.getID())[0]) > 100 else 'A0',
                                          l.getID(), 'C1')
                Cell.getCell(c1_id).switchConnection()
                c3_id = '{}.{}.{}'.format('A1' if int(re.findall(r'[0-9]+|[a-z]+', l.getID())[0]) > 100 else 'A0',
                                          l.getID(), 'C3')
                # c3 = Cell.getCell(c3_id)
                Cell.getCell(c3_id).connection_counts.append(sum(Cell.getCell(c3_id).cfrom[0].connection_counts))
                Cell.getCell(c3_id).connection_counts.append(sum(Cell.getCell(c3_id).cfrom[1].connection_counts))
                del c1_id, c3_id

        self.cells_dic = Cell.idcase
        for c in self.cells_dic.values():
            c.updateRatio()
        print('network established')
        # initial demand flow.
        self.demand = self.net.demand
        self.links = linkdf

        for i in range(len(self.demand)):
            Cell.getFirstCell(self.demand.iloc[i]['link_id']).arr_rate = self.demand.iloc[i]['demand']

        print("Initialize Complete!")

    def runCTM(self, time_current, time_range):
        """
        run CTM cell status from current status and stop at target time
        """
        density = {}
        flow = {}
        number = {}
        steps = time_range//self.tick
        time_start = time.time()
        # cells_old = copy.deepcopy(self.cells_dic)
        for t in range(steps):
            # update demand
            for i in range(len(self.demand)):
                Cell.getFirstCell(self.demand.iloc[i]['link_id']).arr_rate = self.demand.iloc[i]['demand']

            # update signal timing for current step t
            # print('start update signal')
            for n in self.net.node_list.values():
                n.getEdgeSignalPhase(t*5)  # YW: the time current and input time here is absolute time.
            # update cell density
            for cell in self.cells_dic.values():
                cell.updateDensity()
            # collect cell result
            for cell in self.cells_dic.values():
                cell_id = cell.getCompleteAddress()
                if cell_id not in density.keys():
                    density[cell_id] = [cell.k]
                else:
                    density[cell_id].append(cell.k)
                if cell_id not in flow.keys():
                    flow[cell_id] = [cell.outflow]
                else:
                    flow[cell_id].append(cell.outflow)
                cell.updated = False

            if t == 1:
                cells_old = copy.deepcopy(self.cells_dic)  # save the next step cells for update
        time_end = time.time()
        # numbers = density*0.08
        print('time spend for {} steps: {}'.format(steps, time_end-time_start))
        self.density_df = pd.DataFrame(density).T
        self.flow_df = pd.DataFrame(flow).T
        self.number_df = self.density_df * 0.08
        print('yes')
        return cells_old

    def updateSignalTime(self, time_index):
        """
        this function is to update related cell signal flag according to signal timing plan
        """


    def getVehDelay(self, route_info):
        pass

    def getCell(self, cell_id):
        return self.cells_dic[cell_id]

    # def getCellfromEdgePosition(self, edge_position):
    #     """
    #     edge_position: [edge_lane_idx, longitude]
    #     """
    #     edge_lane_idx, longitude = edge_position
    #     edge_idx, lane_idx = re.search(r'([-\w]+)_(\d+)', edge_lane_idx).group(1), re.search(
    #         r'([-\w]+)_(\d+)', edge_lane_idx).group(2)
    #     length = self.net.sumonet.getEdge(edge_idx).getLength()
    #     if length < 400 and edge_idx[0]:
    #         # entry lane

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
