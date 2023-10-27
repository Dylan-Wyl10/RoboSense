"""
Date: Sept 28, 2023,
Author: Yilin Wang
Note:
    - this script is used for analysis on traffic log to figure out the details on the operation on CAVs via different parameters.
List:
"""

import numpy as np
import xml.dom.minidom
import os
from itertools import groupby

def analysisTrip(trip_file):
    print(trip_file)


import xml.etree.ElementTree as ET


def analysisTrip(file_paths):
    """
    Combine trip information from multiple XML files into two dictionaries,
    one for each vehicle type (CAV and regular vehicle), organized by vehicle ID.

    Parameters:
    - file_paths (list of str): List of paths to the XML files

    Returns:
    - tuple of dict: Combined trip information for CAVs and regular vehicles,
                     organized by vehicle ID
    """
    cav_data = {}
    vehicle_data = {}

    for file_path in file_paths:
        tree = ET.parse(file_path)
        root = tree.getroot()

        for trip in root.findall('tripinfo'):
            trip_attrib = trip.attrib
            vehicle_id = trip_attrib['id']

            if "cav" in vehicle_id.lower():
                if vehicle_id not in cav_data:
                    cav_data[vehicle_id] = []
                cav_data[vehicle_id].append(trip_attrib)
            else:
                if vehicle_id not in vehicle_data:
                    vehicle_data[vehicle_id] = []
                vehicle_data[vehicle_id].append(trip_attrib)

    return cav_data, vehicle_data


def extract_attributes(data, attributes):
    """
    Extract specified attributes from the trip data.

    Parameters:
    - data (dict): The original data, organized by vehicle ID
    - attributes (list of str): The attributes to extract

    Returns:
    - dict: Extracted data, organized by vehicle ID
    """
    extracted_data = {}
    for vehicle_id, trips in data.items():
        extracted_data[vehicle_id] = []
        for trip in trips:
            extracted_trip = {attr: trip[attr] for attr in attributes if attr in trip}
            extracted_data[vehicle_id].append(extracted_trip)
    return extracted_data


def combine_vehicle_paths(matrix_list):
    """
    Extract list of link indices for each vehicle ID from a list of
    3D NumPy matrices indexed by [link][time][vehicle]. Provides separate
    paths per scenario for each vehicle.

    Parameters:
    - matrix_list (list of numpy.ndarray): List of 3D NumPy matrices
      indicating vehicle presence. Indexed by [link][time][vehicle].

    Returns:
    - dict: Dictionary where each key is a vehicle ID and each value
      is a list of paths, each path corresponding to a different input matrix.
    """
    combined_paths = {}

    for scenario_index, np_matrix in enumerate(matrix_list):
        num_links, num_times, num_vehicles = np_matrix.shape

        for vehicle in range(num_vehicles):
            if vehicle not in combined_paths:
                combined_paths[vehicle] = []

            # Add a new path list for the current scenario
            combined_paths[vehicle].append([])
            tmp = []

            for time in range(num_times):
                for link in range(num_links):
                    if np_matrix[link, time, vehicle] == 1:
                        tmp.append(link+1)  # sumo link index starts from 1 while matrix starts form zero
                        # combined_paths[vehicle][scenario_index].append(link)
            combined_paths[vehicle][scenario_index] = [key for key, group in groupby(tmp)]
            # print('yes')

    return combined_paths


def write_to_txt(combined_paths, filename="vehicle_paths.txt"):
    with open(filename, "w") as file:
        file.write("Combined Vehicle Paths:\n")
        for vehicle_id, paths in combined_paths.items():
            file.write(f"Vehicle {vehicle_id}:\n")
            for scenario_index, path in enumerate(paths):
                path_str = ", ".join(map(str, path))
                file.write(f"  Scenario {scenario_index}: {path_str}\n")



if __name__ == '__main__':

    current_directory = os.getcwd()
    print(f"Current Working Directory: {current_directory}")

    alpha_set = [0, 100, 300, 500, 1000, 2000]
    pr = 2
    step = 20
    vehicle_path = "vehicle_paths.txt"

    ## this part
    tripFile_dir = {}
    tripFile_dir['trip_bench'] = "../result/sumolog_pr{}/tripinfo_benchmark.xml".format(pr)
    for a in alpha_set:
        tripFile_dir['trip_{}'.format(a)] = "../result/sumolog_pr{}/tripinfo{}.xml".format(pr, a)

    # Example Usage
    file_paths = [tripFile_dir[k] for k in tripFile_dir.keys()]
    cav_data, vehicle_data = analysisTrip(file_paths)

    # Specify attributes to extract
    attributes_to_extract = ["duration", "rerouteNo", "routeLength"]

    # Extract attributes from cav_data
    extracted_cav_data = extract_attributes(cav_data, attributes_to_extract)

    print('yesyes')

    # start from generate path
    path_senario = "PR2 TestingNew"

    covermatrix_path = ['../result/{}/pr{}_cover_{}_step20.npy'.format(path_senario, pr, a) for a in alpha_set]
    covermatrix_path.append('../result/{}/pr{}_cover_benchmark.npy'.format(path_senario, pr))

    covermatrix_list = [np.load(p) for p in covermatrix_path]

    tmp = [cvm[:, :, 84] for cvm in covermatrix_list]  # the number is vehicle index number
    vehicle_paths = combine_vehicle_paths(covermatrix_list)
    write_to_txt(vehicle_paths, filename=vehicle_path)






    # Output example data
    # print("CAV Vehicles:")
    # for vehicle_id, trips in list(cav_data.items())[:5]:
    #     print(f"\nVehicle ID: {vehicle_id}")
    #     for i, trip in enumerate(trips):
    #         print(f"  Trip {i + 1}: {trip}")
    #
    # print("\nRegular Vehicles:")
    # for vehicle_id, trips in list(vehicle_data.items())[:5]:
    #     print(f"\nVehicle ID: {vehicle_id}")
    #     for i, trip in enumerate(trips):
    #         print(f"  Trip {i + 1}: {trip}")

    
    #     save_info = {'cover_table': "../result/PR{} TestingNew/pr{}_cover_{}_step{}.npy".format(pr, pr, a, step),
    #                  'cover_table_benchmark': "../result/PR{} Testing/cover_table_benchmark.npy".format(pr)}
    #
    #     path = "sumo_cfg/toy_net/toy_test_{}.sumocfg".format(a)
    #     lf_table_path = "../result/link_flow/pr{}_link_flow_3600.json".format(pr)
    #     s = Simulation(max_time=3600, link_num=60, resolution=0.1,
    #                    net_file='sumo_cfg/toy_net/toy_net1.net.xml',
    #                    time_interval=step)
    #     s.load_lf(lf_table_path)
    #     s.sim(save_info, path, parameters=(1, p), deroute_num=2, k=256)
    #     traci.close()
    # # s.sim_benchmark(save_info)