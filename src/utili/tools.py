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
from matplotlib.colors import LinearSegmentedColormap
from datetime import datetime
from matplotlib import cm
from matplotlib.colors import Normalize

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

    # time_id_matrix = pd.read_csv(time_id_matrix_path)
    time_id_matrix = time_id_df
    cell_coordinates_df = pd.read_csv('../sumo_cfg/5x5net/CTMcfg/Cells.csv')
    cell_coordinates = cell_coordinates_df.set_index('cell_id').T.to_dict('list')

    cdict = {'red': ((0.0, 0.0, 0.0),
                     (1.0, 1.0, 1.0)),
             'green': ((0.0, 1.0, 1.0),
                       (1.0, 0.0, 0.0)),
             'blue': ((0.0, 0.0, 0.0),
                      (1.0, 0.0, 0.0))}

    green_to_red = LinearSegmentedColormap('GreenToRed', cdict)

    x_values = [coord[0] for coord in cell_coordinates.values()]
    y_values = [coord[1] for coord in cell_coordinates.values()]

    x_min, x_max = min(x_values) - 0.5, max(x_values) + 0.5
    y_min, y_max = min(y_values) - 0.5, max(y_values) + 0.5

    # Normalize vehicle numbers for color mapping
    vehicle_numbers = time_id_matrix.iloc[:, 1:].to_numpy().flatten()
    norm = plt.Normalize(vmin=0, vmax=max(vehicle_numbers))
    # cmap = plt.cm.viridis

    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)

    # Plot non-contiguous rectangles for each cell
    rect_size = 0.45  # Fixed size for all rectangles
    rectangles = []
    annotations = []
    for cell_id, (x, y) in cell_coordinates.items():
        rect = plt.Rectangle((x - rect_size / 2, y - rect_size / 2), rect_size, rect_size, fill=True, edgecolor='white')
        rectangles.append(rect)
        ax.add_patch(rect)

        # Add cell ID annotation
        annotation = ax.text(x, y, cell_id.split('.')[-1][1:], ha='center', va='center', fontsize=6, color='black')
        annotations.append(annotation)

    time_text = ax.text(0.5, 1.05, '', transform=ax.transAxes, ha='center')

    def update(frame):
        for rect, cell_id in zip(rectangles, cell_coordinates.keys()):
            if cell_id not in time_id_matrix.index:
                continue
            vehicle_number = time_id_matrix.loc[cell_id].iloc[frame]
            color = green_to_red(norm(vehicle_number))
            rect.set_facecolor(color)
        time_text.set_text(f'Time Step: {frame+1}')
        return rectangles + [time_text]


    ani = animation.FuncAnimation(fig, update, frames=range(len(time_id_matrix.columns) - 1), interval=500, blit=True)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')

    # Add color bar
    sm = plt.cm.ScalarMappable(cmap=green_to_red, norm=norm)
    sm.set_array([])
    plt.colorbar(sm, ax=ax, orientation='vertical', label='Number of Vehicles')

    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=2, metadata=dict(artist='Me'), bitrate=1800)

    # Save the animation as a video file
    if save_path is None:

        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f'../result/ctmResult/logs/ctm_test1/urban_network_traffic_with_timestep1_{current_time}.mp4'
    else:
        file_name = save_path
    ani.save(file_name, writer=writer)

    plt.close(fig)  # Close the plot to prevent it from displaying in the notebook

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