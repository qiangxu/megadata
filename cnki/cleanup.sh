#!/bin/bash
##############################################################
# CREATED DATE: Sat Mar 29 14:33:20 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
##############################################################


#KILL python dump_site_3.py -c config/1.json
PROCESS_ID=$(ps aux | grep "python dump_site_3.py" | grep -v grep | awk '{print $2}')
kill $PROCESS_ID

DATE_STR=$(date +"%Y-%m-%d-%H-%M-%S")

cp state.json state.json.bak
cp state.json ./bak/state_$DATE_STR.json

grep -v '"downloaded":1' state.json.bak > state.json
rm -rf ./data/links/*.json

#python search_site_3.py -c config/1.json -s --total-pages 1
#python dump_site_3.py -c config/1.json
