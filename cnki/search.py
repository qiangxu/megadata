#!/usr/bin/env python
# CREATED DATE: Fri Mar 28 14:58:54 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com

import requests
from bs4 import BeautifulSoup
import re
import json
import yaml
import urllib.parse
import urllib3
import argparse
import os
import sys
import glob
import time
from datetime import datetime
from pathlib import Path
import random
from requests_toolbelt.utils import dump
import random
import numpy as np
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SEARCH_TARGET_URLS = {
    "2": "http://124.222.211.12:3344/kns8s/brief/grid",
    #"3": "http://222.186.61.87:8085/kns8s/brief/grid",
    "3": "http://122.51.45.239:8085/kns8s/brief/grid",
    "5": "http://175.178.121.173/kns8s/brief/grid",
    "8": "http://222.186.61.87:8082/kns8s/brief/grid",
    "zju": "http://kns-cnki-net-s.webvpn.zju.edu.cn:8001/kns8s/brief/grid?sf_request_type=ajax"
}
REFERERS = {
    "2": "http://124.222.211.12:3344/kns8/defaultresult/index",
    #"3": "http://222.186.61.87:8085/kns8s/defaultresult/index",
    "3": "http://122.51.45.239:8085/kns8s/defaultresult/index",
    "5": "http://175.178.121.173/kns8s/defaultresult/index",
    "8": "http://222.186.61.87:8082/kns8s/defaultresult/index",
    "zju": "http://kns-cnki-net-s.webvpn.zju.edu.cn:8001/kns8s/defaultresult/index",
}

def gen_proxy(config): 

    # 获取API接口返回的代理IP
    proxy_ips = sorted(requests.get(config["proxy_url"]).text.split("\r\n"))
    proxy_ip = proxy_ips[(int(config["var_id"]) % len(proxy_ips))]

    proxy = {
        "http": "http://%(user)s:%(pwd)s@%(proxy)s/"
        % {"user": config["username"], "pwd": config["password"], "proxy": proxy_ip},
        "https": "http://%(user)s:%(pwd)s@%(proxy)s/"
        % {"user": config["username"], "pwd": config["password"], "proxy": proxy_ip},
    }

    return proxy

def read_config(config_file, update_proxy=False):
    """
    读取并解析 JSON 配置文件

    Args:
        config_file (str): 配置文件路径

    Returns:
        dict: 解析后的配置数据
    """
    # 检查是否为YAML文件
    is_yaml = config_file.lower().endswith(('.yaml', '.yml'))
    
    try:
        CNF_DIR = os.path.dirname(os.path.abspath(config_file))
        with open(config_file, "r", encoding="utf-8") as f:
            if is_yaml:
                # 解析YAML文件
                config = yaml.safe_load(f)
            else:
                # 解析JSON文件
                config = json.load(f)
            
            # 处理路径（两种格式通用）
            config["ndjson_dir"] = str(
                Path(os.path.join(CNF_DIR, config["ndjson_dir"])).resolve()
            )
            config["output_dir"] = str(
                Path(os.path.join(CNF_DIR, config["output_dir"])).resolve()
            )
            config["state_file"] = str(
                Path(os.path.join(CNF_DIR, config["state_file"])).resolve()
            )
        
            # 创建必要的目录
            os.makedirs(config["ndjson_dir"], exist_ok=True)
            os.makedirs(config["output_dir"], exist_ok=True)
        
            # 处理代理设置
            #if config.get("use_proxy", False):
            #    config["proxy"] = gen_proxy(config)
            #else:
            #    config["proxy"] = None
            config["proxy"] = None
                
            return config

    except FileNotFoundError:
        print(f"错误: 找不到配置文件 '{config_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        if is_yaml:
            print(f"错误: '{config_file}' 不是有效的 YAML 文件")
        else:
            print(f"错误: '{config_file}' 不是有效的 JSON 文件")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"错误: '{config_file}' 不是有效的 YAML 文件: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取配置文件时发生错误: {str(e)}")
        sys.exit(1)

