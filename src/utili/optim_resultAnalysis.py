import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.colors import LinearSegmentedColormap, Normalize

x = np.load('../../result/middle_result0520/x_tmp.npy')
y = np.load('../../result/middle_result0520/y_tmp.npy')
omg = np.load('../../result/middle_result0520/omg_tmp.npy')

cellidx = ['A1.E101.C0', 'A1.E101.C4', 'A1.E101.C5', 'A1.E101.C6', 'A1.E101.C7',
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

veh_od = {0: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 0},
          1: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 0},
          2: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 1},
          3: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 3},
          4: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 5},
          5: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 9},
          6: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 60},
          7: {'from': cellidx.index('A1.E101.C0'),
              'to': cellidx.index('A1.-E120.C0'),
              'time': 60},
          }

omg_suma = np.sum(omg, axis=0)


def plot_occupancy_3d(state_matrix, cellidx, save_path=None):
    """
    Plot a 3D bar chart of node occupancy/value using green-yellow-red gradient,
    with enhanced styling and automatic label spacing.

    Parameters:
    - state_matrix: np.ndarray (num_nodes, num_timesteps), continuous or binary values
    - cellidx: list of node identifiers (length == num_nodes)
    - save_path: optional path to save high-resolution PNG image
    """
    num_nodes, num_timesteps = state_matrix.shape
    assert len(cellidx) == num_nodes, "cellidx length must match number of nodes"

    fig_height = max(6, num_nodes / 20)
    fig = plt.figure(figsize=(16, fig_height))
    ax = fig.add_subplot(111, projection='3d')

    # Prepare data for 3D bars
    _x = np.arange(num_timesteps)
    _y = np.arange(num_nodes)
    _xx, _yy = np.meshgrid(_x, _y)
    x, y = _xx.ravel(), _yy.ravel()
    z = np.zeros_like(x)
    dz = state_matrix.ravel()

    norm = Normalize(vmin=np.min(dz), vmax=np.max(dz))
    green_red_cmap = LinearSegmentedColormap.from_list("GreenRed", ["green", "yellow", "red"])
    colors = green_red_cmap(norm(dz))

    dx = dy = 0.9
    ax.bar3d(x, y, z, dx, dy, dz, color=colors, alpha=0.9, edgecolor='k', linewidth=0.2)

    ax.set_xlabel('Time Step', labelpad=10, fontsize=12)
    ax.set_ylabel('Node Index', labelpad=10, fontsize=12)
    ax.set_zlabel('Value', labelpad=10, fontsize=12)
    ax.set_title('3D Occupancy Normalized / Value Map (Green → Red)', fontsize=14)

    # Intelligent Y-axis label spacing
    max_labels = 30
    if num_nodes <= max_labels:
        yticks = np.arange(num_nodes)
    else:
        skip = max(1, num_nodes // max_labels)
        yticks = np.arange(0, num_nodes, skip)

    ax.set_yticks(yticks)
    ax.set_yticklabels([cellidx[i] for i in yticks], fontsize=10, rotation=0,
                       verticalalignment='center', horizontalalignment='right')
    ax.tick_params(axis='y', pad=5)
    ax.view_init(elev=25, azim=135)

    mappable = plt.cm.ScalarMappable(cmap=green_red_cmap, norm=norm)
    mappable.set_array(dz)
    cbar = plt.colorbar(mappable, shrink=0.5, pad=0.1)
    cbar.set_label('Value Intensity (Green → Red)', fontsize=10)

    plt.tight_layout()

    if save_path:
        dir_path = os.path.dirname(save_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved 3D occupancy map to {save_path}")
    else:
        plt.show()


def getRouteFromX(cellidx, veh_od, x):
    # cell_idx = self.cellidx
    # input x: [veh, link, time]
    veh_rt = {}
    for a in range(x.shape[0]):
        rt = []
        for t in range(x.shape[2]):
            for i in range(x.shape[1]):
                if (x[a, i, t] == 1 and i != veh_od[a]['to']):
                    rt.append(cellidx[i])
        veh_rt[a] = rt
    return veh_rt


tt = range(0, 3)
for t in tt:
    print(t)

plot_occupancy_3d(y, cellidx, save_path="occupancy_3d.png")
route_list = getRouteFromX(cellidx, veh_od, x)

print('end')
