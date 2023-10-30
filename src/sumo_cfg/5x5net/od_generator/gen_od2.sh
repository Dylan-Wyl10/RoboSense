scp od_file_cav.odtrips.xml ../od_cav.odtrips.xml
cd ..
#duarouter -n toy_net1.net.xml --route-files od_generator/od_file.odtrips.xml -o toy_netOD.rou.xml
rm -r "dualogs"
mkdir "dualogs"
cd dualogs
python3 /usr/share/sumo/tools/assign/duaIterate.py -n ../5x5net.net.xml -t ../od_generator/od_file_bgv.odtrips.xml --additional ../v_type.add.xml duarouter--vtype-output dummy.xml duarouter--additional-files ../v_type.add.xml
scp 049/od_file_bgv.odtrips_049.rou.xml ../od.rou.xml
cd ../../..
python3 collect_history.py
python3 sim_main.py

