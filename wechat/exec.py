import requests
from openpyxl import Workbook
import time
import random
import re
import os
from tqdm import tqdm
from pathlib import Path

FAKE_ID = "MzA4MDE0NzI0Mg"
FAKE_ID = "MzI0Njc5ODM4MQ"
TOKEN = "1035530437"


headers = {
    "cookie": "appmsglist_action_3957525676=card; pgv_pvid=1548114866; RK=n9MUUN8nM/; ptcz=4ee0340b09f43f7b22c54401180c8a984fe74218a4386268887ee33d59527044; eas_sid=61V7Q3Q2B4d5L1O3m5I9B5b852; ua_id=khweIcWptd8JmvvwAAAAAETqnoW1zVqn_ka7nh9I928=; wxuin=32534822856711; fqm_pvqid=40dbbbce-b423-4225-95d6-22890d41bff4; mm_lang=zh_CN; o2_uin=1242545768; pac_uid=0_N91etjDcx372j; _qimei_uuid42=191070a320a10033ecb58f026f8b505693fce519ed; _qimei_fingerprint=e305b881c89032f5a69a690a157fed57; _qimei_h38=2db81a77ecb58f026f8b505602000007019107; _qimei_q32=b72f08c7db969f33122f6f1d050b88bb; _qimei_q36=e794d1fb9f23f0bbf7ac6d76300011918b10; qq_domain_video_guid_verify=892bf548bd7d69c0; _clck=3957525676|1|fsx|0; uuid=c771c1f297b6f06202fdd87d01f5127b; rand_info=CAESIFGkimRLeNCrYRHkK/WV98Yw0SfDoWnoY2UcneZfGlBB; slave_bizuin=3957525676; data_bizuin=3957525676; bizuin=3957525676; data_ticket=ksxENE2q4FuX5CoVae6sKtncecWzHSNllAb+pL6W2mZGSzbDicpqd8Onb/HX+0DS; slave_sid=RnlMYm1vTnNXdXA2QkZ4MmR3Z0hDc2R3OExLSmdMVnVmRFFJaTZvYlU4R3c5aGNkNUthN3NyUjNfZkZpc3Iwam43N1R4SE12bk9kWVlyUjlCcnRkb2RjZURYdmtlSmFBRHJaTUZPajFrSzF3cTZPejlMRG9JbVRjVnBLdW8wNm9lUmY3eXMyTDBJbkc3T3Fu; slave_user=gh_63f4fbfefa04; xid=9e569bb2a2d0945f167c18c9c6047718; _clsk=1y4u44g|1737994425708|5|1|mp.weixin.qq.com/weheat-agent/payload/record",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
}
"""
cookie = "appmsglist_action_3964485035=card; ua_id=TsvXzRqzGo9yUWmnAAAAAPULYybLD0J-9iwrrIkAZN8=; wxuin=38060347467740; _clck=1o25m79|1|fsy|0; uuid=929ddaa96c0b153cc1387840c8a65684; rand_info=CAESIGct3GYdEgdFLIC6aAjzycmEkJp0Ov44/l5QZMrRW5Bz; slave_bizuin=3964485035; data_bizuin=3964485035; bizuin=3964485035; data_ticket=qlM10L7NAbFPvY0bknfJWUC6Rca4ORk+S+sZnAXKCqiuQwd8KKIjdgax4vpOZwhL; slave_sid=QzlhYjhTV193RXZudmpmVEh4YlFlMWRTRzRMR1VRZDF5ZHFHSnBzUVlKYzhORWc5aVJPd29POTM2WndBUnROR0FJbDZiN05kNEdxRjRXeU1kNVVPeUpjRjVXWjRLNGVpRnBMYW9lejBEa0psem9Vb2paeGswcjFUOVdROHU1eVpBakp1NVRoSU90NmNheDJV; slave_user=gh_a6db003f2b77; xid=aa39945033448717096380fbb94ba4a5; mm_lang=en_US; _clsk=111sfue|1738060373679|3|1|mp.weixin.qq.com/weheat-agent/payload/record"
headers = {
    "cookie": cookie,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
}
"""

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


page = 0
counter = 0
Path(f"./{FAKE_ID}").mkdir(parents=True, exist_ok=True) 
while True:
    url = (
        "https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&search_field=null&begin="
        + str(page * 20)
        + f"&count=20&query=&fakeid={FAKE_ID}%3D%3D&type=101_1&free_publish_type=1&sub_action=list_ex&token={TOKEN}&lang=zh_CN&f=json&ajax=1"
    )
    res = requests.get(url, headers=headers).text
    # print(res)
    if "link" not in res:
        break
    for title in tqdm(re.findall('"link":"(.*?)","', res.replace("\\", ""))):
        try:
            title_id =  os.path.basename(title)
            with open(f"./{FAKE_ID}/{counter:04d}-{title_id}.txt", "w") as f: 
                # print(title)
                content = requests.get(title, headers=headers).text
                content_1 = "".join(content.splitlines()).replace("\t", "").replace(" ", "")
                wb = extract_text_from_html(content_1).replace("\t", "").replace(" ", "")
                # print(wb)
                f.write(wb + "\n")
                f.flush()
                time.sleep(random.randint(2, 4))
        except Exception as e: 
            breakpoint()
            pass
        counter += 1
    print("\n")
    page += 1
    time.sleep(2)