def search_cnki_by_category(
    site_id, category_code, page=1, page_size=50, sci_only=True, cookies=None
):
    """
    按分类号搜索中国知网(CNKI)并获取结果

    参数:
    category_code (str): 分类号，例如 'V'
    page (int): 页码，默认为1
    page_size (int): 每页结果数，默认为50
    sci_only (bool): 是否只搜索SCI收录的文献，默认为False
    cookies (dict): 请求用的cookies

    返回:
    str: HTML格式的搜索结果
    """
    # CNKI搜索API地址
    url = SEARCH_TARGET_URLS[site_id]
    # 构建查询JSON
    query_json = {
        # 平台标识，通常为空字符串，可选
        "Platform": "",
        # 资源类型，如"JOURNAL"(期刊)、"CROSSDB"(跨库)，必需
        "Resource": "CROSSDB",
        # 分类ID，标识特定资源类别，必需
        # "WD0FTY92"表示总库，"YSTT4HG0"表示学术期刊
        "Classid": "WD0FTY92",
        # 具体产品列表，以逗号分隔的产品代码，在跨库搜索时必需
        # CJFQ(中文期刊)、CDFD(博士)、CMFD(硕士)、CAPJ(特色期刊)等
        "Products": "CJFQ,CAPJ,CJTL,CDFD,CMFD,CPFD,IPFD,CPVD,CCND,WBFD,SCSF,SCHF,SCSD,SNAD,CCJD,CJFN,CCVD",
        #"Products": "",
        # 查询节点，包含所有查询条件，必需
        "QNode": {
            # 查询组，包含一个或多个查询条件组，必需
            "QGroup": [
                {
                    # 第一个查询组 - 分类号查询
                    "Key": "Subject",  # 键名，标识查询组类型，必需
                    "Title": "",  # 标题，通常为空，可选
                    "Logic": 0,  # 逻辑关系，0表示AND，必需
                    "Items": [  # 查询项，包含具体的检索条件，必需
                        {
                            "Field": "CLC",  # 字段名，CLC表示分类号，必需
                            "Value": category_code,  # 查询值，必需
                            "Operator": "SUFFIX",  # 操作符，SUFFIX表示前缀匹配，必需
                            "Logic": 0,  # 逻辑关系，0表示AND，在多条件时必需
                            "Title": "分类号",  # 标题，显示用，可选
                        }
                    ],
                    "ChildItems": [],  # 子项，可以包含更复杂的嵌套条件，可选
                }
                # 如果需要SCI过滤，将在下面添加另一个查询组
            ]
        },
        # 扩展范围，1表示精确匹配，可选
        "ExScope": 1,
        # 检索类型，2表示高级检索，必需
        "SearchType": 2,
        # 结果语言，CHINESE(中文)、FOREIGN(外文)、BOTH(不限)，必需
        "Rlang": "CHINESE",
        # 跨库编码，多个库ID的组合，跨库检索时必需
        "KuaKuCode": "YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A,EMRPGLPA,WQ0UVIAA,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R",
        # 扩展项，用于特殊查询需求，可选
        "Expands": {},
        # 搜索来源，对于第一页是2，对于后续页是4（重要）
        "SearchFrom": 4 if page > 1 else 1,
    }

    # 添加SCI过滤条件（如果需要）
    if sci_only:
        # SCI过滤条件组
        sci_filter = {
            "Key": "SCDBGroup",  # 特殊键名，用于文献源数据库分组，必需
            "Title": "",  # 标题，通常为空，可选
            "Logic": 0,  # 逻辑关系，0表示AND，必需
            "Items": [],  # 条件项，这里为空，因为使用子项定义，可选
            "ChildItems": [  # 子项目，包含具体的数据库筛选条件，必需
                {
                    "Key": "LYBSM",  # 文献源标识码键名，必需
                    "Title": "",  # 标题，通常为空，可选
                    "Logic": 0,  # 逻辑关系，0表示AND，必需
                    "Items": [  # 条件项，包含SCI的特定条件，必需
                        {
                            "Key": "P0201",  # SCI数据库的代码，必需
                            "Title": "SCI",  # 显示名称，可选
                            "Logic": 1,  # 1表示OR关系，必需
                            "Field": "LYBSM",  # 字段名，必需
                            "Operator": "DEFAULT",  # 操作符，必需
                            "Value": "P0201",  # 值，对应SCI代码，必需
                            "Value2": "",  # 第二个值，范围查询时使用，可选
                            "Name": "LYBSM",  # 字段名称，可选
                            "ExtendType": 0,  # 扩展类型，可选
                        }
                    ],
                    "ChildItems": [],  # 子子项，这里为空，可选
                }
            ],
        }

        # 将SCI过滤条件添加到查询组
        query_json["QNode"]["QGroup"].append(sci_filter)

    # 构建表单数据
    data = {
        # "boolSearch": "false",  # 对所有页面都是false
        "boolSearch": False if page > 1 else True,
        "QueryJson": json.dumps(query_json),
        "pageNum": page,
        "pageSize": page_size,
        "sortField": "PT",  # PT表示按发表时间排序
        "sortType": "DESC",  # 所有页面都是小写desc
        "dstyle": "listmode",  # 列表模式
        "boolSortSearch": "false",  # 必需参数
        "productStr": "YSTT4HG0,LSTPFY1C,RMJLXHZ3,JQIRZIYA,JUP3MUPD,1UR4K4HZ,BPBAFJ5S,R79MZMCB,MPMFIG1A,EMRPGLPA,J708GVCE,ML4DRIDX,WQ0UVIAA,NB3BWEHK,XVLO76FD,HR1YT1Z9,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R,",
        "aside": (
            "" if page > 1 else f"分类号：{category_code}"
        ),  # 第一页有，后续页面为空
        "searchFrom": "资源范围：总库",
        "subject": "",
        "language": "",
        "uniplatform": "",
    }

    # 只有第一页需要CurPage参数，这是关键区别
    if page == 1:
        data["CurPage"] = 1

    # HTTP请求头
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": REFERERS[site_id],
    }

    # 发送HTTP请求
    try:
        response = requests.post(
            url, data=data, headers=headers, cookies=cookies, verify=False
        )
        response.raise_for_status()  # 检查是否有HTTP错误
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        print(f"请求URL: {url}")
        print(f"请求参数: {data}")
        return ""


