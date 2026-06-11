# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

km_file = r'd:\Desktop\快麦商品 - 副本.xlsx'
df = pd.read_excel(km_file, sheet_name='报表1', header=3, dtype=str, usecols=[0,1,2])

# 搜索30*30相关的
for row in df.values:
    code = str(row[0] or '').strip()
    name = str(row[1] or '').strip()
    cat = str(row[2] or '').strip()
    if '30*30' in code or '30*30' in name:
        print(f"{code:30s} | {name:40s} | {cat}")
