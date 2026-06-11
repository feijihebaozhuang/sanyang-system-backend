# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

source = r'D:\Desktop\平台和快麦原始商品\原.xlsx'

# 用 pandas 读取，跳过前2行
print('用pandas读取...')
df = pd.read_excel(source, skiprows=2, dtype=str)
print(f'shape: {df.shape}')
print(f'列名: {list(df.columns)[:10]}')
print(f'前3行:')
for i in range(min(3, len(df))):
    row = df.iloc[i]
    print(f'  {list(row.values)[:10]}')
