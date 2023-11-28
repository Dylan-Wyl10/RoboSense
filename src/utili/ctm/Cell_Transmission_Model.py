"""
Date: Nov 1, 2023,
Author: Yilin Wang
Note: this script is about the CTM model in SUMO network
Features:
 - construct the network from network xml file directly linked with SUMO
 - uniformly
"""
import numpy as np
from component import Cell, Link, Node, Corridor
from CTMsim import CTMSim
import pandas as pd
import re
from datetime import datetime
import threading



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
    def __init__(self, net_ipt, tick_interval):
        super().__init__()
        self.current_step = 0
        



if __name__ == '__main__':
    start = datetime.now()
    sim = initializeCTM()
    for t in range(sim.total_steps):
        sim.simulationStep()
    sim.join()

    for key in Corridor.idcase:
        Corridor.idcase[key].printResults()
    end = datetime.now()
    print("Elapsed Time:", end - start)

