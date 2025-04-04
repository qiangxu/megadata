#!/Users/qiangxu/mambaforge-pypy3/envs/mega/bin/python
# CREATED DATE: Wed Apr  2 14:57:42 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com
"""
知网下载链接提取器的本地消息主机

此脚本实现了一个Native Messaging Host，用于与Chrome扩展通信，
提供文件系统访问能力，包括扫描目录、读取文件、删除文件等功能。

安装步骤:
1. 确保安装了Python 3.6+
2. 修改下面的CHROME_EXTENSION_ID为你的扩展ID
3. 运行此脚本，它会自动注册本地消息主机
4. 重启Chrome浏览器

相关文档:
https://developer.chrome.com/docs/apps/nativeMessaging/
"""

import os
import sys
import json
import struct
import logging
import argparse
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cnki_downloader_host.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("cnki_downloader_host")

# 扩展ID，需要替换为实际的扩展ID
CHROME_EXTENSION_ID = "caebnacoadaakbjbcccfljpkhioieifp"

# 主机名，与manifest.json中的name保持一致
HOST_NAME = "com.cnki.downloader.bak"

# Windows注册表路径
WINDOWS_REGISTRY_KEY = r"SOFTWARE\Google\Chrome\NativeMessagingHosts"

# 获取当前脚本目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_manifest_file() -> str:
    """
    创建Native Messaging Host的manifest.json文件
    
    返回:
        str: manifest文件的路径
    """
    manifest = {
        "name": HOST_NAME,
        "description": "知网下载链接提取器的本地消息主机",
        "path": os.path.abspath(__file__),
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{CHROME_EXTENSION_ID}/"
        ]
    }
    
    manifest_path = os.path.join(CURRENT_DIR, f"{HOST_NAME}_manifest.json")
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
        
    logger.info(f"已创建manifest文件: {manifest_path}")
    return manifest_path

def install_host():
    """安装Native Messaging Host"""
    manifest_path = create_manifest_file()
    
    if platform.system() == "Windows":
        # Windows平台使用注册表
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{WINDOWS_REGISTRY_KEY}\\{HOST_NAME}") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
            logger.info("已在Windows注册表中注册本地消息主机")
        except ImportError:
            logger.error("无法导入winreg模块，请确保在Windows上运行")
            return False
        except Exception as e:
            logger.error(f"注册表操作失败: {e}")
            return False
    else:
        # Linux/Mac平台
        if platform.system() == "Darwin":
            # macOS
            target_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome/NativeMessagingHosts")
        else:
            # Linux
            target_dir = os.path.expanduser("~/.config/google-chrome/NativeMessagingHosts")
            
        # 确保目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        # 复制manifest文件
        target_path = os.path.join(target_dir, f"{HOST_NAME}.json")
        try:
            import shutil
            shutil.copy2(manifest_path, target_path)
            logger.info(f"已复制manifest文件到: {target_path}")
        except Exception as e:
            logger.error(f"复制manifest文件失败: {e}")
            return False
            
    return True

def get_message() -> Optional[Dict]:
    """
    从stdin读取消息
    
    返回:
        dict或None: 解析后的消息，如果读取失败则返回None
    """
    # 首先读取4字节的消息长度
    length_bytes = sys.stdin.buffer.read(4)
    if not length_bytes:
        logger.error("无法读取消息长度，可能是与扩展的连接已关闭")
        return None
        
    # 解析消息长度
    message_length = struct.unpack('i', length_bytes)[0]
    
    # 读取消息内容
    message_bytes = sys.stdin.buffer.read(message_length)
    
    try:
        # 解析JSON消息
        message = json.loads(message_bytes.decode('utf-8'))
        return message
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 内容: {message_bytes}")
        return None
    except Exception as e:
        logger.error(f"读取消息时出错: {e}")
        return None

def send_message(message: Dict):
    """
    向stdout发送消息
    
    参数:
        message: 要发送的消息
    """
    # 将消息转换为JSON字符串
    message_json = json.dumps(message)
    message_bytes = message_json.encode('utf-8')
    
    # 发送消息长度和内容
    sys.stdout.buffer.write(struct.pack('I', len(message_bytes)))
    sys.stdout.buffer.write(message_bytes)
    sys.stdout.buffer.flush()

def handle_scan_directory(request: Dict) -> Dict:
    """
    处理扫描目录请求
    
    参数:
        request: 请求数据
        
    返回:
        dict: 响应数据
    """
    path = request.get('path', '.')
    
    try:
        # 确保路径存在
        if not os.path.exists(path):
            return {'success': False, 'error': f"路径不存在: {path}"}
            
        if not os.path.isdir(path):
            return {'success': False, 'error': f"路径不是目录: {path}"}
            
        # 获取目录下的所有文件
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        
        return {
            'success': True,
            'files': files,
            'path': path
        }
    except Exception as e:
        logger.error(f"扫描目录失败: {e}")
        return {'success': False, 'error': str(e)}

def handle_read_file(request: Dict) -> Dict:
    """
    处理读取文件请求
    
    参数:
        request: 请求数据
        
    返回:
        dict: 响应数据
    """
    path = request.get('path')
    
    if not path:
        return {'success': False, 'error': "缺少路径参数"}
        
    try:
        if not os.path.exists(path):
            return {'success': False, 'error': f"文件不存在: {path}"}
            
        # 读取文件内容
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return {
            'success': True,
            'content': content,
            'path': path
        }
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return {'success': False, 'error': str(e)}

def handle_delete_file(request: Dict) -> Dict:
    """
    处理删除文件请求
    
    参数:
        request: 请求数据
        
    返回:
        dict: 响应数据
    """
    path = request.get('path')
    
    if not path:
        return {'success': False, 'error': "缺少路径参数"}
        
    try:
        if not os.path.exists(path):
            return {'success': False, 'error': f"文件不存在: {path}"}
            
        # 删除文件
        os.remove(path)
            
        return {
            'success': True,
            'path': path
        }
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return {'success': False, 'error': str(e)}

def handle_request(request: Dict) -> Dict:
    """
    处理请求
    
    参数:
        request: 请求数据
        
    返回:
        dict: 响应数据
    """

    action = request.get('action')
    
    if action == 'scanDirectory':
        return handle_scan_directory(request)
    elif action == 'readFile':
        return handle_read_file(request)
    elif action == 'deleteFile':
        return handle_delete_file(request)
    else:
        return {'success': False, 'error': f"不支持的操作: {action}"}

def main_loop():
    """主循环，处理来自扩展的消息"""
    logger.info("本地消息主机已启动，等待消息...")
    
    while True:
        message = get_message()
        if message is None:
            # 读取消息失败，可能是连接已关闭
            logger.warning("读取消息失败，退出...")
            break
            
        logger.info(f"收到消息: {message}")
        
        # 处理请求
        response = handle_request(message)
        
        # 发送响应
        logger.info(f"发送响应: {response}")
        send_message(response)

def main():
    # 检测是否有--install参数
    if len(sys.argv) > 1 and sys.argv[1] == '--install':
        if install_host():
            print("本地消息主机安装成功！请重启Chrome浏览器。")
        else:
            print("本地消息主机安装失败，请查看日志获取详细信息。")
        return 
    else:  
        logger.info("直接启动主循环")
        main_loop()

if __name__ == "__main__":
    main()
