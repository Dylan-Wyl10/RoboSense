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
def CTM_visulization(time_id_matrix_path, cell_coordinates):  # the inputs are file_directory
    """
    :param time_id_matrix:(data-frame) dataframe with time-space number for the cells.
    :param cell_coordinates:network tepology, read as adictionary.
    """

    time_id_matrix = pd.read_csv(time_id_matrix_path)
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
            cell_index = time_id_matrix[time_id_matrix['Unnamed: 0'] == cell_id].index[0]
            vehicle_number = time_id_matrix.iloc[cell_index, frame + 1]
            # color = cmap(norm(vehicle_number))
            # rect.set_facecolor(color)
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
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f'../result/ctmResult/urban_network_traffic_with_timestep1_{current_time}.mp4'
    ani.save(file_name, writer=writer)

    plt.close(fig)  # Close the plot to prevent it from displaying in the notebook

    # print('urban_network_traffic_with_timestep_new1.mp4')

    # return '/mnt/data/urban_network_traffic_with_timestep.mp4'