def extract_publications(site_id, html_content, category_code):
    """
    从HTML响应中提取出版物信息，并转换链接格式

    参数:
    html_content (str): HTML格式的搜索结果
    category_code (str): 分类号

    返回:
    list: 出版物信息列表，每个出版物是一个字典
    """
    if not html_content:
        print("警告: 收到空的HTML内容")
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    publications = []

    # 查找表格中的所有行（每行代表一篇文献）
    rows = soup.find_all("tr")

    if not rows:
        print("警告: 在HTML中未找到任何行")
        return []

    for row in rows:
        try:
            # 跳过表头行
            if not row.find("td", class_="name"):
                continue

            # 提取标题
            title_element = row.find("td", class_="name").find("a", class_="fz14")
            title = title_element.get_text(strip=True) if title_element else "N/A"

            # 移除标题中的字体标签
            title = re.sub(r"<font.*?>|</font>", "", title)

            # 获取原始URL
            orig_url = title_element.get("href") if title_element else None

            # 提取作者
            authors_element = row.find("td", class_="author")
            authors = []
            if authors_element:
                author_links = authors_element.find_all("a", class_="KnowledgeNetLink")
                for author in author_links:
                    authors.append(author.get_text(strip=True))

            # 提取来源（期刊/会议名称）
            source_element = row.find("td", class_="source")
            source = ""
            if source_element:
                source_link = source_element.find("a")
                if source_link:
                    source = source_link.get_text(strip=True)
                else:
                    source = source_element.get_text(strip=True)

            # 提取日期
            date_element = row.find("td", class_="date")
            date = date_element.get_text(strip=True) if date_element else "N/A"

            # 提取数据库代码和文件名
            collect_icon = row.find("a", class_="icon-collect")
            dbname = collect_icon.get("data-dbname", "") if collect_icon else ""
            filename = collect_icon.get("data-filename", "") if collect_icon else ""

            # 构建下载链接
            download_link = None
            if orig_url and "?" in orig_url:
                if site_id == "3":
                    download_link = convert_download_url_site_3(
                        orig_url, filename, dbname, title, authors, source, date
                    )
                elif site_id == "2":
                    download_link = convert_download_url_site_2(
                        orig_url, filename, dbname, title, authors, source, date
                    )
                elif site_id == "8":
                    download_link = convert_download_url_site_8(
                        orig_url, filename, dbname, title, authors, source, date
                    )
                else:
                    download_element = row.find("td", class_="operat").find("a", class_="downloadlink")
                    download_link = download_element.get("href") if download_element else orig_url

                publications.append(
                    {
                        "title": title,
                        "authors": ",".join(authors),
                        "source": source,
                        "date": date,
                        "url": download_link,
                        "category": category_code,
                        "filename": filename,
                        "dbname": dbname,
                    }
                )

        except Exception as e:
            print(f"提取出版物时出错: {e}")
            import traceback

            print(traceback.format_exc())

    return publications


