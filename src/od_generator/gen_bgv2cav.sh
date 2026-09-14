read -p "please provide the pr rate (without %)" bgv_link
read -p "provide the directory path for network configuration (from project root without/)": -e config_path


python3 bgv2cav.py ../../$config_path/od.rou.xml ../../$config_path/od_mixed.rou.xml --rate $bgv_link --seed 42

cd ../../$config_path
python3 ../../src/turn-defs/generateTurnRatios.py -r ../../$config_path/od.rou.xml -i 100
