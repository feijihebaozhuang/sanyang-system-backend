# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
print(f'行数: {len(df)}')
print(f'列名: {list(df.columns)}')

shops = df['店铺简称'].value_counts().head(15)
print(f'\n店铺分布:')
for s, c in shops.items():
    print(f'  {s}: {c}')

print(f'\n前5条样例:')
for _, r in df.head(5).iterrows():
    spec = str(r.get('规格名称', ''))
    print(f'  店铺={r.get("店铺简称","")} | 规格={spec[:60]}')
