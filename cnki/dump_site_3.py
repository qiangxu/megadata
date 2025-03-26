#!/usr/bin/env python
# CREATED DATE: Wed Mar 26 21:42:15 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
from pathlib import Path
from tqdm import tqdm
import argparse
import glob
import json
import ndjson
import os
import pandas as pd
import random
import re
import requests
import sys
import time

def load_state():
    """加载或创建状态DataFrame"""
    if os.path.exists('./state.json'):
        with open('./state.json', 'r', encoding='utf-8') as f:
            records = ndjson.loads(f.read())
        return pd.DataFrame(records)
    return pd.DataFrame(columns=['ndjson', 'title', 'date', 'authors', 'url', 'source', 'downloaded'])

def save_state(df_state):
    """保存状态DataFrame到硬盘(ndjson格式)"""
    df_state.to_json("./state.json", lines=True, orient="records")

def process_ndjson_files(df_state, ndjson_dir):
    """处理ndjson文件并更新状态"""
    # 获取已处理文件
    exist_ndjson_files = set(df_state['ndjson'].unique())
    
    # 查找所有新ndjson文件
    input_ndjson_files = [f for f in glob.glob(ndjson_dir)]
    update_ndjson_files = [f for f in input_ndjson_files if Path(f).name not in exist_ndjson_files]
    
    # 处理新文件
    if len(update_ndjson_files) == 0:
        return df_state 

o   df_update = pd.concat([pd.read_json(f, lines=True, orient="records").assign(file=Path(f).name) for f in update_ndjson_files], ignore_index=True)
        
    if len(df_state) > 0: 
        if len(df_update) > 0:
            df_state = pd.concat([df_state, df_update], ignore_index=True)
            save_state(df_state)
            print(f"添加了{len(df_updates)}条新记录")
        else: 
            pass
    else: 
        if len(df_update) > 0:
            return df_update.copy()
        else: 
            return df_state

    return df_state

def download_pdf(df_state, url_index, output_dir='pdfs'):
 
    # 获取URL
    url = df_state.loc[url_index, 'url']

    try:
        json_response = requests.get(url, cookies=cookies, headers=headers)
        download_data = json_response.json()
        
        if 'url' in download_data:
            real_download_url = download_data['url']
            print(f"获取到真实下载链接: {real_download_url}")
            
            # 第二步：下载实际的文件
            pdf_response = requests.get(real_download_url, cookies=cookies, headers=headers, stream=True)
            
            # 检查内容类型
            content_type = pdf_response.headers.get('content-type', '')
            print(f"文件内容类型: {content_type}")
            
            if 'application/pdf' in content_type.lower() or 'application/octet-stream' in content_type.lower():
                filename = url.split('/')[-1]
                if not filename.endswith('.pdf'):
                    filename += '.pdf'

                # 保存PDF
                file_path = Path(output_dir) / filename
                with open(file_path, 'wb') as f:

                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                # 更新状态
                df_state.loc[url_index, 'downloaded'] = True
                print("PDF 成功下载!")
            else:
                print(f"下载失败，响应不是PDF。内容类型: {content_type}")
                print("响应内容:", pdf_response.text[:200])  # 只打印前200个字符
        else:
            print("获取下载链接失败，JSON响应:", download_data)
    except Exception as e: 
        print(e)
        breakpoint()

def read_config(config_file):
    """
    读取并解析 JSON 配置文件

    Args:
        config_file (str): 配置文件路径

    Returns:
        dict: 解析后的配置数据
    """
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 找不到配置文件 '{config_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: '{config_file}' 不是有效的 JSON 文件")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取配置文件时发生错误: {str(e)}")
        sys.exit(1)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="读取JSON配置文件")
    parser.add_argument("-c", "--config", required=False, help="指定JSON配置文件的路径")

    # 解析命令行参数
    args = parser.parse_args()
    
    breakpoint()
    if args.config:
        # 读取配置文件
        config = read_config(args.config)
        ndjson_dir = config["ndjson_dir"]
        cookies = config["cookies"]

        # 加载状态
        df_state = process_ndjson_files(load_state(), ndjson_dir)

    # 示例：下载未下载的PDF
    for idx in df_state[~df_state['downloaded']].index:
        download_pdf(df_state, idx)       
            

if __name__ == "__main__":
    main()

