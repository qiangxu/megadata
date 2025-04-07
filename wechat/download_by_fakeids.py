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
    fakeid = fakeid.strip().strip("==")
    if os.path.exists(f"./data/lists/{fakeid}.json"):
        return

    page = 0
    print("FAKEID: ", fakeid)
    res = {}
    total_count = 10000
    with tqdm(total=total_count) as pbar:

        while len(res) < total_count:
            url = (
                "https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&search_field=null&begin="
                + str(page * 20)
                + f"&count=20&query=&fakeid={fakeid}%3D%3D&type=101_1&free_publish_type=1&sub_action=list_ex&token={token}&lang=zh_CN&f=json&ajax=1"
            )
            response = requests.get(
                url,
                headers={
                    "cookie": cookie,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
                },
            ).text
            total_count = json.loads(json.loads(response)["publish_page"])[
                "total_count"
            ]
            posts = json.loads(json.loads(response)["publish_page"])["publish_list"]

            if len(posts) == 0:
                break

            with open(f"./data/lists/{fakeid}.json", "a+", encoding="utf-8") as f:
                for p in posts:
                    if len(p["publish_info"]) > 10:
                        p = json.loads(p["publish_info"])
                        p_id = p["appmsgex"][0]["appmsgid"]

                        f.write(json.dumps(p))
                        f.write("\n")

                        res[p_id] = p

            page += 1
            time.sleep(random.randint(1, 10) / 10)
            pbar.update(20 * 10000 / total_count)

