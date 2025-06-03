
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dropbox Batch Download Script
Python script for batch downloading Dropbox files, supporting manual transfer control,
directory-by-directory processing, and configuration via a YAML file.
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
import yaml # Added for YAML configuration

# Default configuration path, can be overridden
DEFAULT_CONFIG_PATH = "config.yaml"

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Optional[Dict]:
    """Loads configuration from a YAML file."""
    logger = logging.getLogger(__name__) # Gets a logger (assuming basicConfig is called in main)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None: # Handles empty or invalid YAML file that parses to None
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
                 config_path: str = DEFAULT_CONFIG_PATH): # Added config_path
        
        # Setup logger first so other init steps can use it
        self._setup_logging() 

        self.current_access_token = access_token # Store the initial token
        self.dbx = dropbox.Dropbox(access_token)
        self.config_path = config_path # Store config path for reloading
        self.local_download_dir = Path(local_download_dir)
        self.state_file = Path(state_file)
        self.batch_size_bytes = int(batch_size_gb * 1024 * 1024 * 1024)
        
        self.local_download_dir.mkdir(parents=True, exist_ok=True)
        
        self.download_state = self._load_state()
        
        self.stats = {
            'total_files_in_current_scope': 0,
            'downloaded_in_run': 0,
            'transferred_in_run': 0,
            'failed_in_run': 0,
        }
    
    def _setup_logging(self):
        """Configures logging for this class instance."""
        # Basic config should be done in main. Here we just get the logger.
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _reload_config_and_update_settings(self):
        """Reloads configuration from the YAML file and updates relevant settings."""
        self.logger.info(f"Attempting to reload configuration from '{self.config_path}'...")
        config = load_config(self.config_path) # Use the global load_config function

        if config is None:
            self.logger.error("Failed to reload configuration. Continuing with existing settings.")
            return

        # Update Access Token if changed
        new_access_token = config.get('DROPBOX_ACCESS_TOKEN')
        if new_access_token and new_access_token != self.current_access_token:
            self.logger.info("Dropbox access token has changed in the config file. Re-initializing Dropbox client.")
            try:
                self.dbx = dropbox.Dropbox(new_access_token) # Re-initialize client
                self.current_access_token = new_access_token # Update stored token
                self.logger.info("Dropbox client re-initialized with new access token.")
            except Exception as e:
                self.logger.error(f"Failed to re-initialize Dropbox client with new token: {e}. Continuing with the old client.")
        elif not new_access_token:
            self.logger.warning("'DROPBOX_ACCESS_TOKEN' not found or empty in reloaded config. Token not updated.")

        # Update Batch Size if changed (example of another updatable parameter)
        new_batch_size_gb_str = config.get('BATCH_SIZE_GB')
        if new_batch_size_gb_str is not None:
            try:
                new_batch_size_gb = float(new_batch_size_gb_str)
                new_batch_size_bytes = int(new_batch_size_gb * 1024 * 1024 * 1024)
                if new_batch_size_bytes != self.batch_size_bytes:
                    old_size_formatted = self._format_size(self.batch_size_bytes)
                    new_size_formatted = self._format_size(new_batch_size_bytes)
                    self.logger.info(f"Batch size changed from {old_size_formatted} to {new_size_formatted}.")
                    self.batch_size_bytes = new_batch_size_bytes
            except ValueError:
                self.logger.error(f"Invalid 'BATCH_SIZE_GB' value ('{new_batch_size_gb_str}') in reloaded config. Batch size not updated.")
        
        self.logger.info("Configuration reload attempt finished.")

    def _load_state(self) -> Dict:
        """Loads download state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    if 'files' not in state: state['files'] = {}
                    if 'processed_top_level_items_for_sync' not in state:
                        state['processed_top_level_items_for_sync'] = []
                    if 'last_update' not in state:
                        state['last_update'] = datetime.now().isoformat()
                    return state
            except Exception as e:
                self.logger.warning(f"Could not load state file: {e}")
        return {
            'files': {},
            'processed_top_level_items_for_sync': [],
            'last_update': datetime.now().isoformat()
        }
    
    def _save_state(self):
        """Saves download state."""
        try:
            self.download_state['last_update'] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.download_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state file: {e}")
    
    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculates MD5 hash of a file."""
        if not file_path.is_file():
            self.logger.warning(f"Cannot calculate hash, file not found or not a file: {file_path}")
            return None
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating hash for {file_path}: {e}")
            return None

    def _format_size(self, size_bytes: int) -> str:
        """Formats file size for display."""
        if size_bytes is None: size_bytes = 0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def _get_local_downloaded_size(self) -> int:
        """Calculates total size of locally downloaded but not yet transferred files."""
        total_size = 0
        if not self.local_download_dir.exists():
            return 0
        
        for file_path_str, file_info in self.download_state.get('files', {}).items():
            if file_info.get('status') == 'downloaded':
                local_path_str = file_info.get('local_path')
                local_file = Path(local_path_str) if local_path_str else (self.local_download_dir / file_path_str.lstrip('/'))
                
                if local_file.exists() and local_file.is_file():
                    try:
                        total_size += local_file.stat().st_size
                    except FileNotFoundError:
                         self.logger.warning(f"State indicates file exists, but not found locally: {local_file}")
        return total_size
    
    def _update_file_state(self, dropbox_path: str, status: str, **kwargs):
        """Updates download state for a file."""
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
    
    def get_dropbox_files(self, folder_path: str = "", recursive: bool = True) -> List[Dict]:
        """Gets Dropbox file list."""
        files = []
        try:
            self.logger.info(f"Scanning Dropbox folder: '{folder_path or 'Root directory'}' (Recursive: {recursive})")
            result = self.dbx.files_list_folder(folder_path, recursive=recursive)
            while True:
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        files.append({
                            'path': entry.path_lower,
                            'name': entry.name,
                            'size': entry.size,
                            'modified': entry.server_modified.isoformat(),
                            'content_hash': entry.content_hash
                        })
                if not result.has_more:
                    break
                result = self.dbx.files_list_folder_continue(result.cursor)
        except ApiError as e:
            self.logger.error(f"Failed to get Dropbox file list for '{folder_path}': {e}")
            return []
        self.logger.info(f"Found {len(files)} files in '{folder_path or 'Root'}' (Recursive: {recursive}).")
        self.stats['total_files_in_current_scope'] = len(files)
        return files
    
    def download_file(self, dropbox_path: str, local_path: Path, file_size: int) -> bool:
        """Downloads a single file."""
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'wb') as f:
                metadata, response = self.dbx.files_download(path=dropbox_path)
                f.write(response.content)
            if local_path.stat().st_size != file_size:
                self.logger.error(f"File size mismatch for {dropbox_path}: Expected {file_size}, Got {local_path.stat().st_size}")
                local_path.unlink(missing_ok=True)
                return False
            return True
        except ApiError as e:
            self.logger.error(f"Download failed for {dropbox_path}: {e}")
            if local_path.exists(): local_path.unlink(missing_ok=True)
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during download of {dropbox_path}: {e}")
            if local_path.exists(): local_path.unlink(missing_ok=True)
            return False
    
    def check_batch_limit(self, check_if_any_downloaded: bool = False) -> Tuple[bool, int]:
        """Checks if batch size limit is reached."""
        current_size = self._get_local_downloaded_size()
        if check_if_any_downloaded:
            return current_size > 0, current_size
        return current_size >= self.batch_size_bytes, current_size
    
    def prompt_transfer(self, current_size: int, current_scope_description: Optional[str] = None, is_final_transfer: bool = False) -> bool:
        """Prompts user for transfer operation. Config is reloaded after this returns."""
        print("\n" + "="*60)
        print("📦 Batch Download Paused for File Transfer!")
        if is_final_transfer:
            print("All scopes processed. This is a final check for any remaining files.")
        elif current_scope_description:
            print(f"Batch limit likely reached during processing of: {current_scope_description}")
        
        print(f"Currently downloaded (pending transfer): {self._format_size(current_size)}")
        print(f"Batch limit: {self._format_size(self.batch_size_bytes)}") # Uses current self.batch_size_bytes
        print("="*60)
        print("\nPlease transfer the downloaded files to your target location:")
        print(f"  Source directory: {self.local_download_dir.resolve()}")
        print("\nTransfer options:")
        print("  1. Copy to NAS/external hard drive")
        print("  2. Use other backup methods")
        print("  3. Manually organize files")
        print("\n⚠️  After completing the transfer, local files will be cleared to continue downloading.")
        
        user_response_positive = False
        while True:
            response = input("\nIs the transfer complete? (y/n/s) [y=yes, n=no, s=show status]: ").lower().strip()
            if response == 'y':
                user_response_positive = True
                break
            elif response == 'n':
                print("Please complete the file transfer before continuing...")
                user_response_positive = False
                break 
            elif response == 's':
                self._show_global_transfer_status()
                continue
            else:
                print("Please enter y, n, or s.")
        
        # Reload config AFTER user responds y/n, as requested.
        self._reload_config_and_update_settings()
        return user_response_positive

    def _show_global_transfer_status(self):
        """Displays current transfer status information."""
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
                        downloaded_files_list.append({
                            'path': file_path,
                            'size': fsize,
                            'local_path': str(local_file.resolve())
                        })
                        total_size_val += fsize
                    except FileNotFoundError:
                        pass
        if downloaded_files_list:
            print(f"Files pending transfer: {len(downloaded_files_list)}")
            print(f"Total size: {self._format_size(total_size_val)}")
            downloaded_files_list.sort(key=lambda x: x['path']) 
            print("\nRecently downloaded files (up to 10, sorted by path):")
            for i, file_item in enumerate(downloaded_files_list[-10:], 1):
                print(f"  {i:2d}. {file_item['path']} ({self._format_size(file_item['size'])})")
        else:
            print("No files are currently pending transfer.")
        print(f"Local download directory: {self.local_download_dir.resolve()}")

    def clear_transferred_files(self):
        """Clears files that were marked as 'downloaded'."""
        self.logger.info("Starting cleanup of transferred files...")
        cleared_count = 0
        cleared_size = 0
        for file_path, file_info in list(self.download_state.get('files', {}).items()):
            if file_info.get('status') == 'downloaded':
                local_path_str = file_info.get('local_path')
                local_file = Path(local_path_str) if local_path_str else (self.local_download_dir / file_path.lstrip('/'))
                if local_file.exists() and local_file.is_file():
                    try:
                        file_size_val = local_file.stat().st_size
                        #local_file.unlink()
                        cleared_count += 1
                        cleared_size += file_size_val
                        self._update_file_state(file_path, 'transferred', 
                                              transferred_time=datetime.now().isoformat())
                    except Exception as e:
                        self.logger.error(f"Failed to delete file {local_file}: {e}")
                else:
                    self.logger.warning(f"File {local_file} marked 'downloaded' but not found locally. Updating status to 'missing_local'.")
                    self._update_file_state(file_path, 'missing_local', missing_time=datetime.now().isoformat())
        #self._cleanup_empty_dirs(self.local_download_dir)
        self.logger.info(f"Cleanup complete: {cleared_count} files, freed {self._format_size(cleared_size)} space.")
        self.stats['transferred_in_run'] += cleared_count
        return cleared_count, cleared_size
    
    def _cleanup_empty_dirs(self, directory: Path):
        """Recursively cleans up empty directories."""
        if not directory.is_dir():
            return
        for item in directory.iterdir():
            if item.is_dir():
                self._cleanup_empty_dirs(item)
        try:
            if not any(directory.iterdir()):
                directory.rmdir()
                self.logger.info(f"Removed empty directory: {directory}")
        except OSError as e:
            self.logger.debug(f"Could not remove directory: {directory} - {e}")
        except Exception as e:
            self.logger.error(f"Error during empty directory cleanup for {directory}: {e}")

    def _get_top_level_entries(self, folder_path: str) -> Tuple[List[Dict], List[str]]:
        """Gets files directly under folder_path and paths of top-level subfolders."""
        direct_files_metadata = []
        top_level_folder_paths = []
        try:
            self.logger.info(f"Listing entries in Dropbox folder: '{folder_path or 'Root'}'")
            result = self.dbx.files_list_folder(folder_path, recursive=False)
            while True:
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        direct_files_metadata.append({
                            'path': entry.path_lower,
                            'name': entry.name,
                            'size': entry.size,
                            'modified': entry.server_modified.isoformat(),
                            'content_hash': entry.content_hash
                        })
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        top_level_folder_paths.append(entry.path_lower)
                if not result.has_more:
                    break
                result = self.dbx.files_list_folder_continue(result.cursor)
        except ApiError as e:
            self.logger.error(f"Failed to list entries in '{folder_path or 'Root'}': {e}")
        top_level_folder_paths.sort()
        direct_files_metadata.sort(key=lambda x: x['path'])
        self.logger.info(f"Found {len(direct_files_metadata)} direct files and {len(top_level_folder_paths)} top-level folders in '{folder_path or 'Root'}'.")
        return direct_files_metadata, top_level_folder_paths

    def _process_file_downloads_for_list(self, files_to_consider: List[Dict], scope_description: str, delay_between_files: float) -> bool:
        """
        Processes a given list of file metadata for download, applying batching logic
        and checking for pre-existing local files.
        Returns True if processing completed normally, False if user interrupted by not transferring.
        """
        self.logger.info(f"Starting to process {len(files_to_consider)} files for scope: {scope_description}")
        self.stats['total_files_in_current_scope'] = len(files_to_consider)
        pending_files = []
        for file_info in files_to_consider:
            file_path = file_info['path']
            file_state = self.download_state['files'].get(file_path, {})
            if file_state.get('status') not in ['downloaded', 'transferred']:
                pending_files.append(file_info)
        
        if not pending_files:
            self.logger.info(f"No pending files to download for scope: {scope_description}")
            return True

        self.logger.info(f"Found {len(pending_files)} pending files for download in scope: {scope_description}")
        pending_files.sort(key=lambda x: x['path']) # Sort by file path

        for i, file_info in enumerate(pending_files, 1):
            dropbox_path = file_info['path']
            local_path = self.local_download_dir / dropbox_path.lstrip('/')
            expected_size = file_info['size']
            
            self.logger.info(f"Handling file {i}/{len(pending_files)} in scope '{scope_description}': {file_info['name']} ({self._format_size(expected_size)}) Path: {dropbox_path}")

            # --- START: Check for existing local file ---
            if local_path.exists() and local_path.is_file():
                local_file_size = local_path.stat().st_size
                if local_file_size == expected_size:
                    self.logger.info(f"File '{dropbox_path}' already exists locally with correct size ({self._format_size(expected_size)}). Skipping download.")
                    file_hash_val = self._get_file_hash(local_path)
                    self._update_file_state(dropbox_path, 'downloaded',
                                          local_path=str(local_path.resolve()),
                                          file_hash=file_hash_val,
                                          size=expected_size, # Store size from Dropbox metadata
                                          modified=file_info['modified']) # Store modified date from Dropbox metadata
                    self.stats['downloaded_in_run'] += 1 # Count as successfully processed
                    if delay_between_files > 0: # Apply delay even if skipped, to be consistent
                        time.sleep(delay_between_files)
                    if i % 10 == 0 or i == len(pending_files):
                        self._print_stats()
                    continue # Move to the next file
                else:
                    self.logger.warning(f"File '{dropbox_path}' exists locally but with incorrect size. Local: {self._format_size(local_file_size)}, Dropbox: {self._format_size(expected_size)}. Proceeding to re-download.")
            # --- END: Check for existing local file ---

            needs_transfer, current_size = self.check_batch_limit()
            if needs_transfer:
                self.logger.info(f"Global batch limit reached ({self._format_size(current_size)}) during processing of scope '{scope_description}'.")
                if self.prompt_transfer(current_size, current_scope_description=scope_description): # prompt_transfer now reloads config
                    self.clear_transferred_files()
                else:
                    self.logger.info("User chose not to transfer. Download process for this scope will stop.")
                    return False 

            self._update_file_state(dropbox_path, 'downloading', 
                                  size=expected_size, # Pass size for 'downloading' state
                                  modified=file_info['modified']) # Pass modified for 'downloading' state
            
            if self.download_file(dropbox_path, local_path, expected_size):
                file_hash_val = self._get_file_hash(local_path)
                self._update_file_state(dropbox_path, 'downloaded',
                                      local_path=str(local_path.resolve()),
                                      file_hash=file_hash_val,
                                      size=expected_size, # Also store size on successful download state
                                      modified=file_info['modified']) # And modified date
                self.stats['downloaded_in_run'] += 1
                self.logger.info(f"✅ Download complete: {dropbox_path}")
            else:
                self._update_file_state(dropbox_path, 'download_failed') # Size/modified already stored from 'downloading'
                self.stats['failed_in_run'] += 1
                self.logger.error(f"❌ Download failed: {dropbox_path}")
            
            if delay_between_files > 0:
                time.sleep(delay_between_files)
            
            if i % 10 == 0 or i == len(pending_files):
                self._print_stats()
        
        self.logger.info(f"Finished processing file downloads for scope: {scope_description}")
        return True

    def sync_by_directory_structure(self, root_dropbox_path: str = "", delay_between_files: float = 1.0) -> bool:
        """Synchronizes files by first processing direct files, then each top-level folder."""
        self.logger.info(f"Starting sync by directory structure for Dropbox path: '{root_dropbox_path or 'Root'}'")
        STATE_KEY_PROCESSED_ITEMS = 'processed_top_level_items_for_sync'
        processed_items_list = self.download_state[STATE_KEY_PROCESSED_ITEMS]
        direct_files_metadata, top_level_folders = self._get_top_level_entries(root_dropbox_path)
        scopes_to_process = []
        root_files_scope_id = f"{root_dropbox_path or '#ROOT#'}#DIRECT_FILES#"
        if direct_files_metadata:
            scopes_to_process.append({
                'id': root_files_scope_id,
                'description': f"Direct files in '{root_dropbox_path or 'Root'}'",
                'files_list': direct_files_metadata,
                'is_folder_scope': False
            })
        for tlf_path in top_level_folders:
            scopes_to_process.append({
                'id': tlf_path,
                'description': f"Folder '{tlf_path}' and its contents",
                'dropbox_path_for_files': tlf_path,
                'is_folder_scope': True
            })
        if not scopes_to_process:
            self.logger.info(f"No direct files or top-level folders found to process under '{root_dropbox_path or 'Root'}'.")
            return True
        for scope in scopes_to_process:
            scope_id = scope['id']
            scope_desc = scope['description']
            if scope_id in processed_items_list:
                self.logger.info(f"Scope '{scope_desc}' (ID: {scope_id}) already processed. Skipping.")
                continue
            self.logger.info(f"--- Starting processing for scope: {scope_desc} ---")
            files_for_this_scope = []
            if scope['is_folder_scope']:
                files_for_this_scope = self.get_dropbox_files(folder_path=scope['dropbox_path_for_files'], recursive=True)
            else:
                files_for_this_scope = scope['files_list']
            if not files_for_this_scope:
                self.logger.info(f"No files found to process for scope '{scope_desc}'. Marking as processed.")
                processed_items_list.append(scope_id)
                self._save_state()
                continue
            completed_normally = self._process_file_downloads_for_list(
                files_to_consider=files_for_this_scope,
                scope_description=scope_desc,
                delay_between_files=delay_between_files
            )
            if not completed_normally:
                self.logger.info(f"Processing for scope '{scope_desc}' was interrupted by user. Overall sync will stop.")
                return False
            self.logger.info(f"--- Finished processing for scope: {scope_desc} ---")
            processed_items_list.append(scope_id)
            self._save_state()
            self.logger.info(f"Scope '{scope_desc}' (ID: {scope_id}) marked as fully processed for this iteration.")
        needs_final_transfer, final_size = self.check_batch_limit(check_if_any_downloaded=True)
        if needs_final_transfer and final_size > 0:
            self.logger.info("All scopes processed. Final check for any remaining downloaded files pending transfer.")
            # Prompt_transfer now reloads config internally AFTER user response
            if self.prompt_transfer(final_size, is_final_transfer=True, current_scope_description="Overall completion"):
                self.clear_transferred_files()
        self.logger.info("Sync by directory structure finished successfully.")
        return True

    def sync_batch(self, folder_path: str = "", delay_between_files: float = 1.0) -> bool:
        """Original sync_batch functionality: processes a given Dropbox folder recursively."""
        self.logger.info(f"Starting sync_batch for Dropbox folder: '{folder_path or 'Root'}' (recursive by default)")
        needs_transfer, current_size = self.check_batch_limit()
        if needs_transfer:
            self.logger.info(f"Initial local file size for sync_batch: {self._format_size(current_size)}")
            # Prompt_transfer now reloads config internally AFTER user response
            if self.prompt_transfer(current_size, current_scope_description=f"folder '{folder_path or 'Root'}' (initial check)"):
                self.clear_transferred_files()
            else:
                self.logger.info("User chose not to transfer yet during initial check. Stopping sync_batch.")
                return False
        all_files_in_scope = self.get_dropbox_files(folder_path=folder_path, recursive=True)
        if not all_files_in_scope:
            self.logger.warning(f"No files found in '{folder_path or 'Root'}' to download for sync_batch.")
            return True 
        scope_desc_for_batch = f"folder '{folder_path or 'Root'}' (recursive sync_batch)"
        process_result = self._process_file_downloads_for_list(
            files_to_consider=all_files_in_scope,
            scope_description=scope_desc_for_batch,
            delay_between_files=delay_between_files
        )
        if not process_result:
            return False
        needs_transfer, current_size = self.check_batch_limit(check_if_any_downloaded=True)
        if needs_transfer and current_size > 0:
            self.logger.info(f"sync_batch for '{folder_path or 'Root'}' completed. Final check for downloaded files.")
            # Prompt_transfer now reloads config internally AFTER user response
            if self.prompt_transfer(current_size, is_final_transfer=True, current_scope_description=f"folder '{folder_path or 'Root'}' (final check)"):
                self.clear_transferred_files()
        self.logger.info(f"sync_batch for '{folder_path or 'Root'}' finished.")
        return True
    
    def _print_stats(self):
        """Prints download statistics."""
        current_local_size = self._get_local_downloaded_size() 
        self.logger.info("=" * 50)
        self.logger.info("Download Statistics (Current Run):")
        self.logger.info(f"  Files in current scope (approx): {self.stats.get('total_files_in_current_scope', 'N/A')}")
        self.logger.info(f"  Downloaded in this run: {self.stats['downloaded_in_run']}")
        self.logger.info(f"  Failed in this run: {self.stats['failed_in_run']}")
        self.logger.info(f"  Files cleared (transferred) in this run: {self.stats['transferred_in_run']}")
        self.logger.info("-" * 50)
        self.logger.info("Overall Local State:")
        self.logger.info(f"  Current local files (pending transfer): {self._format_size(current_local_size)}")
        self.logger.info(f"  Batch size limit: {self._format_size(self.batch_size_bytes)}")
        self.logger.info("=" * 50)
    
    def retry_failed(self):
        """Retries failed downloads."""
        failed_files_paths = []
        for path, state in self.download_state.get('files',{}).items():
            if state.get('status') == 'download_failed':
                failed_files_paths.append(path)
        if not failed_files_paths:
            self.logger.info("No failed files to retry.")
            return
        self.logger.info(f"Retrying {len(failed_files_paths)} failed files.")
        files_to_retry_metadata = []
        for dropbox_path in failed_files_paths:
            try:
                metadata = self.dbx.files_get_metadata(dropbox_path)
                if isinstance(metadata, dropbox.files.FileMetadata):
                    files_to_retry_metadata.append({
                        'path': metadata.path_lower, 'name': metadata.name, 'size': metadata.size,
                        'modified': metadata.server_modified.isoformat(), 'content_hash': metadata.content_hash
                    })
                else:
                    self.logger.warning(f"Path {dropbox_path} is not a file, cannot retry.")
            except ApiError as e:
                self.logger.error(f"Failed to get metadata for retrying {dropbox_path}: {e}")
        if files_to_retry_metadata:
            self.logger.info(f"Attempting to download {len(files_to_retry_metadata)} previously failed files.")
            self._process_file_downloads_for_list(
                files_to_consider=files_to_retry_metadata,
                scope_description="retrying failed files",
                delay_between_files=1.0
            )
        else:
            self.logger.info("No valid previously failed files found to retry after fetching metadata.")

    def show_status(self):
        """Displays detailed status report."""
        print("\n" + "="*60)
        print("📊 Download Status Report")
        print("="*60)
        status_count = {}
        total_file_count_in_state = 0
        total_size_in_state = 0
        for file_info in self.download_state.get('files', {}).values():
            total_file_count_in_state +=1
            status = file_info.get('status', 'unknown')
            status_count[status] = status_count.get(status, 0) + 1
            total_size_in_state += file_info.get('size', 0)
        print(f"Total files tracked in state: {total_file_count_in_state}")
        print(f"Total size (from state info): {self._format_size(total_size_in_state)}")
        print("\nStatus Distribution:")
        for status, count in status_count.items():
            status_name = {'downloaded': 'Downloaded (Pending Transfer)', 'transferred': 'Transferred (Cleared Locally)', 
                           'downloading': 'Downloading (In Progress)', 'download_failed': 'Download Failed',
                           'missing_local': 'Missing Locally (Expected Downloaded)', 'unknown': 'Unknown'}.get(status, status.capitalize())
            print(f"  {status_name}: {count} files")
        current_local_size_val = self._get_local_downloaded_size()
        print(f"\nLocal Files Pending Transfer (Actual Size): {self._format_size(current_local_size_val)}")
        print(f"Batch Size Limit: {self._format_size(self.batch_size_bytes)}")
        if current_local_size_val >= self.batch_size_bytes:
            print("⚠️  Batch limit reached or exceeded. Transferring files is recommended.")
        print("="*60)

