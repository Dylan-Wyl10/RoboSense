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
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime
from matplotlib import cm
from matplotlib.colors import Normalize
import xml.etree.ElementTree as ET
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import mean_squared_error


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

def CTM_static_visulization(time_id_df, cell_coordinates_path, save_path=None):
    """
    Draw static plot of CTM: sum over time for each cell.
    Cell with 0 → white; Cell with >0 → color map from green to red.

    :param time_id_df: DataFrame, indexed by cell_id, columns as time steps.
    :param cell_coordinates_path: str, path to Cells.csv (with cell_id, x, y).
    :param save_path: str or None, save path for image.
    """
    # Load cell coordinates
    cell_coordinates_df = pd.read_csv(cell_coordinates_path)
    cell_coordinates = cell_coordinates_df.set_index('cell_id').T.to_dict('list')

    # Sum over time
    vehicle_sums = time_id_df.sum(axis=1)

    # Normalize over non-zero values
    non_zero_vals = vehicle_sums[vehicle_sums > 0]
    vmin, vmax = non_zero_vals.min(), non_zero_vals.max()
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap('RdYlGn_r')  # good contrast from green to red

    # Plot
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    rect_size = 0.45

    for cell_id, (x, y) in cell_coordinates.items():
        sum_val = vehicle_sums.get(cell_id, 0)

        if sum_val == 0:
            face_color = '#FFFFFF'  # white for 0
            edge_color = 'black'
        else:
            face_color = cmap(norm(sum_val))
            edge_color = 'white'

        rect = plt.Rectangle((x - rect_size / 2, y - rect_size / 2),
                             rect_size, rect_size,
                             facecolor=face_color, edgecolor=edge_color)
        ax.add_patch(rect)

        ax.text(x, y, cell_id.split('.')[-1][1:], ha='center', va='center',
                fontsize=6, color='black')

    # Add colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array(non_zero_vals)
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', label='Sum of Vehicle Numbers (per cell)')

    # Layout
    ax.set_aspect('equal')
    ax.set_title("CTM Total Vehicle Count per Cell (Summed Over Time)")

    x_vals = [v[0] for v in cell_coordinates.values()]
    y_vals = [v[1] for v in cell_coordinates.values()]
    ax.set_xlim(min(x_vals) - 0.5, max(x_vals) + 0.5)
    ax.set_ylim(min(y_vals) - 0.5, max(y_vals) + 0.5)

    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
    else:
        plt.show()

    plt.close()

class Pipline:
    def __init__(self):
        return

    def ctmPlot(self, ctm_value, cell_list, cell_coordinates, save_path=None, mode='numpy', plot='video'):
        if mode == 'numpy':
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
            CTM_static_visulization(time_id_df, cell_coordinates, save_path=save_path)

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
    def evalTripInfo(trip_info):
        """
            Parse SUMO tripinfo XML file and extract vehicle stats by vType.

            Args:
                file_path (str): Path to the tripinfo XML file.

            Returns:
                dict: Dictionary with vType as key, each containing a list of dictionaries
                      with 'id', 'duration', and 'routeLength'.
            """
        tree = ET.parse(trip_info)
        root = tree.getroot()

        result = {}

        for trip in root.findall("tripinfo"):
            veh_id = trip.get("id")
            vtype = trip.get("vType")
            duration = float(trip.get("duration"))
            route_length = float(trip.get("routeLength"))

            if vtype not in result:
                result[vtype] = []

            result[vtype].append({
                "id": veh_id,
                "duration": duration,
                "routeLength": route_length
            })

            # get summarized result
            summary = {}

            for vtype, records in result.items():
                total_duration = sum(r['duration'] for r in records)
                total_length = sum(r['routeLength'] for r in records)
                count = len(records)

                if count > 0:
                    avg_duration = total_duration / count
                    avg_route_length = total_length / count
                else:
                    avg_duration = 0
                    avg_route_length = 0

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