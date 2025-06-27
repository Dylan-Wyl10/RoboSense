read -p "provide the directory path for network configuration(from project root without/)": -e config_path
read -p "provide the path for route file": -e route_file

cd ../../$config_path

python3 ../../src/turn-defs/generateTurnRatios.py -r $route_file