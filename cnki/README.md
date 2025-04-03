| CREATED DATE                 | CREATED BY                    | VERSION |
| ---------------------------- | ----------------------------- | ------- |
| Sat Mar 29 16:50:29 2025     | qiangxu, toxuqiang@gmail.com  | 0.1     |


python dump_site_3.py -c config/1.json 

python search.py -c config/1.json -s --total-pages 2

'''
date  && echo "PDF文件数量: $(find ./ -name "*.pdf" | wc -l)" && echo "总大小: $(du -ch . | grep total | cut  -f 1)"
'''
