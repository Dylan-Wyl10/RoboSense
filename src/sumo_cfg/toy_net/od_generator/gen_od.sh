read -p "please provide the bgv link flow:" bgv_link
read -p "please provide the cav link flow:" cav_link

python3 gen_od.py --timeframe 3600 --savepath 'od_file_bgv.od' --size 6 --linkflow $bgv_link
python3 gen_od.py --timeframe 3600 --savepath 'od_file_cav.od' --size 6 --linkflow $cav_link
od2trips -n  taz_all.taz.xml -d od_file_bgv.od -o od_file_bgv.odtrips.xml --vtype 'bgv' --prefix 'bgv'
od2trips -n  taz_all.taz.xml -d od_file_cav.od -o od_file_cav.odtrips.xml --vtype 'cav' --prefix 'cav'
scp od_file_cav.odtrips.xml ../od_cav.odtrips.xml
cd ..
#duarouter -n toy_net1.net.xml --route-files od_generator/od_file.odtrips.xml -o toy_netOD.rou.xml
rm -r "dualogs"
mkdir "dualogs"
cd dualogs
python3 /usr/share/sumo/tools/assign/duaIterate.py -n ../toy_net1.net.xml -t ../od_generator/od_file_bgv.odtrips.xml --additional ../v_type.add.xml duarouter--vtype-output dummy.xml duarouter--additional-files ../v_type.add.xml
scp 049/od_file_bgv.odtrips_049.rou.xml ../od_bgv.rou.xml