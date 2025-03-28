#!/usr/bin/env python
# CREATED DATE: Fri Mar 28 14:58:54 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com

import requests
from bs4 import BeautifulSoup
import re
import json
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

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def search_cnki_by_category(category_code, page=1, page_size=50, sci_only=False, cookies=None):
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
    url = "http://222.186.61.87:8085/kns8s/brief/grid"
    
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
        
        # 查询节点，包含所有查询条件，必需
        "QNode": {
            # 查询组，包含一个或多个查询条件组，必需
            "QGroup": [
                {
                    # 第一个查询组 - 分类号查询
                    "Key": "Subject",     # 键名，标识查询组类型，必需
                    "Title": "",          # 标题，通常为空，可选
                    "Logic": 0,           # 逻辑关系，0表示AND，必需
                    "Items": [            # 查询项，包含具体的检索条件，必需
                        {
                            "Field": "CLC",           # 字段名，CLC表示分类号，必需
                            "Value": category_code,   # 查询值，必需
                            "Operator": "SUFFIX",     # 操作符，SUFFIX表示前缀匹配，必需
                            "Logic": 0,               # 逻辑关系，0表示AND，在多条件时必需
                            "Title": "分类号"         # 标题，显示用，可选
                        }
                    ],
                    "ChildItems": []      # 子项，可以包含更复杂的嵌套条件，可选
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
        "SearchFrom": 4 if page > 1 else 2
    }
    
    # 添加SCI过滤条件（如果需要）
    if sci_only:
        # SCI过滤条件组
        sci_filter = {
            "Key": "SCDBGroup",   # 特殊键名，用于文献源数据库分组，必需
            "Title": "",          # 标题，通常为空，可选
            "Logic": 0,           # 逻辑关系，0表示AND，必需
            "Items": [],          # 条件项，这里为空，因为使用子项定义，可选
            "ChildItems": [       # 子项目，包含具体的数据库筛选条件，必需
                {
                    "Key": "LYBSM",   # 文献源标识码键名，必需
                    "Title": "",      # 标题，通常为空，可选
                    "Logic": 0,       # 逻辑关系，0表示AND，必需
                    "Items": [        # 条件项，包含SCI的特定条件，必需
                        {
                            "Key": "P0201",       # SCI数据库的代码，必需
                            "Title": "SCI",       # 显示名称，可选
                            "Logic": 1,           # 1表示OR关系，必需
                            "Field": "LYBSM",     # 字段名，必需
                            "Operator": "DEFAULT", # 操作符，必需
                            "Value": "P0201",     # 值，对应SCI代码，必需
                            "Value2": "",         # 第二个值，范围查询时使用，可选
                            "Name": "LYBSM",      # 字段名称，可选
                            "ExtendType": 0       # 扩展类型，可选
                        }
                    ],
                    "ChildItems": []  # 子子项，这里为空，可选
                }
            ]
        }
        
        # 将SCI过滤条件添加到查询组
        query_json["QNode"]["QGroup"].append(sci_filter)
    
    # 构建表单数据
    data = {
        "boolSearch": "false",  # 对所有页面都是false
        "QueryJson": json.dumps(query_json),
        "pageNum": page,
        "pageSize": page_size,
        "sortField": "PT",         # PT表示按发表时间排序
        "sortType": "desc",        # 所有页面都是小写desc
        "dstyle": "listmode",      # 列表模式
        "boolSortSearch": "false", # 必需参数
        "productStr": "YSTT4HG0,LSTPFY1C,RMJLXHZ3,JQIRZIYA,JUP3MUPD,1UR4K4HZ,BPBAFJ5S,R79MZMCB,MPMFIG1A,EMRPGLPA,J708GVCE,ML4DRIDX,WQ0UVIAA,NB3BWEHK,XVLO76FD,HR1YT1Z9,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R,",
        "aside": "" if page > 1 else f"分类号：{category_code}",  # 第一页有，后续页面为空
        "searchFrom": "资源范围：总库",
        "subject": "",
        "language": "",
        "uniplatform": ""
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
        "Referer": "http://222.186.61.87:8085/kns8s/defaultresult/index"
    }
    
    # 如果没有提供cookies，使用默认cookies
    if not cookies:
        cookies = {
            "SID_kns_new": "kns2618106",
            "knsLeftGroupSelectItem": "",
            "SID_sug": "018107",
            "SID_restapi": "018107",
            "dblang": "both",
            "dsorders": "PT",
            "dsortypes": "cur DESC"
        }
    
    # 发送HTTP请求
    try:
        response = requests.post(url, data=data, headers=headers, cookies=cookies, verify=False)
        response.raise_for_status()  # 检查是否有HTTP错误
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        print(f"请求URL: {url}")
        print(f"请求参数: {data}")
        return ""

def extract_publications(html_content, category_code):
    """
    从HTML响应中提取出版物信息
    
    参数:
    html_content (str): HTML格式的搜索结果
    category_code (str): 分类号
    
    返回:
    list: 出版物信息列表，每个出版物是一个字典
    """
    if not html_content:
        print("警告: 收到空的HTML内容")
        return []
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    publications = []
    
    # 查找表格中的所有行（每行代表一篇文献）
    rows = soup.find_all('tr')
    
    if not rows:
        print("警告: 在HTML中未找到任何行")
        return []
        
    for row in rows:
        try:
            # 跳过表头行
            if not row.find('td', class_='name'):
                continue
                
            # 提取标题
            title_element = row.find('td', class_='name').find('a', class_='fz14')
            title = title_element.get_text(strip=True) if title_element else "N/A"
            
            # 移除标题中的字体标签
            title = re.sub(r'<font.*?>|</font>', '', title)
            
            # 提取下载链接
            download_link = title_element.get('href') if title_element else None
            
            # 提取作者
            authors_element = row.find('td', class_='author')
            authors = []
            if authors_element:
                author_links = authors_element.find_all('a', class_='KnowledgeNetLink')
                for author in author_links:
                    authors.append(author.get_text(strip=True))
            
            # 提取来源（期刊/会议名称）
            source_element = row.find('td', class_='source').find('a')
            source = source_element.get_text(strip=True) if source_element else "N/A"
            
            # 提取日期
            date_element = row.find('td', class_='date')
            date = date_element.get_text(strip=True) if date_element else "N/A"
            
            publications.append({
                'title': title,
                'authors': ','.join(authors),
                'source': source,
                'date': date,
                'url': download_link,
                'category': category_code  # 添加分类号
            })
            
        except Exception as e:
            print(f"提取出版物时出错: {e}")
    
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
    filename = os.path.join(ndjson_dir, f"cnki_{category_code}_p{page}_{timestamp}.json")
    
    # 写入NDJSON文件
    with open(filename, 'w', encoding='utf-8') as f:
        for pub in publications:
            f.write(json.dumps(pub, ensure_ascii=False) + '\n')
    
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
        with open(latest_file, 'r', encoding='utf-8') as f:
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
    valid_records = sum(1 for record in records if record.get('url'))
    
    return True, matching_files, valid_records

def search_and_save(category_code, config, sci_only=False, page=1, page_size=50):
    """
    按分类号搜索CNKI并保存结果
    
    参数:
    category_code (str): 分类号，例如 'V'
    config (dict): 配置信息
    sci_only (bool): 是否只搜索SCI收录的文献
    page (int): 页码
    page_size (int): 每页结果数
    
    返回:
    list: 出版物信息列表
    """
    # 获取ndjson目录
    ndjson_dir = config.get("ndjson_dir", "./")
    
    # 确保ndjson_dir是目录而不是通配符模式
    ndjson_dir = os.path.dirname(ndjson_dir) if '*' in ndjson_dir else ndjson_dir
    
    # 检查是否已存在符合条件的文件
    file_exists, matching_files, valid_records = check_existing_file(ndjson_dir, category_code, page)
    
    # 如果文件存在并且有有效记录，直接返回
    if file_exists and valid_records > 0:
        print(f"分类 {category_code} 第 {page} 页: 已存在 {valid_records} 条有效记录，跳过请求")
        # 读取最新的文件中的记录
        latest_file = sorted(matching_files)[-1]
        publications = []
        with open(latest_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    publications.append(record)
                except json.JSONDecodeError:
                    continue
        return publications
    
    # 从配置中获取cookies
    cookies_str = config.get("cookies", "")
    cookies = {}
    
    # 解析cookies字符串
    if cookies_str:
        for item in cookies_str.split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
    
    # 搜索CNKI
    html_content = search_cnki_by_category(category_code, page, page_size, sci_only, cookies)
    
    # 提取出版物信息
    publications = extract_publications(html_content, category_code)
    
    # 保存为NDJSON
    if publications:
        save_to_ndjson(publications, ndjson_dir, category_code, page)
        print(f"分类 {category_code} 第 {page} 页: 成功找到 {len(publications)} 条记录")
    else:
        print(f"分类 {category_code} 第 {page} 页: 未找到匹配的出版物")
    
    return publications

def read_metadata(file_path='./metadata.json'):
    """
    读取metadata.json文件，返回分类数据字典并计算总文章数量
    
    参数:
    file_path (str): JSON文件路径
    
    返回:
    tuple: (分类数据字典, 总文章数量)
    """
    try:
        # 打开并读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 获取SCI分类数据
        sci_data = data.get('SCI', {})
        
        # 计算总文章数量
        total_articles = sum(category['size'] for category in sci_data.values())
        
        return sci_data, total_articles
    
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 未找到")
        return {}, 0
    except json.JSONDecodeError:
        print(f"错误: '{file_path}' 不是有效的JSON文件")
        return {}, 0
    except Exception as e:
        print(f"读取文件时发生错误: {str(e)}")
        return {}, 0

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="按分类号搜索CNKI并保存结果为NDJSON格式")
    parser.add_argument("-c", "--config", required=True, help="指定JSON配置文件的路径")
    parser.add_argument("-s", "--sci", action="store_true", help="只搜索SCI收录的文献")
    parser.add_argument("-m", "--metadata", default="./metadata.json", help="指定metadata.json文件路径")
    parser.add_argument("-p", "--page", type=int, default=1, help="起始页码，默认为1")
    parser.add_argument("-n", "--pages-per-category", type=int, default=5, help="每个分类抓取的页数，默认为5。设为-1表示抓取全部页面")
    parser.add_argument("-z", "--page-size", type=int, default=50, help="每页结果数，默认为50")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 读取配置文件
    config = read_config(args.config)

    # 读取数据并计算总数
    sci_data, total_count = read_metadata(args.metadata)
    
    # 打印结果
    print(f"总文章数量: {total_count}")
    
    # 按文章数量排序的所有分类
    print("\n按文章数量排序的分类:")
    sorted_categories = sorted(sci_data.items(), key=lambda x: x[1]['size'], reverse=True)
    
    for i, (code, info) in enumerate(sorted_categories, 1):
        category_size = info['size']
        
        # 计算该分类的最大页数（每页50条记录）
        max_pages = (category_size + args.page_size - 1) // args.page_size
        
        # 确定要抓取的页数
        if args.pages_per_category == -1:
            # 如果pages_per_category为-1，抓取全部页面
            pages_to_fetch = max_pages
        else:
            # 否则，取指定页数和最大页数的较小值
            pages_to_fetch = min(args.pages_per_category, max_pages)
        
        print(f"{i}. {code}: {info['name']} - {category_size}篇 (最大页数: {max_pages}, 计划抓取: {pages_to_fetch}页)")
        
        # 对每个分类，抓取指定数量的页面
        total_publications = 0
        for page_offset in range(pages_to_fetch):
            current_page = args.page + page_offset
            print(f"\n开始抓取分类 {code} ({info['name']}) 第 {current_page} 页 (总进度: {page_offset+1}/{pages_to_fetch})")
            
            publications = search_and_save(code, config, args.sci, current_page, args.page_size)
            total_publications += len(publications)
            
            # 如果当前页没有结果，认为已到最后一页，停止抓取此分类
            if len(publications) == 0:
                print(f"分类 {code} 没有更多结果，停止抓取")
                break
            
            # 每次请求之间暂停一下，避免请求过于频繁
            if page_offset < pages_to_fetch - 1 and len(publications) > 0:
                delay = random.uniform(2, 5)  # 随机延迟2-5秒
                print(f"等待 {delay:.2f} 秒后继续...")
                time.sleep(delay)
        
        print(f"分类 {code} ({info['name']}) 共抓取 {total_publications} 条记录")
        
        # 每个分类之间暂停一下，避免请求过于频繁
        if i < len(sorted_categories):
            delay = random.uniform(5, 10)  # 随机延迟5-10秒
            print(f"等待 {delay:.2f} 秒后继续下一个分类...")
            time.sleep(delay)
    
    print("\n所有分类抓取完成!")
if __name__ == "__main__":
    main()
