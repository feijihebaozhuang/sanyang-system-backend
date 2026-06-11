# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

df = pd.read_excel(r'd:\Desktop\快麦商品.xlsx', header=None)
print('行数:', len(df))
print('列数:', df.shape[1])
print('\n前5行:')
for i in range(min(5, len(df))):
    print(f'  行{i}: {list(df.iloc[i])}')
print('\n---')
