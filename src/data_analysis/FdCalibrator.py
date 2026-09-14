# this script is for ctm calibration


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import seaborn as sns
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from scipy.spatial import ConvexHull
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import xml.etree.ElementTree as ET
from scipy.optimize import curve_fit

from scipy.interpolate import UnivariateSpline

class FdCalibrator:
    def __init__(self):
        return

    def load_edge_data1(self, xml_file):
        # load file is a xml path
        root = ET.parse(xml_file).getroot()
        for i in root.iter('interval'):
            start_t, end_t = float(i.get('begin')), float(i.get('end'))
        time_hr = (end_t - start_t)/3600  # convert to hour unite
        self.edge_data = []
        for edge in root.iter('edge'):
            edge_id = edge.get('id')
            sampled_steps = float(edge.get('sampledSeconds'))  # accumulative summation of count over time resolution
            speed = float(edge.get('speed'))*3.6  #km/hr
            density = float(edge.get('density'))  # veh/km
            veh_count = 0.5 * (float(edge.get('departed')) + float(edge.get('entered')) + float(edge.get('arrived')) + float(edge.get('left')))
            flow = veh_count/time_hr  # veh/hour
            # flow = speed * density
            self.edge_data.append({'edge_id': edge_id, 'speed': speed, 'flow': flow, 'density': density})
        self.edge_data_df = pd.DataFrame(self.edge_data)
        # return pd.DataFrame(self.edge_data)

    def load_edge_data(self, xml_file):
        def get_float_safe(edge, key):
            """Safely get float value from edge attributes. Default to 0.0 if missing."""
            try:
                return float(edge.get(key, 0))
            except:
                return 0.0

        try:
            # parser = ET.XMLParser(recover=True)
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Remove namespaces for robust tag matching
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]

            edge_data = []
            for interval in root.iter('interval'):
                start_t = float(interval.get('begin', 0))
                end_t = float(interval.get('end', 0))
                time_hr = (end_t - start_t) / 3600 if end_t > start_t else 1e-6  # prevent division by zero

                for edge in interval.iter('edge'):
                    edge_id = edge.get('id', 'unknown')
                    speed = get_float_safe(edge, 'speed') * 3.6  # m/s → km/h
                    density = get_float_safe(edge, 'density')  # veh/km
                    departed = get_float_safe(edge, 'departed')
                    entered = get_float_safe(edge, 'entered')
                    arrived = get_float_safe(edge, 'arrived')
                    left = get_float_safe(edge, 'left')

                    veh_count = 0.5 * (departed + entered + arrived + left)
                    flow = veh_count / time_hr
                    # flow = get_float_safe(edge, 'sampledSeconds') / time_hr

                    edge_data.append({
                        'edge_id': edge_id,
                        'start_time': start_t,
                        'end_time': end_t,
                        'speed': speed,
                        'flow': flow,
                        'density': density
                    })

            self.edge_data_df = pd.DataFrame(edge_data)

        except Exception as e:
            print(f"[Error] Failed to parse XML {xml_file}: {e}")
            self.edge_data_df = pd.DataFrame()

    def plot_and_fit_piecewise(self, x_col, y_col):
        # if self.edge_data_df:
        #     df = self.edge_data_df
        # else:
        #     raise Exception('No edge data, please run edge data load ')

        df = self.edge_data_df
        # Extract the data for the specified columns
        x = df[x_col].values
        y = df[y_col].values

        # Fit the piecewise function to the data with constrained second slope
        params = constrained_piecewise_fit(x, y)
        # Extract parameters
        x_break, k1, k2 = params
        # x_break, k1, k2 = 70, 11.43, -4.08

        # Create the scatter plot
        plt.figure(figsize=(10, 6))
        plt.scatter(x, y, label='Data')

        # Plot the piecewise linear fit
        x_range = np.linspace(min(x), max(x) + 20, 500)
        #     y_range = np.linspace(0, 2300)
        plt.plot(x_range, piecewise_linear(x_range, *params), color='red', label='Piecewise Linear Fit')

        # Display the equations for the piecewise function in the top right corner
        plt.text(0.95, 0.95, f'y = {k1:.2f} * x  (x < {x_break:.2f})', transform=plt.gca().transAxes,
                 verticalalignment='top', horizontalalignment='right')
        plt.text(0.95, 0.90, f'y = {k1 * x_break:.2f} + {k2:.2f} * (x - {x_break:.2f})  (x >= {x_break:.2f})',
                 transform=plt.gca().transAxes, verticalalignment='top', horizontalalignment='right')

        # Customize plot
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title(f'Scatter Plot and Piecewise Linear Fit\n({x_col} vs {y_col})')
        plt.legend(loc='upper left')
        plt.grid(True)
        plt.ylim(0, 1000)
        plt.show()

def piecewise_linear(x, x_break, k1, k2):
    return np.piecewise(x, [x < x_break, x >= x_break],
                        [lambda x: k1 * x,
                         lambda x: k2 * (x - x_break) + k1 * x_break])

def constrained_piecewise_fit(x, y):
    # Constrain the second slope (k2) to be negative
    p0 = [np.median(x), 1, -1]  # initial guess

    # Fit the model
    bounds = ([min(x), 0, -np.inf], [max(x), np.inf, 0])  # constrain k2 < 0
    params, _ = curve_fit(piecewise_linear, x, y, p0=p0, bounds=bounds)

    # return params

    k_1 = 57.6  # 57.6
    x_0 = 870/k_1
    return x_0, k_1, (x_0 * k_1) / (x_0 - 266)

if __name__ == '__main__':
    FdCal = FdCalibrator()
    FdCal.load_edge_data('../../result/tmpnet/CTMTEST/sumolog_tmp/edge_data.xml')
    FdCal.plot_and_fit_piecewise('density', 'flow')