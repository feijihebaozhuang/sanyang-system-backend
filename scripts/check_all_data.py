# -*- coding: utf-8 -*-
"""全面检查所有数据是否完整"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl as oxl
import pandas as pd

out = r'd:\Desktop\换绑输出'
raw_file = r'd:\Desktop\平台商品.xlsx'

# 1. 原始数据中所有店铺
df = pd.read_excel(raw_file, sheet_name=0, dtype=str)
shop_col = None
for c in df.columns:
    if '店铺' in str(c):
        shop_col = c; break

if shop_col:
    all_shops = df[shop_col].astype(str).str.strip()
    shop_counts = all_shops.value_counts()
    print(f'原始数据总行数: {len(df)}')
    print(f'原始数据店铺分布:')
    for s, c in shop_counts.items():
        print(f'  [{c:>6}] {s}')
    
    # 平卡中的店铺
    wb = oxl.load_workbook(os.path.join(out, '平卡_待处理.xlsx'))
    ws = wb['平卡']
    pk_shops = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r and r[0]:
            s = str(r[0]).strip()
            pk_shops[s] = pk_shops.get(s, 0) + 1
    wb.close()
    
    print(f'\n平卡店铺分布:')
    for s, c in sorted(pk_shops.items(), key=lambda x: -x[1]):
        print(f'  [{c:>6}] {s}')
    
    # 哪些原始店铺不在平卡中
    raw_shop_set = set(s for s in shop_counts.index if s)
    pk_shop_set = set(pk_shops.keys())
    missing = raw_shop_set - pk_shop_set
    print(f'\n原始店铺数: {len(raw_shop_set)}')
    print(f'平卡店铺数: {len(pk_shop_set)}')
    print(f'不在平卡的店铺({len(missing)}):')
    for s in sorted(missing):
        cnt = shop_counts.get(s, 0)
        print(f'  {s} (原始{cnt}条)')
