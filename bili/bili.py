import os
import subprocess
import pandas
import requests
import hashlib
import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import re
from http.cookies import SimpleCookie


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()

MAGIC_A = "ea1db124af3c7062474693fa704f4ff8"

KOL_ID = "315846984"
c = SimpleCookie()
c.load(
    "b_lsid=B1107956F_194A8EB3D2B; CURRENT_FNVAL=16; buvid_fp=B393256B-BF20-BBAD-CAF2-67EF5E9C5F8A11329infoc; buvid_fp_plain=undefined; buvid4=2089B47A-058D-4476-F3E9-88391E42DCAB59581-025012709-qFV2siRLP4dbeyiSCgJ77w%3D%3D; browser_resolution=1387-795; enable_feed_channel=DISABLE; enable_web_push=DISABLE; header_theme_version=CLOSE; home_feed_column=4; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzgyNTExMjgsImlhdCI6MTczNzk5MTg2OCwicGx0IjotMX0.nLtTWdmP3ICG1PRSxmBoKzEos819umn3nXPVV8ZDEtE; bili_ticket_expires=1738251068; fingerprint=af2497dc0e694ceb47be4a0ca0e10ffa; is-2022-channel=1; sid=50ca60q9; _uuid=6FA102BC7-FA88-43FB-A55D-C3C55F108310E259459infoc; rpdid=|(u|u)k~JYuk0J'u~kRJu~JRJ; b_nut=1718957611; buvid3=B393256B-BF20-BBAD-CAF2-67EF5E9C5F8A11329infoc"
)
cookies = {k: v.value for k, v in c.items()}
headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "origin": "https://space.bilibili.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": f"https://space.bilibili.com/{KOL_ID}/upload/video",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}


