#!/usr/bin/env python
# CREATED DATE: 2025å¹´05æœˆ25æ—¥ æ˜ŸæœŸæ—¥ 20æ—¶40åˆ†53ç§’
# CREATED BY: qiangxu, toxuqiang@gmail.com


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dropbox Batch Download Script
Python script for batch downloading Dropbox files, supporting manual transfer control,
directory-by-directory processing, configuration via a YAML file, and
targeted folder download with archiving.
"""

import os
import json
import time
import hashlib
import logging
import shutil # For rmtree
import tarfile # For tar.gz compression
import argparse # For command-line arguments
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import dropbox
from dropbox.exceptions import ApiError, AuthError
import yaml

DEFAULT_CONFIG_PATH = "config.yaml"

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Optional[Dict]:
    """Loads configuration from a YAML file."""
    logger = logging.getLogger(__name__)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                logger.warning(f"Config file '{config_path}' is empty or not valid YAML. Returning empty config.")
                return {}
            logger.info(f"Configuration successfully loaded from '{config_path}'.")
            return config
    except FileNotFoundError:
        logger.error(f"Config file '{config_path}' not found.")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file '{config_path}': {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading config '{config_path}': {e}")
        return None

class DropboxBatchDownloader:
    def __init__(self, access_token: str, local_download_dir: str,
                 state_file: str = "download_state.json",
                 batch_size_gb: float = 50.0,
                 config_path: str = DEFAULT_CONFIG_PATH):
        self._setup_logging()
        self.current_access_token = access_token
        self.dbx = dropbox.Dropbox(access_token)
        self.config_path = config_path
        self.local_download_dir = Path(local_download_dir)
        self.state_file = Path(state_file)
        self.batch_size_bytes = int(batch_size_gb * 1024 * 1024 * 1024)
        self.local_download_dir.mkdir(parents=True, exist_ok=True)
        self.download_state = self._load_state()
        self.stats = {
            'total_files_in_current_scope': 0, 'downloaded_in_run': 0,
            'transferred_in_run': 0, 'failed_in_run': 0,
        }

    def _setup_logging(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def _reload_config_and_update_settings(self):
        self.logger.info(f"Attempting to reload configuration from '{self.config_path}'...")
        config = load_config(self.config_path)
        if config is None:
            self.logger.error("Failed to reload configuration. Continuing with existing settings.")
            return
        new_access_token = config.get('DROPBOX_ACCESS_TOKEN')
        if new_access_token and new_access_token != self.current_access_token:
            self.logger.info("Dropbox access token has changed. Re-initializing Dropbox client.")
            try:
                self.dbx = dropbox.Dropbox(new_access_token)
                self.current_access_token = new_access_token
                self.logger.info("Dropbox client re-initialized.")
            except Exception as e:
                self.logger.error(f"Failed to re-initialize Dropbox client: {e}.")
        elif not new_access_token:
            self.logger.warning("'DROPBOX_ACCESS_TOKEN' not found in reloaded config. Token not updated.")
        new_batch_size_gb_str = config.get('BATCH_SIZE_GB')
        if new_batch_size_gb_str is not None:
            try:
                new_batch_size_gb = float(new_batch_size_gb_str)
                new_batch_size_bytes = int(new_batch_size_gb * 1024 * 1024 * 1024)
                if new_batch_size_bytes != self.batch_size_bytes:
                    self.logger.info(f"Batch size changed from {self._format_size(self.batch_size_bytes)} to {self._format_size(new_batch_size_bytes)}.")
                    self.batch_size_bytes = new_batch_size_bytes
            except ValueError:
                self.logger.error(f"Invalid 'BATCH_SIZE_GB' in reloaded config. Not updated.")
        self.logger.info("Configuration reload attempt finished.")

    def _load_state(self) -> Dict:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    for key, default_val in [('files', {}),
                                             ('processed_top_level_items_for_sync', []),
                                             ('last_update', datetime.now().isoformat())]:
                        if key not in state: state[key] = default_val
                    return state
            except Exception as e:
                self.logger.warning(f"Could not load state file: {e}")
        return {'files': {}, 'processed_top_level_items_for_sync': [], 'last_update': datetime.now().isoformat()}

    def _save_state(self):
        try:
            self.download_state['last_update'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.download_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state file: {e}")

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        if not file_path.is_file():
            self.logger.warning(f"Cannot hash, not a file: {file_path}")
            return None
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""): hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Error hashing {file_path}: {e}")
            return None

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes is None: size_bytes = 0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024: return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    def _get_local_downloaded_size(self) -> int:
        total_size = 0
        if not self.local_download_dir.exists(): return 0
        for file_path_str, file_info in self.download_state.get('files', {}).items():
            if file_info.get('status') == 'downloaded':
                local_path_str = file_info.get('local_path')
                local_file = Path(local_path_str) if local_path_str else (self.local_download_dir / file_path_str.lstrip('/'))
                if local_file.exists() and local_file.is_file():
                    try: total_size += local_file.stat().st_size
                    except FileNotFoundError: self.logger.warning(f"File in state but not found: {local_file}")
        return total_size

    def _update_file_state(self, dropbox_path: str, status: str, **kwargs):
        if 'files' not in self.download_state: self.download_state['files'] = {}
        if dropbox_path not in self.download_state['files']: self.download_state['files'][dropbox_path] = {}
        self.download_state['files'][dropbox_path].update({'status': status, 'last_update': datetime.now().isoformat(), **kwargs})
        self._save_state()

    def get_dropbox_files(self, folder_path: str = "", recursive: bool = True) -> List[Dict]:
        files = []
        self.logger.info(f"Scanning Dropbox: '{folder_path or 'Root'}' (Recursive: {recursive})")
        try:
            result = self.dbx.files_list_folder(folder_path, recursive=recursive)
            while True:
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        files.append({'path': entry.path_lower, 'name': entry.name, 'size': entry.size,
                                      'modified': entry.server_modified.isoformat(), 'content_hash': entry.content_hash})
                if not result.has_more: break
                result = self.dbx.files_list_folder_continue(result.cursor)
        except ApiError as e:
            self.logger.error(f"Failed to get file list for '{folder_path}': {e}")
            return []
        self.logger.info(f"Found {len(files)} files in '{folder_path or 'Root'}'.")
        self.stats['total_files_in_current_scope'] = len(files)
        return files

    def download_file(self, dropbox_path: str, local_path: Path, file_size: int) -> bool:
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'wb') as f:
                _, response = self.dbx.files_download(path=dropbox_path)
                f.write(response.content)
            if local_path.stat().st_size != file_size:
                self.logger.error(f"Size mismatch for {dropbox_path}: Expected {file_size}, Got {local_path.stat().st_size}")
                local_path.unlink(missing_ok=True); return False
            return True
        except Exception as e:
            self.logger.error(f"Download of {dropbox_path} failed: {e}")
            if local_path.exists(): local_path.unlink(missing_ok=True)
            return False

    def check_batch_limit(self, check_if_any_downloaded: bool = False) -> Tuple[bool, int]:
        current_size = self._get_local_downloaded_size()
        return (current_size > 0 if check_if_any_downloaded else current_size >= self.batch_size_bytes), current_size

    def prompt_transfer(self, current_size: int, current_scope_description: Optional[str] = None, is_final_transfer: bool = False) -> bool:
        print(f"\n{'='*60}\n📦 Batch Download Paused for File Transfer!")
        if is_final_transfer: print("All scopes processed. Final check for remaining files.")
        elif current_scope_description: print(f"Batch limit likely reached during: {current_scope_description}")
        print(f"Currently downloaded (pending transfer): {self._format_size(current_size)}")
        print(f"Batch limit: {self._format_size(self.batch_size_bytes)}")
        print(f"{'='*60}\nPlease transfer files from: {self.local_download_dir.resolve()}")
        print("Options: 1. Copy to NAS/HDD 2. Other backup 3. Manual organization")
        print("⚠️ After transfer, local files are cleared to continue.\n")
        user_response_positive = False
        while True:
            response = input("Transfer complete? (y/n/s) [y=yes, n=no, s=status]: ").lower().strip()
            if response == 'y': user_response_positive = True; break
            elif response == 'n': print("Please complete transfer..."); user_response_positive = False; break
            elif response == 's': self._show_global_transfer_status()
            else: print("Please enter y, n, or s.")
        self._reload_config_and_update_settings()
        return user_response_positive

    def _show_global_transfer_status(self):
        print("\n📊 Current Global Transfer Status:")
        downloaded_files_list = []
        total_size_val = 0
        for file_path, file_info in self.download_state.get('files',{}).items():
            if file_info.get('status') == 'downloaded':
                local_path_str = file_info.get('local_path')
                local_file = Path(local_path_str) if local_path_str else (self.local_download_dir / file_path.lstrip('/'))
                if local_file.exists() and local_file.is_file():
                    try:
                        fsize = local_file.stat().st_size
                        downloaded_files_list.append({'path': file_path, 'size': fsize})
                        total_size_val += fsize
                    except FileNotFoundError: pass
        if downloaded_files_list:
            print(f"Files pending transfer: {len(downloaded_files_list)}, Total size: {self._format_size(total_size_val)}")
            downloaded_files_list.sort(key=lambda x: x['path'])
            print("Up to 10 files (sorted by path):")
            for i, item in enumerate(downloaded_files_list[-10:], 1): print(f"  {i:2d}. {item['path']} ({self._format_size(item['size'])})")
        else: print("No files pending transfer.")
        print(f"Local download dir: {self.local_download_dir.resolve()}")


    def clear_transferred_files(self):
        self.logger.info("Starting cleanup of transferred files...")
        cleared_count = 0; cleared_size = 0
        for file_path, file_info in list(self.download_state.get('files', {}).items()):
            if file_info.get('status') == 'downloaded':
                local_path_str = file_info.get('local_path')
                local_file = Path(local_path_str) if local_path_str else (self.local_download_dir / file_path.lstrip('/'))
                if local_file.exists() and local_file.is_file():
                    try:
                        size = local_file.stat().st_size; local_file.unlink()
                        cleared_count += 1; cleared_size += size
                        self._update_file_state(file_path, 'transferred', transferred_time=datetime.now().isoformat())
                    except Exception as e: self.logger.error(f"Failed to delete {local_file}: {e}")
                else:
                    self.logger.warning(f"File {local_file} marked 'downloaded' but not found. Status -> 'missing_local'.")
                    self._update_file_state(file_path, 'missing_local', missing_time=datetime.now().isoformat())
        self._cleanup_empty_dirs(self.local_download_dir)
        self.logger.info(f"Cleanup: {cleared_count} files, freed {self._format_size(cleared_size)}.")
        self.stats['transferred_in_run'] += cleared_count


    def _cleanup_empty_dirs(self, directory: Path):
        if not directory.is_dir(): return
        for item in directory.iterdir():
            if item.is_dir(): self._cleanup_empty_dirs(item)
        try:
            if not any(directory.iterdir()): directory.rmdir(); self.logger.info(f"Removed empty dir: {directory}")
        except Exception as e: self.logger.debug(f"Could not remove dir {directory}: {e}")

    def _get_top_level_entries(self, folder_path: str) -> Tuple[List[Dict], List[str]]:
        direct_files_metadata = []; top_level_folder_paths = []
        try:
            self.logger.info(f"Listing entries in Dropbox: '{folder_path or 'Root'}'")
            result = self.dbx.files_list_folder(folder_path, recursive=False)
            while True:
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        direct_files_metadata.append({'path': entry.path_lower, 'name': entry.name, 'size': entry.size,
                                                      'modified': entry.server_modified.isoformat(), 'content_hash': entry.content_hash})
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        top_level_folder_paths.append(entry.path_lower)
                if not result.has_more: break
                result = self.dbx.files_list_folder_continue(result.cursor)
        except ApiError as e: self.logger.error(f"Failed to list entries in '{folder_path}': {e}")
        top_level_folder_paths.sort(); direct_files_metadata.sort(key=lambda x: x['path'])
        self.logger.info(f"Found {len(direct_files_metadata)} direct files and {len(top_level_folder_paths)} folders in '{folder_path or 'Root'}'.")
        return direct_files_metadata, top_level_folder_paths

    def _process_file_downloads_for_list(self, files_to_consider: List[Dict], scope_description: str, delay_between_files: float) -> bool:
        self.logger.info(f"Processing {len(files_to_consider)} files for scope: {scope_description}")
        self.stats['total_files_in_current_scope'] = len(files_to_consider)
        pending_files = []
        for file_info in files_to_consider:
            file_path = file_info['path']
            file_state = self.download_state['files'].get(file_path, {})
            # MODIFIED: Also skip 'archived' files
            if file_state.get('status') not in ['downloaded', 'transferred', 'archived']:
                pending_files.append(file_info)
        if not pending_files: self.logger.info(f"No pending files for scope: {scope_description}"); return True
        self.logger.info(f"Found {len(pending_files)} pending files in scope: {scope_description}")
        pending_files.sort(key=lambda x: x['path'])
        for i, file_info in enumerate(pending_files, 1):
            dropbox_path = file_info['path']; local_path = self.local_download_dir / dropbox_path.lstrip('/')
            expected_size = file_info['size']
            self.logger.info(f"Handling file {i}/{len(pending_files)} in '{scope_description}': {file_info['name']} ({self._format_size(expected_size)}) Path: {dropbox_path}")
            if local_path.exists() and local_path.is_file():
                local_file_size = local_path.stat().st_size
                if local_file_size == expected_size:
                    self.logger.info(f"File '{dropbox_path}' exists locally with correct size. Marking downloaded.")
                    hash_val = self._get_file_hash(local_path)
                    self._update_file_state(dropbox_path, 'downloaded', local_path=str(local_path.resolve()),
                                          file_hash=hash_val, size=expected_size, modified=file_info['modified'])
                    self.stats['downloaded_in_run'] += 1
                    if delay_between_files > 0: time.sleep(delay_between_files)
                    if i % 10 == 0 or i == len(pending_files): self._print_stats()
                    continue
                else:
                    self.logger.warning(f"File '{dropbox_path}' exists locally with incorrect size. Re-downloading.")
            needs_transfer, current_size = self.check_batch_limit()
            if needs_transfer:
                if self.prompt_transfer(current_size, current_scope_description=scope_description):
                    self.clear_transferred_files()
                else: self.logger.info("User stopped. Download for scope will stop."); return False
            self._update_file_state(dropbox_path, 'downloading', size=expected_size, modified=file_info['modified'])
            if self.download_file(dropbox_path, local_path, expected_size):
                hash_val = self._get_file_hash(local_path)
                self._update_file_state(dropbox_path, 'downloaded', local_path=str(local_path.resolve()),
                                      file_hash=hash_val, size=expected_size, modified=file_info['modified'])
                self.stats['downloaded_in_run'] += 1; self.logger.info(f"✅ Downloaded: {dropbox_path}")
            else:
                self._update_file_state(dropbox_path, 'download_failed')
                self.stats['failed_in_run'] += 1; self.logger.error(f"❌ Failed: {dropbox_path}")
            if delay_between_files > 0: time.sleep(delay_between_files)
            if i % 10 == 0 or i == len(pending_files): self._print_stats()
        self.logger.info(f"Finished downloads for scope: {scope_description}")
        return True

    def sync_by_directory_structure(self, root_dropbox_path: str = "", delay_between_files: float = 1.0) -> bool:
        self.logger.info(f"Starting sync by directory structure for: '{root_dropbox_path or 'Root'}'")
        STATE_KEY = 'processed_top_level_items_for_sync'
        processed_list = self.download_state[STATE_KEY]
        direct_files, top_folders = self._get_top_level_entries(root_dropbox_path)
        scopes = []
        root_files_id = f"{root_dropbox_path or '#ROOT#'}#DIRECT_FILES#"
        if direct_files: scopes.append({'id': root_files_id, 'description': f"Direct files in '{root_dropbox_path or 'Root'}'", 'files_list': direct_files, 'is_folder_scope': False})
        for tlf in top_folders: scopes.append({'id': tlf, 'description': f"Folder '{tlf}'", 'dropbox_path_for_files': tlf, 'is_folder_scope': True})
        if not scopes: self.logger.info(f"No items to process under '{root_dropbox_path or 'Root'}'."); return True
        for scope in scopes:
            if scope['id'] in processed_list: self.logger.info(f"Scope '{scope['description']}' already processed. Skipping."); continue
            self.logger.info(f"--- Starting processing for scope: {scope['description']} ---")
            files = scope['files_list'] if not scope['is_folder_scope'] else self.get_dropbox_files(folder_path=scope['dropbox_path_for_files'], recursive=True)
            if not files: self.logger.info(f"No files for scope '{scope['description']}'. Marking processed."); processed_list.append(scope['id']); self._save_state(); continue
            if not self._process_file_downloads_for_list(files, scope['description'], delay_between_files):
                self.logger.info(f"Processing for '{scope['description']}' interrupted. Sync stopping."); return False
            self.logger.info(f"--- Finished scope: {scope['description']} ---"); processed_list.append(scope['id']); self._save_state()
        needs_final, final_size = self.check_batch_limit(check_if_any_downloaded=True)
        if needs_final and final_size > 0:
            self.logger.info("All scopes processed. Final check for transfer.")
            if self.prompt_transfer(final_size, is_final_transfer=True, current_scope_description="Overall completion"):
                self.clear_transferred_files()
        self.logger.info("Sync by directory structure finished."); return True

    def process_specific_folder_and_archive(self, dropbox_folder_path: str, delay_between_files: float) -> bool:
        """Downloads a specific folder, then compresses and cleans it."""
        self.logger.info(f"--- TARGETED MODE: Processing Dropbox folder for archival: {dropbox_folder_path} ---")

        norm_dbx_folder_path = dropbox_folder_path.strip()
        if norm_dbx_folder_path and not norm_dbx_folder_path.startswith('/'):
            norm_dbx_folder_path = '/' + norm_dbx_folder_path
        norm_dbx_folder_path = norm_dbx_folder_path.rstrip('/')
        if norm_dbx_folder_path == '/': norm_dbx_folder_path = "" 

        if not norm_dbx_folder_path:
            self.logger.error("Targeted archival of the Dropbox root is not supported with -d. Please specify a subfolder.")
            return False

        files_in_scope = self.get_dropbox_files(folder_path=norm_dbx_folder_path, recursive=True)
        if not files_in_scope:
            self.logger.warning(f"No files found in Dropbox folder '{norm_dbx_folder_path}'. Nothing to archive.")
            return True 
        
        for i in range(2): 
            self.logger.info(f"Attempting #{i} to download {len(files_in_scope)} files for '{norm_dbx_folder_path}'...")
            download_process_ok = self._process_file_downloads_for_list(
                files_to_consider=files_in_scope,
                scope_description=f"Targeted folder '{norm_dbx_folder_path}'",
                delay_between_files=delay_between_files
            )

            if not download_process_ok:
                self.logger.error(f"Download process for '{norm_dbx_folder_path}' was interrupted. Archival aborted.")
                return False

        self.logger.info(f"Verifying local files for '{norm_dbx_folder_path}' before archiving...")
        all_files_verified = True
        verified_files_for_archive = [] 
        local_target_dir_path = self.local_download_dir / norm_dbx_folder_path.lstrip('/')

        if not local_target_dir_path.is_dir(): # Check if the base local directory was even created
            self.logger.error(f"Local target directory '{local_target_dir_path}' does not exist. Cannot archive.")
            all_files_verified = False
        
        if all_files_verified:
            for file_info_meta in files_in_scope:
                dbx_path = file_info_meta['path']
                state_info = self.download_state['files'].get(dbx_path, {})
                local_path_from_state_str = state_info.get('local_path')

                if not (state_info.get('status') == 'downloaded' and local_path_from_state_str):
                    self.logger.error(f"File {dbx_path} not in 'downloaded' state. Archival aborted.")
                    all_files_verified = False; break
                
                local_file_to_check = Path(local_path_from_state_str)
                try: # Ensure file is within the target directory being archived
                    local_file_to_check.relative_to(local_target_dir_path.resolve())
                except ValueError:
                    self.logger.error(f"File {local_file_to_check} (for {dbx_path}) is not within target dir '{local_target_dir_path}'. Archival aborted.")
                    all_files_verified = False; break

                if not (local_file_to_check.exists() and local_file_to_check.is_file() and 
                        local_file_to_check.stat().st_size == file_info_meta['size']):
                    err_size = local_file_to_check.stat().st_size if local_file_to_check.exists() else 'N/A'
                    self.logger.error(f"Local file check failed for {dbx_path} (Path: {local_file_to_check}, Size: {err_size}, Expected: {file_info_meta['size']}). Archival aborted.")
                    all_files_verified = False; break
                verified_files_for_archive.append({'dropbox_path': dbx_path}) # Only need dbx_path for state update

        if not all_files_verified:
            self.logger.error(f"File verification failed for '{norm_dbx_folder_path}'. Archival aborted.")
            return False
        
        if not verified_files_for_archive and files_in_scope: # files_in_scope was not empty, but verification found none
             self.logger.error(f"No files were verified for archive in '{norm_dbx_folder_path}', though files were expected. Archival aborted.")
             return False
        elif not files_in_scope: # No files to begin with
             self.logger.info(f"No files were found in '{norm_dbx_folder_path}' to archive.")
             return True


        archive_path = local_target_dir_path.with_suffix('.tar.gz')
        self.logger.info(f"Compressing '{local_target_dir_path}' to '{archive_path}'...")
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(local_target_dir_path, arcname=local_target_dir_path.name)
            self.logger.info(f"Successfully compressed to '{archive_path}'. Size: {self._format_size(archive_path.stat().st_size)}")
        except Exception as e:
            self.logger.error(f"Failed to compress '{local_target_dir_path}': {e}")
            if archive_path.exists(): archive_path.unlink(missing_ok=True)
            return False

        self.logger.info(f"Cleaning up original directory '{local_target_dir_path}'...")
        try:
            shutil.rmtree(local_target_dir_path)
            self.logger.info(f"Successfully cleaned up '{local_target_dir_path}'.")
        except Exception as e:
            self.logger.error(f"Failed to clean up directory '{local_target_dir_path}': {e}. Please clean up manually.")

        self.logger.info(f"Updating state for archived files from '{norm_dbx_folder_path}'...")
        for file_to_update in files_in_scope: # Update state for all files that were part of this scope
            self._update_file_state(file_to_update['path'], 'archived',
                                   archived_path=str(archive_path.resolve()),
                                   archived_time=datetime.now().isoformat())
        self._save_state()

        self.logger.info(f"--- TARGETED processing for Dropbox folder: {norm_dbx_folder_path} COMPLETED (Archived & Cleaned) ---")
        return True

    def show_status(self):
        print("\n" + "="*60 + "\n📊 Download Status Report\n" + "="*60)
        status_count = {}; total_files = 0; total_size = 0
        for f_info in self.download_state.get('files', {}).values():
            total_files +=1; status = f_info.get('status', 'unknown')
            status_count[status] = status_count.get(status, 0) + 1
            total_size += f_info.get('size', 0)
        print(f"Total files in state: {total_files}, Total size (from state): {self._format_size(total_size)}")
        print("\nStatus Distribution:")
        status_map = {'downloaded': 'Downloaded (Pending Transfer)', 'transferred': 'Transferred (Cleared)',
                      'downloading': 'Downloading', 'download_failed': 'Download Failed',
                      'missing_local': 'Missing Locally', 'archived': 'Archived and Cleared', # Added
                      'unknown': 'Unknown'}
        for status, count in status_count.items():
            print(f"  {status_map.get(status, status.capitalize())}: {count} files")
        local_size = self._get_local_downloaded_size()
        print(f"\nLocal Files Pending Transfer (Actual Size): {self._format_size(local_size)}")
        print(f"Batch Size Limit: {self._format_size(self.batch_size_bytes)}")
        if local_size >= self.batch_size_bytes: print("⚠️  Batch limit reached. Transfer recommended.")
        print("="*60)

    def retry_failed(self):
        failed_files_paths = []
        for path, state in self.download_state.get('files',{}).items():
            if state.get('status') == 'download_failed':
                failed_files_paths.append(path)
        if not failed_files_paths: self.logger.info("No failed files to retry."); return
        self.logger.info(f"Retrying {len(failed_files_paths)} failed files.")
        files_to_retry_metadata = []
        for dpbx_path in failed_files_paths:
            try:
                meta = self.dbx.files_get_metadata(dpbx_path)
                if isinstance(meta, dropbox.files.FileMetadata):
                    files_to_retry_metadata.append({'path': meta.path_lower, 'name': meta.name, 'size': meta.size,
                                                    'modified': meta.server_modified.isoformat(), 'content_hash': meta.content_hash})
            except ApiError as e: self.logger.error(f"Metadata failed for {dpbx_path}: {e}")
        if files_to_retry_metadata:
            self._process_file_downloads_for_list(files_to_retry_metadata, "retrying failed files", 1.0)
        else: self.logger.info("No valid previously failed files to retry.")

    def _print_stats(self):
        current_local_size = self._get_local_downloaded_size() 
        self.logger.info(f"{'='*50}\nDownload Statistics (Current Run):\n"
                         f"  Files in current scope (approx): {self.stats.get('total_files_in_current_scope', 'N/A')}\n"
                         f"  Downloaded in this run: {self.stats['downloaded_in_run']}\n"
                         f"  Failed in this run: {self.stats['failed_in_run']}\n"
                         f"  Files cleared (transferred) in this run: {self.stats['transferred_in_run']}\n"
                         f"{'-'*50}\nOverall Local State:\n"
                         f"  Current local files (pending transfer): {self._format_size(current_local_size)}\n"
                         f"  Batch size limit: {self._format_size(self.batch_size_bytes)}\n{'='*50}")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
                        handlers=[logging.FileHandler('dropbox_downloader.log', encoding='utf-8'), logging.StreamHandler()])
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Dropbox Batch Downloader with optional targeted folder archival.")
    parser.add_argument("-d", "--directory", type=str, default=None,
                        help="Specific Dropbox directory to download, then compress and clean up (e.g., 'batch_1b/5000' or '/batch_1b/5000').")
    args = parser.parse_args()

    CONFIG_FILE_PATH = "config.yaml"
    config = load_config(CONFIG_FILE_PATH)
    
    # Configuration loading with fallbacks
    if config is None: # Major config load failure
        logger.critical(f"Critical: Could not load config from '{CONFIG_FILE_PATH}'. Attempting to get token via input.")
        DROPBOX_ACCESS_TOKEN = input("Enter Dropbox Access Token: ").strip()
        if not DROPBOX_ACCESS_TOKEN: logger.critical("No token provided. Exiting."); return
        LOCAL_DOWNLOAD_DIR, DROPBOX_FOLDER, BATCH_SIZE_GB, DELAY_BETWEEN_FILES = "./downloads_fb", "", 50.0, 0.5
        logger.warning("Using fallback default settings.")
    else:
        DROPBOX_ACCESS_TOKEN = config.get('DROPBOX_ACCESS_TOKEN')
        if not DROPBOX_ACCESS_TOKEN:
            logger.critical(f"'DROPBOX_ACCESS_TOKEN' missing in '{CONFIG_FILE_PATH}'. Please provide it.")
            DROPBOX_ACCESS_TOKEN = input("Enter Dropbox Access Token: ").strip()
            if not DROPBOX_ACCESS_TOKEN: logger.critical("No token provided. Exiting."); return
        LOCAL_DOWNLOAD_DIR = config.get('LOCAL_DOWNLOAD_DIR', "./downloads")
        DROPBOX_FOLDER = config.get('DROPBOX_FOLDER', "") # For normal mode
        try:
            BATCH_SIZE_GB = float(config.get('BATCH_SIZE_GB', 50.0))
            DELAY_BETWEEN_FILES = float(config.get('DELAY_BETWEEN_FILES', 0.5))
        except ValueError:
            logger.error("Invalid numeric BATCH_SIZE_GB or DELAY_BETWEEN_FILES. Using defaults.")
            BATCH_SIZE_GB, DELAY_BETWEEN_FILES = 50.0, 0.5

    downloader = DropboxBatchDownloader(
        access_token=DROPBOX_ACCESS_TOKEN, local_download_dir=LOCAL_DOWNLOAD_DIR,
        batch_size_gb=BATCH_SIZE_GB, config_path=CONFIG_FILE_PATH
    )
    
    try:
        logger.info(f"🚀 Dropbox Downloader Starting. Target Dropbox Folder for normal sync: '{DROPBOX_FOLDER or 'Root'}'")
        logger.info(f"💾 Local Download Dir: {Path(LOCAL_DOWNLOAD_DIR).resolve()}")
        logger.info(f"📦 Batch Size: {BATCH_SIZE_GB}GB (Initial)")
        downloader.show_status()

        if args.directory:
            target_dbx_path = args.directory
            logger.info(f"🎯 TARGETED MODE: Processing specific Dropbox folder for archival: '{target_dbx_path}'")
            downloader.process_specific_folder_and_archive(
                dropbox_folder_path=target_dbx_path,
                delay_between_files=DELAY_BETWEEN_FILES
            )
        else:
            logger.info(f"🔄 NORMAL MODE: Running sync by directory structure from '{DROPBOX_FOLDER or 'Dropbox Root'}'")
            downloader.sync_by_directory_structure(
                root_dropbox_path=DROPBOX_FOLDER,
                delay_between_files=DELAY_BETWEEN_FILES
            )
        
        logger.info("\n🎉 Task finished (or paused/interrupted).")
        downloader._print_stats()
        downloader.show_status()
        
    except KeyboardInterrupt:
        downloader.logger.info("User interrupted process.")
        print("\n🛑 Interrupted by user. Run again to resume.")
    except AuthError as e:
        downloader.logger.critical(f"Auth error: {e}", exc_info=True)
        print(f"\n❌ Authentication Error: {e}")
    except ApiError as e:
        downloader.logger.critical(f"API error: {e}", exc_info=True)
        print(f"\n❌ API Error: {e}")
    except Exception as e:
        downloader.logger.critical(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
