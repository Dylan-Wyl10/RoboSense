
class CaseStudyConfig(object):
    def __init__(self, mode="toynet"):

        if mode =='small-ctm':
            self.loadCellidx()
        if mode =='toynet':
            self.toy_net_od = {0: {'from': 24, 'to': 25, 'time': 0},
                           1: {'from': 24, 'to': 25, 'time': 0},
                           2: {'from': 24, 'to': 25, 'time': 0},
                           3: {'from': 24, 'to': 25, 'time': 0}}
        if mode == 'small-ctm':
            self.small_net_od = {0: {'from': self.cellidx.index('A1.E101.C0'),
                                'to': self.cellidx.index('A1.-E120.C0'),
                                'time': 0},
                             1: {'from': self.cellidx.index('A1.E101.C0'),
                                'to': self.cellidx.index('A1.-E120.C0'),
                                'time': 0},
                             2: {'from': self.cellidx.index('A1.E101.C0'),
                                 'to': self.cellidx.index('A1.-E120.C0'),
                                 'time': 1},
                             3: {'from': self.cellidx.index('A1.E101.C0'),
                                 'to': self.cellidx.index('A1.-E120.C0'),
                                 'time': 3},
                             4: {'from': self.cellidx.index('A1.E101.C0'),
                                 'to': self.cellidx.index('A1.-E120.C0'),
                                 'time': 5},
                             5: {'from': self.cellidx.index('A1.E101.C0'),
                                 'to': self.cellidx.index('A1.-E120.C0'),
                                 'time': 9},
                             6: {'from': self.cellidx.index('A1.E101.C0'),
                                 'to': self.cellidx.index('A1.-E120.C0'),
                                 'time': 60},
                             7: {'from': self.cellidx.index('A1.E101.C0'),
                                 'to': self.cellidx.index('A1.-E120.C0'),
                                 'time': 60}}

            self.full_net_2200_od ={0: {'from': 286, 'to': 28, 'time': 0, 'route_length': 20},
                                1: {'from': 302, 'to': 18, 'time': 0, 'route_length': 35},
                                2: {'from': 295, 'to': 18, 'time': 0, 'route_length': 30},
                                3: {'from': 295, 'to': 23, 'time': 0, 'route_length': 30},
                                4: {'from': 519, 'to': 85, 'time': 0, 'route_length': 20},
                                5: {'from': 647, 'to': 90, 'time': 0, 'route_length': 20},
                                6: {'from': 598, 'to': 80, 'time': 0, 'route_length': 30},
                                7: {'from': 646, 'to': 90, 'time': 0, 'route_length': 20},
                                8: {'from': 335, 'to': 105, 'time': 0, 'route_length': 45},
                                9: {'from': 731, 'to': 70, 'time': 0, 'route_length':35},
                                10: {'from': 433, 'to': 110, 'time': 0, 'route_length': 40},
                                11: {'from': 148, 'to': 110, 'time': 0, 'route_length': 20},
                                12: {'from': 134, 'to': 110, 'time': 0, 'route_length': 10},
                                13: {'from': 512, 'to': 80, 'time': 0, 'route_length': 30},
                                14: {'from': 122, 'to': 115, 'time': 0, 'route_length': 25},
                                15: {'from': 211, 'to': 53, 'time': 0, 'route_length':35},
                                16: {'from': 154, 'to': 127, 'time': 0, 'route_length':35},
                                17: {'from': 218, 'to': 43, 'time': 0, 'route_length':45},
                                18: {'from': 724, 'to': 75, 'time': 0, 'route_length':10},
                                19: {'from': 223, 'to': 48, 'time': 0, 'route_length':25},
                                20: {'from': 741, 'to': 38, 'time': 0, 'route_length':15},
                                21: {'from': 287, 'to': 38, 'time': 0, 'route_length':10}}

    def loadCellidx(self, mode='full'):
        if mode == 'small':
            self.cellidx = ['A1.E101.C0', 'A1.E101.C4', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7',
           'A1.E102.C0', 'A1.E102.C4', 'A1.E102.C5', 'A1.E102.C6', 'A1.E102.C7',
           'A1.E103.C0', 'A1.E103.C4', 'A1.E103.C5', 'A1.E103.C6', 'A1.E103.C7',
           'A1.E120.C0', 'A1.E120.C4', 'A1.E120.C5', 'A1.E120.C6', 'A1.E120.C7',
           'A1.-E101.C0', 'A1.-E101.C4', 'A1.-E101.C3', 'A1.-E101.C2', 'A1.-E101.C1',
           'A1.-E102.C0', 'A1.-E102.C4', 'A1.-E102.C3', 'A1.-E102.C2', 'A1.-E102.C1',
           'A1.-E103.C0', 'A1.-E103.C4', 'A1.-E103.C3', 'A1.-E103.C2', 'A1.-E103.C1',
           'A1.-E120.C0', 'A1.-E120.C4', 'A1.-E120.C3', 'A1.-E120.C2', 'A1.-E120.C1',
           'A0.E1.C1', 'A0.E1.C2', 'A0.E1.C3', 'A0.E1.C4', 'A0.E1.C5', 'A0.E1.C6', 'A0.E1.C7',
           'A0.-E1.C1', 'A0.-E1.C2', 'A0.-E1.C3', 'A0.-E1.C4', 'A0.-E1.C5', 'A0.-E1.C6', 'A0.-E1.C7',
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
        else:

            with open('../../result/ctmResult/CTMcell_index.json', 'r') as file:
                self.cellidx = [line.strip() for line in file]
