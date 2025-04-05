#!/bin/bash
##############################################################
# CREATED DATE: Sun Apr  6 00:23:27 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
##############################################################

#!/bin/bash
##############################################################
# CREATED DATE: Sun Apr  6 00:23:27 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
# UPDATED: Added support for YAML configuration files
##############################################################

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

# 检查配置文件扩展名
FILE_EXT="${CONFIG_FILE##*.}"
FILE_EXT=$(echo "$FILE_EXT" | tr '[:upper:]' '[:lower:]')

# 根据扩展名决定使用 JSON 还是 YAML 解析
if [ "$FILE_EXT" = "json" ]; then
    # 如果系统未安装jq，请运行: sudo apt-get install jq (Debian/Ubuntu) 或 brew install jq (macOS)
    if ! command -v jq &> /dev/null; then
        echo "错误: 需要安装jq工具来解析JSON"
        echo "请运行: sudo apt-get install jq (Debian/Ubuntu) 或 brew install jq (macOS)"
        exit 1
    fi
    
    # 使用jq解析JSON配置文件
    NDJSON_DIR_REL=$(jq -r '.ndjson_dir' "$CONFIG_FILE")
    STATE_FILE_REL=$(jq -r '.state_file' "$CONFIG_FILE")
    SITE_ID=$(jq -r '.site_id' "$CONFIG_FILE")
    
elif [ "$FILE_EXT" = "yml" ] || [ "$FILE_EXT" = "yaml" ]; then
    # 如果系统未安装yq，请运行: sudo apt-get install yq (Debian/Ubuntu) 或 brew install yq (macOS)
    if ! command -v yq &> /dev/null; then
        echo "错误: 需要安装yq工具来解析YAML"
        echo "请运行: sudo apt-get install yq (Debian/Ubuntu) 或 brew install yq (macOS)"
        exit 1
    fi
    
    # 使用yq解析YAML配置文件
    NDJSON_DIR_REL=$(yq eval '.ndjson_dir' "$CONFIG_FILE")
    STATE_FILE_REL=$(yq eval '.state_file' "$CONFIG_FILE")
    SITE_ID=$(yq eval '.site_id' "$CONFIG_FILE")
else
    echo "错误: 不支持的配置文件格式。请使用 .json、.yml 或 .yaml 扩展名"
    exit 1
fi

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

if [ "$SITE_ID" == "null" ] || [ -z "$SITE_ID" ]; then
    echo "错误: 无法从配置文件中读取 'site_id'"
    exit 1
fi

echo "配置信息:"
echo "NDJSON目录: $NDJSON_DIR"
echo "状态文件: $STATE_FILE"
echo "站点ID: $SITE_ID"

for j in {1..500}; do 
	if [ -d "$NDJSON_DIR" ] && [ "$(ls -A "$NDJSON_DIR" 2>/dev/null)" ]; then
		echo "NDJSON目录中存在文件，休息10秒后再次检查..."
		sleep 10
	else
		echo "NDJSON目录为空，执行search.py..."
		python search.py -c $CONFIG_FILE -S -s $SITE_ID -t 1 -z 20
	fi

    # 删除状态文件
    if [ -f "$STATE_FILE" ]; then
        echo "正在删除状态文件: $STATE_FILE"
        rm -f "$STATE_FILE"
        echo "状态文件已删除"
    else
        echo "警告: 状态文件 '$STATE_FILE' 不存在，无法删除"
    fi
done
