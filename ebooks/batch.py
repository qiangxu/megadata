#!/usr/bin/env python
# CREATED DATE: Sun Jan 26 23:53:23 2025
# CREATED BY: qiangxu, toxuqiang@gmail.com

import os
from pathlib import Path
import shutil

def rename_pdfs(src_dir='mountsmb/batch_1', dst_dir="batch_1b"):
    counter = 1
    for root, _, files in os.walk(src_dir):
        for file in sorted(files):
            if file.lower().endswith('.pdf'):
                if counter > 6725: 
                    try:
                        counter_set = int((counter // 500 + 1) * 500)
                        file_path = Path(root) / file
                        print(counter, file)
                        
                        # Create new filename with zero-padded counter
                        new_filename = f"{dst_dir}/{counter_set}/{counter:05d}_{file}"
                        new_file_path = Path(".") / new_filename 
                        Path(f"{dst_dir}/{counter_set}").mkdir(parents=True, exist_ok=True) 
                        # Copy the file with new name
                        shutil.copy2(file_path, new_file_path)
                    except Exception as e: 
                        breakpoint()
                counter += 1

# Run the function
rename_pdfs()
