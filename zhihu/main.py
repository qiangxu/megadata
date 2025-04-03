import subprocess
import os
import time
import random

# 关键词列表
keywords = [
    "科学", "科研", "人工智能", "教育"
]

# base_config.py 文件路径
config_file = os.path.join('config', 'base_config.py')  # 相对路径指向 config 文件夹中的 base_config.py


# 修改 base_config.py 中的 KEYWORDS
def update_keywords_in_config(keyword):
    with open(config_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # 替换 KEYWORDS 行
    with open(config_file, 'w', encoding='utf-8') as file:
        for line in lines:
            if line.startswith('KEYWORDS'):
                file.write(f'KEYWORDS = "{keyword}"  # 关键词搜索配置，每次填写一个关键词。\n')
            else:
                file.write(line)

# 执行 main.py（使用Popen来启动异步任务）
def run_main():
    process = subprocess.Popen(['python', 'start.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    stdout, stderr = process.communicate()  # 获取输出和错误信息
    print(stdout)  # 输出main.py的执行结果
    time.sleep(random.randint(5, 10))
    if stderr:
        print(stderr)  # 输出错误信息（如果有）
        print("-----------------------------------------------------------------")

# 主函数，遍历所有关键词并执行程序
def main():
    # 遍历所有关键词，逐一更新配置并执行 main.py
    for keyword in keywords:
        print(f"正在处理关键词：{keyword}")
        update_keywords_in_config(keyword)  # 更新配置文件中的关键词
        run_main()  # 运行 main.py
        print(f"完成关键词：{keyword}")


if __name__ == "__main__":
    main()