def getvideolink():

    videourls = []
    for pn in range(1, 5):
        url = f"https://api.bilibili.com/x/space/wbi/arc/search?pn={pn}&ps=40&tid=0&special_type=&order=pubdate&mid={KOL_ID}&index=0&keyword=&order_avoided=true&platform=web&web_location=333.1387&dm_img_list=[%7B%22x%22:2043,%22y%22:1344,%22z%22:0,%22timestamp%22:57531,%22k%22:68,%22type%22:0%7D,%7B%22x%22:2047,%22y%22:1332,%22z%22:6,%22timestamp%22:57632,%22k%22:116,%22type%22:0%7D,%7B%22x%22:2260,%22y%22:1410,%22z%22:187,%22timestamp%22:57732,%22k%22:89,%22type%22:0%7D,%7B%22x%22:2391,%22y%22:1513,%22z%22:310,%22timestamp%22:57832,%22k%22:62,%22type%22:0%7D,%7B%22x%22:2200,%22y%22:1315,%22z%22:117,%22timestamp%22:57933,%22k%22:84,%22type%22:0%7D,%7B%22x%22:2297,%22y%22:1405,%22z%22:212,%22timestamp%22:58105,%22k%22:61,%22type%22:0%7D,%7B%22x%22:2523,%22y%22:1599,%22z%22:419,%22timestamp%22:58215,%22k%22:118,%22type%22:0%7D,%7B%22x%22:2610,%22y%22:1707,%22z%22:328,%22timestamp%22:58316,%22k%22:113,%22type%22:0%7D,%7B%22x%22:2962,%22y%22:2319,%22z%22:383,%22timestamp%22:58416,%22k%22:110,%22type%22:0%7D,%7B%22x%22:3441,%22y%22:2849,%22z%22:755,%22timestamp%22:58517,%22k%22:116,%22type%22:0%7D,%7B%22x%22:3543,%22y%22:2972,%22z%22:817,%22timestamp%22:58621,%22k%22:90,%22type%22:0%7D,%7B%22x%22:3944,%22y%22:3757,%22z%22:1170,%22timestamp%22:58721,%22k%22:101,%22type%22:0%7D,%7B%22x%22:3229,%22y%22:3121,%22z%22:149,%22timestamp%22:58837,%22k%22:91,%22type%22:0%7D,%7B%22x%22:3114,%22y%22:3007,%22z%22:31,%22timestamp%22:58943,%22k%22:78,%22type%22:0%7D,%7B%22x%22:4124,%22y%22:4020,%22z%22:917,%22timestamp%22:59051,%22k%22:70,%22type%22:0%7D,%7B%22x%22:4119,%22y%22:3601,%22z%22:797,%22timestamp%22:64370,%22k%22:105,%22type%22:0%7D,%7B%22x%22:2831,%22y%22:3483,%22z%22:668,%22timestamp%22:64470,%22k%22:117,%22type%22:0%7D,%7B%22x%22:5302,%22y%22:3517,%22z%22:1664,%22timestamp%22:102188,%22k%22:83,%22type%22:0%7D,%7B%22x%22:5097,%22y%22:3163,%22z%22:1768,%22timestamp%22:102289,%22k%22:114,%22type%22:0%7D,%7B%22x%22:3707,%22y%22:1766,%22z%22:376,%22timestamp%22:102531,%22k%22:64,%22type%22:0%7D,%7B%22x%22:5206,%22y%22:2807,%22z%22:1777,%22timestamp%22:102632,%22k%22:64,%22type%22:0%7D,%7B%22x%22:4099,%22y%22:1155,%22z%22:557,%22timestamp%22:102737,%22k%22:108,%22type%22:0%7D,%7B%22x%22:4716,%22y%22:1758,%22z%22:1170,%22timestamp%22:103341,%22k%22:120,%22type%22:0%7D,%7B%22x%22:4893,%22y%22:1928,%22z%22:1345,%22timestamp%22:103444,%22k%22:60,%22type%22:0%7D,%7B%22x%22:5369,%22y%22:2396,%22z%22:1822,%22timestamp%22:103562,%22k%22:74,%22type%22:0%7D,%7B%22x%22:4194,%22y%22:975,%22z%22:695,%22timestamp%22:103663,%22k%22:93,%22type%22:0%7D,%7B%22x%22:6357,%22y%22:2574,%22z%22:2917,%22timestamp%22:103764,%22k%22:69,%22type%22:0%7D,%7B%22x%22:6226,%22y%22:2435,%22z%22:2787,%22timestamp%22:103869,%22k%22:85,%22type%22:0%7D,%7B%22x%22:5605,%22y%22:1824,%22z%22:2159,%22timestamp%22:103971,%22k%22:76,%22type%22:0%7D,%7B%22x%22:3662,%22y%22:-118,%22z%22:213,%22timestamp%22:104085,%22k%22:105,%22type%22:0%7D,%7B%22x%22:7251,%22y%22:3675,%22z%22:3213,%22timestamp%22:104186,%22k%22:114,%22type%22:0%7D,%7B%22x%22:5162,%22y%22:1682,%22z%22:997,%22timestamp%22:104287,%22k%22:116,%22type%22:0%7D,%7B%22x%22:5941,%22y%22:5426,%22z%22:2817,%22timestamp%22:178285,%22k%22:75,%22type%22:0%7D,%7B%22x%22:5764,%22y%22:5171,%22z%22:2644,%22timestamp%22:178388,%22k%22:118,%22type%22:0%7D,%7B%22x%22:3860,%22y%22:3425,%22z%22:657,%22timestamp%22:178489,%22k%22:78,%22type%22:0%7D,%7B%22x%22:5707,%22y%22:5370,%22z%22:2440,%22timestamp%22:178593,%22k%22:77,%22type%22:0%7D,%7B%22x%22:3929,%22y%22:3070,%22z%22:503,%22timestamp%22:180158,%22k%22:122,%22type%22:0%7D,%7B%22x%22:4443,%22y%22:2928,%22z%22:1237,%22timestamp%22:180262,%22k%22:104,%22type%22:0%7D,%7B%22x%22:6566,%22y%22:4699,%22z%22:3427,%22timestamp%22:180363,%22k%22:94,%22type%22:0%7D,%7B%22x%22:3790,%22y%22:1227,%22z%22:669,%22timestamp%22:180464,%22k%22:123,%22type%22:0%7D,%7B%22x%22:7102,%22y%22:4066,%22z%22:4066,%22timestamp%22:180565,%22k%22:86,%22type%22:0%7D,%7B%22x%22:7455,%22y%22:3490,%22z%22:4377,%22timestamp%22:180665,%22k%22:66,%22type%22:0%7D,%7B%22x%22:6768,%22y%22:2182,%22z%22:3759,%22timestamp%22:180766,%22k%22:102,%22type%22:0%7D,%7B%22x%22:5203,%22y%22:544,%22z%22:2206,%22timestamp%22:180866,%22k%22:91,%22type%22:0%7D,%7B%22x%22:7523,%22y%22:2825,%22z%22:4574,%22timestamp%22:180967,%22k%22:78,%22type%22:0%7D,%7B%22x%22:7667,%22y%22:2907,%22z%22:4789,%22timestamp%22:181068,%22k%22:66,%22type%22:0%7D,%7B%22x%22:4750,%22y%22:-18,%22z%22:1873,%22timestamp%22:181171,%22k%22:99,%22type%22:0%7D,%7B%22x%22:4373,%22y%22:-435,%22z%22:1501,%22timestamp%22:181272,%22k%22:105,%22type%22:0%7D,%7B%22x%22:4564,%22y%22:-260,%22z%22:1694,%22timestamp%22:181385,%22k%22:113,%22type%22:0%7D,%7B%22x%22:6032,%22y%22:1152,%22z%22:3192,%22timestamp%22:181486,%22k%22:99,%22type%22:0%7D]&dm_img_str=V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ&dm_cover_img_str=QU5HTEUgKEludGVsLCBJbnRlbChSKSBJcmlzKFIpIFhlIEdyYXBoaWNzICgweDAwMDBBN0EwKSBEaXJlY3QzRDExIHZzXzVfMCBwc181XzAsIEQzRDExKUdvb2dsZSBJbmMuIChJbnRlbC&dm_img_inter=%7B%22ds%22:[%7B%22t%22:7,%22c%22:%22dnVpX2J1dHRvbiB2dWlfYnV0dG9uLS1hY3RpdmUgdnVpX2J1dHRvbi0tYWN0aXZlLWJsdWUgdnVpX2J1dHRvbi0tbm8tdHJhbnNpdGlvbiB2dWlfcGFnZW5hdGlvbi0tYnRuIHZ1aV9wYWdlbmF0aW9uLS1idG4tbn%22,%22p%22:[5591,19,9247],%22s%22:[221,391,442]%7D],%22wh%22:[3661,3027,5],%22of%22:[5133,6956,168]%7D&w_webid=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzcG1faWQiOiIzMzMuOTk5IiwiYnV2aWQiOiJDNUJFRDQ0NS05Rjc3LUE5QzQtQTA4QS00MzAwQzJEODVEMTY4MTEwN2luZm9jIiwidXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzEuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImJ1dmlkX2ZwIjoiMTNhODRlM2U4YTJiNGI5ZDU4MDNjODRlZjVhODA3MzciLCJiaWxpX3RpY2tldCI6ImV5SmhiR2NpT2lKSVV6STFOaUlzSW10cFpDSTZJbk13TXlJc0luUjVjQ0k2SWtwWFZDSjkuZXlKbGVIQWlPakUzTXpnd05UZzROaklzSW1saGRDSTZNVGN6TnpjNU9UWXdNaXdpY0d4MElqb3RNWDAuZjRCbVI2M2R6OTFlUXI3OF9SdG5Mc1RwWUZad0IzVzdyQmRUa1BRdmZCNCIsImNyZWF0ZWRfYXQiOjE3Mzc5OTMwNTIsInR0bCI6ODY0MDAsInVybCI6Ii8yNTQ0NjMyNjkiLCJyZXN1bHQiOjAsImlzcyI6ImdhaWEiLCJpYXQiOjE3Mzc5OTMwNTJ9.L_8oaSaONNygoxeplorJeWjyAaMdFDDe8a5fK5yu2jNGQTGqm1rN5qN257GlyTtYxdz4BnEJt2rTzVt7h_Uo8rvywIssDv3nC3CY0ShSk3a1vteMrN9xeLUJpelnQeqac0fC9Rhl-rXbZ8zjAlKY1hr6WPpmL6iQwCG9WPEVbPmuWPGld9lsuUrLOWxSqKeHCkPbJ0t3ajNQLaOJhzyQPRipSU6wEU786MuDoVefxD2er0OjfI57k_RZ9DfLvOwGSGnjKYSqixcM1kMddQPfgRNzJRy2rcqVJE4ebu-LrnI7HOxCEzZpUoqaUjhVr_0cJlxhB94w4uLbGJvyZ0a6vA&w_rid=d53126921fdab9cd49a4d22d534d38e1&wts={int(time.time())}"
        url = (
            "&".join(
                sorted([i for i in url.split("?")[-1].split("&") if "w_rid=" not in i])
            )
            .replace(",", quote(","))
            .replace(":", quote(":"))
            .replace("[", quote("["))
            .replace("]", quote("]"))
        )
        host = "https://api.bilibili.com/x/space/wbi/arc/search?"
        wrid = md5(url + MAGIC_A)
        url = host + url + "&w_rid=" + wrid

        response = requests.get(
            url,
            cookies=cookies,
            headers=headers,
        ).json()["data"][
            "list"
        ]["vlist"]

        for ui, u in enumerate(response):
            response[ui]["title"] = re.sub(
                ILLEGAL_CHARACTERS_RE, "", response[ui]["title"]
            )
            response[ui]["description"] = re.sub(
                ILLEGAL_CHARACTERS_RE, "", response[ui]["description"]
            )

        videourls.extend(response)
    df = pandas.DataFrame(videourls)
    df.to_excel("bilibili.xlsx", index=False)


def download_bilibili_video(video_url):
    # 调用you-get命令行工具下载视频
    command = ["you-get", "-o", f"./{KOL_ID}", video_url, "--no-caption"]
    try:

        subprocess.run(command, check=True)
        print("下载完成！")
    except subprocess.CalledProcessError as e:

        print("下载失败：", e)


if __name__ == "__main__":
    getvideolink()
    folder_name = f"{KOL_ID}"

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    videourls = [
        f"https://www.bilibili.com/video/{i}"
        for i in pandas.read_excel(f"{KOL_ID}.xlsx")["bvid"].values
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(download_bilibili_video, videourls)
    # breakpoint()
    # for u in videourls:
    #    download_bilibili_video(u)
