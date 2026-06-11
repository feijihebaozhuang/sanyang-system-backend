# -*- coding: utf-8 -*-
import sys, pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

km_file = r'd:\Desktop\快麦商品 - 副本.xlsx'
df = pd.read_excel(km_file, sheet_name='报表1', header=3, dtype=str, usecols=[0,1,2])

# 搜P6D相关
count = 0
for row in df.values:
    code = str(row[0] or '').strip()
    name = str(row[1] or '').strip()
    if 'P6D' in code or 'P6D' in name or '扣底盒' in code or '扣底盒' in name:
        if count < 20:
            print(f"{code:35s} | {name}")
        count += 1
print(f"\n共{count}条P6D/扣底盒")
