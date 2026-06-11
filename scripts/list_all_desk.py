# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

desk = r'D:\Desktop'
all_files = [f for f in os.listdir(desk) if f.endswith('.xlsx')]

# 按大小排序
file_info = []
for f in all_files:
    sz = os.path.getsize(os.path.join(desk, f))
    file_info.append((sz, f))

file_info.sort(reverse=True)
print('桌面xlsx文件:')
for sz, f in file_info:
    tag = ''
    try:
        df = pd.read_excel(os.path.join(desk, f), skiprows=1, dtype=str)
        tag = f' → {len(df)}行'
    except:
        try:
            df = pd.read_excel(os.path.join(desk, f), dtype=str)
            tag = f' → {len(df)}行'
        except:
            tag = ' ⚠️ 读不了'
    print(f'  {sz//1024:>6}KB  {f}{tag}')
