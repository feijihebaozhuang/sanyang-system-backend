# -*- coding: utf-8 -*-
"""分析快麦商品编码结构"""
import sys, re, json
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd

df = pd.read_excel(r'd:\Desktop\快麦商品 - 副本.xlsx', sheet_name='报表1', header=3, dtype=str, usecols=[0,1,2])
df.columns = ['code', 'name', 'cat']
print(f"总条数: {len(df)}", flush=True)

# 分析编码结构
parts_counter = Counter()
dim_counter = Counter()
type_counter = Counter()
material_counter = Counter()
inner_outer_counter = Counter()
has_inner = 0
has_outer = 0
has_no_dk = 0

for _, row in df.iterrows():
    code = str(row['code'] or '').strip()
    if not code or code == 'nan':
        continue
    parts = code.split('-')
    n = len(parts)
    parts_counter[n] += 1
    
    if n >= 3:
        dims = parts[0]
        dk = parts[1]
        mat = parts[2]
        xtype = parts[3] if n >= 4 else ''
        
        dim_counter[len(dims.split('*'))] += 1
        
        if dk == '内径':
            inner_outer_counter['内径'] += 1
        elif dk == '外径':
            inner_outer_counter['外径'] += 1
        else:
            inner_outer_counter[f'其他({dk})'] += 1
        
        material_counter[mat] += 1
        if xtype:
            type_counter[xtype] += 1

print(f"\n=== 编码段数分布 ===", flush=True)
for k, v in sorted(parts_counter.items()):
    print(f"  {k}段: {v} ({v/len(df)*100:.1f}%)", flush=True)

print(f"\n=== 内外径分布 ===", flush=True)
for k, v in sorted(inner_outer_counter.items()):
    print(f"  {k}: {v}", flush=True)

print(f"\n=== 材料分布(TOP 20) ===", flush=True)
for k, v in material_counter.most_common(20):
    print(f"  {k}: {v}", flush=True)

print(f"\n=== 类型分布(有类型的) ===", flush=True)
for k, v in sorted(type_counter.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}", flush=True)

# 看一些外径/内径匹配的样本
print(f"\n=== 内径编码样本(看商品名关系) ===", flush=True)
inner_samples = df[df['code'].str.contains('内径', na=False)].head(10)
for _, r in inner_samples.iterrows():
    print(f"  {r['code']} | {str(r['name'] or '')[:50]}", flush=True)

print(f"\n=== 外径编码样本 ===", flush=True)
outer_samples = df[df['code'].str.contains('外径', na=False)].head(10)
for _, r in outer_samples.iterrows():
    print(f"  {r['code']} | {str(r['name'] or '')[:50]}", flush=True)
