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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


"""
# 隧道域名:端口号
TUNNEL = "q945.kdltps.com:15818"

# 用户名密码方式
USERNAME = "t14319390139362"
PASSWORD = "ngvczjx6"
PROXIES = { "http": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": USERNAME, "pwd": PASSWORD, "proxy": TUNNEL}, "https": "http://%(user)s:%(pwd)s@%(proxy)s/" % {"user": USERNAME, "pwd": PASSWORD, "proxy": TUNNEL} }
"""

HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Referer": "https://api1.sjuku.top/download.php"
}

PAPER_KEYS = [
        'title', 
        'authors', 
        'date', 
        'category', 
        'filename', 
        'dbname',
        'source', 
        'url'
        ]
STATE_KEYS = ['ndjson', 'downloaded']

EXE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"当前脚本目录: {EXE_DIR}")

STATE_FILE = os.path.join(EXE_DIR, "state.json")

def custom_date_parser(date_str):
    try:
        # 先尝试直接解析
        return pd.to_datetime(date_str)
    except:
        # 对于YYYYMM格式特殊处理
        if len(date_str) == 6 and date_str.isdigit():
            return pd.to_datetime(date_str, format="%Y%m")
        # 对于YYYYMMDD格式特殊处理
        elif len(date_str) == 8 and date_str.isdigit():
            return pd.to_datetime(date_str, format="%Y%m%d")
        elif date_str == "N/A":
            return pd.to_datetime("19700101", format="%Y%m%d") 
        else:
            breakpoint()
            # 其他情况返回NaT或抛出异常
            return pd.to_datetime("19700101", format="%Y%m%d") 

def load_state():
    """加载或创建状态DataFrame"""
    if os.path.exists(STATE_FILE):
        df = pd.read_json(STATE_FILE, lines=True, orient="records")[PAPER_KEYS + STATE_KEYS]
        df['date'] = pd.to_datetime(df['date'], unit='ms')
        return df
    return pd.DataFrame(columns=PAPER_KEYS + STATE_KEYS)

def save_state(df_state):
    """保存状态DataFrame到硬盘(ndjson格式)"""
    df_state.to_json(STATE_FILE, lines=True, orient="records", force_ascii=False)

def process_ndjson_files(df_state, ndjson_dir):
    """处理ndjson文件并更新状态"""
    # 获取已处理文件
    exist_ndjson_files = set(df_state['ndjson'].unique())
    
    # 查找所有新ndjson文件
    input_ndjson_files = [f for f in glob.glob(os.path.join(ndjson_dir, "*.json"))]
    update_ndjson_files = [f for f in input_ndjson_files if Path(f).name not in exist_ndjson_files]
    
    # 处理新文件
    if len(update_ndjson_files) == 0:
        return df_state 
    df_update = pd.concat([pd.read_json(f, lines=True, orient="records", convert_dates=False).assign(ndjson=Path(f).name) for f in update_ndjson_files], ignore_index=True)
    df_update['date'] = df_update['date'].apply(custom_date_parser)

    df_update = df_update.sort_values(['title', 'authors', 'source', 'date', 'ndjson']).drop_duplicates(['title', 'authors', 'source', 'date'], keep='last')
    df_update['downloaded'] = 1
        
    if len(df_state) > 0: 
        if len(df_update) > 0:
            df_state = pd.concat([df_state, df_update], ignore_index=True).sort_values(['title', 'authors', 'source', 'date', 'downloaded', 'ndjson'], ascending=[True, True, True, True, False, True]).drop_duplicates(['title', 'authors', 'source', 'date'], keep='last')
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

def extract_pdf_url_site3(url, cookies):
    try:     
        json_url = url.replace("download.php", "download2.php")
        #json_response = requests.get(json_url, headers=HEADERS | {"Cookie": cookies}, proxies=PROXIES)
        #json_response = requests.get(json_url, headers=HEADERS | {"Cookie": cookies}, timeout=10)
        json_response = requests.get(json_url, headers=HEADERS | {"Cookie": cookies})

        json_data = json_response.json()
        if 'url' in json_data:
            pdf_url = json_data['url']
            print(f"获取到真实下载链接: {pdf_url}")
            
            return pdf_url
        else:
            print("URL:\n\t", url, "\n 获取下载链接失败，RESP响应:\n\t", json_data)
            raise Exception("CODE_FAILURE", json_data)

    except requests.exceptions.JSONDecodeError as e:
        if "Couldn\'t fetch mysqli" in json_response.text:
            raise requests.exceptions.Timeout("OVERLOAD", json_response.text)
        if "授权已超时，请重新进入" in json_response.text:
            raise Exception("AUTH_EXPIRED", json_response.text)
        if "请稍后在试" in json_response.text:
            raise Exception("RELIABILITY_ERROR", json_response.text)
        else:
            #breakpoint()
            print("疑似超时", json_response.text)
            raise requests.exceptions.Timeout()