def search_accounts(token=TOKEN, cookie=COOKIE):
    query_bag = {
		"机械工程": ["机械设计", "机械制造", "机械原理", "工程力学", "数控技术"],
		"电气工程": ["电路分析", "电力系统", "高电压", "电机控制", "配电技术"],
		"土木工程": ["结构力学", "工程材料", "基础工程", "建筑设计", "工程测量"],
		"化学工程": ["单元操作", "反应工程", "化工原理", "分离工程", "过程控制"],
		"计算机工程": ["计算机组成", "数字电路", "嵌入式", "微处理器", "硬件设计"],
		"软件工程": ["数据结构", "算法设计", "软件测试", "系统架构", "编程语言"],
		"航空航天工程": ["空气动力", "飞行力学", "航空发动", "导航技术", "航天器"],
		"环境工程": ["污水处理", "大气治理", "固废处理", "环境监测", "生态修复"],
		"生物工程": ["发酵工程", "酶工程", "基因工程", "细胞培养", "代谢工程"],
		"材料工程": ["金属材料", "高分子", "无机材料", "复合材料", "材料性能"],
		"工业工程": ["生产管理", "质量工程", "物流规划", "人因工程", "设施布局"],
		"自动化": ["自动控制", "过程控制", "运动控制", "智能控制", "测控技术"],
		"电子工程": ["模拟电路", "数字电路", "集成电路", "电子设计", "信号处理"],
		"通信工程": ["通信原理", "信号处理", "移动通信", "光通信", "天线技术"],
		"建筑工程": ["建筑设计", "工程施工", "结构设计", "建筑材料", "工程造价"],
		"能源与动力工程": ["热力学", "流体机械", "动力机械", "能源利用", "传热学"],
		"船舶工程": ["船体结构", "船舶设计", "水动力学", "轮机工程", "船舶制造"],
		"汽车工程": ["汽车设计", "发动机", "底盘构造", "车身设计", "汽车电子"],
		"核工程": ["核物理", "反应堆", "辐射防护", "核燃料", "核安全"],
		"测控技术与仪器": ["传感技术", "测量原理", "仪器设计", "信号采集", "控制系统"],

		# 计算机与信息类
		"计算机科学与技术": ["操作系统", "计算机网络", "数据库", "编译原理", "计算理论"],
		"人工智能": ["机器学习", "深度学习", "知识图谱", "神经网络", "自然语言"],
		"数据科学与大数据技术": ["数据挖掘", "统计分析", "预测模型", "数据仓库", "分布式"],
		"网络工程": ["网络协议", "网络安全", "路由交换", "网络规划", "云计算"],
		"信息安全": ["密码学", "网络防护", "系统安全", "渗透测试", "安全审计"],
		"物联网工程": ["传感网络", "嵌入式", "无线通信", "物联控制", "智能感知"],
		"智能科学与技术": ["模式识别", "计算智能", "智能控制", "认知科学", "决策系统"],
		"数字媒体技术": ["图像处理", "视频编码", "动画设计", "媒体压缩", "虚拟现实"],
		"区块链工程": ["分布式", "密码算法", "共识机制", "智能合约", "链式存储"],
		"云计算技术": ["虚拟化", "分布式", "云存储", "微服务", "容器技术"],

		# 数理类
		"数学与应用数学": ["微积分", "代数分析", "概率论", "数值分析", "泛函分析"],
		"统计学": ["概率统计", "回归分析", "时间序列", "多元统计", "抽样调查"],
		"信息与计算科学": ["数值计算", "优化理论", "计算方法", "算法设计", "建模分析"],
		"应用物理学": ["量子力学", "电磁学", "光学原理", "固体物理", "热力学"],
		"光电信息科学与工程": ["激光原理", "光电器件", "光学设计", "光通信", "光电检测"],
		"天文学": ["天体物理", "射电天文", "天体力学", "宇宙学", "行星科学"],
		"空间科学与技术": ["空间物理", "遥感技术", "卫星导航", "空间探测", "轨道力学"],
		"核物理": ["原子核", "粒子物理", "辐射物理", "核反应", "量子场论"],
		"声学": ["声波传播", "超声技术", "噪声控制", "声学测量", "声学设计"],
		"数理基础科学": ["数学物理", "理论力学", "计算物理", "数学建模", "统计物理"],

		# 化学与材料类
		"化学": ["有机化学", "无机化学", "物理化学", "分析化学", "结构化学"],
		"应用化学": ["工业催化", "精细化工", "化工分析", "电化学", "材料化学"],
		"材料科学与工程": ["材料物理", "材料化学", "金属材料", "陶瓷材料", "功能材料"],
		"高分子材料与工程": ["聚合物", "高分子化学", "材料加工", "高分子物理", "复合材料"],
		"无机非金属材料工程": ["陶瓷工艺", "玻璃工艺", "水泥工艺", "材料表征", "工艺设计"],
		"冶金工程": ["金属冶炼", "材料成型", "热处理", "金属分析", "冶金原理"],
		"功能材料": ["智能材料", "磁性材料", "光电材料", "能源材料", "传感材料"],
		"纳米材料与技术": ["纳米制备", "纳米表征", "量子点", "纳米器件", "纳米结构"],
		"复合材料与工程": ["基体材料", "增强体", "界面设计", "成型工艺", "结构设计"],
		"新能源材料与器件": ["电池材料", "光伏材料", "储能材料", "燃料电池", "器件设计"],

		# 生物类
		"生物技术": ["基因工程", "发酵工程", "酶工程", "细胞工程", "蛋白质"],
		"生物信息学": ["序列分析", "结构预测", "基因组学", "蛋白组学", "代谢组学"],
		"生物医学工程": ["医学仪器", "康复工程", "医学影像", "生物力学", "临床工程"],
		"食品科学与工程": ["食品工艺", "食品检测", "营养学", "食品安全", "发酵工艺"],
		"生物制药": ["药物合成", "药物分析", "制剂工艺", "药物设计", "质量控制"],
		"生物系统工程": ["系统生物", "合成生物", "代谢工程", "生物反应", "过程控制"],
		"生物资源科学": ["资源评价", "开发利用", "保护技术", "生态修复", "资源管理"],
		"生物检验技术": ["临床检验", "微生物", "免疫学", "分子诊断", "生化分析"],
		"生物生产工程": ["细胞培养", "发酵工程", "分离纯化", "反应器", "工艺优化"],
		"细胞工程": ["细胞培养", "基因操作", "细胞融合", "克隆技术", "组织工程"],

		# 地球与环境类
		"地质工程": ["工程地质", "水文地质", "岩土工程", "地质勘查", "矿产普查"],
		"勘查技术与工程": ["地球物理", "地球化学", "钻探技术", "测井技术", "物探方法"],
		"资源勘查工程": ["矿产勘查", "石油勘探", "地质填图", "构造地质", "矿床学"],
		"地理信息科学": ["遥感技术", "空间分析", "地图制图", "定位导航", "地理建模"],
		"测绘工程": ["大地测量", "工程测量", "摄影测量", "地图制图", "测绘数据"],
		"遥感科学与技术": ["遥感原理", "图像处理", "遥感应用", "信息提取", "遥感解译"],
		"水利水电工程": ["水文学", "水力学", "水工建筑", "水资源", "水电站"],
		"海洋工程": ["海洋结构", "海洋地质", "海洋测绘", "海洋物理", "海洋化学"],
		"大气科学": ["气象学", "气候学", "大气物理", "大气化学", "天气预报"],
		"环境科学": ["环境化学", "环境生物", "环境监测", "污染控制", "生态修复"],

		# 农业工程类
		"农业机械化及其自动化": ["农机设计", "农机制造", "自动控制", "精准农业", "机械原理"],
		"农业水利工程": ["灌溉排水", "水土保持", "农田水利", "水资源", "水环境"],
		"农业建筑环境与能源工程": ["温室工程", "建筑环境", "能源利用", "环境控制", "设施园艺"],
		"农业电气化": ["电气控制", "农电工程", "自动化", "用电设计", "节能技术"],
		"农业智能装备工程": ["智能控制", "传感技术", "机器视觉", "精准作业", "装备设计"],
		"设施农业科学与工程": ["设施园艺", "环境调控", "栽培技术", "工程设计", "节能技术"],
		"农业生物环境工程": ["环境工程", "生态工程", "环境监测", "污染控制", "废物处理"],
		"农业工程": ["农业机械", "农田建设", "农业电气", "农业水利", "设施农业"],
		"林业工程": ["森林采伐", "木材加工", "林产化工", "森林工程", "林业机械"],
		"园艺工程": ["园艺设施", "栽培技术", "环境控制", "工程设计", "灌溉系统"],

		# 交通运输类
		"交通运输": ["运输组织", "物流管理", "运输规划", "智能交通", "运营管理"],
		"交通工程": ["道路工程", "桥梁工程", "隧道工程", "交通规划", "交通控制"],
		"飞行技术": ["飞行原理", "航空导航", "飞行器", "航空气象", "飞行控制"],
		"航海技术": ["船舶驾驶", "航海气象", "航海仪器", "航线设计", "海事法规"],
		"轨道交通信号与控制": ["信号系统", "通信系统", "控制系统", "调度指挥", "安全防护"],
		"民航空中交通管理": ["空管运行", "雷达管制", "航空气象", "空域管理", "飞行管理"],
		"船舶与海洋工程": ["船舶设计", "船体结构", "海洋工程", "轮机工程", "水动力学"],
		"港口航道与海岸工程": ["港口规划", "航道整治", "海岸工程", "疏浚工程", "防波堤"],
		"邮政工程": ["邮政管理", "物流系统", "自动分拣", "快递技术", "信息系统"],
		"物流工程": ["仓储技术", "运输系统", "供应链", "物流规划", "配送管理"],

		# 其他工程类
		"安全工程": ["安全管理", "风险评估", "应急救援", "消防技术", "安全监测"],
		"消防工程": ["火灾防控", "消防设施", "应急疏散", "消防水力", "安全评估"],
		"质量管理工程": ["质量控制", "可靠性", "统计分析", "工程检测", "标准化"],
		"印刷工程": ["印刷技术", "印前处理", "印后加工", "包装印刷", "数字印刷"],
		"包装工程": ["包装材料", "包装设计", "包装工艺", "包装机械", "防护包装"],
		"假肢矫形工程": ["人体工程", "康复器具", "生物力学", "矫形技术", "功能仿生"],
	}
    count = 10
    page = 10
    
    query_words = []
    for query_key in query_bag.keys():
        query_words.extend(query_bag[query_key])

    query_words = ["学术", "百科", "教育", "科技"]

    for query in tqdm(query_words):
		
        for page_no in range(page): 
            begin = page_no * count 
            url = f"https://mp.weixin.qq.com/cgi-bin/searchbiz?action=search_biz&begin={begin}&count={count}&query={query}&token={token}&lang=zh_CN&f=json&ajax=1"
            response = requests.get(
                url,
                headers={
                    "cookie": cookie,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
                },
            ).text
            
            if 'list' not in response: 
                breakpoint()
                continue

            accounts = json.loads(response)['list']
            with open(f"./accounts.json", "a+", encoding="utf-8") as f:
                for a in accounts:
                    f.write(json.dumps(a))
                    f.write("\n")

            time.sleep(random.randint(10, 20) / 10)

