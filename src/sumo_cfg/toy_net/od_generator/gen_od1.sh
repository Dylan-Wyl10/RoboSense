read -p "please provide the bgv link flow:" bgv_link
read -p "please provide the cav link flow:" cav_link

python3 gen_od.py --timeframe 3600 --savepath 'od_file_bgv.od' --size 6 --linkflow $bgv_link
python3 gen_od.py --timeframe 3600 --savepath 'od_file_cav.od' --size 6 --linkflow $cav_link
od2trips -n  taz_all.taz.xml -d od_file_bgv.od -o od_file_bgv.odtrips.xml --vtype 'bgv' --prefix 'bgv'
od2trips -n  taz_all.taz.xml -d od_file_cav.od -o od_file_cav.odtrips.xml --vtype 'cav' --prefix 'cav'