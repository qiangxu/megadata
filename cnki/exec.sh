#!/bin/bash
##############################################################
# CREATED DATE: Sun Mar 30 02:04:01 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
##############################################################

#!/bin/bash

# 检查是否提供了配置文件参数
if [ $# -lt 1 ]; then
    echo "用法: $0 <配置文件路径>"
    exit 1
fi

CONFIG_FILE="$1"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 '$CONFIG_FILE' 不存在"
    exit 1
fi

# 使用jq解析JSON配置文件
# 如果系统未安装jq，请运行: sudo apt-get install jq (Debian/Ubuntu) 或 brew install jq (macOS)
if ! command -v jq &> /dev/null; then
    echo "错误: 需要安装jq工具来解析JSON"
    echo "请运行: sudo apt-get install jq (Debian/Ubuntu) 或 brew install jq (macOS)"
    exit 1
fi

CONFIG_DIR=$(dirname "$(realpath "$CONFIG_FILE")")

# 从配置文件中提取ndjson_dir和state_file（相对路径）
NDJSON_DIR_REL=$(jq -r '.ndjson_dir' "$CONFIG_FILE")
STATE_FILE_REL=$(jq -r '.state_file' "$CONFIG_FILE")
SITE_ID=$(jq -r '.site_id' "$CONFIG_FILE")

#!/bin/bash

# 检查是否提供了配置文件参数
if [ $# -lt 1 ]; then
    echo "用法: $0 <配置文件路径>"
    exit 1
fi

CONFIG_FILE="$1"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 '$CONFIG_FILE' 不存在"
    exit 1
fi

# 使用jq解析JSON配置文件
# 如果系统未安装jq，请运行: sudo apt-get install jq (Debian/Ubuntu) 或 brew install jq (macOS)
if ! command -v jq &> /dev/null; then
    echo "错误: 需要安装jq工具来解析JSON"
    echo "请运行: sudo apt-get install jq (Debian/Ubuntu) 或 brew install jq (macOS)"
    exit 1
fi

# 检测操作系统类型
OS_TYPE=$(uname)

# 获取配置文件的目录路径
if [ "$OS_TYPE" = "Darwin" ]; then
    # macOS 系统
    CONFIG_DIR=$(cd "$(dirname "$CONFIG_FILE")" && pwd)
else
    # Linux 系统
    CONFIG_DIR=$(dirname "$(realpath "$CONFIG_FILE")")
fi

# 从配置文件中提取ndjson_dir和state_file（相对路径）
NDJSON_DIR_REL=$(jq -r '.ndjson_dir' "$CONFIG_FILE")
STATE_FILE_REL=$(jq -r '.state_file' "$CONFIG_FILE")

# 转换为绝对路径（相对于配置文件所在目录）
if [ "$OS_TYPE" = "Darwin" ]; then
    # macOS 系统
    NDJSON_DIR="$CONFIG_DIR/$NDJSON_DIR_REL"
    NDJSON_DIR=$(cd "$(dirname "$NDJSON_DIR")" 2>/dev/null && pwd)/$(basename "$NDJSON_DIR")
    STATE_FILE="$CONFIG_DIR/$STATE_FILE_REL"
    STATE_FILE=$(cd "$(dirname "$STATE_FILE")" 2>/dev/null && pwd)/$(basename "$STATE_FILE")
else
    # Linux 系统
    NDJSON_DIR=$(realpath -m "$CONFIG_DIR/$NDJSON_DIR_REL")
    STATE_FILE=$(realpath -m "$CONFIG_DIR/$STATE_FILE_REL")
fi

# 检查是否成功提取了配置
if [ "$NDJSON_DIR" == "null" ] || [ -z "$NDJSON_DIR" ]; then
    echo "错误: 无法从配置文件中读取 'ndjson_dir'"
    exit 1
fi

if [ "$STATE_FILE" == "null" ] || [ -z "$STATE_FILE" ]; then
    echo "错误: 无法从配置文件中读取 'state_file'"
    exit 1
fi

echo "配置信息:"
echo "NDJSON目录: $NDJSON_DIR"
echo "状态文件: $STATE_FILE"


for j in {1..100}; do 
	# 删除NDJSON目录中的所有文件
	if [ -d "$NDJSON_DIR" ]; then
		echo "正在删除 $NDJSON_DIR 中的所有文件..."
		rm -f "$NDJSON_DIR"/*
		echo "NDJSON目录清理完成"
	else
		echo "警告: NDJSON目录 '$NDJSON_DIR' 不存在，无法删除文件"
	fi

	# 删除状态文件
	if [ -f "$STATE_FILE" ]; then
		echo "正在删除状态文件: $STATE_FILE"
		rm -f "$STATE_FILE"
		echo "状态文件已删除"
	else
		echo "警告: 状态文件 '$STATE_FILE' 不存在，无法删除"
	fi

	echo "清理操作完成"

    for i in {1..10}; do
        python search.py -c $CONFIG_FILE -S -s $SITE_ID -t 1 -z 20
        python dump.py -c $CONFIG_FILE
        python dump.py -c $CONFIG_FILE
    done
done