def gen_safe_filepath(file_dir, title, authors, date):

    os.makedirs(file_dir, exist_ok=True)

    # 解码URL编码的字符串
    file_name = re.sub(r'[^\w\u4e00-\u9fa5\.\-]', '_', "%s_%s_%s" % (date, authors, urllib.parse.unquote(urllib.parse.quote(title, safe='()/:?=&'), encoding='utf-8').split('/')[-1])).split(".PDF")[0][0:200] + ".pdf"

    return Path(file_dir) / file_name

def download_pdf(url, cookies, file_path):
    # 获取URL
    try:
        if "download.php" in url: 
            # PHP -> JSON -> PDF
            pdf_url = extract_pdf_url_site3(url, cookies)
        elif "api88.wenxian.shop/v1/api/download?" in url:
            pdf_url, _, _, remaining_seconds = extract_pdf_url_site2(url, cookies)
        else:
            breakpoint()
            return 1000
        
        # 第二步：下载实际的文件
        #pdf_response = requests.get(pdf_url, headers=HEADERS | {"Cookie": cookies}, proxies=PROXIES, stream=True)
        pdf_response = requests.get(pdf_url, headers=HEADERS | {"Cookie": cookies}, verify=False, stream=True)
        
        # 检查内容类型
        content_type = pdf_response.headers.get('content-type', '')
        content_disposition =  pdf_response.headers['Content-Disposition']
        # print(f"文件内容类型: {content_type}")
        
        if 'application/pdf' in content_type.lower() or 'application/octet-stream' in content_type.lower() or content_disposition.upper().endswith('.PDF'):
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as f:
                    for chunk in pdf_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print("PDF 成功下载!")
            else: 
                print("PDF 已存在!")
            return -1
        else: 
            print(f"下载失败，响应不是PDF。内容类型: {content_type}")
            return 0
    except requests.exceptions.Timeout as e:
        if "OVERLOAD" in str(e):
            print("负载过高", e)
            return 2000
        if "Read timed out" in str(e): 
            print("连接超时", e)
            return 3000

        return 1
    except Exception as e: 
        if "RELIABILITY_ERROR" in str(e): 
            print("稍后再试, 延长SLEEP", e)
            return 4000
        if "AUTH_EXPIRED" in str(e): 
            print("认证超时, 换COOKIES", e)
            return 5000
        if "Remote end closed connection without response" in str(e):
            print("连接超时", e)
            return 3000
        if "EOF occurred" in str(e): 
            print("网络断开", e)
            return 3000
        if "CODE_FAILURE" in str(e): 
            print("需要调试DBEUG URL", e)
            return 6000
        print("Unknown Error:", e)
        return 9000

def read_config(config_file):
    """
    读取并解析 JSON 配置文件

    Args:
        config_file (str): 配置文件路径

    Returns:
        dict: 解析后的配置数据
    """
    try:
        CNF_DIR = os.path.dirname(os.path.abspath(config_file))
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            config["ndjson_dir"] = str(Path(os.path.join(CNF_DIR, config["ndjson_dir"])).resolve())
            config["output_dir"] = str(Path(os.path.join(CNF_DIR, config['output_dir'])).resolve())

            os.makedirs(config["ndjson_dir"], exist_ok=True)
            os.makedirs(config["output_dir"], exist_ok=True)
            return config

    except FileNotFoundError:
        print(f"错误: 找不到配置文件 '{config_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: '{config_file}' 不是有效的 JSON 文件")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取配置文件时发生错误: {str(e)}")
        sys.exit(1)

def reload_cookies(config_file):
    return read_config(config_file)["dump_cookies"]

