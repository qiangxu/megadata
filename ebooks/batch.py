#!/usr/bin/env python
# CREATED DATE: Sun Jan 26 23:53:23 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com

import os
from pathlib import Path
import shutil
import glob

def rename_pdfs(src_dir='/Users/qiangxu/Downloads/batch_2', dst_dir="../../batch_2b"):
    counter = 2357
    for file in sorted(glob.glob(f"{src_dir}/**/*.pdf", recursive=True)):
        if file.lower().endswith('.pdf'):
            try:
                counter_set = int((counter // 500 + 1) * 500)
                file_path = Path(file)
                print(counter, file)
                
                # Create new filename with zero-padded counter
                file_basename = os.path.basename(file)
                new_filename = f"{dst_dir}/{counter_set:05d}/{counter:05d}_{file_basename}"
                new_file_path = Path(".") / new_filename 
                Path(f"{dst_dir}/{counter_set:05d}").mkdir(parents=True, exist_ok=True) 
                # Copy the file with new name
                shutil.copy2(file_path, new_file_path)
            except Exception as e: 
                breakpoint()
                pass
            counter += 1

# Run the function
rename_pdfs()
