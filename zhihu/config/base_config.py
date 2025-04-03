# 基础配置
PLATFORM = "zhihu"
KEYWORDS = "教育"  # 关键词搜索配置，每次填写一个关键词。

LOGIN_TYPE = "cookie"  # qrcode or phone or cookie
COOKIES = "Hm_lpvt_98beee57fd2ef70ccdd5ca52b9740c49=1742824068; Hm_lvt_98beee57fd2ef70ccdd5ca52b9740c49=1742549723,1742788885; tst=r; BEC=5ee33e0856ed13c879689106c041a08d; JOID=VFwRBUsqGZ9ZbeA8QCtdz7pTatxbXX6uaAmmUCZcVPhvCoNfCUt5ej5p4j5EE34148r_nwsxJhXVlL7WmFy1UzQ=; SESSIONID=ug37bDldpOg4aeaIPSEL9BDAA8qgvH7cEbno8OWoCtP; osd=VVkXAkorHJlebOE5Rixczr9Vbd1aWHipaQijViFdVf1pDYJeDE1-ez9s5DlFEnsz5Mv-mg02JxTQkrnXmVmzVDU=; HMACCOUNT=DE6C26B054BF0196; __zse_ck=004_6kPP9Mr0//z/LZbhHrSPxfOI6DlvrBTXNe0trehI=lirSh9ciNe=NPSMIRW27ECvfX5mSduJr3pLp1RFHraQ/oHXvdyge/Kfyzud1pkaec3fnvg/H1n0PNy0IX9VRggz-q7exWxt94u29YQ6lQvYI5t5OscNSugQFco6P3mVxbNl3Oaw5RQBTMC3JGR9VY49WNGx8KVXQuQS/GRt7PYx/psqKISw1zfz87/po754ekYmw1bTitTPHNEOP+mr7kCGu; __utma=51854390.1175779376.1737618520.1742549745.1742788745.3; __utmc=51854390; __utmv=51854390.100-1|2=registration_date=20150429=1^3=entry_date=20150429=1; __utmz=51854390.1742549745.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); q_c1=749d7a08122d49b9a28286a706f16d40|1742788812000|1669091382000; _xsrf=TXJUBXHREeQ148UPCmY3flTs78ICROxy; q_c1=749d7a08122d49b9a28286a706f16d40|1732527618000|1669091382000; _zap=02958876-2b56-4c4e-bce4-4d3e1cebc000; d_c0=\"AGBRHPAguRSPTvIkVAz4oLXKaImiHVXnj6s=|1648801158\""

SORT_TYPE = "popularity_descending"

PUBLISH_TIME_TYPE = 0
CRAWLER_TYPE = (
    "search"
)
# 自定义User Agent
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 单位秒
CRAWLER_MAX_SLEEP_SEC = 5

# 代理IP池数量
IP_PROXY_POOL_COUNT = 10

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# 数据保存类型选项配置,支持三种类型：csv、db、json, 最好保存到DB，有排重的功能。
SAVE_DATA_OPTION = "csv"  # csv or db or json

# 用户浏览器缓存的浏览器文件配置
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取数量控制
CRAWLER_MAX_NOTES_COUNT = 500

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬图片模式, 默认不开启爬图片
ENABLE_GET_IMAGES = False

# 是否开启爬评论模式, 默认不开启爬评论
ENABLE_GET_COMMENTS = False

# 爬取一级评论的数量控制(单视频/帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 5

ENABLE_GET_SUB_COMMENTS = False

# 自定义词语及其分组
# 添加规则：xx:yy 其中xx为自定义添加的词组，yy为将xx该词组分到的组名。
CUSTOM_WORDS = {
    "零几": "年份",  # 将“零几”识别为一个整体
    "高频词": "专业术语",  # 示例自定义词
}

# 停用(禁用)词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"
