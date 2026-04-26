"""
Date: June 13, 2023
Author: Yilin Wang
Note: script file for useful links.
List:
1. gen_LF_table(): generate a blank table to restore the travel information for each link.
2. update_LF_table(): update link-flow table
"""
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import json
from datetime import datetime
from matplotlib import cm
from matplotlib.colors import Normalize
import xml.etree.ElementTree as ET
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import mean_squared_error, mean_absolute_error
from collections import Counter
from typing import Iterable, Dict, Any, List, Tuple, Optional
import pickle
import os
from scipy import stats
from scipy.optimize import minimize_scalar, least_squares


def gen_LF_table(link_num):
    '''
    Note: this function generate a blank link flow table with list space
    :param link_num: total number of links
    :return:
    '''
    table = {}
    for idx in range(link_num):
        table['E' + str(idx + 1)] = []
        table['-E' + str(idx + 1)] = []
    return table


# Function to plot cells as non-contiguous rectangles with the same size and color them based on the number of vehicles, including the time step
def CTM_visulization(time_id_df, cell_coordinates, save_path):  # the inputs are file_directory
    """
    :param time_id_matrix:(data-frame) dataframe with time-space number for the cells.
    :param cell_coordinates:network tepology, read as adictionary.
    """

    cell_coordinates_df = pd.read_csv(cell_coordinates)
    cell_coordinates = cell_coordinates_df.set_index('cell_id').T.to_dict('list')

    x_values = [coord[0] for coord in cell_coordinates.values()]
    y_values = [coord[1] for coord in cell_coordinates.values()]

    x_min, x_max = min(x_values) - 0.5, max(x_values) + 0.5
    y_min, y_max = min(y_values) - 0.5, max(y_values) + 0.5

    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)

    # Fixed rectangle size
    rect_size = 0.45
    rectangles = []
    annotations = []

    for cell_id, (x, y) in cell_coordinates.items():
        rect = plt.Rectangle((x - rect_size / 2, y - rect_size / 2),
                             rect_size, rect_size, fill=True, edgecolor='black')
        rectangles.append(rect)
        ax.add_patch(rect)
        annotation = ax.text(x, y, cell_id.split('.')[-1][1:], ha='center', va='center', fontsize=6, color='black')
        annotations.append(annotation)

    time_text = ax.text(0.5, 1.05, '', transform=ax.transAxes, ha='center')

    def get_color(val):
        if val == 0:
            return 'white'
        elif val == 1:
            return '#90ee90'  # light green
        elif val == 2:
            return 'yellow'
        else:
            return 'red'

    def update(frame):
        for rect, cell_id in zip(rectangles, cell_coordinates.keys()):
            if cell_id not in time_id_df.index:
                continue
            vehicle_number = time_id_df.loc[cell_id].iloc[frame]
            rect.set_facecolor(get_color(vehicle_number))
        time_text.set_text(f'Time Step: {frame + 1}')
        return rectangles + [time_text]

    ani = animation.FuncAnimation(fig, update, frames=range(len(time_id_df.columns)), interval=500, blit=True)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')
    ax.axis('off')

    if save_path is None:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f'../result/ctmResult/logs/ctm_test1/urban_network_traffic_with_timestep1_{current_time}.mp4'

    writer = animation.writers['ffmpeg'](fps=2, metadata=dict(artist='CTM'), bitrate=1800)
    ani.save(save_path, writer=writer)
    plt.close(fig)
    # print('urban_network_traffic_with_timestep_new1.mp4')

    # return '/mnt/data/urban_network_traffic_with_timestep.mp4'


def CTM_static_visulization(time_id_df, cell_coordinates_path, title_str, save_path=None, colorbar_range=(0, 600)):
    """
    Draw static plot of CTM: sum over time for each cell.
    Cell with 0 → white; Cell with >0 → color map from green to red.
    Colorbar range is fixed by colorbar_range, values > max are shown as red.

    :param time_id_df: DataFrame, indexed by cell_id, columns as time steps.
    :param cell_coordinates_path: str, path to Cells.csv (with cell_id, x, y).
    :param title_str: str, title for the plot.
    :param save_path: str or None, save path for image.
    :param colorbar_range: tuple (vmin, vmax), fixed colorbar range.
    """
    # Load cell coordinates
    cell_coordinates_df = pd.read_csv(cell_coordinates_path)
    cell_coordinates = cell_coordinates_df.set_index('cell_id').T.to_dict('list')

    # Sum over time
    vehicle_sums = time_id_df.sum(axis=1)

    # Fixed color range
    vmin, vmax = colorbar_range
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap('RdYlGn_r')

    # Plot
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    rect_size = 0.45

    for cell_id, (x, y) in cell_coordinates.items():
        sum_val = vehicle_sums.get(cell_id, 0)

        if sum_val == 0:
            face_color = '#FFFFFF'  # white for 0
            edge_color = 'black'
        else:
            clipped_val = np.clip(sum_val, vmin, vmax)
            face_color = cmap(norm(clipped_val))
            edge_color = 'white'

        rect = plt.Rectangle((x - rect_size / 2, y - rect_size / 2),
                             rect_size, rect_size,
                             facecolor=face_color, edgecolor=edge_color)
        ax.add_patch(rect)

        ax.text(x, y, cell_id.split('.')[-1][1:], ha='center', va='center',
                fontsize=6, color='black')

    # Add colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(np.array([vmin, vmax]))  # only needed to register with the colormap
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', label='Sum of Vehicle Numbers (per cell)')

    # Layout
    ax.set_aspect('equal')
    ax.set_title(title_str)

    x_vals = [v[0] for v in cell_coordinates.values()]
    y_vals = [v[1] for v in cell_coordinates.values()]
    ax.set_xlim(min(x_vals) - 0.5, max(x_vals) + 0.5)
    ax.set_ylim(min(y_vals) - 0.5, max(y_vals) + 0.5)

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
    else:
        plt.show()

    plt.close()


def plot_multi_occupancy_histogram(
        arrays,
        labels=None,
        bins=30,
        title="Blended Cell Occupancy Time Histograms",
        time_range=None,
        save_path=None
):
    """
    Plot overlapping histograms of cell total occupancy durations from multiple datasets.

    Parameters:
    - arrays: list of numpy arrays, each of shape (num_cells, num_timesteps), with 0/1 occupancy
    - labels: list of str, labels for each dataset (optional)
    - bins: int, number of histogram bins
    - title: str, title for the plot
    - save_path: str or None, where to save the plot if needed
    """
    if labels is None:
        labels = [f"Dataset {i + 1}" for i in range(len(arrays))]

    colors = ['red', 'yellow', 'red', 'blue', 'purple']
    plt.figure(figsize=(10, 6))

    # Collect all occupancy sums to determine shared bin range
    all_occupancies = []
    occ_per_dataset = []
    start, end = time_range[0] // 5, time_range[1] // 5

    for arr in arrays:
        occ = arr[:, start:end].sum(axis=1)  # Sum over time axis → total occupied steps per cell
        occ_per_dataset.append(occ)
        all_occupancies.extend(occ)

    # Define shared bin edges
    min_occ, max_occ = min(all_occupancies), max(all_occupancies)
    bin_edges = np.linspace(min_occ, max_occ, bins + 1)

    # Plot histograms with transparent colors
    for i, occ in enumerate(occ_per_dataset):
        plt.hist(
            occ,
            bins=bin_edges,
            alpha=0.4,
            color=colors[i % len(colors)],
            label=labels[i],
            edgecolor='black',
            linewidth=0.5
        )

    plt.xlabel("Total Occupied Time Steps per Cell", fontsize=19)
    plt.ylabel("Frequency", fontsize=19)
    plt.title(title, fontsize=20)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tick_params(axis='both', labelsize=16)
    plt.legend(fontsize=18)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
    else:
        plt.show()


