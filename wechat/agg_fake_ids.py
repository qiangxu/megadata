#!/usr/bin/env python
# CREATED DATE: Wed Jan 29 23:48:38 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com

from urllib.parse import urlparse, parse_qs
import glob
def extract_fakeids(file_path):
    fakeids = []
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        urls = f.readlines()
    
    # 处理每个URL
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        try:
            # 解析URL
            parsed = urlparse(url)
            # 获取查询参数
            params = parse_qs(parsed.query)
            # 提取fakeid
            fakeid = params.get('fakeid', [''])[0]
            
            if fakeid:
                fakeids.append(fakeid)
        except Exception as e:
            print(f"处理URL时出错: {url}")
            print(f"错误信息: {str(e)}")
    
    return fakeids

def save_fakeids(fakeids, output_file):
    """保存提取的fakeids到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for fakeid in fakeids:
            f.write(f"{fakeid}\n")

def main():
    # 输入和输出文件路径
    fakeids = []
    for file_path in glob.glob("../metadata/cap_fake_id_*.csv"):
        fakeids.extend(extract_fakeids(file_path))

    output_file = 'fakeids.csv'

    # 保存到文件
    save_fakeids(fakeids, output_file)
    print(f"\nfakeids已保存到文件: {output_file}")

if __name__ == '__main__':
    main()
