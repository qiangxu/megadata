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
import urllib.parse


HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Referer": "https://api1.sjuku.top/download.php"
}


def load_state():
    """加载或创建状态DataFrame"""
    if os.path.exists('./state.json'):
        return pd.read_json('./state.json', lines=True, orient="records", convert_dates=True)
    return pd.DataFrame(columns=['ndjson', 'title', 'date', 'authors', 'url', 'source', 'downloaded'])

def save_state(df_state):
    """保存状态DataFrame到硬盘(ndjson格式)"""
    df_state.to_json("./state.json", lines=True, orient="records", force_ascii=False)

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

    df_update = pd.concat([pd.read_json(f, lines=True, orient="records", convert_dates=True).assign(ndjson=Path(f).name) for f in update_ndjson_files], ignore_index=True)

    df_update = df_update.sort_values(['title', 'authors', 'source', 'date', 'ndjson']).drop_duplicates(['title', 'authors', 'source', 'date'], keep='last')
    df_update['downloaded'] = False
        
    if len(df_state) > 0: 
        if len(df_update) > 0:
            df_state = pd.concat([df_state, df_update], ignore_index=True).sort_values(['title', 'authors', 'source', 'date', 'downloaded', 'ndjson']).drop_duplicates(['title', 'authors', 'source', 'date'], keep='last')
            save_state(df_state)
            print(f"MERGED {len(df_update)}条新记录")
        else: 
            pass
    else: 
        if len(df_update) > 0:
            save_state(df_update)
            return df_update.copy()
        else: 
            return df_state

    return df_state

def download_pdf(php_url, cookies, output_dir, filename_prefix):
    # 获取URL

    try:
        # PHP -> JSON -> PDF
        json_url = php_url.replace("download.php", "download2.php")
        json_response = requests.get(json_url, headers=HEADERS | {"Cookie": cookies})
        json_data = json_response.json()
        
        if 'url' in json_data:
            pdf_url = json_data['url']
            print(f"获取到真实下载链接: {pdf_url}")
            
            # 第二步：下载实际的文件
            pdf_response = requests.get(pdf_url, headers=HEADERS | {"Cookie": cookies}, stream=True)
            
            # 检查内容类型
            content_type = pdf_response.headers.get('content-type', '')
            content_disposition =  pdf_response.headers['Content-Disposition']
            # print(f"文件内容类型: {content_type}")
            
            if 'application/pdf' in content_type.lower() or 'application/octet-stream' in content_type.lower() or content_disposition.upper().endswith('.PDF'):
                assert "FILENAME*=UTF" in content_disposition.upper()

                encoded_str = content_disposition.upper().split("FILENAME*=UTF-8''")[-1]

                # 解码URL编码的字符串
                filename = urllib.parse.unquote(encoded_str, encoding='utf-8')
                filename = filename_prefix + filename.split('/')[-1]
                
                safe_filename = re.sub(r'[^\w\u4e00-\u9fa5\.\-]', '_', filename)
                assert safe_filename.endswith('.PDF')
                safe_filename = safe_filename.split(".PDF")[0] + ".pdf"

                # 保存PDF
                filepath = Path(output_dir) / safe_filename

                with open(filepath, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print("PDF 成功下载!")
            else:
                breakpoint()
                print(f"下载失败，响应不是PDF。内容类型: {content_type}")
                print("响应内容:", pdf_response.text[:200])  # 只打印前200个字符
        else:
            print("获取下载链接失败，JSON响应:", json_data)
    except requests.exceptions.JSONDecodeError as e:
        print("可能超时")
    except Exception as e: 
        breakpoint()
        print("Unknown Error:", e)
        pass

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
        
    if args.config:
        # 读取配置文件
        config = read_config(args.config)
        ndjson_dir = config["ndjson_dir"]
        cookies = config["cookies"]
        output_dir = config['output_dir']

        # 加载状态
        df_state = process_ndjson_files(load_state(), ndjson_dir)

        counter = 0
        to_download_url_index = df_state[~df_state['downloaded']].index
        print(f"{len(to_download_url_index)}下载")
        for url_idx in tqdm(to_download_url_index):
            try:
                url = df_state.loc[url_idx]['url']
                authors = df_state.loc[url_idx]['authors']
                date = pd.to_datetime(df_state.loc[url_idx]['date']).strftime('%Y-%m-%d')
                source = df_state.loc[url_idx]['source']
                source = re.sub(r'[^\w\u4e00-\u9fa5\.\-]', '_', source)

                os.makedirs(os.path.join(output_dir, source), exist_ok=True)

                filename_prefix = "%s_%s_" % (date, authors)
                download_pdf(url, cookies, os.path.join(output_dir, source), filename_prefix)
                counter += 1
                if counter % 100 == 0: 
                    save_state(df_state)
                
                # 更新状态
                df_state.loc[url_idx, 'downloaded'] = True
            except Exception as e: 
                save_state(df_state)

        save_state(df_state)
if __name__ == "__main__":
    main()