class Pipline:
    def __init__(self):
        return

    def ctmPlot(self, ctm_value, cell_list, cell_coordinates, title_str, save_path=None, mode='numpy', plot='video',
                eval_start=0, eval_duration=0):
        if mode == 'numpy' and plot != 'historgram':
            time_id_matrix_np = np.load(ctm_value)
            time_occupation = (time_id_matrix_np > 0).astype(int)
            print(f'the time occupation is: {np.mean(time_occupation)}')
            time_id_df = pd.DataFrame(time_id_matrix_np, index=cell_list)
            print('yes')
        else:
            time_id_df = ctm_value
        if plot == 'video':
            CTM_visulization(time_id_df, cell_coordinates, save_path=save_path)  # coordinates is a path for csv
        elif plot == 'figure':
            CTM_static_visulization(time_id_df, cell_coordinates, title_str, save_path=save_path)
        elif plot == 'historgram':
            matrix1 = np.load(ctm_value[0])
            matrix2 = np.load(ctm_value[1])
            # matrix3 = np.load(ctm_value[2])

            plot_multi_occupancy_histogram(
                arrays=[matrix1, matrix2],
                # (matrix3, "alpha=1000000")
                labels=[r"$\alpha_1:\alpha_2=1:0$", r"$\alpha_1:\alpha_2=1:10^{6}$"],
                title=title_str,
                time_range=(eval_start // 5, eval_duration // 5)
            )

    @staticmethod
    def apply_temporal_decay(matrix):
        # decay_steps = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0]
        # decay_steps = [0.9, 0.7, 0.4, 0]
        decay_steps = [0]
        num_links, num_time = matrix.shape
        output = np.zeros_like(matrix, dtype=float)

        for i in range(num_links):
            t = 0
            while t < num_time:
                if matrix[i, t] == 1:
                    output[i, t] = 1.0
                    for d, decay_value in enumerate(decay_steps, start=1):
                        next_t = t + d
                        if next_t >= num_time:
                            break
                        if matrix[i, next_t] == 1:
                            break  # reset decay on next 1
                        output[i, next_t] = decay_value
                    t += 1
                else:
                    # Keep whatever value was set previously
                    t += 1

        return output

    def evalOcc(self, bench_occ, ctm_occ, eval_start, eval_duration):
        """
        :param bench_occ: path for benchmark occupation result
        :param ctm_occ: path for ctm occupation result
        """
        """
        Notes:
        occnp: number of vehicles in cells
        occ_bin: binary occupation
        decay: apply a information decay model on temproal occupation
        """

        start_idx = eval_start // 5 + 1
        bench_occnp = np.load(bench_occ)[:, start_idx:start_idx + eval_duration // 5]
        ctm_occnp = np.load(ctm_occ)[:, start_idx:start_idx + eval_duration // 5]
        bench_occ_bin = (bench_occnp > 0).astype(int)
        ctm_occ_bin = (ctm_occnp > 0).astype(int)
        bench_decay = self.apply_temporal_decay(bench_occ_bin)  # apply a information decay in occupation
        ctm_decay = self.apply_temporal_decay(ctm_occ_bin)
        score1 = np.mean(bench_decay)
        score2 = np.mean(ctm_decay)

        sum_ben = np.sum(bench_occ_bin)
        sum_ctm = np.sum(ctm_occ_bin)

        result = {'bench occu score': score1,
                  'optim occu score': score2,
                  'bench tt sum': sum_ben,
                  'optim occu sum': sum_ctm}

        # plot_time_space_heatmap(bench_decay)
        # plot_time_space_heatmap(ctm_decay)
        # print('a')
        return result

    def getOcc(self, matrix_ls, eval_start, eval_duration):
        r, r_or = [], []
        start_idx = eval_start // 5 + 1
        for mat in matrix_ls:
            occ = np.load(mat)[:, start_idx:start_idx + eval_duration // 5]
            occ_bin = (occ > 0).astype(int)
            r.append(occ_bin)
            r_or.append(np.load(mat))
        return r, r_or

    @staticmethod
    def evalTripInfo(trip_info, eval_start=0, eval_end=float('inf')):
        """
        Parse SUMO tripinfo XML file and extract vehicle stats by vType,
        filtered by departure and arrival time range.

        Args:
            trip_info (str): Path to the tripinfo XML file.
            eval_start (float): Start time threshold (vehicle depart time must be > this).
            eval_end (float): End time threshold (vehicle arrival time must be < this).

        Returns:
            tuple:
                - result (dict): vType → list of {'id', 'duration', 'routeLength'}
                - summary (dict): vType → summary stats: avg_duration, avg_routeLength, vehicle_count
        """
        tree = ET.parse(trip_info)
        root = tree.getroot()

        result = {}

        for trip in root.findall("tripinfo"):
            veh_id = trip.get("id")
            vtype = trip.get("vType")
            duration = float(trip.get("duration"))
            route_length = float(trip.get("routeLength"))
            depart = float(trip.get("depart"))
            arrival = float(trip.get("arrival"))
            stop = float(trip.get("waitingCount"))
            reroute = float(trip.get("rerouteNo"))
            waitTime = float(trip.get("waitingTime"))

            # Filter by time window
            if depart > eval_start and arrival < eval_end:
                if vtype not in result:
                    result[vtype] = []

                result[vtype].append({
                    "id": veh_id,
                    "duration": duration,
                    "routeLength": route_length,
                    "speed": route_length / duration,
                    "stop": stop,
                    "reroute": reroute,
                    "waitTime": waitTime,
                })

        # Summary stats
        summary = {}
        for vtype, records in result.items():
            total_duration = sum(r['duration'] for r in records)
            total_length = sum(r['routeLength'] for r in records)
            count = len(records)

            avg_duration = total_duration / count if count > 0 else 0
            avg_route_length = total_length / count if count > 0 else 0
            avg_speed = sum(r['speed'] for r in records) / count if count > 0 else 0
            avg_stop = sum(r['stop'] for r in records) / count if count > 0 else 0
            avg_reroute = sum(r['reroute'] for r in records) / count if count > 0 else 0
            # dev_reroute =
            avg_waitT = sum(r['waitTime'] for r in records) / count if count > 0 else 0

            summary[vtype] = {
                "avg_duration": avg_duration,
                "avg_routeLength": avg_route_length,
                "vehicle_count": count,
                "avg_speed": avg_speed,
                "avg_stop": avg_stop,
                "avg_reroute": avg_reroute,
            }

        return result, summary

    @staticmethod
    def plotTripInfo(trip_data):
        plt.figure(figsize=(10, 6))
        for vtype, records in trip_data.items():
            durations = [r["duration"] for r in records]
            lengths = [r["routeLength"] for r in records]
            plt.scatter(lengths, durations, label=vtype, alpha=0.7)

        plt.ylabel("Duration (s)")
        plt.xlabel("Route Length (m)")
        plt.title("Duration vs Route Length per Vehicle")
        plt.legend(title="Vehicle Type")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    @staticmethod
    def evalCTM(file_gt, file_rec, cell_json, eval_start, eval_duration, method, vis=False):

        start_idx = eval_start // 5 + 1
        mat_1r = np.load(file_gt)[:, start_idx:start_idx + eval_duration // 5]
        mat_2r = np.load(file_rec)[:, start_idx:start_idx + eval_duration // 5]

        # plot_time_space_heatmap(mat1)
        # plot_time_space_heatmap(mat2)

        # with open(cell_json, 'r') as f:
        #     cell_data = json.load(f)

        with open(cell_json, 'r') as file:
            cell_data = [line.strip() for line in file]

        mat1, b = remove_branch(cell_data, mat_1r)
        mat2, b = remove_branch(cell_data, mat_2r)

        sm1 = np.sum(mat1)
        sm2 = np.sum(mat2)

        if vis:
            plot_time_space_heatmap(mat1)
            plot_time_space_heatmap(mat2)

        if mat1.shape != mat2.shape:
            raise ValueError(f"Shape mismatch: {mat1.shape} vs {mat2.shape}")

        if method == "mse":
            return mean_squared_error(mat1.flatten(), mat2.flatten()), mat_1r, mat_2r

        if method == "mae":
            return mean_absolute_error(mat1, mat2), mat_1r, mat_2r

        elif method == "cosine":
            # reshape to (n_samples, n_features)
            aa = cosine_similarity(mat1.reshape(1, -1), mat2.reshape(1, -1))
            return aa, mat_1r, mat_2r

        elif method == "correlation":
            return np.corrcoef(mat1.flatten(), mat2.flatten())[0, 1], mat_1r, mat_2r

        elif method == "mape":
            non_zero_mask = mat1 != 0
            if not np.any(non_zero_mask):
                return np.nan  # or raise an error if preferred
            return np.mean(
                np.abs((mat1[non_zero_mask] - mat2[non_zero_mask]) / mat1[non_zero_mask])) * 100, mat_1r, mat_2r

        # note: add mape

        else:
            raise ValueError(f"Unknown method '{method}'. Choose from 'mse', 'cosine', or 'correlation'.")

    import numpy as np

    @staticmethod
    def evaluate_distribution_balance(occ_path, eval_start, eval_duration, ):
        """
        Evaluate the spatiotemporal distribution balance using four metrics:
        1. Average spatial variance (across time steps)
        2. Average temporal variance (across nodes)
        3. Gini coefficient
        4. Entropy

        Parameters:
            matrix (np.ndarray): A 2D numpy array of shape (num_nodes, num_timesteps),
                                 representing vehicle count at each node and time.

        Returns:
            dict: A dictionary with keys 'spatial_variance', 'temporal_variance', 'gini', and 'entropy'
        """
        start_idx = eval_start // 5 + 1
        mat1 = np.load(occ_path)[:, start_idx:start_idx + eval_duration // 5]
        matrix = np.array(mat1)
        num_nodes, num_timesteps = matrix.shape

        # 1. Spatial variance: variance across nodes for each time step, then averaged
        spatial_variance = np.mean(np.var(matrix, axis=0))

        # 2. Temporal variance: variance across time for each node, then averaged
        temporal_variance = np.mean(np.var(matrix, axis=1))

        # 3. Gini coefficient
        flat = matrix.flatten()
        if np.sum(flat) == 0:
            gini = 0.0  # all zeros → uniform
        else:
            sorted_flat = np.sort(flat)
            n = len(sorted_flat)
            index = np.arange(1, n + 1)
            gini = (np.sum((2 * index - n - 1) * sorted_flat)) / (n * np.sum(sorted_flat))

        # 4. Entropy
        total_sum = np.sum(flat)
        if total_sum == 0:
            entropy = 0.0
        else:
            prob = flat / total_sum
            prob = prob[prob > 0]  # remove zero entries for log
            entropy = -np.sum(prob * np.log(prob))

        return {
            'spatial_variance': spatial_variance,
            'temporal_variance': temporal_variance,
            'gini': gini,
            'entropy': entropy
        }


def plot_time_space_heatmap(matrix, title="Time-Space Heatmap", xlabel="Time", ylabel="Link ID", cmap="viridis"):
    """
    Plot a 2D heatmap for a time-space matrix.

    Args:
        matrix (np.ndarray): A 2D array of shape (link_num, time_steps)
        title (str): Title of the heatmap
        xlabel (str): Label for time axis
        ylabel (str): Label for link axis
        cmap (str): Matplotlib colormap to use (e.g., "viridis", "hot", "plasma")
    """
    plt.figure(figsize=(12, 6))
    plt.imshow(matrix, aspect='auto', cmap=cmap, origin='lower')
    plt.colorbar(label="Value")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.show()


def remove_branch(cell_data, ctm_matrix):
    """
    Removes rows corresponding to cells ending with 'C0' from a spatio-temporal matrix.

    Parameters:
        json_path (str): Path to the JSON file containing cell names.
        ctm_matrix (np.ndarray): Matrix with shape (space, time).

    Returns:
        np.ndarray: The filtered matrix with 'C0' cells removed.
        list: List of removed cell indices.
    """
    # Load JSON file
    # with open(json_path, 'r') as f:
    #     cell_data = json.load(f)

    # with open(json_path, 'r') as file:
    #     cell_data = [line.strip() for line in file]

    # Assume the cell names are in a list or dict → extract name list
    if isinstance(cell_data, list):
        cell_names = cell_data
    elif isinstance(cell_data, dict):
        cell_names = list(cell_data.values())
    else:
        raise ValueError("Unsupported JSON structure. Expecting list or dict of cell names.")

    # Find indices where name ends with 'C0'
    # c0_indices = [i for i, name in enumerate(cell_names) if str(name).endswith("C0")]
    branch_indices = [i for i, name in enumerate(cell_names) if str(name).startswith("A1")]

    # Remove corresponding rows from matrix
    filtered_matrix = np.delete(ctm_matrix, branch_indices, axis=0)

    return filtered_matrix, branch_indices


# def plot_cav_duration_histogram(
#         data_list,
#         labels=None,
#         attribute="duration",
#         bins=30,
#         title="Travel Duration Distribution (CAV)",
#         save_path=None
# ):
#     """
#     Plot overlapping histograms of CAV durations with shared bin edges and color blending.
#
#     Parameters:
#     - data_list: list of dicts, each with key 'cav' mapping to list of dicts with 'duration'
#     - labels: list of str, labels for each dataset
#     - bins: int, number of histogram bins
#     - title: str, plot title
#     - save_path: str or None, if set, saves the figure
#     """
#     if labels is None:
#         labels = [f"Dataset {i + 1}" for i in range(len(data_list))]
#
#     # Use base RGB color tuples for better blending
#     base_colors = [(0, 0, 1.0),  # blue
#                    (1.0, 0.8, 0.2),  # yellow
#                    (0.1, 1.0, 0.1)]  # green (if needed for third)
#
#     plt.figure(figsize=(10, 6))
#
#     # Collect all durations to determine global bin edges
#     all_durations = []
#     durations_per_dataset = []
#
#     for data in data_list:
#         durations = [entry[attribute] for entry in data["cav"] if attribute in entry]
#         durations_per_dataset.append(durations)
#         all_durations.extend(durations)
#
#     durations_per_dataset[1] = durations_per_dataset[1][:len(durations_per_dataset[0])]
#
#     # Define global bin edges
#     min_dur, max_dur = min(all_durations), max(all_durations)
#     bin_edges = np.linspace(min_dur, max_dur, bins + 1)
#
#     # Draw each histogram with alpha for blending effect
#     for i, durations in enumerate(durations_per_dataset):
#         plt.hist(
#             durations,
#             bins=bin_edges,
#             alpha=0.5,  # semi-transparent for blending
#             label=labels[i],
#             color=base_colors[i % len(base_colors)],
#             edgecolor='black'
#         )
#
#     # plt.xlabel(f"CAV {attribute}")
#     plt.ylabel(r"Number of Vehicles", fontsize=19)
#     if attribute == "routeLength":
#         plt.xlabel(r"CAV Travel Distance ($\mathrm{m}$)", fontsize=19)
#         plt.xlim(1500, 8000)
#     elif attribute == "duration":
#         plt.xlabel(r"CAV Travel Time ($\mathrm{s}$)", fontsize=19)
#         plt.xlim(0, 2000)
#     plt.tick_params(axis='both', labelsize=16)
#     plt.title(title, fontsize=20)
#     plt.grid(axis='y', linestyle='--', alpha=0.7)
#     plt.legend(fontsize=18)
#     plt.tight_layout()
#
#     if save_path:
#         plt.savefig(save_path, bbox_inches='tight')
#     else:
#         plt.show()


def plot_cav_duration_histogram(
        data_list,
        labels=None,
        attribute="duration",
        bins=30,
        title="Travel Duration Distribution (CAV)",
        save_path=None,
        mode="time",   # <-- new argument: 'time' or 'distance'
):
    """
    Plot overlapping histograms of CAV durations with shared bin edges and color blending.

    Parameters:
    - data_list: list of dicts, each with key 'cav' mapping to list of dicts with 'duration' (or other attribute)
    - labels: list of str, labels for each dataset
    - bins: int, number of histogram bins (used when mode='time')
    - title: str, plot title
    - save_path: str or None, if set, saves the figure
    - mode: str, 'time' or 'distance'
        * 'time'     -> use automatic bins from min to max (original behavior)
        * 'distance' -> use fixed bin edges starting at 2080, then 2880, ... with step 800
    """
    if labels is None:
        labels = [f"Dataset {i + 1}" for i in range(len(data_list))]

    # Use base RGB color tuples for better blending
    base_colors = [(0, 0, 1.0),    # blue
                   (1.0, 0.8, 0.2),  # yellow
                   (0.1, 1.0, 0.1)]  # green (if needed for third)

    plt.figure(figsize=(10, 6))

    # Collect all attribute values to determine global bin edges
    all_durations = []
    durations_per_dataset = []

    for data in data_list:
        durations = [entry[attribute] for entry in data["cav"] if attribute in entry]
        durations_per_dataset.append(durations)
        all_durations.extend(durations)

    # keep your original behavior (clip second dataset to length of first)
    if len(durations_per_dataset) > 1:
        durations_per_dataset[1] = durations_per_dataset[1][:len(durations_per_dataset[0])]

    if not all_durations:
        raise ValueError(f"No values found for attribute '{attribute}'.")

    # Define global bin edges
    min_dur, max_dur = min(all_durations), max(all_durations)

    if attribute == "routeLength":
        # Fixed distance-based bins: 2080, 2880, 3680, ... with step 800

        start = 2080.0
        step = 800.0

        # If all data are below 2080, fall back to default behavior
        if max_dur <= start:
            bin_edges = np.linspace(min_dur, max_dur, bins + 1)
        else:
            # Compute how many steps we need so that last edge >= max_dur
            k_max = int(np.ceil((max_dur - start) / step))
            distance_edges = start + step * np.arange(k_max + 1)

            # If there are values below 2080, prepend min_dur as first edge
            if min_dur < start:
                bin_edges = np.concatenate(([min_dur], distance_edges))
            else:
                bin_edges = distance_edges
    else:
        # Original 'time' behavior: evenly spaced between min and max
        bin_edges = np.linspace(min_dur, max_dur, bins + 1)

    # Draw each histogram with alpha for blending effect
    for i, durations in enumerate(durations_per_dataset):
        if not durations:
            continue
        plt.hist(
            durations,
            bins=bin_edges,
            alpha=0.5,  # semi-transparent for blending
            label=labels[i],
            color=base_colors[i % len(base_colors)],
            edgecolor='black'
        )

    plt.ylabel(r"Number of Vehicles", fontsize=19)
    if attribute == "routeLength":
        plt.xlabel(r"CAV Travel Distance ($\mathrm{m}$)", fontsize=19)
        plt.xlim(1500, 10000)
    elif attribute == "duration":
        plt.xlabel(r"CAV Travel Time ($\mathrm{s}$)", fontsize=19)
        plt.xlim(0, 2000)
    else:
        plt.xlabel(f"CAV {attribute}", fontsize=19)

    plt.tick_params(axis='both', labelsize=16)
    plt.title(title, fontsize=20)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(fontsize=18)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
    else:
        plt.show()




class ODProcessor:
    """
    A class for processing vehicle Origin–Destination (OD) data from JSON files.

    Current functionality:
    - Load vehicle data from a JSON file
    - Group vehicles by OD pair (origin, destination)
    - Save grouped results to a file

    Future extensions:
    - Visualization of OD flows
    - Statistics (e.g., busiest OD pair, route overlap analysis)
    - Graph/network export (for network analysis)
    """

    def __init__(self):
        self.raw_data: Dict[str, Any] = {}
        self.od_groups: Dict[str, Any] = {}

    def load_data(self, input_json_path: str) -> None:
        """Load vehicle JSON file into memory."""
        with open(input_json_path, "r") as f:
            self.raw_data = json.load(f)

    def build_od_groups(self, sort_by: str = "alpha") -> Dict[str, Any]:
        """
        Build OD-grouped dictionary from raw data.

        Args:
            sort_by: 'alpha' for alphabetical sorting of OD keys,
                     'count' for sorting OD pairs by vehicle count (descending).

        Returns:
            dict: OD-grouped dictionary.
        """
        if not self.raw_data:
            raise ValueError("No data loaded. Call load_data() first.")

        groups: Dict[str, Any] = {}

        for v_id, info in self.raw_data.items():
            origin = info.get("origin")
            dest = info.get("destination")
            route = info.get("route", [])
            # route_node = info.get("route_node", [])
            if origin is None or dest is None:
                continue

            od_key = f"({origin},{dest})"
            if od_key not in groups:
                groups[od_key] = {"count": 0, "vehicles": []}

            groups[od_key]["vehicles"].append({"v_id": v_id, "route": route})
            groups[od_key]["count"] += 1

        # Sort vehicles inside each OD
        for od in groups:
            groups[od]["vehicles"].sort(key=lambda x: x["v_id"])

        # Sort OD pairs
        if sort_by == "alpha":
            groups = dict(sorted(groups.items(), key=lambda kv: kv[0]))
        elif sort_by == "count":
            groups = dict(sorted(groups.items(), key=lambda kv: kv[1]["count"], reverse=True))

        self.od_groups = groups
        # return self.od_groups

    @staticmethod
    def load_topology_config(input_json_path: str) -> None:
        """
        Returns a JSON-serializable template for the grid (or general) network topology.
        - nodes: dict[node_id] -> {"x": float, "y": float}
        - edges: dict[edge_id]  -> {"u": node_id, "v": node_id}
          NOTE: edge_id MUST MATCH the IDs you use in routes (e.g., "E113", "-E36").
                If you have bidirectional links, list both IDs explicitly.

        Example:
        {
          "nodes": {
            "N00": {"x": 0.0, "y": 0.0},
            "N01": {"x": 0.0, "y": 1.0},
            "N10": {"x": 1.0, "y": 0.0},
            "N11": {"x": 1.0, "y": 1.0}
          },
          "edges": {
            "E113": {"u": "N00", "v": "N01"},
            "-E113": {"u": "N01", "v": "N00"},
            "E200": {"u": "N00", "v": "N10"},
            "-E200": {"u": "N10", "v": "N00"}
          }
        }
        """

        with open(input_json_path, "r") as f:
            topology = json.load(f)
        return topology

    def set_topology(self, topology: Dict[str, Any]) -> None:
        """
        Set topology from a dict matching topology_config_template().
        """
        # Basic validation
        if "nodes" not in topology or "edges" not in topology:
            raise ValueError("Topology must contain 'nodes' and 'edges' keys.")
        for nid, attrs in topology["nodes"].items():
            if not {"x", "y"}.issubset(attrs.keys()):
                raise ValueError(f"Node '{nid}' must have 'x' and 'y'.")
        for eid, attrs in topology["edges"].items():
            if not {"u", "v"}.issubset(attrs.keys()):
                raise ValueError(f"Edge '{eid}' must have 'u' and 'v' node IDs.")
            if attrs["u"] not in topology["nodes"] or attrs["v"] not in topology["nodes"]:
                raise ValueError(f"Edge '{eid}' endpoints must exist in 'nodes'.")
        self.topology = topology

    def load_topology(self, topology_json_path: str) -> None:
        """Load topology from a JSON file matching topology_config_template()."""
        with open(topology_json_path, "r") as f:
            topo = json.load(f)
        self.set_topology(topo)

    # -----------------------------
    # Edge usage aggregation
    # -----------------------------
    def get_edge_usage_for_od(self, od_key: str) -> Dict[str, int]:
        """
        Count how many vehicles (for a specific OD pair) traverse each edge.
        Edges are counted once per vehicle pass (i.e., if a route lists an edge twice, it contributes twice).

        Returns:
            dict[edge_id] -> usage_count
        """
        if not self.od_groups:
            raise ValueError("OD groups not available. Call build_od_groups() first.")
        if od_key not in self.od_groups:
            raise KeyError(f"OD key '{od_key}' not found. Available keys: {list(self.od_groups.keys())[:5]}...")

        usage = Counter()
        for v in self.od_groups[od_key]["vehicles"]:
            for e in v.get("route", []):
                usage[e] += 1
        return dict(usage)

    def get_all_edge_usage(self) -> Dict[str, int]:
        """
        Count total edge usage across all OD pairs.
        """
        if not self.od_groups:
            raise ValueError("OD groups not available. Call build_od_groups() first.")
        usage = Counter()
        for info in self.od_groups.values():
            for v in info["vehicles"]:
                for e in v.get("route", []):
                    usage[e] += 1
        return dict(usage)

    # -----------------------------
    # Visualization
    # -----------------------------
    def plot_network_edge_usage(
            self,
            od_key: Optional[str] = None,
            case_string: str = "bench",
            mode: str = "width",  # "width" or "color"
            base_linewidth: float = 0.5,
            max_linewidth: float = 4.0,
            show_unused: bool = True,
            figsize: Tuple[int, int] = (12, 12),
            title: Optional[str] = None,
            # direction splitting
            split_directions: bool = True,
            offset_pts_normal: float = 8.0,  # perpendicular offset (points)
            offset_pts_tangent: float = 0,  # along-edge offset (points)
            # label controls
            show_labels: bool = True,
            label_fontsize: int = 12,
            label_bg_alpha: float = 0.6,
    ) -> None:
        """
        Plot network edge usage for a specific OD (or all ODs if od_key=None).

        - Opposite directions are drawn as parallel lines (offset in points).
        - mode="width": line width encodes usage (uniform color).
        - mode="color": color encodes usage from green (0) to red (max).
        - Labels show "edge_id (count)" and are offset with their lines so +/− don't overlap.
        """
        import numpy as np
        import matplotlib.pyplot as plt
        import matplotlib.lines as mlines
        from matplotlib.transforms import ScaledTranslation
        import matplotlib as mpl
        import matplotlib.patheffects as pe

        if not self.topology:
            raise ValueError("No topology set. Call set_topology() or load_topology().")

        usage = self.get_all_edge_usage() if od_key is None else self.get_edge_usage_for_od(od_key)
        max_use = max(usage.values()) if usage else 0

        nodes = self.topology["nodes"]
        edges = self.topology["edges"]

        # green -> red
        cmap = mpl.cm.get_cmap("RdYlGn_r")
        norm = mpl.colors.Normalize(vmin=0, vmax=max_use if max_use > 0 else 1)

        fig, ax = plt.subplots(figsize=figsize)

        for eid, ev in edges.items():
            u, v = ev["u"], ev["v"]
            if u not in nodes or v not in nodes:
                continue

            x1, y1 = nodes[u]["x"], nodes[u]["y"]
            x2, y2 = nodes[v]["x"], nodes[v]["y"]
            dx, dy = (x2 - x1), (y2 - y1)
            L = np.hypot(dx, dy)
            if L == 0:
                continue

            count = usage.get(eid, 0)

            # Respect show_unused
            if not show_unused and count == 0:
                continue

            # width & color
            if mode == "width":
                if max_use > 0 and count > 0:
                    lw = base_linewidth + (max_linewidth - base_linewidth) * (count / max_use)
                else:
                    lw = base_linewidth
                color = "tab:blue" if count > 0 else "lightgray"
            elif mode == "color":
                lw = base_linewidth if count == 0 else base_linewidth * 1.8
                color = cmap(norm(count)) if (count > 0 or show_unused) else (0.8, 0.8, 0.8, 0.6)
            else:
                raise ValueError("mode must be 'width' or 'color'")

            # offset directions (+ on one side, − on the other)
            if split_directions:
                theta = np.arctan2(dy, dx)
                is_negative = str(eid).startswith("-")
                # sgn = -1 if is_negative else 1  # <-- FIXED: opposite directions get opposite offsets
                sgn = -1
                t_pts = sgn * offset_pts_tangent
                p_pts = sgn * offset_pts_normal
                dx_pts = t_pts * np.cos(theta) - p_pts * np.sin(theta)
                dy_pts = t_pts * np.sin(theta) + p_pts * np.cos(theta)
                trans = ax.transData + ScaledTranslation(dx_pts / 72.0, dy_pts / 72.0, fig.dpi_scale_trans)
            else:
                trans = ax.transData

            # draw the line
            line = mlines.Line2D(
                [x1, x2], [y1, y2],
                linewidth=lw,
                color=color,
                alpha=0.95 if count > 0 else 0.6,
                solid_capstyle="round",
                transform=trans,
                zorder=2 if count == 0 else 3
            )
            ax.add_line(line)

            # label text (follows the same transform so +/− labels separate with their lines)
            if show_labels:
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                angle_deg = np.degrees(np.arctan2(dy, dx))
                text = f"{eid} ({count})"
                ax.text(
                    mx, my, text,
                    fontsize=label_fontsize,
                    rotation=angle_deg,
                    rotation_mode="anchor",
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=label_bg_alpha),
                    path_effects=[pe.withStroke(linewidth=1.0, foreground="black", alpha=0.25)],
                    transform=trans,
                    zorder=5
                )

        # nodes
        xs = [nodes[n]["x"] for n in nodes]
        ys = [nodes[n]["y"] for n in nodes]
        ax.scatter(xs, ys, s=100, color="black", zorder=6)

        if title is None:
            title = "Edge Usage (All ODs)" if od_key is None else f"Edge Usage for OD {od_key} in {case_string}"
        ax.set_title(title, fontsize=label_fontsize + 6)
        ax.set_aspect("equal", adjustable="box")
        ax.autoscale()
        ax.axis("off")

        if mode == "color" and max_use > 0:
            sm = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
            sm.set_array([])
            cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.02)
            cbar.set_label("Edge usage (count)")

        plt.show()

    def plot_od_histogram(
            self,
            sort: str = "count",
            rotation: int = 45,
            figsize: Tuple[int, int] = (8, 5),
            title: str = "Vehicles per OD Pair",
    ) -> None:
        """
        Plot a histogram (bar chart) for number of vehicles per OD pair.

        Args:
            sort: 'count' (descending) or 'alpha' (alphabetical by OD key)
        """
        if not self.od_groups:
            raise ValueError("OD groups not available. Call build_od_groups() first.")

        items = list(self.od_groups.items())
        if sort == "count":
            items.sort(key=lambda kv: kv[1]["count"], reverse=True)
        else:
            items.sort(key=lambda kv: kv[0])

        labels = [k for k, _ in items]
        counts = [v["count"] for _, v in items]

        plt.figure(figsize=figsize)
        plt.bar(range(len(labels)), counts)
        plt.xticks(range(len(labels)), labels, rotation=rotation, ha="right")
        plt.ylabel("Number of vehicles")
        plt.title(title)
        plt.tight_layout()
        plt.show()

    # -----------------------------
    # Convenience getters
    # -----------------------------
    def available_od_keys(self) -> List[str]:
        """Return the list of OD keys currently in memory."""
        return list(self.od_groups.keys())

    def od_counts(self) -> Dict[str, int]:
        """Return {od_key: count} map."""
        return {k: v["count"] for k, v in self.od_groups.items()}

    def save_od_groups(self, output_json_path: str) -> None:
        """Save OD groups to a JSON file."""
        if not self.od_groups:
            raise ValueError("OD groups not built yet. Run build_od_groups() first.")
        with open(output_json_path, "w") as f:
            json.dump(self.od_groups, f, indent=2)


def evalCTM(ctm_gt, ctm_rec, cell_list, eval_start, eval_duration, method, vis=False, mode="numpy"):
    start_idx = eval_start // 5 + 1
    if mode == "file":
        mat_1r = np.load(ctm_gt)[:, start_idx:start_idx + eval_duration // 5]
        mat_2r = np.load(ctm_rec)[:, start_idx:start_idx + eval_duration // 5]
    elif mode == "numpy":
        mat_1r = ctm_gt
        mat_2r = ctm_rec

    # plot_time_space_heatmap(mat1)
    # plot_time_space_heatmap(mat2)

    mat1, b = remove_branch(cell_list, mat_1r)
    mat2, b = remove_branch(cell_list, mat_2r)

    sm1 = np.sum(mat1)
    sm2 = np.sum(mat2)

    if vis:
        plot_time_space_heatmap(mat1)
        plot_time_space_heatmap(mat2)

    if mat1.shape != mat2.shape:
        raise ValueError(f"Shape mismatch: {mat1.shape} vs {mat2.shape}")

    if method == "mse":
        return mean_squared_error(mat1.flatten(), mat2.flatten()), mat_1r, mat_2r

    elif method == "cosine":
        # reshape to (n_samples, n_features)
        aa = cosine_similarity(mat1.reshape(1, -1), mat2.reshape(1, -1))
        return aa, mat_1r, mat_2r

    elif method == "correlation":
        return np.corrcoef(mat1.flatten(), mat2.flatten())[0, 1], mat_1r, mat_2r

    elif method == "mape":
        non_zero_mask = mat_1r != 0
        if not np.any(non_zero_mask):
            return np.nan  # or raise an error if preferred
        return 100 * np.sum(np.abs((mat_1r[non_zero_mask] - mat_2r[non_zero_mask]) / mat_1r[non_zero_mask])) / (
                mat_1r.shape[0] * mat_1r.shape[1]), mat_1r, mat_2r

    elif method == "mae":
        return np.mean(np.abs(mat_1r - mat_2r)), mat_1r, mat_2r

    # note: add mape

    else:
        raise ValueError(f"Unknown method '{method}'. Choose from 'mse', 'cosine', or 'correlation'.")


def plot_gt_ctm_and_mae(link_gt: np.ndarray, link_ctm: np.ndarray, cell_idx: list, cell_ids: list,
                        saving_dir='../result/plot_ctm'):
    """
    For matrices shaped (cell_number, time), plot one figure per cell:
    - x-axis: time steps
    - y-axis: value for that cell
    Plots GT and CTM with different colors and computes MAE.
    """
    if link_gt.shape != link_ctm.shape:
        raise ValueError(f"Shape mismatch: link_gt {link_gt.shape} vs link_ctm {link_ctm.shape}")

    n_cells, n_times = link_gt.shape
    t = np.arange(n_times)

    # Overall MAE
    mae_overall = np.mean(np.abs(link_gt - link_ctm))
    print(f"Overall Mean Absolute Error (MAE): {mae_overall:.6f}")

    # Optional: per-cell MAE
    mae_per_cell = np.mean(np.abs(link_gt - link_ctm), axis=1)
    for i, m in enumerate(mae_per_cell):
        print(f"Cell {cell_idx[cell_ids[i]]} MAE: {m:.6f}")

    # Plot one figure per cell
    for cell_id in range(n_cells):
        ym = getcellmaxnumber(cell_idx[cell_ids[cell_id]])
        plt.figure(figsize=(16, 4))
        plt.plot(t, link_gt[cell_id], label="Ground Truth", linewidth=1.8)
        plt.plot(t, link_ctm[cell_id], label="CTM", linestyle="--", linewidth=1.8)
        plt.xlabel("Time step")
        plt.ylabel("Value")
        plt.ylim((0, ym))
        plt.title(f"Cell {cell_idx[cell_ids[cell_id]]}: Ground Truth vs CTM")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(f"{saving_dir}/Cell_{cell_idx[cell_ids[cell_id]]}.png")
        # plt.show()
        time.sleep(1)

    return mae_overall


def getcellmaxnumber(cid):
    # a = cid[-2:]
    if cid[-1] == '1' or cid[-1] == '2' or cid[-1] == '6' or cid[-1] == '7':
        return 12
    elif cid[-1] == '3' or cid[-1] == '4':
        return 22
    elif cid[-2] == '40':
        return 6
    elif cid[2] == '1' and cid[-1] == '5':
        return 6
    elif cid[2] == '0' and cid[-1] == '5':
        return 22


def linkCTMvislz(cell_idx, ctm, ctm_gt, mode='full'):
    # link_cellls = ['A1.E101.C40', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7']
    # link_cellls = ['A0.E11.C1', 'A0.E11.C2', 'A0.E11.C3', 'A0.E11.C4', 'A0.E11.C5', 'A0.E11.C6', 'A0.E11.C7']   # internal link

    # choose one intersection
    # link_cellls = ['A0.E5.C3', 'A0.E5.C4', 'A0.E5.C5', 'A0.E5.C6', 'A0.E5.C7',
    #                'A0.-E5.C1', 'A0.-E5.C2', 'A0.-E5.C3', 'A0.-E5.C4', 'A0.-E5.C5',
    #                'A0.E6.C1', 'A0.E6.C2', 'A0.E6.C3', 'A0.E6.C4', 'A0.E6.C5',
    #                'A0.-E6.C3', 'A0.-E6.C4', 'A0.-E6.C5', 'A0.-E6.C6', 'A0.-E6.C7',
    #                'A0.E25.C3', 'A0.E25.C4', 'A0.E25.C5', 'A0.E25.C6', 'A0.E25.C7',
    #                'A0.-E25.C1', 'A0.-E25.C2', 'A0.-E25.C3', 'A0.-E25.C4', 'A0.-E25.C5',
    #                'A0.E26.C1', 'A0.E26.C2', 'A0.E26.C3', 'A0.E26.C4', 'A0.E26.C5',
    #                'A0.-E26.C3', 'A0.-E26.C4', 'A0.-E26.C5', 'A0.-E26.C6', 'A0.-E26.C7']

    link_cellls = ['A1.E101.C40', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7',
                   'A1.E102.C40', 'A1.E102.C5', 'A1.E102.C6', 'A1.E102.C7',
                   'A1.E103.C40', 'A1.E103.C5', 'A1.E103.C6', 'A1.E103.C7',
                   'A1.E104.C40', 'A1.E104.C5', 'A1.E104.C6', 'A1.E104.C7',
                   'A1.E105.C40', 'A1.E105.C5', 'A1.E105.C6', 'A1.E105.C7',
                   'A1.E106.C40', 'A1.E106.C5', 'A1.E106.C6', 'A1.E106.C7',
                   'A1.E107.C40', 'A1.E107.C5', 'A1.E107.C6', 'A1.E107.C7',
                   'A1.E108.C40', 'A1.E108.C5', 'A1.E108.C6', 'A1.E108.C7',
                   'A1.E109.C40', 'A1.E109.C5', 'A1.E109.C6', 'A1.E109.C7',
                   'A1.E110.C40', 'A1.E110.C5', 'A1.E110.C6', 'A1.E110.C7',
                   'A1.E111.C40', 'A1.E111.C5', 'A1.E111.C6', 'A1.E111.C7',
                   'A1.E112.C40', 'A1.E112.C5', 'A1.E112.C6', 'A1.E112.C7',
                   'A1.E113.C40', 'A1.E113.C5', 'A1.E113.C6', 'A1.E113.C7',
                   'A1.E114.C40', 'A1.E114.C5', 'A1.E114.C6', 'A1.E114.C7',
                   'A1.E115.C40', 'A1.E115.C5', 'A1.E115.C6', 'A1.E115.C7',
                   'A1.E116.C40', 'A1.E116.C5', 'A1.E116.C6', 'A1.E116.C7',
                   'A1.E117.C40', 'A1.E117.C5', 'A1.E117.C6', 'A1.E117.C7',
                   'A1.E118.C40', 'A1.E118.C5', 'A1.E118.C6', 'A1.E118.C7',
                   'A1.E119.C40', 'A1.E119.C5', 'A1.E119.C6', 'A1.E119.C7',
                   'A1.E120.C40', 'A1.E120.C5', 'A1.E120.C6', 'A1.E120.C7']
    # 'A0.E3.C1', 'A0.E3.C2', 'A0.E3.C3', 'A0.E3.C4',
    # 'A0.E3.C5', 'A0.E3.C6', 'A0.E3.C7',]

    # cell_ids = [cell_idx.index(c) for c in link_cellls]
    # link_gt = ctm_gt[cell_ids]
    # link_ctm = ctm[cell_ids]

    if mode == "full":
        cell_ids = [i for i in range(len(cell_idx))]
        mae = plot_gt_ctm_and_mae(ctm_gt, ctm, cell_idx, cell_ids)
    elif mode == "link":
        cell_ids = [cell_idx.index(c) for c in link_cellls]
        link_gt = ctm_gt[cell_ids]
        link_ctm = ctm[cell_ids]
        mae = plot_gt_ctm_and_mae(link_gt, link_ctm, cell_idx, cell_ids)


def checkCTM(n, y_in, y_out):
    s1, s2, s3 = np.sum(n), np.sum(y_in), np.sum(y_out)
    print(f'summation is {s1}, {s2}, {s3}')

    # 1. check n(t+1) = n(t) + yin(t) - yout(t)
    # for link in range(n.shape[0]):
    #     for t in range(n.shape[1] - 1):
    #         if n[link, t+1] != n[link, t] + y_in[link, t] - y_out[link, t]:
    #             print(f"link {link} and {t} is not correct")
    # 2. check c5-c67 connection
    for t in range(n.shape[1]):
        if y_out[85, t] != y_in[86, t] + y_in[87, t]:
            print(f'link cell c5-67 is not correct at {t}')
    for t in range(n.shape[1]):
        if y_out[84, t] != y_in[85, t]:
            print(f'link cell c4-5 is not correct at {t}')
    for t in range(n.shape[1]):
        if y_out[83, t] != y_in[84, t]:
            print(f'link cell c3-4 is not correct at {t}')
    for t in range(n.shape[1]):
        if y_out[81, t] + y_out[82, t] != y_in[83, t]:
            print(f'link cell c12-3 is not correct at {t}')


# def popularity_from_visit_matrix(visit_mat: np.ndarray, *, mode: str = "count", window_step: int) -> np.ndarray:
#     """
#     Convert a binary visit matrix (segments x time) into popularity pmf p_i (sum_i p_i = 1).
#
#     Parameters
#     ----------
#     visit_mat : np.ndarray of shape (n_segments, n_time), entries in {0,1}
#     mode : {"count", "time_fraction"}
#         "count": p_i ∝ (# of visited time bins) ; "time_fraction": p_i ∝ (#visited / T).
#         两者都会做一次归一化，确保 sum p_i = 1。
#
#     Returns
#     -------
#     p : np.ndarray, shape (n_segments,), nonnegative and sums to 1
#     """
#     if visit_mat.ndim != 2:
#         raise ValueError("visit_mat must be 2D (segments x time)")
#
#     n_segments, T = visit_mat.shape
#     counts = visit_mat.astype(float).sum(axis=1)  # 0..T
#
#     if mode == "time_fraction":
#         counts = counts / max(T, 1)
#
#     total = float(counts.sum())  # still use the visited segment
#     # total = n_segments * T  # Nov 18th update:
#     if total <= 0:
#         # 没有任何访问记录，退化为均匀分布
#         p = np.ones(n_segments, dtype=float) / max(n_segments, 1)
#     else:
#         p = counts / total
#
#     # 数值清理
#     p = np.clip(p, 0.0, 1.0)
#     s = p.sum()
#     if s == 0:
#         p[:] = 1.0 / len(p)
#     else:
#         p /= s
#     return p


def popularity_from_visit_matrix(
        visit_mat: np.ndarray,
        *,
        mode: str = "count",
        window_step: int | None = None
) -> np.ndarray:
    """
    Convert a binary visit matrix (segments x time) into popularity pmf p_i (sum_i p_i = 1),
    optionally averaging popularity over temporal windows.

    Parameters
    ----------
    visit_mat : np.ndarray of shape (n_segments, n_time), entries in {0,1}
    mode : {"count", "time_fraction"}
        "count":        p_i ∝ (# of visited time bins in the window)
        "time_fraction":p_i ∝ (#visited / window_length_in_steps) in each window.
        Both modes are normalized within each window to ensure sum_i p_i^{(w)} = 1.
    window_step : int or None
        Temporal window size in number of time steps.
        - If None: use the entire time horizon as one window (original behavior).
        - If an integer k: split the time axis into consecutive windows of length k.
          The last window may be shorter if T is not a multiple of k.

    Returns
    -------
    p : np.ndarray, shape (n_segments,), nonnegative and sums to 1
        The average popularity over all windows:
            p = (1 / n_windows) * sum_w p^{(w)}.
    """
    if visit_mat.ndim != 2:
        raise ValueError("visit_mat must be 2D (segments x time)")

    n_segments, T = visit_mat.shape

    if T == 0:
        # Degenerate case: no time dimension
        return np.ones(n_segments, dtype=float) / max(n_segments, 1)

    # If window_step is not specified or invalid, use full horizon as one window
    if window_step is None or window_step <= 0 or window_step >= T:
        window_step = T

    window_pop_list = []

    for start in range(0, T, window_step):
        end = min(start + window_step, T)
        sub_mat = visit_mat[:, start:end]  # shape: (n_segments, window_len)
        window_len = sub_mat.shape[1]

        # counts: number of visited time bins for each segment in this window
        counts = sub_mat.astype(float).sum(axis=1)  # 0..window_len

        if mode == "time_fraction":
            # Normalize by window length before turning into a pmf
            counts = counts / max(window_len, 1)

        total = float(counts.sum())
        # total = window_step

        if total <= 0:
            # No visits at all in this window -> fall back to uniform in this window
            p_w = np.zeros(n_segments, dtype=float) / max(T, 1)
        else:
            p_w = counts / total

        # # Numerical clean-up for this window
        # p_w = np.clip(p_w, 0.0, 1.0)
        # s_w = p_w.sum()
        # if s_w == 0:
        #     p_w[:] = 1.0 / len(p_w)
        # else:
        #     p_w /= s_w

        window_pop_list.append(p_w)
    # pop_list.append(window_pop_list)

        # If you really only want full windows and want to ignore a short tail,
        # you could break when end - start < window_step, but here we keep it.

    # Average popularity over all windows
    # if not window_pop_list:
    #     # Fallback: should not really happen, but keep it safe
    #     p = np.ones(n_segments, dtype=float) / max(n_segments, 1)
    # else:
    #     p = np.mean(window_pop_list, axis=0)
    # pop_list.append(window_pop_list)

    return window_pop_list


def Cnv_curve(Ns: int, B: float, p: np.ndarray, Nv_vals: Iterable[int]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorized evaluation of C_nv(Nv) for a sequence of Nv values.
    C_nv = 1 - (1/Ns) * sum_i (1 - p_i)^(B * Nv)

    Parameters
    ----------
    Ns : int
    B : float
    p : np.ndarray, shape (S,), pmf with sum=1
    Nv_vals : iterable of ints

    Returns
    -------
    Nv_arr, Cnv_arr
    """
    if Ns <= 0:
        raise ValueError("Ns must be positive.")
    p = np.asarray(p, dtype=float)
    p = np.mean(p, axis=0)
    if np.any(p < -1e-12) or not np.isfinite(p).all():
        raise ValueError("p must be finite and nonnegative.")
    # if not np.isclose(p.sum(), 1.0, atol=1e-8):
    #     raise ValueError("p must sum to 1.")

    Nv_arr = np.asarray(list(Nv_vals), dtype=float)  # shape (K,)
    one_minus_p = 1.0 - p[:, None]  # (S,1)
    exponents = (B * Nv_arr)[None, :]  # (1,K)
    terms = one_minus_p ** exponents  # (S,K)
    Cnv_arr = 1.0 - terms.sum(axis=0) / float(Ns)  # (K,)
    return Nv_arr, Cnv_arr


# ---------- Public plotting API (single or multiple curves) ----------

def plot_Cnv_curves(
        curves: List[Dict[str, Any]],
        *,
        mode: str = "count",
        figsize: Tuple[float, float] = (7.0, 4.5),
        dpi: int = 150,
        title: Optional[str] = r"Sensing Power($C_{nv}$) vs Number of CAV ($N_v$)",
        xlabel: str = r"Number of CAV ($N_v$)",
        ylabel: str = r"Sensing Power ($C_{nv}$)",
        legend: bool = True,
        grid: bool = True,
        save_path: Optional[str] = None,
        show: bool = True,
        check_ns_equals_segments: bool = False,
) -> List[Dict[str, Any]]:
    """
    Plot one or multiple C_nv(Nv) curves. Each curve config is a dict with:
        - "Ns": int
        - "B": float
        - "visit_mat": np.ndarray [n_segments, n_time] with entries in {0,1}
        - "Nv_vals": iterable of ints (e.g., range(0, 201))
        - "label": Optional[str]  (legend label)

    Parameters
    ----------
    curves : list of dicts
    mode : {"count","time_fraction"}  -> how to turn visit_mat into popularity pmf
    figsize, dpi, title, xlabel, ylabel, legend, grid : plotting options
    save_path : optional path to save the figure
    show : whether to call plt.show()
    check_ns_equals_segments : if True, assert Ns == n_segments

    Returns
    -------
    results : list of dicts, length == len(curves)
        For each curve: {
            "label": str,
            "Ns": int,
            "B": float,
            "Nv": np.ndarray,
            "Cnv": np.ndarray,
            "p": np.ndarray,           # popularity pmf used
            "n_segments": int,
            "n_time": int
        }
    """

    results: List[Dict[str, Any]] = []

    plt.figure(figsize=figsize, dpi=dpi)

    cmap = plt.get_cmap('tab10')

    pnp_ls = []

    for cfg in curves:

        # load occupation matrix
        Ns = int(cfg["Ns"])
        B = float(cfg["B"])
        visit_mat = np.asarray(cfg["visit_mat"])

        with open('../result/plot_ctm/CTMcell_index.json', 'r') as file:
            cell_idx = [line.strip() for line in file]
        cav_num = remove_branch(cell_idx, np.asarray(cfg["cav_num"]))[0]  # here is the full time cav number in cells
        # cav_num = remove_branch()
        Nv_vals = cfg["Nv_vals"]
        label = cfg.get("label", f"Ns={Ns}, B={B}")

        # get sensor power
        sensor_power = getSensorPower((cav_num[:,1:] > 0).astype(int), step_seconds=5, window_seconds=100)[:-1]  #
        # ncav_ls = np.sum(cav_num, axis=0)[1:]

        with open(cfg["ncav_list"], "rb") as f:
            ncav_ls = pickle.load(f)[:-1]

        if visit_mat.ndim != 2:
            raise ValueError("Each 'visit_mat' must be 2D (segments x time)")

        n_segments, n_time = visit_mat.shape
        if check_ns_equals_segments and Ns != n_segments:
            raise AssertionError(f"Ns ({Ns}) must equal number of segments ({n_segments}).")

        p = popularity_from_visit_matrix(visit_mat, mode=mode, window_step=720)  # p = popularity_from_visit_matrix((cav_num > 0).astype(int), mode=mode)
        pnp_ls.append(np.asarray(p, dtype=float))

        Nv_arr, Cnv_arr = Cnv_curve(Ns=Ns, B=B, p=p, Nv_vals=Nv_vals)
        print('begin to fit sensing power')
        # Nv_fit, Cnv_fit, B_fit, C_lo, C_hi = fit_sensing_power_curve(Nv=ncav_ls, C=sensor_power, p=p, nv_ls=Nv_vals)
        # B_ls.append(B_fit)

        color = cmap(curves.index(cfg)%cmap.N)
        plt.plot(Nv_arr, Cnv_arr, linewidth=1, label=label, color=color)  # sensing power model curve
        # plt.scatter(ncav_ls, sensor_power, color=color, s=30, label=f'Empirical {label}')  # sensing power scatter plot
        # plt.plot(Nv_fit, Cnv_fit, color=color, linewidth=2, label=f"Sensing power curve {label}")  # sensing power fit curve
        # plt.fill_between(Nv_fit, C_lo, C_hi, alpha=0.2, label="95% confidence band")  # confident band for fit curve

        results.append({
            "label": label,
            "Ns": Ns,
            "B": B*80,
            "Nv": Nv_arr,
            "Cnv": Cnv_arr,
            "p": p,
            "n_segments": n_segments,
            "n_time": n_time,
            "_color": color,
        })

    # --- Print ranking: highest to lowest by end-of-line Cnv value ---
    ranked = sorted(results, key=lambda r: r["Cnv"][-1], reverse=True)
    print("\n[Curve ranking by final Cnv value (highest -> lowest)]")
    for rank, r in enumerate(ranked, 1):
        print(f"  {rank}. {r['label']:30s}  Cnv_end={r['Cnv'][-1]:.4f}")

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    if title:
        plt.title(title)
    if grid:
        plt.grid(True, linestyle="--", alpha=0.6)
    if legend and len(curves) > 1:
        plt.legend(loc=4, fontsize=6)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches="tight", pad_inches=0.02)
    if show:
        plt.show()

    return results, pnp_ls


def getSensorPower(M, step_seconds=5, window_seconds=5):
    """
    Compute sensing power every fixed time window using the definition-based covering fraction.

    Parameters:
        M : numpy array, shape = (n_segments, n_timesteps)
            0/1 matrix representing whether a segment is detected at each time.
        step_seconds : int
            Duration of each time step (default 5 seconds).
        window_seconds : int
            Duration of each evaluation window (default 100 seconds).

    Returns:
        list of floats:
            Sensing power for each window.
    """

    n_segments, n_timesteps = M.shape

    # 每个窗口多少列
    steps_per_window = window_seconds // step_seconds  # = 20

    sensing_list = []

    # 遍历每个窗口
    for start in range(0, n_timesteps, steps_per_window):
        end = min(start + steps_per_window, n_timesteps)

        # 当前窗口的子矩阵: (n_segments, window_steps)
        subM = M[:, start:end]

        # 对每个 segment，看这一窗口内是否至少有一次被访问过
        # covered_per_segment: shape (n_segments,), bool
        covered_per_segment = (subM.sum(axis=1) > 0)

        # 这一窗口的覆盖率 = 被覆盖的segment数 / 总segment数
        C_window = covered_per_segment.mean()  # True/False 会自动转成 1/0

        sensing_list.append(float(C_window))

    return sensing_list


def plot_cav_time_boxplots(
        cases: Dict[str, Dict[str, Dict[str, str]]],
        save_dir: Optional[str] = None,
        show: bool = True,
):
    """
    Plot boxplots of CAV number and solving time for each category and case.

    """
    categories = []
    cav_by_cat = []
    time_by_cat = []

    # 1. Aggregate data for each category
    for category, case_dict in cases.items():
        if not case_dict:
            continue

        cav_list = []
        time_list = []

        for case_name, paths in case_dict.items():
            cav_path = paths.get("cav")
            time_path = paths.get("time")

            if cav_path is None or time_path is None:
                raise ValueError(
                    f"Case '{case_name}' in category '{category}' must "
                    f"have both 'cav' and 'time' paths."
                )

            with open(cav_path, "rb") as f:
                cav = pickle.load(f)
            with open(time_path, "rb") as f:
                t = pickle.load(f)

            cav = np.asarray(cav).ravel()
            t = np.asarray(t).ravel()

            cav_list.append(cav)
            time_list.append(t)

        # Concatenate all cases for this category
        cav_cat = np.concatenate(cav_list, axis=0)
        time_cat = np.concatenate(time_list, axis=0)

        categories.append(category)
        cav_by_cat.append(cav_cat)
        time_by_cat.append(time_cat)

    if not categories:
        raise ValueError("No valid categories found in 'cases'.")

    n_cat = len(categories)
    x_center = np.arange(n_cat) + 1  # 1..n_cat
    x_text = [r"$2\%$", r"$5\%$", r"$10\%$"]
    offset = 0.18

    # 2. Create figure with twin y-axes
    fig, ax1 = plt.subplots(figsize=(1.8 * n_cat + 3, 6))
    ax2 = ax1.twinx()

    # Positions for CAV and time boxes
    x_cav = x_center - offset
    x_time = x_center + offset

    # 3. Boxplots
    # CAV number on left axis
    bp_cav = ax1.boxplot(
        cav_by_cat,
        positions=x_cav,
        widths=0.3,
        showmeans=True,
        patch_artist=True,
    )

    # Solving time on right axis
    bp_time = ax2.boxplot(
        time_by_cat,
        positions=x_time,
        widths=0.3,
        showmeans=True,
        patch_artist=True,
    )

    # 4. Color settings (different colors for the two metrics)
    # (You can customize these colors if you like.)
    cav_color = "tab:blue"
    time_color = "tab:orange"

    for patch in bp_cav["boxes"]:
        patch.set_facecolor(cav_color)
        patch.set_alpha(0.5)
    for patch in bp_time["boxes"]:
        patch.set_facecolor(time_color)
        patch.set_alpha(0.5)

    # Also color the mean markers/lines for clarity (optional)
    for element in ["medians", "means", "whiskers", "caps"]:
        for line in bp_cav[element]:
            line.set_color(cav_color)
        for line in bp_time[element]:
            line.set_color(time_color)

    # 5. Axis labels and ticks
    ax1.set_xlabel("Penetration Rate")
    ax1.set_ylabel("CAV number", color=cav_color)
    ax2.set_ylabel("Solving time(s)", color=time_color)

    ax1.set_xticks(x_center)
    ax1.set_xticklabels(categories, rotation=0)

    # 6. Annotate mean values
    for x, cav_arr in zip(x_cav, cav_by_cat):
        mean_cav = int(float(np.mean(cav_arr)))
        ax1.text(
            x,
            mean_cav,
            f"{mean_cav:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color=cav_color,
        )

    for x, time_arr in zip(x_time, time_by_cat):
        mean_time = int(float(np.mean(time_arr)))
        ax2.text(
            x,
            mean_time,
            f"{mean_time:.3g}",
            ha="center",
            va="bottom",
            fontsize=8,
            color=time_color,
        )

    # 7. Legend
    cav_handle = bp_cav["boxes"][0]
    time_handle = bp_time["boxes"][0]
    ax1.legend(
        [cav_handle, time_handle],
        ["CAV number", "Solving time"],
        loc="upper left",
    )

    fig.suptitle("CAV number and solving time by category", y=0.97)
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])

    # 8. Save / show
    if save_dir is not None:
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_dir) or ".", exist_ok=True)
        fig.savefig(save_dir, dpi=300, bbox_inches="tight")
    else:
        fig.savefig(save_dir, dpi=300, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)


def fit_sensing_power_curve(Nv, C, p, nv_ls, num_points: int = 300, ci_alpha=0.05, rel_step=0.1):
    """
    Weighted Least Squares fitting for better handling of heterogeneous data.

    Parameters:
    -----------
    Nv : list, length 53
    C : list, length 53
    p : array, shape (36, 760)
    nv_ls : iterable for fitted curve range
    num_points : int, number of points in fitted curve
    ci_alpha : float, confidence level
    rel_step : float, relative step for finite difference

    Returns:
    --------
    Nv_fit, C_fit, gamma_best, C_lower, C_upper
    """
    # Take last 35 points of C and Nv, first 35 groups of p
    Nv_data = np.asarray(Nv[-35:], dtype=float)
    C_data = np.asarray(C[-35:], dtype=float)
    p_data = np.asarray(p, dtype=float)[:35, :]
    p_data = np.clip(p_data, 0.0, 0.999999)

    n_groups = len(Nv_data)

    def model_C_single(Nv_val, p_vec, gamma):
        """Model for single group"""
        return 1.0 - np.mean((1.0 - p_vec) ** (gamma * Nv_val))

    # Residual function for least_squares
    def residuals(gamma):
        res = np.zeros(n_groups)
        for i in range(n_groups):
            pred = model_C_single(Nv_data[i], p_data[i], gamma[0])
            res[i] = pred - C_data[i]
        return res

    # Use scipy's least_squares for robust optimization
    gamma_init = 0.5
    result = least_squares(residuals, [gamma_init], bounds=([1e-6], [100.0]))
    gamma_best = result.x[0]

    # Generate fitted curve using average p
    Nv_arr = np.asarray(list(nv_ls), dtype=float)
    Nv_fit = np.linspace(Nv_arr.min(), Nv_arr.max(), num_points)
    p_mean = np.mean(p_data, axis=0)
    C_fit = np.array([model_C_single(n, p_mean, gamma_best) for n in Nv_fit])

    # Confidence interval using Jacobian from least_squares
    J = result.jac
    residual_var = np.sum(result.fun ** 2) / (n_groups - 1)
    # Check for singular matrix and use robust estimation
    try:
        JtJ = J.T @ J
        # Add small regularization to avoid singularity
        JtJ_reg = JtJ + 1e-8 * np.eye(JtJ.shape[0])
        cov_matrix = residual_var * np.linalg.inv(JtJ_reg)
        se_gamma = np.sqrt(max(cov_matrix[0, 0], 0))

        t_crit = stats.t.ppf(1 - ci_alpha / 2, n_groups - 1)
        gamma_low = max(gamma_best - t_crit * se_gamma, 1e-8)
        gamma_high = gamma_best + t_crit * se_gamma
    except np.linalg.LinAlgError:
        # Fallback: use finite difference method
        print("[WLS] Warning: Singular Jacobian, using finite difference CI")
        h = rel_step * gamma_best if gamma_best > 0 else rel_step

        def loss_fn(g):
            return np.sum(residuals([g]) ** 2)

        L0 = loss_fn(gamma_best)
        L_plus = loss_fn(gamma_best + h)
        L_minus = loss_fn(max(gamma_best - h, 1e-8))

        Lpp = (L_plus - 2.0 * L0 + L_minus) / (h ** 2)

        if Lpp > 0:
            var_gamma = 2.0 * residual_var / Lpp
            se_gamma = np.sqrt(max(var_gamma, 0))
            t_crit = stats.t.ppf(1 - ci_alpha / 2, n_groups - 1)
            gamma_low = max(gamma_best - t_crit * se_gamma, 1e-8)
            gamma_high = gamma_best + t_crit * se_gamma
        else:
            # If all else fails, use bootstrap percentile
            gamma_low = gamma_best * 0.8
            gamma_high = gamma_best * 1.2
            print("[WLS] Warning: CI estimation failed, using ±20% range")

    C_lower = np.array([model_C_single(n, p_mean, gamma_low) for n in Nv_fit])
    C_upper = np.array([model_C_single(n, p_mean, gamma_high) for n in Nv_fit])

    print(f"[WLS] Optimal gamma: {gamma_best:.6f}")
    print(f"[WLS] 95% CI: [{gamma_low:.6f}, {gamma_high:.6f}]")
    print(f"[WLS] RMSE: {np.sqrt(np.mean(result.fun ** 2)):.6f}")

    return Nv_fit, C_fit, gamma_best, C_lower, C_upper


def plot_p_distribution(
    p: np.ndarray,
    title: str,
    save_dir: str,
    num_bins: int = 30,
    y_lim: tuple = (0, 400)
):
    """
    Plot the value-based frequency distribution of probability array p.

    Parameters
    ----------
    p : np.ndarray
        Probability array with shape (1, 760) or (760,).
        Values are expected to sum to 1.
    title : str
        Title of the plot.
    save_dir : str
        Directory to save the figure.
    num_bins : int, optional
        Number of bins for value-based distribution.
    """

    # Ensure p is a 1D array
    p = np.asarray(p).squeeze()
    assert p.ndim == 1, "Input p must be a 1D array after squeeze."

    # Normalize to avoid numerical drift
    p_sum = np.sum(p)
    if not np.isclose(p_sum, 1.0):
        p = p / p_sum

    # Compute histogram (value-based distribution)
    counts, bin_edges = np.histogram(p, bins=num_bins)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_width = bin_edges[1] - bin_edges[0]

    # Plot as bar chart
    plt.figure(figsize=(8, 4))
    plt.bar(bin_centers, counts, width=bin_width, align="center")
    plt.xlabel("p value")
    plt.ylabel("Frequency")
    plt.title(title)

    plt.ylim(y_lim)

    # Save figure
    # os.makedirs(save_dir, exist_ok=True)
    # save_path = os.path.join(save_dir, "p_value_distribution.png")
    save_path = save_dir

    # plt.tight_layout()
    # plt.show()
    plt.savefig(save_path, dpi=300)
    # plt.close()