read -p "provide the directory path for network configuration (from project root without/)": -e config_path

#simtime=$((3600 * simtime_hr))

od2trips -n  ../../$config_path/od/taz_all.taz.xml -d ../../$config_path/od/od_file_bgv.od -o ../../$config_path/od/od_file_bgv_manualtmp.odtrips.xml --vtype 'bgv' --prefix 'bgv'
od2trips -n  ../../$config_path/od/taz_all.taz.xml -d ../../$config_path/od/od_file_cav.od -o ../../$config_path/od/od_file_cav_manualtmp.odtrips.xml --vtype 'cav' --prefix 'cav'