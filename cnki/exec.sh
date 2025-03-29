#!/bin/bash
##############################################################
# CREATED DATE: Sun Mar 30 02:04:01 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
##############################################################

for i in {1..5000}; do
    rm site3/links/cnki_*; python site3/search_site_3.py -c config/3.json -S -s 3 -t 1 -z 20
    python site3/dump_site_3.py -c config/3.json
    python site3/dump_site_3.py -c config/3.json
done
