read -p "please provide the bgv link flow:" bgv_link
read -p "please provide the cav link flow:" cav_link
read -p "please provide the length of simulation in hour:" simtime_hr
read -p "provide the directory path for network configuration (from project root without/)": -e config_path

simtime=$((3600 * simtime_hr))

python3 gen_od.py --timeframe "$simtime" --savepath ../../$config_path/od/od_file_bgv.od --size 5 --linkflow $bgv_link
python3 gen_od.py --timeframe "$simtime" --savepath ../../$config_path/od/od_file_cav.od --size 5 --linkflow $cav_link
od2trips -n  ../../$config_path/od/taz_all.taz.xml -d ../../$config_path/od/od_file_bgv.od -o ../../$config_path/od/od_file_bgv.odtrips.xml --vtype 'bgv' --prefix 'bgv'
od2trips -n  ../../$config_path/od/taz_all.taz.xml -d ../../$config_path/od/od_file_cav.od -o ../../$config_path/od/od_file_cav.odtrips.xml --vtype 'cav' --prefix 'cav'