def crawl_account(fakeid, token=TOKEN, cookie=COOKIE):
    fakeid = fakeid.strip().strip("==")
    print("FAKEID: ", fakeid)
    Path(f"./data/posts/{fakeid}").mkdir(parents=True, exist_ok=True)

    if not glob.glob(f"./data/lists/{fakeid}.json"):
        get_posts(fakeid, token=token, cookie=cookie)

    if not glob.glob(f"./data/lists/{fakeid}.json"):
        print(f"NO: ./data/lists/{fakeid}.json")
        print(f"FAKEID: {fakeid} IS SKIPPED")
        return 

    with open(f"./data/lists/{fakeid}.json", "r", encoding="utf-8") as f:
        posts = f.readlines()

    posts = [json.loads(p) for p in posts]
    random.shuffle(posts)

    count = 0
    for post in tqdm(posts):
        post_id = post["appmsgex"][0]["appmsgid"]

        if post["appmsgex"][0]["is_deleted"]:
            continue

        suffix = str(post_id)[-2:]
        if glob.glob(f"./data/posts/{fakeid}/{suffix}/{post_id}.html"):
            continue

        Path(f"./data/posts/{fakeid}/{suffix}").mkdir(parents=True, exist_ok=True)
        title = post["appmsgex"][0]["title"]

        link = post["appmsgex"][0]["link"]
        count += 1
        with open(f"./data/posts/{fakeid}/{suffix}/{post_id}.html", "w") as f:
            print(f"./data/posts/{fakeid}/{suffix}/{post_id}.html")
            content = requests.get(
                        link,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
                        },
                    ).text
            """
            content = (
                "".join(
                    requests.get(
                        link,
                        headers={
                            #"cookie": cookie,
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
                        },
                    ).text.splitlines()
                )
                .replace("\t", "")
                .replace(" ", "")
            )
            """
            #wb = extract_text_from_html(content).replace("\t", "").replace(" ", "")
            f.write(content + "\n")
        time.sleep(random.randint(30, 50) / 10)
    print(f"FAKEID: {fakeid} IS COMPLETED W/ {count} UPDATES")
    
    return count 
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
    
    """
    with open("fakeids.csv", "r", encoding="utf-8") as f:
        fakeids = f.readlines()
    """
    with open("data/accounts/accounts.json", 'r', encoding='utf-8') as f:
        accounts = [json.loads(l) for l in f.readlines()]

    fakeids = list(set([a['fakeid'] for a in accounts]))
    if args.config:
        # 读取配置文件
        config = read_config(args.config)
        cookie = config["cookie"]
        token = config["token"]
        random.shuffle(fakeids)
    else:
        cookie = COOKIE
        token = TOKEN

    #search_accounts(token=token, cookie=cookie)
    #return
    for fakeid in tqdm(fakeids):
        try:
            # get_posts(fakeid, token=token, cookie=cookie)
            count = crawl_account(fakeid, token=token, cookie=cookie)
            time.sleep(min(count, 10))
        except Exception as e:
            print("EXCEPTION:", e)
            # breakpoint()
            pass
        # crawl_account(fakeid)


if __name__ == "__main__":
    main()