def exec_dump_task(config_file): 
    breakpoint()
    config = read_config(config_file)
    ndjson_dir = config["ndjson_dir"]
    cookies = config["dump_cookies"]
    output_dir = config['output_dir']

    # 加载状态

    df_state = process_ndjson_files(load_state(), ndjson_dir)

    #to_download_mask = (df_state['downloaded'] == 1) | (df_state['downloaded'] >= 1000)
    to_download_mask = (df_state['downloaded'] == 1)
    to_download_url_index = df_state[to_download_mask | (df_state['downloaded'] >0)].index.values
    print(f"{len(to_download_url_index)}下载")
    random.shuffle(to_download_url_index)
    for count in tqdm(range(len(to_download_url_index))): 
        url_idx = to_download_url_index[count]
        url = df_state.loc[url_idx]['url']
        title = df_state.loc[url_idx]['title'] 
        authors = df_state.loc[url_idx]['authors']
        date = pd.to_datetime(df_state.loc[url_idx]['date']).strftime('%Y-%m-%d')
        month = pd.to_datetime(df_state.loc[url_idx]['date']).strftime('%m')
        category = df_state.loc[url_idx]['category']

        file_dir = os.path.join(output_dir, category, month)
        file_path = gen_safe_filepath(file_dir, title, authors, date)

        if os.path.exists(file_path):
            print("PDF 已存在!")
            df_state.loc[url_idx, 'downloaded'] = downloaded

        try:
            downloaded = download_pdf(url, cookies, file_path)
            # 更新状态
            if downloaded == -1 or downloaded == 0: 
                df_state.loc[url_idx, 'downloaded'] = downloaded

            elif downloaded == 1: 
                df_state.loc[url_idx, 'downloaded'] = df_state.loc[url_idx, 'downloaded'] + downloaded
            elif downloaded in [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000]: 
                df_state.loc[url_idx, 'downloaded'] = downloaded
            else:
                save_state(df_state)
                assert False

            if count % 10 == 0:
                cookies = reload_cookies(config_file)
                save_state(df_state)
                print("COOKIES RELOADED /STATE SAVED, %s" % cookies)

            if count % 30 == 0:
                pass

            delay = random.uniform(6, 10)  # 随机延迟2-5秒
            print(f"等待 {delay:.2f} 秒后继续...")
            time.sleep(delay)
    
        except Exception as e: 
            save_state(df_state)
            print("Unknown Error:", e)
            breakpoint()

    if len(df_state) > 0:
        save_state(df_state)

def extract_pdf_url_site2(url, cookies=None):
    """
    从API获取下载页面，提取最终下载URL和过期时间
    
    Parameters:
    url (str): API下载链接
    cookies (dict): 请求所需的cookies，可选
    
    Returns:
    dict: 包含下载信息的字典
    """
    # 发送请求获取下载页面的HTML

    response = requests.get(url, headers=HEADERS | {'Cookie': cookies})
    
    # 寻找setTimeout函数中的链接
    pdf_urls = re.findall(r'https?://[\w\d\.\-:]+/[^"\s]+\.pdf[^"\s]*', response.text)
    if pdf_urls:
        pdf_url = pdf_urls[0].replace('\\u0026', '&').replace('\\\\u0026', '&')
    else:
        print("URL:\n\t", url, "\n 获取下载链接失败，RESP响应:\n\t", response.text)
        raise Exception("CODE_FAILURE", response.text)
    
    # 解析URL参数
    parsed_url = urllib.parse.urlparse(pdf_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    # 提取过期时间
    expires = None
    expires_datetime = None
    if 'Expires' in query_params:
        expires = int(query_params['Expires'][0])
        expires_datetime = datetime.fromtimestamp(expires)
        current_time = time.time()
        remaining_seconds = int(expires - current_time)
    else:
        remaining_seconds = None

    # 返回提取的信息
    return pdf_url, expires, expires_datetime, remaining_seconds

# 使用示例
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="读取JSON配置文件")
    parser.add_argument("-c", "--config", required=False, help="指定JSON配置文件的路径")

    # 解析命令行参数
    args = parser.parse_args()
        
    if args.config:
        while True: 
            breakpoint()
            config = read_config(args.config)

            url="https://api88.wenxian.shop/v1/api/download?dflag=pdfdown&v=ruzfSYlMP8zJCull+fSglmCz15EJRuKE8f3HEEf9MivhSB83riJzhQnJl0qL0iRNaS90YNt8qluN3ISpRDnPB0DnozoURArsvX/tY3Eb4KFMrT29NTxradORtyy+uWRj2uH5dmwYheBmoKlXyRbpUZkCpADDr0Vwbk46Rg1Y4I1/c5vjcRr6A3fSxfIMn4W4RZLvNkxCFhm/jThZuUnQcmrGpG4tWWXiGJGmfZA0VIPizpVuUHfMcC5gwu9HsOq6TNbUBwKH+t5CaHhhYTL5S66ziUjlrVcfs9jfGP2lZao=&fileid=CQJT20250326001&dataDbname=CAPJ&pd=2025-03-28%2008:49&t=1743248397377"
            download_pdf(url, config['dump_cookies'], "./abc.pdf")
            #exec_dump_task(args.config)
            time.sleep(10)


if __name__ == "__main__":
    main()