def main():
    """Main function."""
    # Setup basic logging as early as possible for the entire application
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
        handlers=[
            logging.FileHandler('dropbox_downloader.log', encoding='utf-8'), # Consolidated log file
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__) # Logger for main function

    CONFIG_FILE_PATH = "config.yaml"
    config = load_config(CONFIG_FILE_PATH)

    if config is None:
        logger.critical(f"Critical error: Could not load configuration from '{CONFIG_FILE_PATH}'. Please ensure it exists and is valid.")
        # Fallback to asking for token if config fails badly, or just exit
        DROPBOX_ACCESS_TOKEN = input("Could not load config. Please enter your Dropbox Access Token: ").strip()
        if not DROPBOX_ACCESS_TOKEN:
            logger.critical("No access token provided. Exiting.")
            return
        # Use defaults for other params if config fails
        LOCAL_DOWNLOAD_DIR = "./downloads_fallback"
        DROPBOX_FOLDER = ""
        BATCH_SIZE_GB = 50.0
        DELAY_BETWEEN_FILES = 0.5
        logger.warning("Using fallback default settings as config loading failed.")
    else:
        DROPBOX_ACCESS_TOKEN = config.get('DROPBOX_ACCESS_TOKEN')
        if not DROPBOX_ACCESS_TOKEN:
            logger.critical(f"Critical error: 'DROPBOX_ACCESS_TOKEN' not found or empty in '{CONFIG_FILE_PATH}'.")
            # Optionally, ask for token here as well
            DROPBOX_ACCESS_TOKEN = input(f"'DROPBOX_ACCESS_TOKEN' not in {CONFIG_FILE_PATH}. Please enter token: ").strip()
            if not DROPBOX_ACCESS_TOKEN:
                logger.critical("No access token provided. Exiting.")
                return
        
        LOCAL_DOWNLOAD_DIR = config.get('LOCAL_DOWNLOAD_DIR', "./downloads")
        DROPBOX_FOLDER = config.get('DROPBOX_FOLDER', "")
        try:
            BATCH_SIZE_GB = float(config.get('BATCH_SIZE_GB', 50.0))
            DELAY_BETWEEN_FILES = float(config.get('DELAY_BETWEEN_FILES', 0.5))
        except ValueError:
            logger.error("Invalid numeric value for BATCH_SIZE_GB or DELAY_BETWEEN_FILES in config. Using defaults.")
            BATCH_SIZE_GB = 50.0
            DELAY_BETWEEN_FILES = 0.5

    downloader = DropboxBatchDownloader(
        access_token=DROPBOX_ACCESS_TOKEN,
        local_download_dir=LOCAL_DOWNLOAD_DIR,
        batch_size_gb=BATCH_SIZE_GB,
        config_path=CONFIG_FILE_PATH # Pass config path for reloading
    )
    
    try:
        logger.info("🚀 Dropbox Batch Downloader - Starting")
        logger.info(f"💾 Download Directory: {Path(LOCAL_DOWNLOAD_DIR).resolve()}")
        logger.info(f"📦 Batch Size: {BATCH_SIZE_GB}GB (Initial, may change if config reloaded)")
        logger.info(f"📁 Dropbox Path: '{DROPBOX_FOLDER}' (Empty means root)")
        logger.info("-" * 40)
        
        downloader.show_status()
        
        downloader.sync_by_directory_structure(
            root_dropbox_path=DROPBOX_FOLDER,
            delay_between_files=DELAY_BETWEEN_FILES # Initial delay, not dynamically reloaded by this script version
        )
        
        # logger.info("\nRetrying failed downloads if any...")
        # downloader.retry_failed()

        logger.info("\n🎉 Download task finished (or paused by user)!")
        downloader._print_stats()
        downloader.show_status()
        
    except KeyboardInterrupt:
        downloader.logger.info("User interrupted the download process.")
        print("\n🛑 Download interrupted by user. Run again to resume.")
    except AuthError as e:
        downloader.logger.critical(f"Dropbox authentication error: {e}", exc_info=True)
        print(f"\n❌ Authentication Error: Check your access token. Details: {e}")
    except ApiError as e:
        downloader.logger.critical(f"Dropbox API error: {e}", exc_info=True)
        print(f"\n❌ API Error: Dropbox API returned an error. Details: {e}")
    except Exception as e:
        downloader.logger.critical(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
