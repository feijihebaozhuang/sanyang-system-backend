# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

# 查看扣底盒文件
f = r'D:\Desktop\扣底盒双插盒商品.xlsx'
df = pd.read_excel(f)
print(f'扣底盒: {len(df)} 行, 列: {list(df.columns)}')
print(f'前2行:')
print(df.head(2).to_string())

# 查找 777
mask = df['平台商品id'].astype(str).str.strip() == '777564404927'
if mask.any():
    print(f'\n找到 {mask.sum()} 条:')
    for _, r in df[mask].iterrows():
        print(f'  {r["规格名称"]}')
else:
    print('\n未找到 777564404927')

# 看其余商品文件
f2 = r'D:\Desktop\其余商品.xlsx'
try:
    df2 = pd.read_excel(f2)
    print(f'\n其余商品: {len(df2)} 行, 列: {list(df2.columns)}')
except Exception as e:
    print(f'\n其余商品读不了: {e}')
    # 试试不skiprows
    df2 = pd.read_excel(f2, engine='openpyxl')
    print(f'  用openpyxl: {df2.shape}, cols: {list(df2.columns)}')
