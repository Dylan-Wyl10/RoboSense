python3 gen_od.py --timeframe 600 --savepath 'od_file.od' --size 6 --linkflow 300
od2trips -n  taz_all.taz.xml -d od_file.od -o od_file.odtrips.xml
cd ..
#duarouter -n toy_net1.net.xml --route-files od_generator/od_file.odtrips.xml -o toy_netOD.rou.xml
mkdir "dualogs"
cd dualogs
python3 /usr/share/sumo/tools/assign/duaIterate.py -n ../toy_net1.net.xml -t ../od_generator/od_file.odtrips.xml --clean-alt