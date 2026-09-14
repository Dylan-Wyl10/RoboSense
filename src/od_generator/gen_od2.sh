read -p "provide the directory path for network configuration(from project root without/)": -e config_path

scp ../../$config_path/od/od_file_cav.odtrips.xml ../../$config_path/od_cav.odtrips.xml
cd ../../$config_path
#duarouter -n toy_net1.net.xml --route-files od/od_file.odtrips.xml -o toy_netOD.rou.xml
rm -r "dualogs"
mkdir "dualogs"
cd dualogs
python3 /usr/share/sumo/tools/assign/duaIterate.py -n ../5x5net.net.xml -t ../od/od_file_bgv.odtrips.xml --additional ../v_type.add.xml duarouter--vtype-output dummy.xml duarouter--additional-files ../v_type.add.xml
scp 049/od_file_bgv.odtrips_049.rou.xml ../od.rou.xml
#cd ../../../src
#python3 main_getBench.py
#python3 sim_main.py