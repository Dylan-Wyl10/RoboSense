"""
Date: June 13, 2023
Author: Yilin Wang
Note: script file for useful links.
List:
1. gen_LF_table(): generate a blank table to restore the travel information for each link.
2. update_LF_table(): update link-flow table
"""

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
from sklearn.metrics import mean_squared_error

from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict, Counter

from matplotlib.collections import LineCollection



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
        labels = [f"Dataset {i+1}" for i in range(len(arrays))]

    colors = ['red', 'yellow', 'red', 'blue', 'purple']
    plt.figure(figsize=(10, 6))

    # Collect all occupancy sums to determine shared bin range
    all_occupancies = []
    occ_per_dataset = []
    start, end = time_range[0]//5, time_range[1]//5

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

    def ctmPlot(self, ctm_value, cell_list, cell_coordinates, title_str, save_path=None, mode='numpy', plot='video', eval_start=0, eval_duration=0):
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
                time_range=(eval_start//5, eval_duration//5)
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
        start_idx = eval_start//5 + 1
        bench_occnp = np.load(bench_occ)[:, start_idx:start_idx + eval_duration//5]
        ctm_occnp = np.load(ctm_occ)[:, start_idx:start_idx + eval_duration//5]
        bench_occ_bin = (bench_occnp > 0).astype(int)
        ctm_occ_bin = (ctm_occnp > 0).astype(int)
        bench_decay = self.apply_temporal_decay(bench_occ_bin)
        ctm_decay = self.apply_temporal_decay(ctm_occ_bin)
        score1 = np.mean(bench_decay)
        score2 = np.mean(ctm_decay)

        sum_ben = np.sum(bench_occnp)
        sum_ctm = np.sum(ctm_occnp)

        result = {'bench occu score': score1,
                  'optim occu score': score2,
                  'bench tt sum': sum_ben,
                  'optim occu sum': sum_ctm}

        # plot_time_space_heatmap(bench_decay)
        # plot_time_space_heatmap(ctm_decay)
        # print('a')
        return result

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

            # Filter by time window
            if depart > eval_start and arrival < eval_end:
                if vtype not in result:
                    result[vtype] = []

                result[vtype].append({
                    "id": veh_id,
                    "duration": duration,
                    "routeLength": route_length
                })

        # Summary stats
        summary = {}
        for vtype, records in result.items():
            total_duration = sum(r['duration'] for r in records)
            total_length = sum(r['routeLength'] for r in records)
            count = len(records)

            avg_duration = total_duration / count if count > 0 else 0
            avg_route_length = total_length / count if count > 0 else 0

            summary[vtype] = {
                "avg_duration": avg_duration,
                "avg_routeLength": avg_route_length,
                "vehicle_count": count
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
        mat_1r = np.load(file_gt)[:, start_idx:start_idx + eval_duration//5]
        mat_2r = np.load(file_rec)[:, start_idx:start_idx + eval_duration//5]

        # plot_time_space_heatmap(mat1)
        # plot_time_space_heatmap(mat2)

        mat1, b = remove_C0(cell_json, mat_1r)
        mat2, b = remove_C0(cell_json, mat_2r)

        sm1 = np.sum(mat1)
        sm2 = np.sum(mat2)

        if vis:
            plot_time_space_heatmap(mat1)
            plot_time_space_heatmap(mat2)


        if mat1.shape != mat2.shape:
            raise ValueError(f"Shape mismatch: {mat1.shape} vs {mat2.shape}")

        if method == "mse":
            return mean_squared_error(mat1.flatten(), mat2.flatten())

        elif method == "cosine":
            # reshape to (n_samples, n_features)
            return cosine_similarity(mat1.reshape(1, -1), mat2.reshape(1, -1))[0][0]

        elif method == "correlation":
            return np.corrcoef(mat1.flatten(), mat2.flatten())[0, 1]

        elif method == "mape":
            non_zero_mask = mat1 != 0
            if not np.any(non_zero_mask):
                return np.nan  # or raise an error if preferred
            return np.mean(np.abs((mat1[non_zero_mask] - mat2[non_zero_mask]) / mat1[non_zero_mask])) * 100

        # note: add mape

        else:
            raise ValueError(f"Unknown method '{method}'. Choose from 'mse', 'cosine', or 'correlation'.")

    import numpy as np

    @staticmethod
    def evaluate_distribution_balance(occ_path, eval_start, eval_duration,):
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

def remove_C0(json_path, ctm_matrix):
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

    with open(json_path, 'r') as file:
        cell_data = [line.strip() for line in file]

    # Assume the cell names are in a list or dict → extract name list
    if isinstance(cell_data, list):
        cell_names = cell_data
    elif isinstance(cell_data, dict):
        cell_names = list(cell_data.values())
    else:
        raise ValueError("Unsupported JSON structure. Expecting list or dict of cell names.")

    # Find indices where name ends with 'C0'
    c0_indices = [i for i, name in enumerate(cell_names) if str(name).endswith("C0")]

    # Remove corresponding rows from matrix
    filtered_matrix = np.delete(ctm_matrix, c0_indices, axis=0)

    return filtered_matrix, c0_indices


def plot_cav_duration_histogram(
    data_list,
    labels=None,
    attribute="duration",
    bins=30,
    title="Travel Duration Distribution (CAV)",
    save_path=None
):
    """
    Plot overlapping histograms of CAV durations with shared bin edges and color blending.

    Parameters:
    - data_list: list of dicts, each with key 'cav' mapping to list of dicts with 'duration'
    - labels: list of str, labels for each dataset
    - bins: int, number of histogram bins
    - title: str, plot title
    - save_path: str or None, if set, saves the figure
    """
    if labels is None:
        labels = [f"Dataset {i+1}" for i in range(len(data_list))]

    # Use base RGB color tuples for better blending
    base_colors = [(0, 0, 1.0),  # blue
                   (1.0, 0.8, 0.2),  # yellow
                   (0.1, 1.0, 0.1)]  # green (if needed for third)

    plt.figure(figsize=(10, 6))

    # Collect all durations to determine global bin edges
    all_durations = []
    durations_per_dataset = []

    for data in data_list:
        durations = [entry[attribute] for entry in data["cav"] if attribute in entry]
        durations_per_dataset.append(durations)
        all_durations.extend(durations)

    durations_per_dataset[1] = durations_per_dataset[1][:len(durations_per_dataset[0])]

    # Define global bin edges
    min_dur, max_dur = min(all_durations), max(all_durations)
    bin_edges = np.linspace(min_dur, max_dur, bins + 1)

    # Draw each histogram with alpha for blending effect
    for i, durations in enumerate(durations_per_dataset):
        plt.hist(
            durations,
            bins=bin_edges,
            alpha=0.5,  # semi-transparent for blending
            label=labels[i],
            color=base_colors[i % len(base_colors)],
            edgecolor='black'
        )

    # plt.xlabel(f"CAV {attribute}")
    plt.ylabel(r"Number of Vehicles", fontsize=19)
    if attribute == "routeLength":
        plt.xlabel(r"CAV Travel Distance ($\mathrm{m}$)", fontsize=19)
        plt.xlim(1500, 8000)
    elif attribute == "duration":
        plt.xlabel(r"CAV Travel Time ($\mathrm{s}$)", fontsize=19)
        plt.xlim(0, 2000)
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
        ax.set_title(title, fontsize=label_fontsize+6)
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