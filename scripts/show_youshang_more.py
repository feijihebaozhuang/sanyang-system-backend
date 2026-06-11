# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pandas as pd
from collections import Counter

out = r'd:\Desktop\换绑输出'
df = pd.read_excel(out + r'\平卡_待处理.xlsx')
mask = df['店铺简称'].str.contains('友尚', na=False)
df2 = df[mask].copy()

# 特硬/超硬/白色 等材料关键词匹配到的到底是什么格式
cats = Counter()
def classify(s):
    if '优质牛卡' in s: return '优质牛卡'
    if '【内径尺寸】' in s: return '内径尺寸mm'
    if '【内径】' in s: return '内径直接'
    if '外尺寸 【长宽】' in s: return '外尺寸长宽'
    if '外尺寸' in s or '外径' in s: return '外尺寸'
    if '【长宽】' in s: return '纸箱MM'
    if re.search(r'-\d+个[\*x]', s): return '直接格式'
    if '长【' in s and '宽【' in s: return '长L宽W'
    if '长' in s and 'mm' in s and '宽高' in s: return 'mm宽高'
    return '未分类'

for _, row in df2.iterrows():
    s = str(row['规格名称'])
    cats[classify(s)] += 1

print('=== 完整分类 ===')
for k, v in cats.most_common():
    print(f'  {k}: {v}')

# 看看"未分类"的是啥
print('\n=== 未分类 抽样 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if classify(s) == '未分类' and s not in seen:
        seen.add(s)
        print(f'  {s}')
        if len(seen) >= 20:
            break

# 看看⑤纸箱MM更多样本（不同材料）
print('\n=== ⑤纸箱MM(【厘米高】)更多 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '【长宽】' in s and '外尺寸' not in s:
        if s not in seen:
            seen.add(s)
            print(f'  {s}')
            if len(seen) >= 10:
                break

# 看看⑥直接格式更多材料
print('\n=== ⑥直接格式更多 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if re.search(r'-\d+个[\*x]', s) and s not in seen:
        seen.add(s)
        print(f'  {s}')
        if len(seen) >= 10:
            break

# 看看④外尺寸更多材料
print('\n=== ④外尺寸(不含【长宽】)更多 ===')
seen = set()
for _, row in df2.iterrows():
    s = str(row['规格名称'])
    if '外尺寸' in s and '【长宽】' not in s and s not in seen:
        seen.add(s)
        print(f'  {s}')
        if len(seen) >= 10:
            break
