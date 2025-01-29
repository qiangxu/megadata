#!/usr/bin/env python
# CREATED DATE: Wed Jan 29 16:45:52 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com

import json
import glob

def deduplicate_accounts(file_pattern: str):
    # 用于存储唯一账号的字典
    unique_accounts = {}
    
    # 处理所有匹配的文件
    for file_path in glob.glob(file_pattern):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                # 将账号添加到字典中，自动去重
                for account in accounts:
                    unique_accounts[account['accountId']] = account
                    
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
    
    # 将结果保存到新文件
    result = list(unique_accounts.values())
    with open('wechat_accounts.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"去重完成，共有 {len(result)} 个唯一账号")

# 运行代码
deduplicate_accounts("../metadata/cap_wechat_id_*.json")
