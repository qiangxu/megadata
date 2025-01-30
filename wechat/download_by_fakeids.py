import requests
from openpyxl import Workbook
import time
import random
import re
import os
import json
import glob
from tqdm import tqdm
from pathlib import Path
import argparse
import sys

TOKEN = "1035530437"
COOKIE = "appmsglist_action_3957525676=card; pgv_pvid=1548114866; RK=n9MUUN8nM/; ptcz=4ee0340b09f43f7b22c54401180c8a984fe74218a4386268887ee33d59527044; eas_sid=61V7Q3Q2B4d5L1O3m5I9B5b852; ua_id=khweIcWptd8JmvvwAAAAAETqnoW1zVqn_ka7nh9I928=; wxuin=32534822856711; fqm_pvqid=40dbbbce-b423-4225-95d6-22890d41bff4; mm_lang=zh_CN; o2_uin=1242545768; pac_uid=0_N91etjDcx372j; _qimei_uuid42=191070a320a10033ecb58f026f8b505693fce519ed; _qimei_fingerprint=e305b881c89032f5a69a690a157fed57; _qimei_h38=2db81a77ecb58f026f8b505602000007019107; _qimei_q32=b72f08c7db969f33122f6f1d050b88bb; _qimei_q36=e794d1fb9f23f0bbf7ac6d76300011918b10; qq_domain_video_guid_verify=892bf548bd7d69c0; _clck=3957525676|1|fsx|0; uuid=c771c1f297b6f06202fdd87d01f5127b; rand_info=CAESIFGkimRLeNCrYRHkK/WV98Yw0SfDoWnoY2UcneZfGlBB; slave_bizuin=3957525676; data_bizuin=3957525676; bizuin=3957525676; data_ticket=ksxENE2q4FuX5CoVae6sKtncecWzHSNllAb+pL6W2mZGSzbDicpqd8Onb/HX+0DS; slave_sid=RnlMYm1vTnNXdXA2QkZ4MmR3Z0hDc2R3OExLSmdMVnVmRFFJaTZvYlU4R3c5aGNkNUthN3NyUjNfZkZpc3Iwam43N1R4SE12bk9kWVlyUjlCcnRkb2RjZURYdmtlSmFBRHJaTUZPajFrSzF3cTZPejlMRG9JbVRjVnBLdW8wNm9lUmY3eXMyTDBJbkc3T3Fu; slave_user=gh_63f4fbfefa04; xid=9e569bb2a2d0945f167c18c9c6047718; _clsk=1y4u44g|1737994425708|5|1|mp.weixin.qq.com/weheat-agent/payload/record"

def extract_text_from_html(html):
    pattern = r"<section[^>]*>(?:<(?!section|p)[^>]*>)*([^<]*)((?:<(?!section|p)[^>]*>)*)(?:<\/(?!section|p)[^>]*>)*<\/section>|<p[^>]*>(?:<(?!section|p)[^>]*>)*([^<]*)((?:<(?!section|p)[^>]*>)*)(?:<\/(?!section|p)[^>]*>)*<\/p>"
    matches = re.findall(pattern, html)
    text = ""
    for match in matches:
        if match[0]:
            text += match[0] + " "
        if match[2]:
            text += match[2] + " "
    return text

def get_posts(fakeid, token=TOKEN, cookie=COOKIE):
    fakeid=fakeid.strip().strip('==')
    if os.path.exists(f"./metadata/{fakeid}.json"):
        return 

    page = 0
    print("FAKEID: ", fakeid)
    res = {}
    total_count = 10000
    with tqdm(
        total=total_count
    ) as pbar:

        while len(res) < total_count:
            url = (
                "https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&search_field=null&begin="
                + str(page * 20)
                + f"&count=20&query=&fakeid={fakeid}%3D%3D&type=101_1&free_publish_type=1&sub_action=list_ex&token={token}&lang=zh_CN&f=json&ajax=1"
            )
            response = requests.get(url, headers={
                "cookie": cookie,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
                }).text
            total_count = json.loads(json.loads(response)['publish_page'])['total_count']
            posts = json.loads(json.loads(response)['publish_page'])['publish_list']
            
            if len(posts) == 0: 
                break

            with open(f"./metadata/{fakeid}.json", 'a+', encoding='utf-8') as f:
                for p in posts:
                    if len(p['publish_info']) > 10:
                        p = json.loads(p['publish_info'])
                        p_id = p['appmsgex'][0]['appmsgid'] 

                        f.write(json.dumps(p))
                        f.write("\n")

                        res[p_id] = p

            page += 1
            time.sleep(random.randint(1, 10) / 10) 
            pbar.update(20 * 10000 / total_count )

def crawl_account(fakeid, token=TOKEN, cookie=COOKIE): 
    fakeid=fakeid.strip().strip('==')
    print("FAKEID: ", fakeid)
    Path(f"./{fakeid}").mkdir(parents=True, exist_ok=True) 
    
    if not glob.glob(f"./metadata/{fakeid}.json"):
        get_posts(fakeid, token=token, cookie=cookie)

    with open(f"./metadata/{fakeid}.json", 'r', encoding='utf-8') as f:
        posts = f.readlines()

    posts = [json.loads(p) for p in posts]
    random.shuffle(posts)
        
    for post in tqdm(posts):
        post_id = post['appmsgex'][0]['appmsgid']

        is post['appmsgex'][0]['is_deleted']:
            continue 

        if glob.glob(f"{fakeid}/{post_id}*.txt"):
            continue 
        
        title = post['appmsgex'][0]['title']

        link = post['appmsgex'][0]['link']

        with open(f"./{fakeid}/{post_id}.txt", "w") as f: 
            print(post_id, title)
            content = "".join(requests.get(link, headers={
                "cookie" : cookie, 
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
                }).text.splitlines()).replace("\t", "").replace(" ", "")
            wb = extract_text_from_html(content).replace("\t", "").replace(" ", "")
            f.write(wb + "\n")
            time.sleep(random.randint(1, 10) / 10)

def read_config(config_file):
    """
    读取并解析 JSON 配置文件
    
    Args:
        config_file (str): 配置文件路径
        
    Returns:
        dict: 解析后的配置数据
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
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
    breakpoint()
    parser = argparse.ArgumentParser(description='读取JSON配置文件')
    parser.add_argument('-c', '--config', 
                        required=False,
                        help='指定JSON配置文件的路径')
    
    # 解析命令行参数
    args = parser.parse_args()
 
    with open("fakeids.csv", 'r', encoding='utf-8') as f:
        fakeids = f.readlines()
  
    if args.config: 
        # 读取配置文件
        config = read_config(args.config)
        cookie = config['cookie']
        token = config['token']    
        random.shuffle(fakeids)
    else: 
        cookie = COOKIE
        token = TOKEN

    for fakeid in tqdm(fakeids): 
        try:
            #get_posts(fakeid, token=token, cookie=cookie)
            crawl_account(fakeid, token=token, cookie=cookie)
            time.sleep(30)
        except Exception as e: 
            breakpoint()
            pass
        #crawl_account(fakeid)

if __name__ == '__main__':
    main()

