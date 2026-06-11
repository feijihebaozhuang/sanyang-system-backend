# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re

# 原.xlsx 列8是 pid
source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'
df = pd.read_excel(source, skiprows=2, dtype=str)
print(f'shape: {len(df)}')

# 取第一行数据的 pid（列8）
pid_val = str(df.iloc[0, 8]).strip()
spec_val = str(df.iloc[0, 5]).strip()
print(f'第一行 pid(列8): {pid_val}')
print(f'第一行 规格(列5): {spec_val}')

# 对比 原始商品所有格式.txt 里的 pid
with open(r'D:\Desktop\原始商品所有格式.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if pid_val in line:
            print(f'原始商品所有格式.txt 匹配行: {line.strip()[:100]}')
            break
