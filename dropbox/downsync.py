#!/usr/bin/env python
# CREATED DATE: 2025年05月25日 星期日 20时40分53秒
# CREATED BY: qiangxu, toxuqiang@gmail.com


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dropbox Batch Download Script
分批下载Dropbox文件的Python脚本，支持手动转移控制
"""

import os
import json
import time
import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import dropbox
from dropbox.exceptions import ApiError, AuthError


class DropboxBatchDownloader:
    def __init__(self, access_token: str, local_download_dir: str, 
                 state_file: str = "download_state.json",
                 batch_size_gb: float = 50.0):
        """
        初始化下载器
        
        Args:
            access_token: Dropbox访问令牌
            local_download_dir: 本地下载目录
            state_file: 状态记录文件路径
            batch_size_gb: 批次大小限制(GB)
        """
        self.dbx = dropbox.Dropbox(access_token)
        self.local_download_dir = Path(local_download_dir)
        self.state_file = Path(state_file)
        self.batch_size_bytes = int(batch_size_gb * 1024 * 1024 * 1024)  # 转换为字节
        
        # 创建必要目录
        self.local_download_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载状态
        self.download_state = self._load_state()
        
        # 配置日志
        self._setup_logging()
        
        # 统计信息
        self.stats = {
            'total_files': 0,
            'downloaded': 0,
            'transferred': 0,
            'pending_transfer': 0,
            'failed': 0,
            'current_batch_size': 0
        }
    
    def _setup_logging(self):
        """配置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dropbox_download.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_state(self) -> Dict:
        """加载下载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"无法加载状态文件: {e}")
        return {
            'files': {},
            'batches': {},
            'current_batch': 1,
            'last_update': datetime.now().isoformat()
        }
    
    def _save_state(self):
        """保存下载状态"""
        try:
            self.download_state['last_update'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.download_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def _get_local_downloaded_size(self) -> int:
        """计算本地已下载但未转移的文件总大小"""
        total_size = 0
        if not self.local_download_dir.exists():
            return 0
        
        for file_path, file_info in self.download_state['files'].items():
            if file_info.get('status') == 'downloaded':
                local_file = self.local_download_dir / file_path.lstrip('/')
                if local_file.exists():
                    total_size += local_file.stat().st_size
        
        return total_size
    
    def _update_file_state(self, dropbox_path: str, status: str, **kwargs):
        """更新文件下载状态"""
        if 'files' not in self.download_state:
            self.download_state['files'] = {}
        
        if dropbox_path not in self.download_state['files']:
            self.download_state['files'][dropbox_path] = {}
        
        self.download_state['files'][dropbox_path].update({
            'status': status,
            'last_update': datetime.now().isoformat(),
            **kwargs
        })
        self._save_state()
    
    def get_dropbox_files(self, folder_path: str = "") -> List[Dict]:
        """获取Dropbox文件列表"""
        files = []
        try:
            self.logger.info(f"扫描Dropbox文件夹: {folder_path or '根目录'}")
            
            result = self.dbx.files_list_folder(folder_path, recursive=True)
            
            while True:
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        files.append({
                            'path': entry.path_lower,
                            'size': entry.size,
                            'modified': entry.server_modified.isoformat(),
                            'content_hash': entry.content_hash
                        })
                
                if not result.has_more:
                    break
                result = self.dbx.files_list_folder_continue(result.cursor)
                
        except ApiError as e:
            self.logger.error(f"获取Dropbox文件列表失败: {e}")
            return []
        
        self.logger.info(f"发现 {len(files)} 个文件")
        self.stats['total_files'] = len(files)
        return files
    
    def download_file(self, dropbox_path: str, local_path: Path, file_size: int) -> bool:
        """下载单个文件"""
        try:
            self.logger.info(f"下载文件: {dropbox_path} ({self._format_size(file_size)})")
            
            # 创建本地目录
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 下载文件
            with open(local_path, 'wb') as f:
                metadata, response = self.dbx.files_download(dropbox_path)
                f.write(response.content)
            
            # 验证文件大小
            if local_path.stat().st_size != file_size:
                self.logger.error(f"文件大小不匹配: {dropbox_path}")
                local_path.unlink(missing_ok=True)
                return False
            
            return True
            
        except ApiError as e:
            self.logger.error(f"下载文件失败 {dropbox_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"下载文件出现异常 {dropbox_path}: {e}")
            return False
    
    def check_batch_limit(self) -> Tuple[bool, int]:
        """检查是否达到批次大小限制"""
        current_size = self._get_local_downloaded_size()
        return current_size >= self.batch_size_bytes, current_size
    
    def prompt_transfer(self, current_size: int) -> bool:
        """提示用户进行转移操作"""
        print("\n" + "="*60)
        print("📦 批次下载完成！")
        print(f"当前已下载: {self._format_size(current_size)}")
        print(f"批次限制: {self._format_size(self.batch_size_bytes)}")
        print("="*60)
        print("\n请将已下载的文件转移到目标位置：")
        print(f"  源目录: {self.local_download_dir.absolute()}")
        print("\n转移选项：")
        print("  1. 复制到NAS/移动硬盘")
        print("  2. 使用其他方式备份")
        print("  3. 手动整理文件")
        print("\n⚠️  转移完成后，本地文件将被清理以继续下载")
        
        while True:
            response = input("\n转移完成了吗？(y/n/s) [y=是 n=否 s=查看状态]: ").lower().strip()
            
            if response == 'y':
                return True
            elif response == 'n':
                print("请完成文件转移后再继续...")
                continue
            elif response == 's':
                self._show_transfer_status()
                continue
            else:
                print("请输入 y/n/s")
    
    def _show_transfer_status(self):
        """显示转移状态信息"""
        print("\n📊 当前状态：")
        
        downloaded_files = []
        for file_path, file_info in self.download_state['files'].items():
            if file_info.get('status') == 'downloaded':
                local_file = self.local_download_dir / file_path.lstrip('/')
                if local_file.exists():
                    downloaded_files.append({
                        'path': file_path,
                        'size': local_file.stat().st_size,
                        'local_path': local_file
                    })
        
        if downloaded_files:
            print(f"等待转移的文件: {len(downloaded_files)} 个")
            total_size = sum(f['size'] for f in downloaded_files)
            print(f"总大小: {self._format_size(total_size)}")
            
            print("\n最近下载的文件:")
            for i, file_info in enumerate(downloaded_files[-10:], 1):
                print(f"  {i:2d}. {file_info['path']} ({self._format_size(file_info['size'])})")
        else:
            print("没有等待转移的文件")
    
    def clear_transferred_files(self):
        """清理已转移的文件"""
        cleared_count = 0
        cleared_size = 0
        
        for file_path, file_info in list(self.download_state['files'].items()):
            if file_info.get('status') == 'downloaded':
                local_file = self.local_download_dir / file_path.lstrip('/')
                if local_file.exists():
                    file_size = local_file.stat().st_size
                    try:
                        local_file.unlink()
                        cleared_count += 1
                        cleared_size += file_size
                        
                        # 更新状态为已转移
                        self._update_file_state(file_path, 'transferred', 
                                              transferred_time=datetime.now().isoformat())
                        
                    except Exception as e:
                        self.logger.error(f"删除文件失败 {local_file}: {e}")
        
        # 清理空目录
        self._cleanup_empty_dirs(self.local_download_dir)
        
        self.logger.info(f"清理完成：{cleared_count} 个文件，释放 {self._format_size(cleared_size)} 空间")
        return cleared_count, cleared_size
    
    def _cleanup_empty_dirs(self, directory: Path):
        """递归清理空目录"""
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    self._cleanup_empty_dirs(item)
                    try:
                        item.rmdir()  # 只能删除空目录
                    except OSError:
                        pass  # 目录不为空，忽略
        except Exception:
            pass
    
    def sync_batch(self, folder_path: str = "", delay_between_files: float = 1.0) -> bool:
        """执行批次同步"""
        # 检查当前是否需要转移
        needs_transfer, current_size = self.check_batch_limit()
        if needs_transfer:
            self.logger.info(f"当前本地文件大小: {self._format_size(current_size)}")
            if self.prompt_transfer(current_size):
                self.clear_transferred_files()
            else:
                self.logger.info("等待用户完成文件转移...")
                return False
        
        # 获取文件列表
        files = self.get_dropbox_files(folder_path)
        if not files:
            self.logger.warning("没有找到要下载的文件")
            return True
        
        # 过滤出需要下载的文件
        pending_files = []
        for file_info in files:
            file_path = file_info['path']
            file_state = self.download_state['files'].get(file_path, {})
            
            if file_state.get('status') not in ['downloaded', 'transferred']:
                pending_files.append(file_info)
        
        if not pending_files:
            self.logger.info("所有文件都已下载完成")
            return True
        
        self.logger.info(f"待下载文件: {len(pending_files)} 个")
        
        # 按大小排序，小文件优先
        pending_files.sort(key=lambda x: x['size'])
        
        # 开始下载
        for i, file_info in enumerate(pending_files, 1):
            dropbox_path = file_info['path']
            local_path = self.local_download_dir / dropbox_path.lstrip('/')
            
            self.logger.info(f"处理文件 {i}/{len(pending_files)}: {dropbox_path}")
            
            # 检查批次限制
            needs_transfer, current_size = self.check_batch_limit()
            if needs_transfer:
                self.logger.info("达到批次大小限制，暂停下载")
                if self.prompt_transfer(current_size):
                    self.clear_transferred_files()
                else:
                    return False
            
            # 下载文件
            self._update_file_state(dropbox_path, 'downloading', 
                                  size=file_info['size'],
                                  modified=file_info['modified'])
            
            if self.download_file(dropbox_path, local_path, file_info['size']):
                self._update_file_state(dropbox_path, 'downloaded',
                                      local_path=str(local_path),
                                      file_hash=self._get_file_hash(local_path))
                self.stats['downloaded'] += 1
                self.logger.info(f"✅ 下载完成: {dropbox_path}")
            else:
                self._update_file_state(dropbox_path, 'download_failed')
                self.stats['failed'] += 1
                self.logger.error(f"❌ 下载失败: {dropbox_path}")
            
            # 控制下载频率
            if delay_between_files > 0:
                time.sleep(delay_between_files)
            
            # 每下载10个文件显示一次统计
            if i % 10 == 0:
                self._print_stats()
        
        # 检查是否还有待转移文件
        needs_transfer, current_size = self.check_batch_limit()
        if needs_transfer:
            self.logger.info("所有文件下载完成，还有文件待转移")
            if self.prompt_transfer(current_size):
                self.clear_transferred_files()
        
        return True
    
    def _print_stats(self):
        """打印统计信息"""
        current_size = self._get_local_downloaded_size()
        
        self.logger.info("=" * 50)
        self.logger.info("下载统计:")
        self.logger.info(f"  总文件数: {self.stats['total_files']}")
        self.logger.info(f"  已下载: {self.stats['downloaded']}")
        self.logger.info(f"  失败数: {self.stats['failed']}")
        self.logger.info(f"  本地大小: {self._format_size(current_size)}")
        self.logger.info(f"  批次限制: {self._format_size(self.batch_size_bytes)}")
        self.logger.info("=" * 50)
    
    def retry_failed(self):
        """重试失败的文件"""
        failed_files = []
        for path, state in self.download_state['files'].items():
            if state.get('status') == 'download_failed':
                failed_files.append(path)
        
        if not failed_files:
            self.logger.info("没有失败的文件需要重试")
            return
        
        self.logger.info(f"重试 {len(failed_files)} 个失败的文件")
        
        for dropbox_path in failed_files:
            try:
                metadata = self.dbx.files_get_metadata(dropbox_path)
                if isinstance(metadata, dropbox.files.FileMetadata):
                    local_path = self.local_download_dir / dropbox_path.lstrip('/')
                    
                    if self.download_file(dropbox_path, local_path, metadata.size):
                        self._update_file_state(dropbox_path, 'downloaded',
                                              local_path=str(local_path),
                                              file_hash=self._get_file_hash(local_path))
                        self.logger.info(f"✅ 重试成功: {dropbox_path}")
                    else:
                        self.logger.error(f"❌ 重试失败: {dropbox_path}")
                        
            except ApiError as e:
                self.logger.error(f"重试文件失败 {dropbox_path}: {e}")
    
    def show_status(self):
        """显示详细状态"""
        print("\n" + "="*60)
        print("📋 下载状态报告")
        print("="*60)
        
        # 统计各状态文件数量
        status_count = {}
        total_size = 0
        
        for file_info in self.download_state['files'].values():
            status = file_info.get('status', 'unknown')
            status_count[status] = status_count.get(status, 0) + 1
            total_size += file_info.get('size', 0)
        
        print(f"总文件数: {len(self.download_state['files'])}")
        print(f"总大小: {self._format_size(total_size)}")
        print("\n状态分布:")
        for status, count in status_count.items():
            status_name = {
                'downloaded': '已下载',
                'transferred': '已转移', 
                'downloading': '下载中',
                'download_failed': '下载失败',
                'unknown': '未知'
            }.get(status, status)
            print(f"  {status_name}: {count} 个")
        
        # 本地文件状态
        current_local_size = self._get_local_downloaded_size()
        print(f"\n本地待转移: {self._format_size(current_local_size)}")
        print(f"批次限制: {self._format_size(self.batch_size_bytes)}")
        
        if current_local_size >= self.batch_size_bytes:
            print("⚠️  已达到批次限制，建议转移文件")


def main():
    """主函数"""
    # 配置参数
    DROPBOX_ACCESS_TOKEN = "sl.u.AFt9_Dn2MdbRhPjtzvGMMQNcofU5JWA3pAFwjU0Mr7CRHSzK0lpxkig097N9V_diQySqVVCaXxwQh9CcUvL8nyzqnPcSQbhZUAeUh0gUp_pgsutrNSE1wFeEqgs3mKugqx1qofL2wWzBofoBB4_2q8P-xSk6tkZ2rMAm-wUgTo_Td-jdGLRJ3AnkENDOsUx_cz_iq--oHdJ1AZdkGANdKyEPcpTsR2CCIESAZjmrhj0grX2QsYereMAg2w3noV24WyPZvxNa29xGZrJpOtcaoXtsZ_umkKL_hdXRUgwsSX8t9IhVU10g02MjR0SEhoGmMPElDOyDaRmMYORMrCtKUhTF6w4xYE4sXgWB_oIoprZWIhI87a3jC6cGxTcU0MrqCTJ0qOw-oHDK0CINB1ZG9o1xVyICFC88Zio1BnSmsJ3jxHT-QxPtc4u5lugpPb-war0hwjGN_nK3bxNu_8x_vB3TO8Cv6aRSL-N3pVCw6ZPUo1z3xnjFFtMfLzlUR4QY2pxZA8AFqDXpG8ZTooFDbqXUTg1ZRnqEpP0riddY3sfVEpkktjnVTq8EcfJc8KRmgth_jhS8hrDxSjYBk11bmNkTHw1j3SAWmrw-5eA9Gmy2aP7T6wGtWR9gs3AKEvWr11ezUS-Gu29nu00t5P-9Nz-gF939xn7-nH7eiVHFLIpGuaaJrqB7_c8kRH21Cmz7qvjUnkK-KluhvZWzM7F4nmEVdabR7Qsh9EATiYKGJR2yRcM15icimE0D9fxO9g98Rz5iVx8-m8VMx6MBbTJQiX8WYQHIhXA4aO9u0bwPht3orY2HjGR0h6-HoYIxqc8byVsSTCwya3DB0PHPLFwFT896HLv4S6eN8OU2qEyp5nTJFSsMogAG6QzrS6Dgx5K9ud1ipA8fIDnm_w6L1a2zspCICd4pLg0jSBgyEnOpMWzk6_1NxX9NtY175iKINh4TpG9XGzYa-gQOqOxsDk5X70VH4gzkHa1vq0ujxliWTtNxZHh3PAf5F6B7ysoHbYoKbSsp8kYYyo8YKDXaPh9BKYbFOPvHBfb_lvXhqmaNDWtdtLVeT4wFLuzGhWGfgoh0mAhABpMx4T9PqSmU2Go1ZM06Po5bQbfaEpECZrtBZ61-YzcP5JeGCnrVSrycs6RjORNBYp-ZhDuwpzdbaN3L58AH02pKt1-OqdF0CWpEdHU83YQjQ9414JuLUToHLeCfCDZzOvZFady_oBMLvZZSZ8AewLQjEAyiM-4nBXbH4J18tSKVLW1TBrfTesry0UBg8DDcalWxcwPzUlNrLcymx3dSI-YQiHOSs6K-WX3thA4YB3GmQcTa-BkfAZ5T6YK1w4gN9AthGvm9xEc1761DKcFwKKB_K3ZuQ4efZleSQcq_cMEVPoV_u_ZVPSR74ozqbzNuUfhRHTzbo7ZeAPcFDRXg"
    LOCAL_DOWNLOAD_DIR = "./downloads"  # 本地下载目录
    DROPBOX_FOLDER = ""  # Dropbox文件夹路径，空字符串表示根目录
    BATCH_SIZE_GB = 50.0  # 批次大小限制(GB)
    
    # 创建下载器
    downloader = DropboxBatchDownloader(
        access_token=DROPBOX_ACCESS_TOKEN,
        local_download_dir=LOCAL_DOWNLOAD_DIR,
        batch_size_gb=BATCH_SIZE_GB
    )
    
    try:
        print("🚀 Dropbox 批量下载器")
        print(f"📁 下载目录: {LOCAL_DOWNLOAD_DIR}")
        print(f"📦 批次大小: {BATCH_SIZE_GB}GB")
        print("-" * 40)
        
        # 显示当前状态
        downloader.show_status()
        
        # 开始批次同步
        downloader.sync_batch(
            folder_path=DROPBOX_FOLDER,
            delay_between_files=1.0
        )
        
        print("\n🎉 下载任务完成！")
        downloader._print_stats()
        
    except KeyboardInterrupt:
        downloader.logger.info("用户中断下载")
        print("\n⏸️  下载已暂停，可随时继续")
    except Exception as e:
        downloader.logger.error(f"下载过程出现异常: {e}")
        print(f"\n❌ 出现错误: {e}")


if __name__ == "__main__":
    main()

