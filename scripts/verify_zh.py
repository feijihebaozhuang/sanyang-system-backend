# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd

f = r'D:\Desktop\换绑输出\无匹配_待处理.xlsx'
df = pd.read_excel(f)
mask = df['尝试解析'].notna() & (df['尝试解析'] != '')
samples = df[mask][['店铺简称', '规格名称', '尝试解析', '标记']].drop_duplicates(subset='尝试解析').head(15)

print('=== 解析样本验证 ===')
for _, r in samples.iterrows():
    print(f'  规格: {r["规格名称"][:50]}')
    print(f'  解析: {r["尝试解析"]}')
    print(f'  标记: {r["标记"]}')
    print()

# 统计解析类型
from collections import Counter
types = Counter()
for v in df[mask]['尝试解析']:
    parts = str(v).split('-')
    if len(parts) >= 2:
        types[parts[1]] += 1
print('=== 解析类型分布 ===')
for k, v in types.most_common():
    print(f'  {k}: {v}')