def save_to_ndjson(publications, ndjson_dir, category_code, page):
    """
    将出版物信息保存为NDJSON格式

    参数:
    publications (list): 出版物信息列表
    ndjson_dir (str): NDJSON文件保存目录
    category_code (str): 分类号
    page (int): 页码

    返回:
    str: 保存的文件名
    """
    # 确保目录存在
    os.makedirs(ndjson_dir, exist_ok=True)

    # 生成文件名，使用当前时间戳和分类号、页码
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = os.path.join(
        ndjson_dir, f"cnki_{category_code}_p{page}_{timestamp}.json"
    )

    # 写入NDJSON文件
    with open(filename, "w", encoding="utf-8") as f:
        for pub in publications:
            f.write(json.dumps(pub, ensure_ascii=False) + "\n")

    print(f"保存了 {len(publications)} 条记录到 {filename}")
    return filename


def check_existing_file(ndjson_dir, category_code, page):
    """
    检查是否已存在符合条件的文件

    参数:
    ndjson_dir (str): NDJSON文件保存目录
    category_code (str): 分类号
    page (int): 页码

    返回:
    tuple: (是否存在, 文件列表, 有效记录数)
    """
    # 确保目录存在
    os.makedirs(ndjson_dir, exist_ok=True)

    # 查找符合条件的文件
    pattern = os.path.join(ndjson_dir, f"cnki_{category_code}_p{page}_*.json")
    matching_files = glob.glob(pattern)

    # 如果没有找到匹配的文件，返回False
    if not matching_files:
        return False, [], 0

    # 检查最新的文件中是否有有效记录
    latest_file = sorted(matching_files)[-1]  # 获取最新的文件

    # 读取文件中的记录
    records = []
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    records.append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"读取文件 {latest_file} 时出错: {e}")
        return False, matching_files, 0

    # 统计有效记录数（有URL的记录）
    valid_records = sum(1 for record in records if record.get("url"))

    return True, matching_files, valid_records


