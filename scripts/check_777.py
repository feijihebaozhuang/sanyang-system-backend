# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(f, header=1, dtype=str)

pids = ['777564404927']
for pid in pids:
    rows = df[df['平台商品id'].astype(str).str.strip() == pid]
    print(f'\n=== 商品id: {pid} ({len(rows)}条规格) ===')
    for _, r in rows.iterrows():
        spec = r['平台规格名称']
        shop = r['店铺名称']
        print(f'  店铺: {shop}')
        print(f'  规格: {spec}')
        print()
