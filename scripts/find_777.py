# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

source = r'D:\Desktop\未识别飞机盒_待分析.xlsx'
df = pd.read_excel(source, dtype=str, header=None)
data = df.iloc[1:].copy()
data.columns = ['店铺名称', '平台商品id', '平台规格名称', '平台规格id']

pid = '777723063661'
rows = data[data['平台商品id'].str.strip() == pid]
print(f'PID {pid}: {len(rows)} 条')
for _, r in rows.iterrows():
    print(f'  店铺: {r["店铺名称"]}')
    print(f'  规格: {r["平台规格名称"]}')
    print(f'  规格id: {r["平台规格id"]}')
    print()