def search_and_save(
    site_id, category_code, config, sci_only=True, page=1, page_size=50
):
    """
    按分类号搜索CNKI并保存结果

    参数:
    category_code (str): 分类号，例如 'V'
    config (dict): 配置信息
    sci_only (bool): 是否只搜索SCI收录的文献
    page (int): 页码
    page_size (int): 每页结果数

    返回:
    tuple: (出版物信息列表, 是否实际发送了请求)
    """
    # 获取ndjson目录
    ndjson_dir = config.get("ndjson_dir", "./")

    # 确保ndjson_dir是目录而不是通配符模式
    ndjson_dir = os.path.dirname(ndjson_dir) if "*" in ndjson_dir else ndjson_dir

    # 检查是否已存在符合条件的文件
    file_exists, matching_files, valid_records = check_existing_file(
        ndjson_dir, category_code, page
    )

    # 如果文件存在并且有有效记录，直接返回
    if file_exists and valid_records > 0:
        print(
            f"分类 {category_code} 第 {page} 页: 已存在 {valid_records} 条有效记录，跳过请求"
        )
        # 读取最新的文件中的记录
        latest_file = sorted(matching_files)[-1]
        publications = []
        with open(latest_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    publications.append(record)
                except json.JSONDecodeError:
                    continue
        return publications, False  # 返回数据和"未发送请求"标志

    # 从配置中获取cookies
    cookies_str = config.get("search_cookies", "")
    cookies = {}

    # 解析cookies字符串
    if cookies_str:
        for item in cookies_str.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
    # 搜索CNKI
    html_content = search_cnki_by_category(
        site_id, category_code, page, page_size, sci_only, cookies
    )

    # 提取出版物信息
    publications = extract_publications(site_id, html_content, category_code)

    # 保存为NDJSON
    if publications:
        save_to_ndjson(publications, ndjson_dir, category_code, page)
        print(f"分类 {category_code} 第 {page} 页: 成功找到 {len(publications)} 条记录")
    else:
        print(f"分类 {category_code} 第 {page} 页: 未找到匹配的出版物")

    return publications, True  # 返回数据和"已发送请求"标志


def read_metadata(file_path="./metadata.json"):
    """
    读取metadata.json文件，返回分类数据字典并计算总文章数量

    参数:
    file_path (str): JSON文件路径

    返回:
    tuple: (分类数据字典, 总文章数量)
    """
    try:
        # 打开并读取JSON文件
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # 获取SCI分类数据
        categories_data = data.get("SCI", {})

        # 计算总文章数量
        total_articles = sum(category["size"] for category in categories_data.values())

        return categories_data, total_articles

    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 未找到")
        return {}, 0
    except json.JSONDecodeError:
        print(f"错误: '{file_path}' 不是有效的JSON文件")
        return {}, 0
    except Exception as e:
        print(f"读取文件时发生错误: {str(e)}")
        return {}, 0


def generate_timestamp_with_check():
    """
    生成带校验和的时间戳，模拟JavaScript中的generateTimestampWithCheck函数
    """
    timestamp = str(int(time.time() * 1000))
    # 获取时间戳后三位的数字
    last_three = timestamp[-4:-1]

    # 计算各位数字之和
    digit_sum = sum(int(digit) for digit in last_three)

    # 计算校验和 (数字之和模10)
    checksum = digit_sum % 10

    # 将校验和附加到时间戳末尾
    timestamp = timestamp[:-1] + str(checksum)

    return timestamp


def encrypt(data, key):
    """
    使用AES-ECB加密，模拟JavaScript中的encrypt函数
    """
    if not isinstance(data, str):
        data = json.dumps(data)

    # 将key转换为bytes
    key_bytes = key.encode("utf-8")

    # 使用AES-ECB模式加密
    cipher = AES.new(key_bytes, AES.MODE_ECB)

    # 填充数据并加密
    padded_data = pad(data.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded_data)

    # 返回Base64编码的结果
    return base64.b64encode(encrypted).decode("utf-8")

def convert_download_url_site_8(
    orig_url, file_id, db_name, title, authors, source, pub_date
):
    # 获取查询参数部分 - 确保保持原始编码格式
    query_part = orig_url.split("?")[1]

    # 替换&为&amp;以匹配JavaScript行为
    query_part = query_part.replace("&", "&amp;")

    # 构建ddata参数 - 使用原始的URL编码函数，不对:进行编码
    # f"{file_id}|{db_name}|{title}||{source}|{pub_date}"

    ddata_str_encoded = "|".join(
        [
            urllib.parse.quote(file_id, safe="()/:?=&"),
            urllib.parse.quote(db_name, safe="()/:?=&"),
            urllib.parse.quote(title, safe="()"),
            urllib.parse.quote("", safe="()/:?=&"),
            urllib.parse.quote(source, safe="()/:?=&"),
            urllib.parse.quote(pub_date, safe="()/:?=&"),
        ]
    )

    # 构建新URL
    download_url = f"https://api2.sjuku.top/download.php?{query_part}&;ddata={ddata_str_encoded}"
    return download_url

def convert_download_url_site_3(
    orig_url, file_id, db_name, title, authors, source, pub_date
):
    # 获取查询参数部分 - 确保保持原始编码格式
    query_part = orig_url.split("?")[1]

    # 替换&为&amp;以匹配JavaScript行为
    query_part = query_part.replace("&", "&amp;")

    # 构建ddata参数 - 使用原始的URL编码函数，不对:进行编码
    # f"{file_id}|{db_name}|{title}||{source}|{pub_date}"

    ddata_str_encoded = "|".join(
        [
            urllib.parse.quote(file_id, safe="()/:?=&"),
            urllib.parse.quote(db_name, safe="()/:?=&"),
            urllib.parse.quote(title, safe="()"),
            urllib.parse.quote("", safe="()/:?=&"),
            urllib.parse.quote(source, safe="()/:?=&"),
            urllib.parse.quote(pub_date, safe="()/:?=&"),
        ]
    )

    # 构建新URL
    download_url = f"https://api1.sjuku.top/download.php?{query_part}&amp;ddata={ddata_str_encoded}"
    return download_url


def convert_download_url_site_2(
    orig_url,
    file_id=None,
    db_name=None,
    title=None,
    authors=[],
    source=None,
    pub_date=None,
):
    """
    将CNKI原始URL转换为加密的下载URL

    Args:
        orig_url: 原始CNKI URL，例如https://kns.cnki.net/kcms2/article/abstract?v=...
        file_id: 文件ID，例如HJJZ20250328001
        db_name: 数据库名称，例如CAPJ
        pub_date: 发布日期，例如2025-03-28 17:16

    Returns:
        加密的下载URL
    """
    # 提取URL中的v参数
    match = re.search(r"v=([^&]+)", orig_url)
    if not match:
        raise ValueError("无法从URL中提取v参数")

    v_param = match.group(1)

    # 进行解码处理（因为URL可能是编码过的）
    v_param = v_param.replace("&amp;", "&")

    # 使用固定密钥加密数据
    encryption_key = "Q5vGEmoCW59MW4Bc"  # 从JavaScript代码中提取的密钥
    encrypted_data = encrypt(v_param, encryption_key)

    # 生成带校验和的时间戳
    timestamp = generate_timestamp_with_check()

    # 构建下载URL
    download_url = (
        f"https://api88.wenxian.shop/v1/api/download?dflag=pdfdown&v={encrypted_data}"
    )

    # 添加可选参数
    if file_id:
        download_url += f"&fileid={file_id}"
    if db_name:
        download_url += f"&dataDbname={db_name}"
    if pub_date:
        # URL编码空格
        encoded_date = pub_date.replace(" ", "%20")
        download_url += f"&pd={encoded_date}"

    # 添加时间戳
    download_url += f"&t={timestamp}"

    return download_url


def random_page(
    site_id, num_pages, config, page_size=50, sci_only=True, metadata="./metadata.json"
):
    # 读取数据并计算总数
    categories_data, total_count = read_metadata(metadata)

    # 打印结果
    print(f"总文章数量: {total_count}")

    # 按文章数量排序的所有分类
    print("\n按文章数量排序的分类:")
    sorted_categories = sorted(
        categories_data.items(), key=lambda x: x[1]["size"], reverse=True
    )

    # 计算权重 - 使用分类大小作为权重
    categories = []
    weights = []

    for category_code, category_info in sorted_categories:

        categories.append((category_code, category_info))
        weights.append(category_info["size"])

    # 归一化权重
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()

    # 显示所有分类及其权重
    for i, ((category_code, category_info), weight) in enumerate(
        zip(categories, weights), 1
    ):
        print(
            f"{i}. {category_code}: {category_info['name']} - {category_info['size']}篇 (权重: {weight:.4f})"
        )

    # 总页数计数器
    num_pages_feteched = 0

    # 当尚未达到总页数要求时，继续抓取
    while num_pages_feteched < num_pages:
        # 使用权重随机选择一个分类
        random_category_idx = np.random.choice(len(categories), p=weights)
        category_code, category_info = categories[random_category_idx]

        print(
            f"\n随机选择分类: {category_code}: {category_info['name']} (权重: {weights[random_category_idx]:.4f})"
        )

        # 计算该分类的最大页数（每页50条记录） 随机选择一个页码
        random_page = random.randint(1, min((category_info['size'] + page_size - 1) // page_size, 300))
        
        print(f"开始抓取分类 {category_code} ({category_info['name']}) 第 {random_page} 页")
        
        # 搜索并保存，获取是否实际发送了请求的标志
        publications, not_cached = search_and_save(
            site_id, category_code, config, sci_only, random_page, page_size
        )

        # 增加计数器
        if len(publications) > 0:
            num_pages_feteched += 1
            print(f"总进度: {num_pages_feteched}/{num_pages}")

        # 延迟，避免请求过于频繁
        if not_cached and num_pages_feteched < num_pages and len(publications) > 0:
            delay = random.uniform(2, 5)  # 随机延迟2-5秒
            print(f"等待 {delay:.2f} 秒后继续...")
            time.sleep(delay)


# 示例使用
"""
if __name__ == "__main__":
    # 示例原始URL
    breakpoint()
    original_url = "https://kns.cnki.net/kcms2/article/abstract?v=aR5N6Ks7Vo3RGDDNBJroVO7oWxEMUMYGd6ZUo5ii1rQ6kj6S3UXiBtvTZOgKO9BeMEK5q7iQxVCFe38_NNzQ4wlQoCBrGY5w5x-Mkwt6FukHk5r25NiT5Bagvha9ZHOCxP09h-5gK3BOn2H5L4KbWZY6ad2i4mIhUVzQJ4M-LF1uMjr9Rq6Pez4-21Ru7ZqU&uniplatform=NZKPT&language=CHS"
    
    # 其他参数
    file_id = "HJJZ20250328001"
    db_name = "CAPJ"
    pub_date = "2025-03-28 17:16"
    
    # 转换URL
    download_url = convert_cnki_url(original_url, file_id, db_name, pub_date)
    print("原始URL:", original_url)
    print("转换后的下载URL:", download_url)
"""


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="按分类号搜索CNKI并保存结果为NDJSON格式"
    )
    parser.add_argument("-c", "--config", required=True, help="指定JSON配置文件的路径")
    parser.add_argument("-S", "--sci", action="store_true", help="只搜索SCI收录的文献")
    parser.add_argument(
        "-s", "--site-id", required=True, help="site_tag"
    )
    parser.add_argument(
        "-m", "--metadata", default="./metadata.json", help="指定metadata.json文件路径"
    )
    parser.add_argument("-p", "--page", type=int, default=1, help="起始页码，默认为1")
    parser.add_argument(
        "-n",
        "--pages-per-category",
        type=int,
        default=5,
        help="每个分类抓取的页数，默认为5。设为-1表示抓取全部页面",
    )
    parser.add_argument(
        "-z", "--page-size", type=int, default=50, help="每页结果数，默认为50"
    )
    parser.add_argument(
        "-C", "--category-code", action="store_true", help="指定JSON配置文件的路径"
    )
    parser.add_argument(
        "-t",
        "--total-pages",
        type=int,
        default=None,
        help="指定总共要抓取的页数，默认为None，表示由pages-per-category决定",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 读取配置文件
    config = read_config(args.config)
    random_page(
        args.site_id, args.total_pages, config, args.page_size, args.sci, args.metadata
    )
    # publications, not_cached = search_and_save(args.site_id, "N1", config, False, 1, 50)


if __name__ == "__main__":
    main()
