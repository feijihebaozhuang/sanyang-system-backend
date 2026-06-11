# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
import re
from collections import Counter

f = r'D:\Desktop\平台商品.xlsx'
df = pd.read_excel(f, header=1, dtype=str)

# 已经提取到的商品id
dot_file = r'D:\Desktop\长宽高含小数商品.xlsx'
df_dot = pd.read_excel(dot_file, skiprows=1, dtype=str)
dot5_file = r'D:\Desktop\长宽高三项全5商品.xlsx'
df_dot5 = pd.read_excel(dot5_file, skiprows=1, dtype=str)
int_file = r'D:\Desktop\长宽高为整数商品.xlsx'
df_int = pd.read_excel(int_file, skiprows=1, dtype=str)

extracted_ids = set()
for d in [df_dot, df_dot5, df_int]:
    if '平台商品id' in d.columns:
        for v in d['平台商品id'].dropna():
            extracted_ids.add(str(v).strip())

# 没提取到的
mask = ~df['平台商品id'].astype(str).isin(extracted_ids)
unrec = df[mask]
print(f'未提取到长宽高的商品: {len(unrec)} 条')

specs = unrec['平台规格名称'].dropna().astype(str).str.strip()
print(f'规格名称非空: {len(specs)} 条')

# 看前60字符的模式分布
prefixes = Counter()
for s in specs:
    p = s[:60]
    prefixes[p] += 1

print('\n=== 前30个模式（去重）===')
for p, cnt in prefixes.most_common(30):
    print(f'  [{cnt:>4}] {p}')

# 看店铺分布
shops = unrec['店铺名称'].dropna().astype(str).str.strip()
shop_counts = Counter(shops)
print('\n=== 店铺分布 ===')
for shop, cnt in shop_counts.most_common(20):
    print(f'  [{cnt:>4}] {shop}')
